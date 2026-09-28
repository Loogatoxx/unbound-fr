# unbound-fr — traduction française de Pokémon Unbound

Outils pour traduire la ROM GBA de Pokémon Unbound (hack de Rouge Feu, moteur CFRU)
en français, en respectant les limites mémoire de la cartouche (32 Mo).

## Arborescence

- `rom/` — la ROM de travail (**jamais versionnée**), `unbound_original.gba` en lecture seule
- `outils/charmap.py` — table de caractères : décodage et encodage du texte du jeu
- `outils/extraire.py` — étape 1 : extraction des textes et bilan mémoire
- `outils/glossaire.py` — étape 2 : noms anglais → noms officiels français, contrôle des tailles
- `outils/largeur.py` — largeur en pixels d'un texte (table des largeurs de la police lue dans la ROM)
- `outils/verifier.py` — étape 4 : vérification et remise en forme des traductions
- `tests/` — tests automatiques (`python3 -m unittest discover tests`)
- `donnees/traductions/*.json` — les traductions, `{"T01234": "texte français"}`
- `donnees/glossaire_choix.json` — **choix manuels** (abréviations, créations d'Unbound) : le fichier à relire
- `donnees/` — textes extraits (`*_en.json`, régénérables) puis traductions
- `docs/etat_des_lieux.md` — bilan chiffré de l'étape 1
- `docs/glossaire_bilan.md` — bilan du glossaire et liste des choix à relire

## Utilisation

```bash
python3 outils/extraire.py rom/unbound_original.gba
```

Références PokéAPI (noms officiels, à télécharger une fois) :

```bash
mkdir -p donnees/reference && for f in pokemon_species_names move_names ability_names item_names type_names nature_names; do curl -sfL -o donnees/reference/$f.csv https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/$f.csv; done
```

```bash
python3 outils/glossaire.py
```

Vérifier les traductions (`--reformater` redécoupe d'abord les lignes et corrige la typographie) :

```bash
python3 outils/verifier.py --reformater
```

```bash
python3 -m unittest discover tests
```

Aucune dépendance : Python 3 standard suffit.

## Plan

1. ✅ Extraction et état des lieux
2. ✅ Glossaire (noms officiels français ; noms propres d'Unbound conservés)
3. Traduction par lots
4. ✅ Validation automatique (largeur en pixels, structure des boîtes, variables, typographie)
   — faite avant l'étape 3 pour contrôler chaque lot dès sa traduction
5. Réinsertion avec repointage, génération d'un patch `.bps`
6. Tests en jeu (mGBA)

Diffusion : uniquement sous forme de patch, jamais la ROM.

## Principes de traduction

- Les noms des dresseurs et les noms propres d'Unbound (villes, organisations, personnages)
  ne sont **jamais traduits** : l'histoire doit rester racontable et discutable avec les
  noms des guides.
- Ce qui a un nom officiel français prend ce nom (PokéAPI, Poképédia).
- Typographie : apostrophe ’, guillemets “ ” (les « » et ' n'existent pas dans la police),
  espace avant ! ? : ; comme dans les jeux Pokémon français. `--reformater` corrige tout seul.
- Ce qui dépasse sa place en mémoire est abrégé selon des règles fixes (voir
  `docs/glossaire_bilan.md`), jamais coupé au hasard.
