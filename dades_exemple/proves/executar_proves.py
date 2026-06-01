#!/usr/bin/env python3
"""
Executa totes les proves d'auditoria i compara amb les respostes esperades.
Executar des de eina_auditoria_priv/:  py dades_exemple/proves/executar_proves.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from eina_auditoria_priv.model import DadesEntradaAuditoria
from eina_auditoria_priv.evaluator import avaluar, avaluar_per_tipus_dades
from eina_auditoria_priv.recommendations import generar_recomanacions
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "generar_esperades",
    Path(__file__).parent / "generar_esperades.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
generar_esperada = _mod.generar_esperada


def comparar(actual: dict, esperada: dict) -> list[str]:
    errors = []

    for camp in ("resum", "num_riscos", "num_recomanacions"):
        if actual.get(camp) != esperada.get(camp):
            errors.append(f"  {camp}: actual={actual.get(camp)!r} esperat={esperada.get(camp)!r}")

    def clau_finding(f: dict) -> tuple:
        return (f["criteri_id"], f.get("tractament_id"), f["resultat"])

    actual_nc = {clau_finding(f): f for f in actual.get("findings_no_compleix", [])}
    esperada_nc = {clau_finding(f): f for f in esperada.get("findings_no_compleix", [])}

    if set(actual_nc.keys()) != set(esperada_nc.keys()):
        nomes_actual = set(actual_nc) - set(esperada_nc)
        nomes_esperat = set(esperada_nc) - set(actual_nc)
        if nomes_actual:
            errors.append(f"  findings_no_compleix extra: {sorted(nomes_actual)}")
        if nomes_esperat:
            errors.append(f"  findings_no_compleix absents: {sorted(nomes_esperat)}")

    for tipus in set(actual.get("per_tipus_dades", {})) | set(esperada.get("per_tipus_dades", {})):
        a = actual.get("per_tipus_dades", {}).get(tipus, {})
        e = esperada.get("per_tipus_dades", {}).get(tipus, {})
        if a.get("num_no_compleix") != e.get("num_no_compleix"):
            errors.append(
                f"  per_tipus[{tipus}].num_no_compleix: actual={a.get('num_no_compleix')} esperat={e.get('num_no_compleix')}"
            )

    return errors


def main() -> int:
    base = Path(__file__).parent
    entrada_dir = base / "entrada"
    esperades_dir = base / "esperades"

    fitxers = sorted(entrada_dir.glob("*.json"))
    if not fitxers:
        print("No hi ha fitxers d'entrada.")
        return 1

    ok = 0
    ko = 0
    for fitxer in fitxers:
        esperada_path = esperades_dir / fitxer.name
        if not esperada_path.exists():
            print(f"KO  {fitxer.name} — falta fitxer esperat (executeu generar_esperades.py)")
            ko += 1
            continue

        with open(esperada_path, encoding="utf-8") as f:
            esperada = json.load(f)

        actual = generar_esperada(fitxer)
        errors = comparar(actual, esperada)

        if errors:
            print(f"KO  {fitxer.name}")
            for e in errors:
                print(e)
            ko += 1
        else:
            nc = actual["resum"].get("per_resultat", {}).get("no_compleix", 0)
            print(f"OK  {fitxer.name}  (no_compleix={nc}, riscos={actual['num_riscos']})")
            ok += 1

    print(f"\nResultat: {ok} OK, {ko} KO de {ok + ko} proves")
    return 0 if ko == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
