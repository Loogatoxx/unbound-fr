# État des lieux — Pokémon Unbound (étape 1)

ROM analysée : `rom/unbound_original.gba` (32 Mo)

## Tables de noms à taille fixe

Ces noms sont copiés dans des emplacements de taille fixe : la traduction ne doit
pas dépasser la taille maximale (octet FF de fin compris). Exception : quand la
colonne « noms longs » n'est pas nulle, le moteur CFRU accepte à la place un pointeur
vers un nom plus long (à vérifier en jeu : la fenêtre d'affichage peut le couper).

| Table | Adresse | Entrées | Taille max (FF compris) | Noms longs par pointeur | Nom le plus long actuel |
|---|---|---|---|---|---|
| pokemon | `0x166a98c` | 1294 | 11 | 0 | Charmander (11) |
| attaques | `0xa40a10` | 923 | 13 | 0 | ThunderPunch (13) |
| talents | `0xa36398` | 293 | 17 | 0 | Power Construct (16) |
| objets | `0x876200` | 729 | 14 | 33 | Braille Converter (18) |
| classes_dresseurs | `0x23e558` | 107 | 13 | 9 | Black Ferrothorn Boss (22) |
| dresseurs | `0x23eac8` | 743 | 12 | 0 | Bryce & Mag (12) |

## Textes trouvés par pointeurs

- Chaînes détectées : **35466** (confiance haute 21019, moyenne 382, sous-chaîne 180, basse 13885)
- Chaînes fiables (confiance haute) : **21019**, dont 8538 appelées depuis un script
- Volume fiable : **1,540,510 octets**, 1,448,211 caractères, ~297,282 mots
- Répartition par longueur : 1-20 car. : 5356, 21-100 car. : 11862, 101-300 car. : 3352, 300+ car. : 449
- Chaînes qui partagent des octets avec une autre : 553 (à traiter avec soin : les modifier sans repointer casserait l'autre)
- Vérification aller-retour décodage → encodage : **OK, 0 erreur**

## Espace libre dans la ROM

Estimation : blocs d'octets FF consécutifs (c'est ainsi que l'espace vide est
rempli). Un gros bloc de FF est presque toujours libre, un petit peut être une donnée.

- Blocs ≥ 4 Ko : **1,102,013 octets** (1076 Ko) en 68 blocs
- Blocs ≥ 256 octets : 1,683,585 octets (1644 Ko) en 539 blocs
- Plus grands blocs : `0x15fbc90` (336 Ko), `0xb2b280` (147 Ko), `0x1fe6c64` (100 Ko), `0x1b2938` (34 Ko), `0x1acd64` (20 Ko)

## Verdict mémoire

La ROM fait déjà 32 Mo, le maximum qu'une GBA peut adresser : impossible de l'agrandir.
Mais un texte déplacé (repointé) libère son ancienne place, qui redevient utilisable.

- Pire cas, tout le texte fiable réécrit avec +25 % : **1,925,637 octets**
- Place disponible = espace libre (1,102,013) + anciennes places récupérées (1,540,510) = **2,642,523 octets**
- Marge : 716,886 octets (le français peut être en moyenne jusqu'à +72 % plus long que l'anglais)
- ✅ Ça tient, **à condition** de connaître tous les pointeurs de chaque texte déplacé (un pointeur oublié = texte corrompu en jeu) et de rester concis.
