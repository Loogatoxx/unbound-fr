"""Tests du vérificateur de traductions.

Lancement : python3 -m unittest discover tests
Ils ont besoin de la ROM (non versionnée) et de donnees/textes_en.json :
sans eux, les tests sont ignorés au lieu d'échouer.
"""

import json
import sys
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "outils"))

ROM = RACINE / "rom" / "unbound_original.gba"
TEXTES = RACINE / "donnees" / "textes_en.json"


@unittest.skipUnless(ROM.exists() and TEXTES.exists(), "ROM ou textes extraits absents")
class TestVerificateur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from verifier import Verificateur
        cls.textes = [t for t in json.loads(TEXTES.read_text(encoding="utf-8")) if t["confiance"] != "basse"]
        cls.v = Verificateur(ROM.read_bytes(), cls.textes)
        # Un dialogue avec {PLAYER} et une 2e ligne, et une description d'attaque
        cls.dialogue = next(t for t in cls.textes if t["script"] and "{PLAYER}" in t["texte"]
                            and "\\n" in t["texte"] and "{FC" not in t["texte"])
        cls.description = next(t for t in cls.textes if t.get("famille") == "0x99f190" and not t["script"])

    def erreurs(self, ident, fr):
        return [m for niveau, m in self.v.verifier(ident, fr) if niveau == "ERREUR"]

    def test_l_anglais_passe_sans_erreur(self):
        """Contre-épreuve : l'anglais d'origine s'affiche bien en jeu, donc 0 erreur."""
        fautifs = [t["id"] for t in self.textes if self.erreurs(t["id"], t["texte"])]
        self.assertEqual(fautifs, [])

    def test_ligne_trop_large(self):
        fr = "{PLAYER} " + "m" * 40
        self.assertTrue(any("px" in m for m in self.erreurs(self.dialogue["id"], fr)))

    def test_variable_oubliee(self):
        fr = self.dialogue["texte"].replace("{PLAYER}", "Sacha")
        self.assertTrue(any("manquante" in m for m in self.erreurs(self.dialogue["id"], fr)))

    def test_caractere_hors_police(self):
        fr = self.dialogue["texte"] + " 5 €"
        self.assertTrue(any("police" in m for m in self.erreurs(self.dialogue["id"], fr)))

    def test_trois_lignes_dans_une_boite(self):
        fr = "{PLAYER} un\\ndeux\\ntrois"
        self.assertTrue(any("\\n dans une boîte" in m for m in self.erreurs(self.dialogue["id"], fr)))

    def test_reformater_corrige_une_phrase_longue(self):
        phrase = ("{PLAYER}, tu es enfin arrivé ! Je t'attendais depuis ce matin, "
                  "le professeur voulait absolument te parler avant ton départ vers la ville voisine.")
        propre = self.v.reformater(self.dialogue["id"], phrase)
        self.assertEqual(self.erreurs(self.dialogue["id"], propre), [])
        self.assertIn("\\n", propre)
        self.assertIn("\\l", propre)  # au-delà de 2 lignes, le texte défile

    def test_reformater_corrige_la_typographie(self):
        propre = self.v.reformater(self.dialogue["id"], "{PLAYER}, c'est « génial »... Vraiment !")
        self.assertIn("c’est", propre)
        self.assertIn("“génial”", propre)
        self.assertIn("…", propre)
        self.assertEqual(self.erreurs(self.dialogue["id"], propre), [])

    def test_point_d_exclamation_jamais_seul_en_debut_de_ligne(self):
        import verifier

        # Phrases de longueurs variées : certaines amènent le « ! » pile en fin de ligne
        phrases = ["{PLAYER} " + "mmmm " * n + "i" * k + " !" for n in range(12) for k in range(1, 8)]

        def lignes_commencant_par_exclamation():
            return [p for p in phrases
                    if any(l.startswith("!") for l in
                           self.v.reformater(self.dialogue["id"], p).replace("\\l", "\\n").split("\\n"))]

        # 1. Sans la protection, le piège fonctionne (sinon ce test ne prouverait rien)
        protection = verifier.PONCTUATION_COLLEE
        verifier.PONCTUATION_COLLEE = ()
        try:
            self.assertTrue(lignes_commencant_par_exclamation(), "aucune phrase ne piège : test inutile")
        finally:
            verifier.PONCTUATION_COLLEE = protection
        # 2. Avec la protection, plus aucun « ! » seul en début de ligne
        self.assertEqual(lignes_commencant_par_exclamation(), [])

    def test_reformater_garde_les_codes_entiers(self):
        phrase = "Tu as reçu {FC 01 02}la Clé Barrière{FC 01 01} ! " * 3
        propre = self.v.reformater(self.dialogue["id"], "{PLAYER} " + phrase)
        self.assertEqual(propre.count("{FC 01 02}"), 3)

    def test_description_sans_boite_supplementaire(self):
        fr = self.description["texte"] + "\\pSuite impossible."
        self.assertTrue(any("\\p" in m for m in self.erreurs(self.description["id"], fr)))


if __name__ == "__main__":
    unittest.main()
