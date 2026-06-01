"""Proves de validació de l'estructura JSON d'entrada."""

import json
import unittest
from pathlib import Path

from eina_auditoria_priv.model import ValidacioDadesError, carregar_des_de_dict, validar_dict

_EXEMPLE_DIR = Path(__file__).resolve().parent.parent / "dades_exemple"


class TestValidacioTractaments(unittest.TestCase):
    def test_cas_error_tractaments_no_llista(self):
        path = _EXEMPLE_DIR / "cas_error_tractaments_no_llista.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validar_dict(data)
        self.assertTrue(errors)
        self.assertTrue(any("tractaments" in e for e in errors))
        with self.assertRaises(ValidacioDadesError):
            carregar_des_de_dict(data)

    def test_cas_mixt_carrega_ok(self):
        path = _EXEMPLE_DIR / "cas_mixt_3_tractaments.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(validar_dict(data), [])
        dades = carregar_des_de_dict(data)
        self.assertEqual(len(dades.tractaments), 3)


if __name__ == "__main__":
    unittest.main()
