#!/usr/bin/env python3
"""
Genera fitxers de resposta esperada a partir de les entrades de prova.
Executar des de eina_auditoria_priv/:  py dades_exemple/proves/generar_esperades.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from eina_auditoria_priv.model import DadesEntradaAuditoria
from eina_auditoria_priv.evaluator import avaluar, avaluar_per_tipus_dades
from eina_auditoria_priv.recommendations import generar_recomanacions


def finding_to_dict(f) -> dict:
    return {
        "criteri_id": f.criteri_id,
        "resultat": f.resultat.value,
        "nivell_risc": f.nivell_risc.value,
        "descripcio": f.descripcio,
        "tractament_id": f.tractament_id,
        "tractament_nom": f.tractament_nom,
    }


def generar_esperada(entrada_path: Path) -> dict:
    with open(entrada_path, encoding="utf-8") as f:
        dades_dict = json.load(f)
    dades = DadesEntradaAuditoria.from_dict(dades_dict)
    resultat = avaluar(dades)
    recomanacions = generar_recomanacions(resultat)
    per_tipus = avaluar_per_tipus_dades(dades)

    no_compleix = [finding_to_dict(f) for f in resultat.findings if f.resultat.value == "no_compleix"]
    sense_dades = [finding_to_dict(f) for f in resultat.findings if f.resultat.value == "sense_dades"]

    return {
        "fitxer_entrada": entrada_path.name,
        "resum": resultat.resum,
        "num_riscos": len(resultat.riscos),
        "num_recomanacions": len(recomanacions),
        "findings_no_compleix": no_compleix,
        "findings_sense_dades": sense_dades,
        "riscos": [
            {
                "id": r.id,
                "titol": r.titol,
                "nivell": r.nivell.value,
                "tractament_id": r.tractament_id,
            }
            for r in resultat.riscos
        ],
        "per_tipus_dades": {
            tipus: {
                "resum": res.resum,
                "num_no_compleix": res.resum.get("per_resultat", {}).get("no_compleix", 0),
            }
            for tipus, res in per_tipus.items()
        },
    }


def main() -> int:
    entrada_dir = Path(__file__).parent / "entrada"
    esperades_dir = Path(__file__).parent / "esperades"
    esperades_dir.mkdir(exist_ok=True)

    fitxers = sorted(entrada_dir.glob("*.json"))
    if not fitxers:
        print("No hi ha fitxers d'entrada a", entrada_dir)
        return 1

    for fitxer in fitxers:
        esperada = generar_esperada(fitxer)
        out = esperades_dir / fitxer.name
        with open(out, "w", encoding="utf-8") as f:
            json.dump(esperada, f, ensure_ascii=False, indent=2)
        nc = esperada["resum"].get("per_resultat", {}).get("no_compleix", 0)
        print(f"  {fitxer.name} -> {out.name}  (no_compleix={nc}, riscos={esperada['num_riscos']})")

    print(f"\nGenerades {len(fitxers)} respostes esperades a {esperades_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
