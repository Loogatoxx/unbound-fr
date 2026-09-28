"""Étape 4 : vérification (et remise en forme) des traductions.

Usage :
  python3 outils/verifier.py              vérifie donnees/traductions/*.json
  python3 outils/verifier.py --reformater redécoupe d'abord les lignes, puis vérifie

Format d'un fichier de traduction : {"T01234": "texte français", ...}
Les identifiants sont ceux de donnees/textes_en.json.

Règles vérifiées (toutes déduites des textes anglais d'Unbound, pas supposées) :
  - chaque caractère existe dans la police du jeu ;
  - les variables ({PLAYER}, {STR_VAR_1}...) sont toutes conservées ;
  - aucune ligne ne dépasse la largeur de sa fenêtre, en pixels ;
  - la structure des boîtes est respectée : dans un dialogue, une boîte
    affiche 2 lignes, donc au plus un \\n par boîte, les lignes suivantes
    défilant avec \\l.
Niveaux : ERREUR (casserait l'affichage), ATTENTION (à vérifier en jeu).
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from charmap import encoder  # noqa: E402
from largeur import LARGEUR_BOITE, Mesureur, trouver_table_largeurs  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_TRADUCTIONS = RACINE / "donnees" / "traductions"
SAUTS = ("\\n", "\\l", "\\p")
_VARIABLE = re.compile(r"\{(?:PLAYER|RIVAL|STR_VAR_\d|KUN|FD [0-9A-F]{2}|F[89] [0-9A-F]{2})\}")
_CODE_FC = re.compile(r"\{FC [^}]*\}")


# Typographie : caractères courants au clavier mais absents de la police du jeu
TYPOGRAPHIE = [
    ("«\u00a0", "“"), ("« ", "“"), ("«", "“"),      # guillemets français -> “ ”
    ("\u00a0»", "”"), (" »", "”"), ("»", "”"),
    ("'", "’"),                                        # apostrophe droite -> typographique
    ("...", "…"),                                      # trois points -> points de suspension (1 case)
    ("\u00a0", " "), ("\u202f", " "),                  # espaces insécables -> espace simple
]
# Ponctuation précédée d'une espace en français (« Salut ! ») : jamais seule en début de ligne
PONCTUATION_COLLEE = ("!", "?", ":", ";", "”", "…")


def corriger_typographie(texte):
    for avant, apres in TYPOGRAPHIE:
        texte = texte.replace(avant, apres)
    return texte


def paragraphes(texte):
    return texte.split("\\p")


def sauts_du_paragraphe(paragraphe):
    return re.findall(r"\\[nl]", paragraphe)


class Regles:
    """Contraintes d'affichage d'un texte, déduites de l'anglais."""

    def __init__(self, genre, largeur_sure, largeur_absolue, max_n, max_lignes, style, boites_autorisees):
        self.genre = genre                      # "dialogue", "famille" ou "isole"
        self.largeur_sure = largeur_sure        # au-delà : ATTENTION
        self.largeur_absolue = largeur_absolue  # au-delà : ERREUR
        self.max_n = max_n                      # nombre max de \n par boîte
        self.max_lignes = max_lignes            # nombre max de lignes par boîte (hors dialogue)
        self.style = style                      # "dialogue" (\n puis \l) ou "simple" (\n partout)
        self.boites_autorisees = boites_autorisees  # \p permis ?


class Verificateur:
    def __init__(self, rom, textes):
        self.mesureur = Mesureur(trouver_table_largeurs(rom)[1])
        self.textes = {t["id"]: t for t in textes}
        self._stats_familles(textes)

    # --- Règles -----------------------------------------------------------

    def _profil(self, texte):
        """(largeur max, \\n max par boîte, lignes max par boîte, utilise \\l, utilise \\p)."""
        largeur = self.mesureur.largeur_max(texte)
        paras = paragraphes(texte)
        max_n = max(p.count("\\n") for p in paras)
        max_lignes = max(len(sauts_du_paragraphe(p)) + 1 for p in paras)
        return largeur, max_n, max_lignes, "\\l" in texte, "\\p" in texte

    def _stats_familles(self, textes):
        self.familles = defaultdict(lambda: [0, 0, 0, False, False])
        for t in textes:
            if t["confiance"] == "basse" or not t.get("famille") or t["script"]:
                continue
            f = self.familles[t["famille"]]
            larg, n, lignes, avec_l, avec_p = self._profil(t["texte"])
            f[0], f[1], f[2] = max(f[0], larg), max(f[1], n), max(f[2], lignes)
            f[3], f[4] = f[3] or avec_l, f[4] or avec_p

    def regles(self, ident):
        t = self.textes[ident]
        larg, n, lignes, avec_l, avec_p = self._profil(t["texte"])
        if t["script"]:
            # Boîte de dialogue : 208 px (ou plus si l'anglais prouve une fenêtre plus large)
            limite = max(LARGEUR_BOITE, larg)
            return Regles("dialogue", limite, limite, max(1, n), None, "dialogue", True)
        if t.get("famille"):
            fl, fn, flignes, fl_l, fl_p = self.familles[t["famille"]]
            return Regles("famille", fl, fl, fn, flignes, "dialogue" if fl_l else "simple", fl_p)
        # Texte isolé : fenêtre inconnue. L'anglais tient, donc sa largeur est sûre ;
        # au-delà (jusqu'à 208 px), il faudra vérifier en jeu.
        return Regles("isole", larg, max(LARGEUR_BOITE, larg), n, lignes,
                      "dialogue" if avec_l else "simple", avec_p)

    # --- Vérification -----------------------------------------------------

    def verifier(self, ident, fr):
        """Renvoie la liste des problèmes : [(niveau, message), ...]."""
        en = self.textes[ident]["texte"]
        r = self.regles(ident)
        problemes = []
        if not fr.strip():
            return [("ERREUR", "traduction vide")]
        try:
            encoder(fr)
        except ValueError:
            absents = sorted({c for c in re.sub(r"\{[^}]*\}|\\[nlp]", "", fr) if not _encodable(c)})
            return [("ERREUR", f"caractère(s) absent(s) de la police : {' '.join(absents)}")]
        # Variables : toutes conservées, ni plus ni moins
        manque = Counter(_VARIABLE.findall(en)) - Counter(_VARIABLE.findall(fr))
        trop = Counter(_VARIABLE.findall(fr)) - Counter(_VARIABLE.findall(en))
        if manque:
            problemes.append(("ERREUR", f"variable(s) manquante(s) : {' '.join(manque.elements())}"))
        if trop:
            problemes.append(("ERREUR", f"variable(s) en trop : {' '.join(trop.elements())}"))
        if Counter(_CODE_FC.findall(en)) != Counter(_CODE_FC.findall(fr)):
            problemes.append(("ATTENTION", "codes {FC ..} (couleur, pause, son) différents de l'anglais"))
        # Largeur de chaque ligne
        for largeur, _, ligne in self.mesureur.lignes(fr):
            if largeur > r.largeur_absolue:
                problemes.append(("ERREUR", f"ligne de {largeur} px > {r.largeur_absolue} px : « {ligne} »"))
            elif largeur > r.largeur_sure:
                problemes.append(("ATTENTION", f"ligne de {largeur} px, l'anglais tenait en "
                                               f"{r.largeur_sure} px (fenêtre inconnue) : « {ligne} »"))
        # Structure des boîtes
        if "\\p" in fr and not r.boites_autorisees:
            problemes.append(("ERREUR", "\\p (nouvelle boîte) impossible dans cette fenêtre"))
        for para in paragraphes(fr):
            sauts = sauts_du_paragraphe(para)
            if r.style == "dialogue":
                if sauts.count("\\n") > r.max_n:
                    problemes.append(("ERREUR", f"{sauts.count(chr(92) + 'n')} \\n dans une boîte "
                                                f"(max {r.max_n}) : utiliser \\l pour faire défiler"))
                if sauts and sauts[0] == "\\l":
                    problemes.append(("ATTENTION", "\\l avant tout \\n dans une boîte"))
            if r.max_lignes is not None and r.genre != "dialogue" and len(sauts) + 1 > r.max_lignes:
                problemes.append(("ERREUR", f"{len(sauts) + 1} lignes dans une fenêtre de {r.max_lignes}"))
        return problemes

    # --- Remise en forme ----------------------------------------------------

    def reformater(self, ident, fr):
        """Redécoupe les lignes au plus près de la largeur permise.

        Les \\p (boîtes) voulus par le traducteur sont gardés ; les \\n et \\l
        sont recalculés : dans un dialogue, \\n pour la 2e ligne d'une boîte puis
        \\l pour les suivantes, comme dans l'anglais.
        """
        r = self.regles(ident)
        fr = corriger_typographie(fr)
        espace = self.mesureur.largeur_jeton(" ")
        boites = []
        for para in paragraphes(fr):
            mots = _mots(re.sub(r"\\[nl]", " ", para))
            lignes, courante, largeur = [], [], 0
            for mot in mots:
                l_mot = sum(self.mesureur.largeur_jeton(j) for j in _jetons(mot))
                if courante and largeur + espace + l_mot > r.largeur_sure:
                    lignes.append(" ".join(courante))
                    courante, largeur = [mot], l_mot
                else:
                    largeur += (espace if courante else 0) + l_mot
                    courante.append(mot)
            lignes.append(" ".join(courante))
            if r.style == "dialogue":
                texte = lignes[0] + "".join(("\\n" if i == 1 else "\\l") + l for i, l in enumerate(lignes[1:], 1))
            else:
                texte = "\\n".join(lignes)
            boites.append(texte)
        return "\\p".join(boites)


def _encodable(caractere):
    try:
        encoder(caractere)
        return True
    except ValueError:
        return False


def _jetons(mot):
    return re.findall(r"\{[^}]*\}|.", mot)


def _mots(texte):
    """Découpe en mots sur les espaces, sans casser les codes {FC 01 02}."""
    mots, courant, dans_code = [], "", False
    for c in texte:
        if c == "{":
            dans_code = True
        elif c == "}":
            dans_code = False
        if c == " " and not dans_code:
            if courant:
                mots.append(courant)
            courant = ""
        else:
            courant += c
    if courant:
        mots.append(courant)
    # « Salut ! » : le « ! » reste attaché au mot précédent (espace insécable)
    colles = []
    for mot in mots:
        if colles and mot.startswith(PONCTUATION_COLLEE) and len(mot) <= 3:
            colles[-1] += " " + mot
        else:
            colles.append(mot)
    return colles


def charger_traductions():
    traductions = {}
    for fichier in sorted(DOSSIER_TRADUCTIONS.glob("*.json")):
        for ident, fr in json.loads(fichier.read_text(encoding="utf-8")).items():
            traductions[ident] = (fichier, fr)
    return traductions


def main():
    rom = (RACINE / "rom" / "unbound_original.gba").read_bytes()
    textes = json.loads((RACINE / "donnees" / "textes_en.json").read_text(encoding="utf-8"))
    v = Verificateur(rom, textes)
    traductions = charger_traductions()
    if "--reformater" in sys.argv:
        par_fichier = defaultdict(dict)
        for ident, (fichier, fr) in traductions.items():
            par_fichier[fichier][ident] = v.reformater(ident, fr)
        for fichier, contenu in par_fichier.items():
            fichier.write_text(json.dumps(contenu, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        traductions = charger_traductions()

    erreurs = attentions = octets_en = octets_fr = 0
    lignes = ["# Vérification des traductions", ""]
    for ident, (fichier, fr) in sorted(traductions.items()):
        problemes = v.verifier(ident, fr)
        octets_en += v.textes[ident]["octets"]
        octets_fr += len(encoder(fr)) if not any("police" in m for _, m in problemes) else 0
        if problemes:
            lignes += [f"## {ident} ({fichier.name}, {v.regles(ident).genre})", "", f"> {fr}", ""]
            lignes += [f"- **{niveau}** : {message}" for niveau, message in problemes]
            lignes.append("")
        erreurs += sum(n == "ERREUR" for n, _ in problemes)
        attentions += sum(n == "ATTENTION" for n, _ in problemes)
    croissance = f"{(octets_fr / octets_en - 1) * 100:+.1f} %" if octets_en else "—"
    resume = (f"{len(traductions)} textes vérifiés : {erreurs} erreur(s), {attentions} attention(s). "
              f"Taille : {octets_en:,} → {octets_fr:,} octets ({croissance}).")
    lignes.insert(2, resume + "\n")
    (RACINE / "docs" / "verification.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(resume)
    sys.exit(1 if erreurs else 0)


if __name__ == "__main__":
    main()
