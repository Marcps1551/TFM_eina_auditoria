"""
Importació de tractaments des de fitxer CSV.
Permet mapar columnes del CSV als camps del model (id, nom, finalitat, etc.).
"""

import csv
import io
from typing import Optional

from .model import Tractament


# Columnes que es poden mapear des del CSV (codi intern → etiqueta)
CAMPOS_TRACTAMENT = [
    ("id", "ID"),
    ("nom", "Nom del tractament"),
    ("finalitat", "Finalitat"),
    ("base_legal", "Base legal"),
    ("categories_dades", "Categories de dades (separades per coma)"),
    ("destinataris", "Destinataris (separats per coma)"),
    ("transferencies_internacionals", "Transferències internacionals (sí/no)"),
    ("termini_conservacio", "Termini de conservació"),
    ("mesures_seguretat", "Mesures de seguretat (separades per coma)"),
    ("dpo_assignat", "DPO assignat (sí/no)"),
    ("tipus_dades", "Tipus de dades (ex.: curriculums, treballadors, clients)"),
    ("conte_dades_sensibles", "Conté dades sensibles (sí/no)"),
    ("notes", "Notes"),
]


def _normalitzar_bool(val: str) -> bool:
    """Converteix text a booleà. Accepta la nomenclatura que vulgueu (sí/si/yes/1/true/cert = True; no/n/0/false = False)."""
    v = (val or "").strip().lower()
    if v in ("sí", "si", "s", "yes", "y", "1", "true", "cert", "x", "veritat"):
        return True
    if v in ("no", "n", "0", "false", "fals", "f"):
        return False
    # Qualsevol altre valor es considera False (camp no marcat / sense indicar)
    return False


def _llista_des_de_string(val: str) -> list[str]:
    """Converteix un string separat per comes o punt-i-coma en llista de strings."""
    if not val or not val.strip():
        return []
    return [s.strip() for s in val.replace(";", ",").split(",") if s.strip()]


def llegir_csv_raw(contingut: bytes | str) -> tuple[list[str], list[list[str]]]:
    """Llegeix CSV i retorna (capçaleres, files). Detecta encoding i separador."""
    if isinstance(contingut, bytes):
        try:
            text = contingut.decode("utf-8")
        except UnicodeDecodeError:
            text = contingut.decode("latin-1")
    else:
        text = contingut
    reader = csv.reader(io.StringIO(text), delimiter=";")
    rows = list(reader)
    if not rows:
        return [], []
    # Si la primera fila té una sola columna llarga, provar amb coma
    if len(rows[0]) == 1 and "," in rows[0][0]:
        reader = csv.reader(io.StringIO(text), delimiter=",")
        rows = list(reader)
    headers = [h.strip() for h in rows[0]]
    data = rows[1:]
    return headers, data


def construir_tractaments_des_de_csv(
    headers: list[str],
    rows: list[list[str]],
    mapping: dict[str, str],
) -> list[Tractament]:
    """
    Construeix la llista de Tractament a partir de files CSV mapades.

    Args:
        headers: Capçaleres del CSV.
        rows: Files de dades (sense capçalera).
        mapping: Diccionari camp_intern -> nom_columna CSV (ex. "nom" -> "Nom tractament").
    """
    tractaments = []
    for i, row in enumerate(rows):
        # Construir dict fila: nom_columna -> valor
        fila = {}
        for j, col in enumerate(headers):
            if j < len(row):
                fila[col] = row[j].strip() if row[j] else ""
        # Aplicar mapping
        def get(camp: str) -> str:
            col = mapping.get(camp)
            if not col:
                return ""
            return fila.get(col, "")

        id_val = get("id") or f"T{i+1:03d}"
        nom_val = get("nom") or id_val
        categories = _llista_des_de_string(get("categories_dades"))
        destinataris = _llista_des_de_string(get("destinataris"))
        mesures = _llista_des_de_string(get("mesures_seguretat"))
        transfer = _normalitzar_bool(get("transferencies_internacionals"))
        dpo = _normalitzar_bool(get("dpo_assignat"))
        termini = get("termini_conservacio") or None
        raw_bl = get("base_legal") or ""
        if isinstance(raw_bl, str):
            base_legal = [x.strip() for x in raw_bl.split(",") if x.strip()]
        elif isinstance(raw_bl, list):
            base_legal = [str(x).strip() for x in raw_bl if x and str(x).strip()]
        else:
            base_legal = []

        tipus_dades_val = get("tipus_dades") or None
        if tipus_dades_val and not tipus_dades_val.strip():
            tipus_dades_val = None
        conte_sensibles = _normalitzar_bool(get("conte_dades_sensibles"))
        tractaments.append(Tractament(
            id=id_val,
            nom=nom_val,
            finalitat=get("finalitat"),
            base_legal=base_legal,
            categories_dades=categories,
            destinataris=destinataris,
            transferencies_internacionals=transfer,
            termini_conservacio=termini,
            mesures_seguretat=mesures,
            dpo_assignat=dpo,
            tipus_dades=tipus_dades_val.strip() if tipus_dades_val else None,
            conte_dades_sensibles=conte_sensibles,
            notes=get("notes"),
        ))
    return tractaments
