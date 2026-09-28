"""Mesure de la largeur en pixels d'un texte du jeu.

La police de Rouge Feu est proportionnelle : chaque caractère a sa propre
largeur (un « i » fait 4 pixels, un « m » 6). Pour savoir si une ligne tient
dans une boîte de dialogue, on additionne donc la largeur de ses caractères,
lue dans la table des largeurs de la police, stockée dans la ROM.

Les variables comme {PLAYER} sont remplacées en jeu par un texte de longueur
inconnue : on compte leur largeur maximale possible (pire cas).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from charmap import encoder  # noqa: E402

LARGEUR_BOITE = 208  # boîte de dialogue standard : 26 cases de 8 pixels

# Largeur maximale des variables (pire cas), en pixels
LARGEUR_VARIABLES = {
    "PLAYER": 7 * 6,     # nom du joueur : 7 caractères
    "RIVAL": 7 * 6,      # nom du rival : 7 caractères
    "STR_VAR_1": 10 * 6,  # le plus souvent un nom de Pokémon (10 caractères)
    "STR_VAR_2": 10 * 6,
    "STR_VAR_3": 10 * 6,
    "KUN": 0,
}
LARGEUR_VARIABLE_INCONNUE = 10 * 6
LARGEUR_ICONE = 12  # icônes de bouton {F8 xx} et symboles {F9 xx}

_JETON = re.compile(r"\{[^}]*\}|\\[nlp]|.", re.S)


def trouver_table_largeurs(rom):
    """Repère la table des largeurs de la police normale (256 octets).

    On la reconnaît à ses propriétés plutôt qu'à une adresse fixe : largeurs
    entre 1 et 12, « i » plus étroit que « m », chiffres de largeur égale.
    La première trouvée est celle de la police normale (les suivantes sont
    des copies identiques utilisées par d'autres fenêtres).
    """
    i_, l_, m_, w_ = (0xD5 + ord(c) - 97 for c in "ilmw")
    for p in range(0, len(rom) - 256, 4):
        t = rom[p:p + 256]
        if max(t[0xA1:0xEF]) > 12 or min(t[0xA1:0xEF]) == 0 or not 2 <= t[0] <= 8:
            continue
        if t[i_] < t[m_] and t[l_] < t[w_] and t[m_] - t[i_] >= 2 and len(set(t[0xA1:0xAB])) <= 2:
            return p, list(t)
    raise ValueError("Table des largeurs introuvable")


class Mesureur:
    def __init__(self, largeurs):
        self.largeurs = largeurs

    def largeur_jeton(self, jeton):
        if jeton.startswith("{"):
            code = jeton[1:-1]
            if code in LARGEUR_VARIABLES:
                return LARGEUR_VARIABLES[code]
            octets = code.split()
            if octets[0] == "FD":
                return LARGEUR_VARIABLE_INCONNUE
            if octets[0] in ("F8", "F9"):
                return LARGEUR_ICONE
            if octets[0] == "FC":
                return 0  # couleur, pause, son... : pas de largeur
            # symbole d'une case ({PK}, {LV}...) : largeur lue dans la table
            return self.largeurs[encoder(jeton)[0]]
        return self.largeurs[encoder(jeton)[0]]

    def lignes(self, texte):
        """Découpe le texte en lignes affichées.

        Renvoie une liste de (largeur_px, saut_qui_suit, texte_de_la_ligne),
        où saut_qui_suit vaut "\\n", "\\l", "\\p" ou "" (fin du texte).
        Les codes {FC 12 xx} (avancer de xx pixels) et {FC 13 xx} (aller à la
        position xx) déplacent le curseur : on en tient compte.
        """
        resultat, x, debut = [], 0, 0
        jetons = _JETON.findall(texte)
        courant = []
        for jeton in jetons:
            if jeton in ("\\n", "\\l", "\\p"):
                resultat.append((x, jeton, "".join(courant)))
                x, courant = 0, []
                continue
            courant.append(jeton)
            if jeton.startswith("{FC 12 "):
                x += int(jeton[7:9], 16)
            elif jeton.startswith("{FC 13 "):
                x = int(jeton[7:9], 16)
            else:
                x += self.largeur_jeton(jeton)
        resultat.append((x, "", "".join(courant)))
        return resultat

    def largeur_max(self, texte):
        return max(l for l, _, _ in self.lignes(texte))
