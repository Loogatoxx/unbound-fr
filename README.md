# unbound-fr — traduction française de Pokémon Unbound

Outils pour traduire la ROM GBA de Pokémon Unbound (hack de Rouge Feu, moteur CFRU)
en français, en respectant les limites mémoire de la cartouche (32 Mo).

## Arborescence

- `rom/` — la ROM de travail (**jamais versionnée**), `unbound_original.gba` en lecture seule
- `outils/charmap.py` — table de caractères : décodage et encodage du texte du jeu
- `outils/extraire.py` — étape 1 : extraction des textes et bilan mémoire
- `donnees/` — textes extraits (`*_en.json`, régénérables) puis traductions
- `docs/etat_des_lieux.md` — bilan chiffré de l'étape 1

## Utilisation

```bash
python3 outils/extraire.py rom/unbound_original.gba
```

Aucune dépendance : Python 3 standard suffit.

## Plan

1. ✅ Extraction et état des lieux
2. Glossaire (noms officiels français + noms propres à Unbound)
3. Traduction par lots
4. Validation automatique (longueur, largeur en pixels, codes de contrôle)
5. Réinsertion avec repointage, génération d'un patch `.bps`
6. Tests en jeu (mGBA)

Diffusion : uniquement sous forme de patch, jamais la ROM.
