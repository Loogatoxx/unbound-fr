"""Étape 1 : extraction et état des lieux du texte de la ROM.

Usage : python3 outils/extraire.py rom/unbound_original.gba

Produit :
  donnees/tables_en.json   noms à taille fixe (Pokémon, attaques, talents...)
  donnees/textes_en.json   toutes les chaînes trouvées par leurs pointeurs
  docs/etat_des_lieux.md   le bilan chiffré (volume de texte, espace libre)

Principe : un texte du jeu est une suite d'octets terminée par FF. Le jeu le
retrouve grâce à un pointeur, c'est-à-dire son adresse écrite sur 4 octets
(0x08000000 + position dans la ROM). On parcourt donc la ROM à la recherche
de tout ce qui ressemble à un pointeur, et on garde ceux qui mènent à du texte.
"""

import bisect
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from charmap import ChaineInvalide, decoder, encoder  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
BASE_ROM = 0x08000000

# Tables de noms à taille fixe : (nom, nom de l'entrée 1, nom de l'entrée 2,
# taille d'une entrée, taille max du nom, position du nom dans l'entrée, règle
# de fin de table). On les repère par leur contenu plutôt que par des adresses
# codées en dur, car Unbound a déplacé la plupart des tables.
# Règles de fin : "remplissage" = après le FF, que des 00/FF ;
# "objet" = la fiche objet a un pointeur de description et une poche valides ;
# "fiche" = la fiche dresseur a une taille d'équipe 1-6 et un pointeur valide.
TABLES = [
    ("pokemon", "Bulbasaur", "Ivysaur", 11, 11, 0, "remplissage"),
    ("attaques", "Pound", "Karate Chop", 13, 13, 0, "remplissage"),
    ("talents", "Stench", "Drizzle", 17, 17, 0, "remplissage"),
    ("objets", "Master Ball", "Ultra Ball", 44, 14, 0, "objet"),
    ("classes_dresseurs", "Youngster", "Bug Catcher", 13, 13, 0, "remplissage"),
    ("dresseurs", "Joey", "Kelly", 40, 12, 4, "fiche"),
]

# Caractères courants d'un texte anglais : sert à écarter les faux textes
# (octets aléatoires qui se décodent par hasard en « ÌÌÌ » ou « ÚÔpvÉ »).
COURANTS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
               " .,!?'’‘“”…-:;/()&+%é♂♀×¥")


def trouver_tout(rom, motif):
    positions, i = [], rom.find(motif)
    while i != -1:
        positions.append(i)
        i = rom.find(motif, i + 1)
    return positions


def pointeurs_vers(rom, adresse):
    """Positions de la ROM qui contiennent un pointeur vers `adresse`."""
    return trouver_tout(rom, (BASE_ROM + adresse).to_bytes(4, "little"))


def est_pointeur(rom, valeur):
    return BASE_ROM <= valeur < BASE_ROM + len(rom)


def lire_nom(rom, adresse, taille_nom):
    """Lit le nom d'une entrée de table.

    Deux cas : soit le nom est écrit directement (terminé par FF), soit ses
    4 premiers octets sont un pointeur vers un nom plus long rangé ailleurs.
    Ce second cas est une astuce du moteur CFRU d'Unbound pour dépasser la
    taille fixe (ex. « Silver Powder », 13 lettres, dans un champ de 14).
    Renvoie (texte, nb_octets, adresse_du_nom_long ou None).
    """
    valeur = int.from_bytes(rom[adresse:adresse + 4], "little")
    if est_pointeur(rom, valeur):
        try:
            texte, n, visibles, _ = decoder(rom, valeur - BASE_ROM, 64)
            if visibles:
                return texte, n, valeur - BASE_ROM
        except ChaineInvalide:
            pass
    texte, n, _, _ = decoder(rom, adresse, taille_nom)  # peut lever ChaineInvalide
    return texte, n, None


def entree_valide(rom, entree, index, taille_nom, decalage, regle):
    """Vérifie qu'une entrée appartient bien à la table (sinon : fin de table)."""
    if regle == "fiche":
        taille_equipe = int.from_bytes(rom[entree + 32:entree + 36], "little")
        ptr = int.from_bytes(rom[entree + 36:entree + 40], "little")
        return index == 0 or (1 <= taille_equipe <= 6 and est_pointeur(rom, ptr))
    try:
        _, n, long = lire_nom(rom, entree + decalage, taille_nom)
    except ChaineInvalide:
        return False
    if regle == "objet":  # fiche objet : pointeur de description + poche du sac
        description = int.from_bytes(rom[entree + 20:entree + 24], "little")
        return est_pointeur(rom, description) and rom[entree + 26] <= 10
    # "remplissage" : après le FF, rien que des 00/FF (sauf nom long par pointeur)
    return long is not None or all(
        o in (0x00, 0xFF) for o in rom[entree + decalage + n:entree + decalage + taille_nom])


def extraire_tables(rom):
    tables = {}
    for nom, premier, second, pas, taille_nom, decalage, regle in TABLES:
        a, b = encoder(premier), encoder(second)
        candidats = [x for x in trouver_tout(rom, a) if rom[x + pas:x + pas + len(b)] == b]
        # Le début de la table est l'endroit que le jeu référence par pointeur.
        # On recule entrée par entrée depuis le nom connu (tant que les entrées
        # restent valides) et on garde le début le plus référencé. S'il existe
        # plusieurs copies de la table, la plus référencée l'emporte aussi.
        meilleur = None
        for x in candidats:
            ancre = x - decalage
            # Pour "objet" et "fiche", le nom connu est l'entrée 1 : pas besoin de reculer
            recul_max = 200 if regle == "remplissage" else 1
            for k in range(1, recul_max + 1):
                debut = ancre - k * pas
                if regle == "remplissage" and not entree_valide(rom, debut, 0, taille_nom, decalage, regle):
                    break
                refs = pointeurs_vers(rom, debut)
                if meilleur is None or len(refs) > len(meilleur[1]):
                    meilleur = (debut, refs, len(candidats))
        debut, refs, copies = meilleur
        entrees, i = [], 0
        while entree_valide(rom, debut + i * pas, i, taille_nom, decalage, regle):
            try:
                texte, n, long = lire_nom(rom, debut + i * pas + decalage, taille_nom)
            except ChaineInvalide:  # emplacement vide ou cassé : on le garde tel quel
                texte, n, long = None, 0, None
            entree = {"index": i, "texte": texte, "octets": n}
            if long is not None:
                entree["nom_long"] = hex(long)
            entrees.append(entree)
            i += 1
        nb_longs = sum("nom_long" in e for e in entrees)
        tables[nom] = {
            "adresse": hex(debut), "taille_entree": pas, "taille_nom_max": taille_nom,
            "decalage_nom": decalage, "nb_entrees": len(entrees), "noms_longs": nb_longs,
            "copies_trouvees": copies, "pointeurs_vers_table": [hex(r) for r in refs],
            "entrees": entrees,
        }
        print(f"  table {nom:17s} {hex(debut):>10s}  {len(entrees):5d} entrées"
              f"  ({len(refs)} pointeurs, {copies} copie(s), {nb_longs} noms longs)")
    return tables


def zones_tables(tables):
    """Zones déjà couvertes par les tables : les tables elles-mêmes et leurs noms longs."""
    zones = [(int(t["adresse"], 16), int(t["adresse"], 16) + t["taille_entree"] * t["nb_entrees"])
             for t in tables.values()]
    zones += [(int(e["nom_long"], 16), int(e["nom_long"], 16) + e["octets"])
              for t in tables.values() for e in t["entrees"] if "nom_long" in e]
    return zones


def est_texte_plausible(visibles, lettres):
    return visibles >= 2 and lettres >= 2 and lettres / visibles >= 0.5


def texte_courant(texte):
    """Part de caractères « normaux » une fois les codes {..} et \\x retirés."""
    brut = re.sub(r"\{[^}]*\}|\\[nlp]", "", texte)
    return sum(c in COURANTS for c in brut) / len(brut) if brut else 0


def debut_propre(rom, adresse):
    """Vrai si le texte ne commence pas au milieu d'une phrase.

    Un pointeur réel vise le début d'une chaîne ; un faux pointeur (4 octets
    qui ressemblent par hasard à une adresse) tombe souvent en plein mot.
    """
    avant = rom[adresse - 1]
    if avant == 0x00:  # une espace... ou un octet nul de remplissage
        return not (rom[adresse - 2] in range(0xA1, 0xEF))
    return not (0xA1 <= avant <= 0xEE or avant in (0xFE, 0xFA, 0xFB, 0xB0, 0xB4))


def extraire_textes(rom, zones_exclues):
    """Balaye la ROM à la recherche de pointeurs menant à du texte."""
    cache = {}
    cibles = {}  # adresse du texte -> liste des positions de ses pointeurs
    taille = len(rom)
    # Un pointeur vaut 0x08xxxxxx ou 0x09xxxxxx : son 4e octet est 08 ou 09.
    # Les pointeurs des scripts ne sont pas alignés sur 4 : on teste chaque octet.
    for m in re.finditer(rb"[\x08\x09]", rom):
        pos = m.start() - 3
        if pos < 0:
            continue
        cible = int.from_bytes(rom[pos:pos + 4], "little") - BASE_ROM
        if not 0 < cible < taille:
            continue
        if cible not in cache:
            try:
                texte, n, visibles, lettres = decoder(rom, cible)
                cache[cible] = (texte, n, visibles, lettres) if est_texte_plausible(visibles, lettres) else None
            except ChaineInvalide:
                cache[cible] = None
        if cache[cible] is not None:
            cibles.setdefault(cible, []).append(pos)

    def lisible(texte, visibles):
        # Un vrai texte de 12 caractères ou plus contient au moins une espace
        # ou un saut de ligne (écarte « zzzzzzzzzzzAAEi9 » et consorts).
        if visibles >= 12 and not re.search(r" |\\[nlp]", texte):
            return False
        return texte_courant(texte) >= 0.9

    retenues = [c for c in sorted(cibles) if not any(a <= c < b for a, b in zones_exclues)]
    # 1re passe : les textes au début propre forment la base fiable
    propres = [(c, c + cache[c][1]) for c in retenues
               if debut_propre(rom, c) and lisible(cache[c][0], cache[c][2])]
    debuts = [a for a, _ in propres]

    def couvert(adresse):
        i = bisect.bisect_right(debuts, adresse) - 1
        return i >= 0 and propres[i][0] < adresse < propres[i][1]

    textes = []
    for cible in retenues:
        texte, n, visibles, lettres = cache[cible]
        ptrs = cibles[cible]
        depuis_script = any(rom[p - 2:p] == b"\x0f\x00" for p in ptrs)  # loadpointer
        # haute       : vrai texte quasi certain, compté dans le bilan
        # moyenne     : texte court (menus : « Use », « No. »...) à confirmer en jeu
        # sous_chaine : fin d'un autre texte, visée par son propre pointeur
        #               (traduire l'un modifie l'autre : à traiter ensemble)
        # basse       : probablement un faux pointeur, ignoré pour l'instant
        if not lisible(texte, visibles):
            confiance = "basse"
        elif couvert(cible):
            confiance = "sous_chaine" if rom[cible - 1] in (0xFB, 0xFE, 0xFA) else "basse"
        elif visibles >= 4:
            confiance = "haute"
        else:
            confiance = "moyenne"
        textes.append({
            "adresse": hex(cible), "octets": n, "caracteres": visibles,
            "pointeurs": [hex(p) for p in ptrs], "script": depuis_script,
            "confiance": confiance, "texte": texte,
        })
    for i, t in enumerate(textes):
        t["id"] = f"T{i:05d}"
    marquer_familles(rom, textes)
    return textes


def marquer_familles(rom, textes, taille_min=4):
    """Rattache chaque texte à sa « famille » : la table de pointeurs qui le contient.

    Une table de pointeurs (ex. les descriptions d'attaques) est une suite de
    pointeurs alignés, rangés côte à côte, qui mènent tous à du texte. Tous les
    textes d'une même table s'affichent dans la même fenêtre : la famille sert
    donc ensuite à connaître la largeur de fenêtre disponible.
    """
    fiables = {int(t["adresse"], 16) for t in textes if t["confiance"] != "basse"}
    famille_de_pointeur, debut = {}, None
    nb_mots = len(rom) // 4
    for i in range(nb_mots + 1):
        vise_texte = i < nb_mots and int.from_bytes(rom[4 * i:4 * i + 4], "little") - BASE_ROM in fiables
        if vise_texte and debut is None:
            debut = i
        elif not vise_texte and debut is not None:
            if i - debut >= taille_min:
                for j in range(debut, i):
                    famille_de_pointeur[4 * j] = hex(4 * debut)
            debut = None
    for t in textes:
        familles = {famille_de_pointeur[int(p, 16)] for p in t["pointeurs"] if int(p, 16) in famille_de_pointeur}
        t["famille"] = min(familles) if familles else None


def chevauchements(textes):
    """Textes fiables qui partagent des octets (l'un est la fin d'un autre)."""
    n, fin_prec = 0, -1
    for t in textes:
        if t["confiance"] == "basse":
            continue
        a = int(t["adresse"], 16)
        if a < fin_prec:
            n += 1
        fin_prec = max(fin_prec, a + t["octets"])
    return n


def espace_libre(rom, seuil):
    """Blocs d'octets FF consécutifs d'au moins `seuil` octets."""
    return [(m.start(), m.end() - m.start())
            for m in re.finditer(rb"\xff{%d,}" % seuil, rom)]


def verifier_aller_retour(rom, textes, tables):
    """Décoder puis réencoder doit redonner exactement les mêmes octets."""
    erreurs = 0
    for t in textes:
        a = int(t["adresse"], 16)
        if encoder(t["texte"]) != rom[a:a + t["octets"]]:
            erreurs += 1
    for tab in tables.values():
        base = int(tab["adresse"], 16) + tab["decalage_nom"]
        for e in tab["entrees"]:
            if e["texte"] is None:
                continue
            a = int(e["nom_long"], 16) if "nom_long" in e else base + e["index"] * tab["taille_entree"]
            if encoder(e["texte"]) != rom[a:a + e["octets"]]:
                erreurs += 1
    return erreurs


def ecrire_bilan(rom, tables, textes, erreurs, chemin_rom):
    fiables = [t for t in textes if t["confiance"] == "haute"]
    octets = sum(t["octets"] for t in fiables)
    caracteres = sum(t["caracteres"] for t in fiables)
    mots = sum(len(t["texte"].replace("\\n", " ").replace("\\l", " ").replace("\\p", " ").split())
               for t in fiables)
    libre_256 = espace_libre(rom, 256)
    libre_4k = espace_libre(rom, 4096)
    total_256 = sum(n for _, n in libre_256)
    total_4k = sum(n for _, n in libre_4k)
    besoin = int(octets * 1.25)  # le français est environ 20 à 25 % plus long
    par_confiance = Counter(t["confiance"] for t in textes)
    tranches = Counter()
    for t in fiables:
        c = t["caracteres"]
        tranches["1-20" if c <= 20 else "21-100" if c <= 100 else "101-300" if c <= 300 else "300+"] += 1

    lignes = [
        "# État des lieux — Pokémon Unbound (étape 1)", "",
        f"ROM analysée : `{chemin_rom}` ({len(rom) // (1024 * 1024)} Mo)", "",
        "## Tables de noms à taille fixe", "",
        "Ces noms sont copiés dans des emplacements de taille fixe : la traduction ne doit",
        "pas dépasser la taille maximale (octet FF de fin compris). Exception : quand la",
        "colonne « noms longs » n'est pas nulle, le moteur CFRU accepte à la place un pointeur",
        "vers un nom plus long (à vérifier en jeu : la fenêtre d'affichage peut le couper).", "",
        "| Table | Adresse | Entrées | Taille max (FF compris) | Noms longs par pointeur | Nom le plus long actuel |",
        "|---|---|---|---|---|---|",
    ]
    for nom, t in tables.items():
        plus_long = max((e for e in t["entrees"] if e["texte"]), key=lambda e: len(e["texte"].strip()))
        lignes.append(f"| {nom} | `{t['adresse']}` | {t['nb_entrees']} | {t['taille_nom_max']} | {t['noms_longs']} "
                      f"| {plus_long['texte']} ({plus_long['octets']}) |")
    lignes += [
        "", "## Textes trouvés par pointeurs", "",
        f"- Chaînes détectées : **{len(textes)}** "
        f"(confiance haute {par_confiance['haute']}, moyenne {par_confiance['moyenne']}, "
        f"sous-chaîne {par_confiance['sous_chaine']}, basse {par_confiance['basse']})",
        f"- Chaînes fiables (confiance haute) : **{len(fiables)}**, dont "
        f"{sum(t['script'] for t in fiables)} appelées depuis un script",
        f"- Volume fiable : **{octets:,} octets**, {caracteres:,} caractères, ~{mots:,} mots",
        f"- Répartition par longueur : " + ", ".join(f"{k} car. : {tranches[k]}" for k in ["1-20", "21-100", "101-300", "300+"]),
        f"- Chaînes qui partagent des octets avec une autre : {chevauchements(textes)} "
        "(à traiter avec soin : les modifier sans repointer casserait l'autre)",
        f"- Vérification aller-retour décodage → encodage : "
        + ("**OK, 0 erreur**" if erreurs == 0 else f"**{erreurs} erreur(s)**"),
        "", "## Espace libre dans la ROM", "",
        "Estimation : blocs d'octets FF consécutifs (c'est ainsi que l'espace vide est",
        "rempli). Un gros bloc de FF est presque toujours libre, un petit peut être une donnée.", "",
        f"- Blocs ≥ 4 Ko : **{total_4k:,} octets** ({total_4k / 1024:.0f} Ko) en {len(libre_4k)} blocs",
        f"- Blocs ≥ 256 octets : {total_256:,} octets ({total_256 / 1024:.0f} Ko) en {len(libre_256)} blocs",
        "- Plus grands blocs : " + ", ".join(f"`{hex(a)}` ({n // 1024} Ko)" for a, n in sorted(libre_4k, key=lambda x: -x[1])[:5]),
        "", "## Verdict mémoire", "",
        "La ROM fait déjà 32 Mo, le maximum qu'une GBA peut adresser : impossible de l'agrandir.",
        "Mais un texte déplacé (repointé) libère son ancienne place, qui redevient utilisable.", "",
        f"- Pire cas, tout le texte fiable réécrit avec +25 % : **{besoin:,} octets**",
        f"- Place disponible = espace libre ({total_4k:,}) + anciennes places récupérées ({octets:,})"
        f" = **{total_4k + octets:,} octets**",
        f"- Marge : {total_4k + octets - besoin:,} octets "
        f"(le français peut être en moyenne jusqu'à "
        f"+{(total_4k + octets) / octets * 100 - 100:.0f} % plus long que l'anglais)",
    ]
    if total_4k + octets >= besoin:
        lignes.append("- ✅ Ça tient, **à condition** de connaître tous les pointeurs de chaque texte "
                      "déplacé (un pointeur oublié = texte corrompu en jeu) et de rester concis.")
    else:
        lignes.append("- ❌ Ça ne tient pas à +25 % : la traduction devra être plus compacte.")
    (RACINE / "docs" / "etat_des_lieux.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))


def main():
    chemin_rom = sys.argv[1] if len(sys.argv) > 1 else "rom/unbound_original.gba"
    rom = Path(chemin_rom).read_bytes()
    print("Recherche des tables de noms...")
    tables = extraire_tables(rom)
    print("Balayage des pointeurs (environ une minute)...")
    textes = extraire_textes(rom, zones_tables(tables))
    erreurs = verifier_aller_retour(rom, textes, tables)
    (RACINE / "donnees").mkdir(exist_ok=True)
    (RACINE / "docs").mkdir(exist_ok=True)
    for nom, contenu in [("tables_en.json", tables), ("textes_en.json", textes)]:
        with open(RACINE / "donnees" / nom, "w", encoding="utf-8") as f:
            json.dump(contenu, f, ensure_ascii=False, indent=1)
    print()
    ecrire_bilan(rom, tables, textes, erreurs, chemin_rom)


if __name__ == "__main__":
    main()
