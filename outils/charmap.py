"""Table de caractères de Pokémon Rouge Feu (charmap).

Le jeu ne stocke pas les lettres en ASCII : chaque octet correspond à un
caractère selon une table propre à la 3e génération. Ce module sait :
  - décoder des octets de la ROM en texte lisible,
  - réencoder ce texte en octets, à l'identique.

Notation choisie pour les codes de contrôle (réversible sans perte) :
  \\n  saut de ligne (FE)          \\l  défilement d'une ligne (FA)
  \\p  nouvelle boîte (FB)          {PLAYER}, {STR_VAR_1}... variables (FD xx)
  {FC 01 02} code de contrôle étendu brut (couleur, pause, son...)
  {PK} {MN} {LV}... symboles spéciaux sans équivalent Unicode
"""

FIN = 0xFF  # fin de chaîne

# Caractères imprimables : octet -> caractère
CARACTERES = {
    0x00: " ",
    0x01: "À", 0x02: "Á", 0x03: "Â", 0x04: "Ç", 0x05: "È", 0x06: "É", 0x07: "Ê",
    0x08: "Ë", 0x09: "Ì", 0x0B: "Î", 0x0C: "Ï", 0x0D: "Ò", 0x0E: "Ó", 0x0F: "Ô",
    0x10: "Œ", 0x11: "Ù", 0x12: "Ú", 0x13: "Û", 0x14: "Ñ", 0x15: "ß", 0x16: "à",
    0x17: "á", 0x19: "ç", 0x1A: "è", 0x1B: "é", 0x1C: "ê", 0x1D: "ë", 0x1E: "ì",
    0x20: "î", 0x21: "ï", 0x22: "ò", 0x23: "ó", 0x24: "ô", 0x25: "œ", 0x26: "ù",
    0x27: "ú", 0x28: "û", 0x29: "ñ", 0x2A: "º", 0x2B: "ª", 0x2D: "&", 0x2E: "+",
    0x35: "=", 0x36: ";", 0x51: "¿", 0x52: "¡", 0x5A: "Í", 0x5B: "%", 0x5C: "(",
    0x5D: ")", 0x68: "â", 0x6F: "í", 0x79: "↑", 0x7A: "↓", 0x7B: "←", 0x7C: "→",
    0x85: "<", 0x86: ">",
    0xAB: "!", 0xAC: "?", 0xAD: ".", 0xAE: "-", 0xAF: "·", 0xB0: "…", 0xB1: "“",
    0xB2: "”", 0xB3: "‘", 0xB4: "’", 0xB5: "♂", 0xB6: "♀", 0xB7: "¥", 0xB8: ",",
    0xB9: "×", 0xBA: "/", 0xEF: "▶", 0xF0: ":",
    0xF1: "Ä", 0xF2: "Ö", 0xF3: "Ü", 0xF4: "ä", 0xF5: "ö", 0xF6: "ü",
}
for i in range(10):
    CARACTERES[0xA1 + i] = str(i)
for i in range(26):
    CARACTERES[0xBB + i] = chr(ord("A") + i)
    CARACTERES[0xD5 + i] = chr(ord("a") + i)

# Symboles spéciaux (une seule case dans la police, pas d'équivalent Unicode)
SYMBOLES = {
    0x2C: "ER", 0x34: "LV", 0x53: "PK", 0x54: "MN", 0x55: "PO", 0x56: "KE",
    0x57: "BL", 0x58: "OC", 0x59: "K", 0x84: "SUP_E", 0xA0: "SUP_RE",
}

# Codes de mise en page (un seul octet)
SAUTS = {0xFE: "\\n", 0xFA: "\\l", 0xFB: "\\p"}

# Variables remplacées à l'affichage (FD xx)
VARIABLES = {
    0x01: "PLAYER", 0x02: "STR_VAR_1", 0x03: "STR_VAR_2", 0x04: "STR_VAR_3",
    0x05: "KUN", 0x06: "RIVAL",
}

# Codes étendus FC xx : nombre d'octets d'arguments après xx
# (couleur, ombre, pause, musique, son... cf. pokefirered, GetExtCtrlCodeLength)
ARGS_FC = {
    0x00: 0, 0x01: 1, 0x02: 1, 0x03: 1, 0x04: 3, 0x05: 1, 0x06: 1, 0x07: 0,
    0x08: 1, 0x09: 0, 0x0A: 0, 0x0B: 2, 0x0C: 1, 0x0D: 1, 0x0E: 1, 0x0F: 0,
    0x10: 2, 0x11: 2, 0x12: 1, 0x13: 1, 0x14: 1, 0x15: 0, 0x16: 0, 0x17: 0,
    0x18: 0,
}

# Octets suivis d'un argument d'un octet (icône de bouton, symbole...)
AVEC_ARG = {0xF7: "F7", 0xF8: "F8", 0xF9: "F9"}

LETTRES = set(range(0xBB, 0xEF)) | {o for o, c in CARACTERES.items() if c.isalpha()}


class ChaineInvalide(Exception):
    """Les octets ne forment pas une chaîne de texte valide."""


def decoder(rom, adresse, longueur_max=2000):
    """Décode la chaîne qui commence à `adresse`.

    Renvoie (texte, nb_octets_avec_FF, nb_caracteres_visibles, nb_lettres).
    Lève ChaineInvalide si un octet inconnu apparaît avant le FF final.
    """
    morceaux = []
    visibles = lettres = 0
    i = adresse
    fin = min(len(rom), adresse + longueur_max)
    while i < fin:
        o = rom[i]
        if o == FIN:
            return "".join(morceaux), i - adresse + 1, visibles, lettres
        if o in CARACTERES:
            morceaux.append(CARACTERES[o])
            visibles += 1
            if o in LETTRES:
                lettres += 1
            i += 1
        elif o in SYMBOLES:
            morceaux.append("{" + SYMBOLES[o] + "}")
            visibles += 1
            i += 1
        elif o in SAUTS:
            morceaux.append(SAUTS[o])
            i += 1
        elif o == 0xFD:
            if i + 1 >= fin:
                raise ChaineInvalide(i)
            v = rom[i + 1]
            morceaux.append("{" + VARIABLES.get(v, f"FD {v:02X}") + "}")
            visibles += 1
            i += 2
        elif o == 0xFC:
            if i + 1 >= fin or rom[i + 1] not in ARGS_FC:
                raise ChaineInvalide(i)
            n = ARGS_FC[rom[i + 1]]
            octets = rom[i + 1:i + 2 + n]
            if len(octets) < n + 1:
                raise ChaineInvalide(i)
            morceaux.append("{FC " + " ".join(f"{b:02X}" for b in octets) + "}")
            i += 2 + n
        elif o in AVEC_ARG:
            if i + 1 >= fin:
                raise ChaineInvalide(i)
            morceaux.append("{" + AVEC_ARG[o] + f" {rom[i + 1]:02X}" + "}")
            visibles += 1
            i += 2
        else:
            raise ChaineInvalide(i)
    raise ChaineInvalide(i)  # pas de FF trouvé


# Tables inverses pour l'encodage
_INV_CARACTERES = {c: o for o, c in CARACTERES.items()}
_INV_ACCOLADES = {n: bytes([o]) for o, n in SYMBOLES.items()}
_INV_ACCOLADES.update({n: bytes([0xFD, v]) for v, n in VARIABLES.items()})
_INV_SAUTS = {"n": 0xFE, "l": 0xFA, "p": 0xFB}


def encoder(texte):
    """Encode un texte (notation ci-dessus) en octets, FF final compris."""
    sortie = bytearray()
    i = 0
    while i < len(texte):
        c = texte[i]
        if c == "\\":
            sortie.append(_INV_SAUTS[texte[i + 1]])
            i += 2
        elif c == "{":
            j = texte.index("}", i)
            code = texte[i + 1:j]
            if code in _INV_ACCOLADES:
                sortie += _INV_ACCOLADES[code]
            else:  # forme brute : {FC 01 02}, {FD 07}, {F8 00}
                sortie += bytes(int(x, 16) for x in code.split())
            i = j + 1
        elif c in _INV_CARACTERES:
            sortie.append(_INV_CARACTERES[c])
            i += 1
        else:
            raise ValueError(f"Caractère absent de la police : {c!r} dans {texte!r}")
    sortie.append(FIN)
    return bytes(sortie)
