# Historique des prompts — unbound-fr

## 1. Faisabilité du projet — 28/09/2026

**Prompt :** « j ai un projet tres lourd pour toi pense tu etre capable de traduire la rom GBA de pokemon unbound en Francais tout en pensant au choix tecnique des mot pour pas depasser les memoir allouer »

**Réponse :** Oui, mais en projet de plusieurs semaines. Explication des trois contraintes mémoire (champs de taille fixe, largeur des boîtes en pixels, espace libre de la ROM), du repointage, et d'un plan en 6 étapes. Rappel : diffuser uniquement un patch, demander l'accord de l'auteur (Skeli).

**Modifications :** aucune (discussion).

**Objectif :** cadrer le projet et ses limites techniques avant d'écrire du code.

## 2. Étape 1 : extraction et état des lieux — 28/09/2026

**Prompt :** « @"/Users/carlos/Downloads/1636 - Pokemon Fire Red (U)(Squirrels) (patched).gba" voici la rom oui tu peu ranger comme ça et on fait d abord l etape une »

**Réponse :** ROM identifiée comme Unbound (base Rouge Feu BPRE, 32 Mo). Extraction faite : 6 tables de noms, ~21 000 textes fiables (~1,54 Mo), ~1,1 Mo d'espace libre. Verdict : la traduction tient en mémoire à condition de repointer proprement et de rester concis. Découverte : le moteur CFRU accepte des « noms longs » par pointeur pour les objets et les classes de dresseur.

**Modifications :**
- Création de `~/Projets/unbound-fr/` (`rom/`, `outils/`, `donnees/`, `docs/`), copie de la ROM en lecture seule dans `rom/unbound_original.gba`
- `outils/charmap.py` : table de caractères Rouge Feu, décodage et encodage réversibles
- `outils/extraire.py` : repérage des tables (Pokémon, attaques, talents, objets, classes de dresseur, dresseurs), balayage des pointeurs, classement des textes par confiance, estimation de l'espace libre, vérification aller-retour, bilan
- `docs/etat_des_lieux.md` (généré), `donnees/tables_en.json` et `donnees/textes_en.json` (générés, non versionnés)
- `.gitignore` (ROM, textes extraits), `README.md`

**Objectif :** savoir combien de texte il y a, où il se trouve et combien de place reste avant de s'engager sur la traduction. La vérification aller-retour (décoder puis réencoder redonne exactement les mêmes octets) garantit que la réinsertion future ne corrompra pas la ROM à cause de la table de caractères.
