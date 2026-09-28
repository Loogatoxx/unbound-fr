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

## 3. Dépôt GitHub et étape 2 : glossaire — 28/09/2026

**Prompt :** « oui tu peu faire un github sans probleme juste en priver, je te laisse continuer »

**Réponse :** Dépôt privé créé (https://github.com/Loogatoxx/unbound-fr) avec le commit de l'étape 1. Glossaire construit à partir des noms officiels de PokéAPI (téléchargement accepté) : 935 Pokémon et 782 attaques ont un nom français qui tient dans la limite, dont 169 grâce à des abréviations proposées (à relire). Restent à traduire : 33 capacités G-Max, 3 attaques, 22 talents et 28 objets propres à Unbound, et les 102 classes de dresseur.

**Modifications :**
- `outils/glossaire.py` : association anglais → français (exact, alias, capacités Max, noms tronqués par Unbound), mesure en octets, statuts (ok, nom long, trop long, à traduire), bilan
- `donnees/glossaire_choix.json` : 169 choix manuels (abréviations d'attaques et de Pokémon, Œuf, Œuf Abîmé, Guerrier)
- `docs/glossaire_bilan.md` (généré) : tableau récapitulatif et choix à relire
- `.gitignore` : références PokéAPI et glossaire calculé (régénérables) ; `README.md` : nouvelles commandes

**Objectif :** figer une fois pour toutes le nom français de chaque Pokémon, attaque, talent et objet avant de traduire les dialogues, pour que le jeu soit cohérent et qu'aucun nom ne dépasse sa place en mémoire. Les abréviations d'Unbound ont été identifiées grâce aux descriptions des capacités lues dans la ROM, et non devinées.

## 4. Noms des dresseurs conservés et fin de l'étape 2 — 28/09/2026

**Prompt :** « touche pas au nom de dresseur, faut que le jeu sois comprhensible si je dois racconter a quelqu un d autre si on commence a changer le nom des dresseur ça change une petite partie de l histoire et faut que se sois comprhensible par l ia si j ai des question sur le jeu continue »

**Réponse :** Règle adoptée et étendue aux noms propres d'Unbound (villes, organisations, personnages). Glossaire terminé : les 6 tables ont toutes un nom français qui tient en mémoire (directement ou par nom long), sans doublon.

**Modifications :**
- `donnees/glossaire_choix.json` : principes de traduction ; 33 capacités G-Max (noms officiels Poképédia sans « G-Max », « Hantise GMax » pour éviter le doublon avec Phantom Force) ; 3 attaques, 23 talents et 28 objets propres à Unbound ; 106 classes de dresseur (noms officiels vérifiés dans la catégorie Poképédia, 21 en traduction libre listées dans `_classes_traduction_libre`)
- `outils/glossaire.py` : règle Zarbi appliquée avant la recherche exacte (« Unown ? » → « Zarbi ? »)
- `README.md` : section « Principes de traduction »

**Objectif :** garder le jeu compréhensible et discutable avec les noms des guides anglais, tout en traduisant ce qui a un équivalent officiel. La recherche de doublons évite qu'un joueur voie deux attaques différentes sous le même nom.

## 5. Étape 4 avant l'étape 3 : vérificateur de largeur — 28/09/2026

**Prompt :** « oui ça me semble logique de faire comme ça »

**Réponse :** Vérificateur construit et testé. Table des largeurs de la police trouvée dans la ROM (`0x1fb100`) et validée sur les dialogues anglais : 99,9 % des lignes font au plus 206 px, pour une boîte de 208 px. Chaque texte est rattaché à sa « famille » (table de pointeurs = même fenêtre d'affichage), ce qui donne la limite de largeur de chaque fenêtre. Le commit de l'étape 2 reste en attente de ton accord.

**Modifications :**
- `outils/largeur.py` : recherche de la table des largeurs, mesure des lignes en pixels (variables comptées au pire cas)
- `outils/extraire.py` : champ `famille` sur chaque texte (identifiants inchangés, vérifié)
- `outils/verifier.py` : vérification (police, variables, largeur, structure des boîtes) et remise en forme automatique (découpage des lignes, typographie)
- `tests/test_verifier.py` : 10 tests, dont la contre-épreuve « l'anglais passe sans erreur » et un test qui prouve qu'il sait piéger avant de valider la protection
- `README.md`, `.gitignore` (rapport de vérification généré)

**Objectif :** que chaque lot traduit soit contrôlé et mis en page automatiquement. Tout est déduit des textes anglais d'Unbound (qui s'affichent correctement), jamais supposé. Les tests ont révélé que l'apostrophe droite et les guillemets « » n'existent pas dans la police : ils sont maintenant corrigés automatiquement.
