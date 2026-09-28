"""Étape 2 : glossaire des noms (anglais d'Unbound -> français officiel).

Usage : python3 outils/glossaire.py

Entrées :
  donnees/tables_en.json          noms extraits de la ROM (étape 1)
  donnees/reference/*.csv         noms officiels multilingues (PokéAPI)
  donnees/glossaire_choix.json    choix manuels : abréviations, noms propres à Unbound
Sorties :
  donnees/glossaire.json          une entrée par nom de table, avec son statut
  docs/glossaire_bilan.md         ce qui tient, ce qui dépasse, ce qui reste à traduire

Pourquoi un fichier de choix séparé ? Le glossaire est régénéré à chaque
lancement ; les décisions humaines (abréger « Lance-Flammes » en
« Lance-Flamme ») doivent survivre à ces régénérations et rester relisibles.
"""

import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from charmap import encoder  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
REFERENCE = RACINE / "donnees" / "reference"
LANGUE_FR, LANGUE_EN = "5", "9"  # identifiants de langue dans PokéAPI

# Table de la ROM -> fichier de référence PokéAPI (None : pas de référence)
SOURCES = {
    "pokemon": "pokemon_species_names.csv",
    "attaques": "move_names.csv",
    "talents": "ability_names.csv",
    "objets": "item_names.csv",
    "classes_dresseurs": None,
    "dresseurs": None,
}

# Tables dont les noms sont gardés tels quels par défaut : les prénoms des
# dresseurs sont des personnages propres à Unbound (un choix peut les changer)
CONSERVES = {"dresseurs"}

# Tables où le moteur CFRU accepte un pointeur vers un nom long (étape 1).
# Limite d'affichage retenue : le plus long nom long déjà présent dans Unbound,
# donc déjà prouvé lisible en jeu.
NOMS_LONGS_POSSIBLES = {"objets", "classes_dresseurs"}

# Nom dans Unbound -> nom anglais officiel. Deux origines :
#  - anciennes graphies de la 3e génération (« Faint Attack ») ;
#  - abréviations d'Unbound pour tenir dans la table, identifiées une à une
#    grâce à la description de la capacité dans la ROM (étape 2).
ALIAS_EN = {
    # Graphies 3e génération
    "Faint Attack": "Feint Attack", "Hi Jump Kick": "High Jump Kick",
    "ViceGrip": "Vise Grip", "SmellingSalt": "Smelling Salts",
    # Attaques abrégées par Unbound (vérifiées par leur description)
    "Doll Eyes": "Baby-Doll Eyes", "Drain Kiss": "Draining Kiss",
    "Dazzle Gleam": "Dazzling Gleam", "Disarm Cry": "Disarming Voice",
    "Flower Guard": "Flower Shield", "Petal Storm": "Petal Blizzard",
    "Space Hole": "Hyperspace Hole", "Space Fury": "Hyperspace Fury",
    "Cliff Blades": "Precipice Blades", "Steam Pump": "Steam Eruption",
    "Water Star": "Water Shuriken", "Mystic Fire": "Mystical Fire",
    "Power-Up Hit": "Power-Up Punch", "1000 Arrows": "Thousand Arrows",
    "1000 Waves": "Thousand Waves", "Para Charge": "Parabolic Charge",
    "Clang Scales": "Clanging Scales", "Dark Lariat": "Darkest Lariat",
    "Draco Hammer": "Dragon Hammer", "First Press": "First Impression",
    "HiHorsepower": "High Horsepower", "Geist Beam": "Moongeist Beam",
    "Prism Laser": "Prismatic Laser", "Revel Dance": "Revelation Dance",
    "Sparkle Aria": "Sparkling Aria", "Spect Thief": "Spectral Thief",
    "Spirit Lock": "Spirit Shackle", "Bad Tantrum": "Stomping Tantrum",
    "Sunsteel Ram": "Sunsteel Strike", "Teary Look": "Tearful Look",
    "Elec Terrain": "Electric Terrain", "GrassTerrain": "Grassy Terrain",
    "Mist Terrain": "Misty Terrain", "Psyc Terrain": "Psychic Terrain",
    "Crafty Guard": "Crafty Shield", "Aroma Mist": "Aromatic Mist",
    "Magnet Flux": "Magnetic Flux", "TrickoTreat": "Trick-or-Treat",
    "Woods Curse": "Forest's Curse", "Light o Ruin": "Light of Ruin",
    "DMax Cannon": "Dynamax Cannon", "Clang Soul": "Clangorous Soul",
    "Giant Blade": "Behemoth Blade", "Giant Bash": "Behemoth Bash",
    "Break Swipe": "Breaking Swipe", "False Yield": "False Surrender",
    "Meteor Rush": "Meteor Assault", "Expand Force": "Expanding Force",
    "MistyExplode": "Misty Explosion", "Jealous Burn": "Burning Jealousy",
    "Corrode Gas": "Corrosive Gas", "Scorch Sands": "Scorching Sands",
    "SurgeStrikes": "Surging Strikes", "Freeze Glare": "Freezing Glare",
    "Thunder Kick": "Thunderous Kick", "Astral Storm": "Astral Barrage",
    "PsyshieldRam": "Psyshield Bash", "Mystic Power": "Mystical Power",
    "InfernalRage": "Infernal Parade", "Endless Edge": "Ceaseless Edge",
    "BleakiceWind": "Bleakwind Storm", "WildboltWind": "Wildbolt Storm",
    "SandsearWind": "Sandsear Storm", "Spring Wind": "Springtide Storm",
    # Talents abrégés (vérifiés par leur description)
    "Neutralize Gas": "Neutralizing Gas", "Wandering Soul": "Wandering Spirit",
    "Odd Medicine": "Curious Medicine", "Valiant Shield": "Dauntless Shield",
    "Alchemic Power": "Power of Alchemy",
    # Objets renommés depuis
    "Clever Wing": "Clever Feather", "Genius Wing": "Genius Feather",
    "Health Wing": "Health Feather", "Muscle Wing": "Muscle Feather",
    "Pretty Wing": "Pretty Feather", "Resist Wing": "Resist Feather",
    "Swift Wing": "Swift Feather", "Draco Memory": "Dragon Memory",
    "Earth Memory": "Ground Memory", "Fist Memory": "Fighting Memory",
    "Psych Memory": "Psychic Memory", "Sky Memory": "Flying Memory",
    "Toxic Memory": "Poison Memory", "Zap Memory": "Electric Memory",
    "Utility Parasol": "Utility Umbrella", "Ylw Nectar": "Yellow Nectar",
    "Necrozium Z": "Ultranecrozium Z",
}

# Noms factices ou techniques, jamais affichés : pas de traduction
FACTICES = {"", "?", "???", "?????", "??????", "????????", "??????????",
            "????????????", "-", "-------", "MISSINGNO.", "Unused"}
FACTICE_MOTIF = re.compile(r"Z-Move \d+")


def normaliser(nom):
    """Clé de comparaison : minuscules, sans accents, espaces ni ponctuation.

    « ThunderPunch » (graphie GBA) et « Thunder Punch » (graphie moderne)
    donnent tous deux « thunderpunch ».
    """
    nom = re.sub(r"\{[^}]*\}", "", nom)
    nom = unicodedata.normalize("NFD", nom)
    nom = "".join(c for c in nom if unicodedata.category(c) != "Mn")
    nom = nom.replace("♀", "f").replace("♂", "m")
    return re.sub(r"[^a-z0-9]", "", nom.lower())


def charger_reference(fichier):
    """Renvoie {clé normalisée de l'anglais: nom français, ou None si PokéAPI n'en a pas}."""
    par_id = {}
    with open(REFERENCE / fichier, encoding="utf-8") as f:
        lecteur = csv.reader(f)
        next(lecteur)
        for ligne in lecteur:
            ident, langue, nom = ligne[0], ligne[1], ligne[2]
            if langue in (LANGUE_FR, LANGUE_EN):
                par_id.setdefault(ident, {})[langue] = nom
    reference = {}
    for noms in par_id.values():
        if LANGUE_EN in noms:
            cle = normaliser(noms[LANGUE_EN])
            if reference.get(cle) is None:  # la 1re occurrence avec du français l'emporte
                reference[cle] = noms.get(LANGUE_FR)
    return reference


def sous_suite(courte, longue):
    """Vrai si les lettres de `courte` apparaissent dans l'ordre dans `longue`."""
    lettres = iter(longue)
    return all(c in lettres for c in courte)


ALIAS = {normaliser(court): normaliser(officiel) for court, officiel in ALIAS_EN.items()}


def chercher(reference, nom_en):
    """Renvoie (nom français officiel, méthode).

    Méthodes : exact, alias, max (capacité Max stockée sans « Max »),
    regle (CT/CS, Zarbi), tronque (nom raccourci par Unbound : à relire),
    sans_fr (connu de PokéAPI mais sans nom français), ou (None, None).
    """
    # Zarbi : Unbound a une espèce par lettre (« Unown B » -> « Zarbi B »).
    # Avant la recherche exacte, qui ignore la ponctuation (« Unown ? » = « Unown »).
    m = re.fullmatch(r"Unown ([A-Z?!])", nom_en)
    if m:
        return "Zarbi " + m.group(1), "regle"
    cle = normaliser(nom_en)
    cle = ALIAS.get(cle, cle)
    for prefixe, methode in (("", "exact"), ("max", "max")):
        if prefixe + cle in reference:
            fr = reference[prefixe + cle]
            if fr is None:
                return None, "sans_fr"
            return fr, "alias" if cle != normaliser(nom_en) else methode
    # CT/CS : « TM01 » -> « CT01 », « HM01 » -> « CS01 »
    m = re.fullmatch(r"(tm|hm)(\d+)", cle)
    if m:
        return ("CT" if m.group(1) == "tm" else "CS") + m.group(2).zfill(2), "regle"
    # Nom raccourci pour tenir dans la table (« Corvknight », « Blastoisite ») :
    # mêmes 3 premières lettres, lettres dans le même ordre, au moins 65 % du
    # nom officiel (sinon « Package » deviendrait « Packaged Curry »), un seul candidat
    if len(cle) >= 6:
        candidats = [c for c in reference if c[:3] == cle[:3] and len(cle) >= 0.65 * len(c)
                     and sous_suite(cle, c) and reference[c]]
        if len(candidats) == 1:
            return reference[candidats[0]], "tronque"
    return None, None


def octets(texte):
    """Taille encodée, FF final compris, ou None si un caractère est absent de la police."""
    try:
        return len(encoder(texte))
    except ValueError:
        return None


def construire():
    tables = json.loads((RACINE / "donnees" / "tables_en.json").read_text(encoding="utf-8"))
    chemin_choix = RACINE / "donnees" / "glossaire_choix.json"
    choix = json.loads(chemin_choix.read_text(encoding="utf-8")) if chemin_choix.exists() else {}

    glossaire = {}
    for nom_table, table in tables.items():
        limite = table["taille_nom_max"]
        limite_longue = None
        if nom_table in NOMS_LONGS_POSSIBLES:
            limite_longue = max((e["octets"] for e in table["entrees"] if "nom_long" in e), default=None)
        source = SOURCES.get(nom_table)
        reference = charger_reference(source) if source else {}
        choix_table = choix.get(nom_table, {})
        entrees = []
        for e in table["entrees"]:
            en = e["texte"]
            if en is None or en.strip() in FACTICES or FACTICE_MOTIF.fullmatch(en):
                continue
            officiel, methode = chercher(reference, en) if reference else (None, None)
            if nom_table in CONSERVES:
                officiel, methode = en, "conserve"
            fr = choix_table.get(en, officiel)
            taille = octets(fr) if fr else None
            if fr is None:
                statut = "sans_fr" if methode == "sans_fr" else "a_traduire"
            elif taille is None:
                statut = "caractere_absent"
            elif taille <= limite:
                statut = "ok"
            elif limite_longue and taille <= limite_longue:
                statut = "nom_long"  # passera par un pointeur vers un nom long
            else:
                statut = "trop_long"
            entrees.append({
                "index": e["index"], "en": en, "fr_officiel": officiel, "fr": fr,
                "source": "choix" if en in choix_table else methode,
                "octets": taille, "limite": limite, "statut": statut,
            })
        glossaire[nom_table] = {"limite": limite, "limite_nom_long": limite_longue, "entrees": entrees}
    return glossaire


def ecrire_bilan(glossaire):
    lignes = [
        "# Glossaire — bilan (étape 2)", "",
        "Taille en octets, FF de fin compris. « nom long » : dépasse la table mais passe",
        "par le pointeur vers un nom long du moteur CFRU (limite = plus long nom long déjà",
        "présent dans Unbound, donc déjà prouvé lisible en jeu).", "",
        "| Table | Noms (uniques) | OK | Nom long | Trop long | À traduire | Sans nom FR dans PokéAPI | Caractère absent |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for nom, g in glossaire.items():
        uniques = {e["en"]: e for e in g["entrees"]}
        c = Counter(e["statut"] for e in uniques.values())
        lignes.append(f"| {nom} | {len(uniques)} | {c['ok']} | {c['nom_long']} | {c['trop_long']} "
                      f"| {c['a_traduire']} | {c['sans_fr']} | {c['caractere_absent']} |")
    for nom, g in glossaire.items():
        choisis = {e["en"]: e for e in g["entrees"] if e["source"] == "choix"}
        if not choisis:
            continue
        lignes += ["", f"## Choix manuels à relire — {nom} ({len(choisis)})", "",
                   "| Anglais (Unbound) | Officiel français | Choix | Octets |", "|---|---|---|---|"]
        for e in sorted(choisis.values(), key=lambda x: x["fr_officiel"] or x["en"]):
            lignes.append(f"| {e['en']} | {e['fr_officiel'] or '—'} | **{e['fr']}** | {e['octets']}/{e['limite']} |")
    for statut, titre in [("trop_long", "Trop longs : abréviation à choisir"),
                          ("caractere_absent", "Caractère absent de la police"),
                          ("a_traduire", "Sans nom officiel : à traduire")]:
        for nom, g in glossaire.items():
            uniques = {e["en"]: e for e in g["entrees"] if e["statut"] == statut}
            if not uniques:
                continue
            lignes += ["", f"## {titre} — {nom} ({len(uniques)})", ""]
            if statut == "a_traduire" and len(uniques) > 60:
                lignes.append(f"{len(uniques)} noms : liste complète dans `donnees/glossaire.json`.")
                continue
            for e in sorted(uniques.values(), key=lambda x: x["en"]):
                detail = f" → {e['fr']} ({e['octets']}/{e['limite']})" if e["fr"] else ""
                lignes.append(f"- {e['en']}{detail}")
    (RACINE / "docs" / "glossaire_bilan.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return lignes


def main():
    glossaire = construire()
    with open(RACINE / "donnees" / "glossaire.json", "w", encoding="utf-8") as f:
        json.dump(glossaire, f, ensure_ascii=False, indent=1)
    print("\n".join(ecrire_bilan(glossaire)[:14]))


if __name__ == "__main__":
    main()
