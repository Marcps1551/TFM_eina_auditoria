"""
API REST per al frontend React.
Endpoints: dades, executar auditoria, plantilles, import ROPA, export.
"""

import io
import json
import traceback
import uuid
from pathlib import Path
from datetime import datetime

from flask import Blueprint, request, jsonify, send_file, Response

from .model import DadesEntradaAuditoria
from .criteria import get_checklist_metadata
from .constants import (
    MESURES_SEGURETAT_PREDEFINIDES,
    TERMINI_OPCIONS_PREDEFINIDES,
    TERMINI_UNITATS,
    CATEGORIES_DADES_PREDEFINIDES,
)
from .evaluator import avaluar_per_tipus_dades, avaluar
from .recommendations import generar_recomanacions
from .reports import resultat_a_dict
from .ropa_import import ropa_to_internal


# Emmagatzematge en memòria (compartit amb webapp si cal)
_informes_guardats: dict[str, dict] = {}
_dades_session: dict[str, dict] = {}  # session_id -> dades (per API sense cookies)


api = Blueprint("api", __name__, url_prefix="/api")

# Ruta base de plantilles (relativa al cwd o al paquet)
PLANTILLES_DIR = Path(__file__).resolve().parent.parent / "dades_exemple" / "plantilles"


def _get_plantilles_dir() -> Path:
    if PLANTILLES_DIR.exists():
        return PLANTILLES_DIR
    return Path("dades_exemple") / "plantilles"


@api.route("/plantilles", methods=["GET"])
def list_plantilles():
    """Llista les plantilles disponibles (id, nom, descripcio)."""
    base = _get_plantilles_dir()
    if not base.exists():
        return jsonify([])
    out = []
    for f in sorted(base.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            out.append({
                "id": data.get("id", f.stem),
                "nom": data.get("nom", f.stem),
                "descripcio": data.get("descripcio", ""),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return jsonify(out)


@api.route("/plantilles/<plantilla_id>", methods=["GET"])
def get_plantilla(plantilla_id: str):
    """Retorna les dades de la plantilla (format DadesEntradaAuditoria)."""
    base = _get_plantilles_dir()
    # Cercar per id o per nom de fitxer
    for f in base.glob("*.json"):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            if data.get("id") == plantilla_id or f.stem == plantilla_id:
                dades = data.get("dades", data)
                if "dades" in data:
                    dades = data["dades"]
                # Assegurar format vàlid
                DadesEntradaAuditoria.from_dict(dades)
                return jsonify(dades)
        except (json.JSONDecodeError, OSError, Exception):
            continue
    return jsonify({"error": "Plantilla no trobada"}), 404


@api.route("/checklist-metadata", methods=["GET"])
def checklist_metadata():
    """Retorna la llista de controls del checklist amb base_legal per filtrar per bases dels tractaments."""
    return jsonify(get_checklist_metadata())


@api.route("/mesures-seguretat", methods=["GET"])
def mesures_seguretat():
    """Retorna les mesures de seguretat preestablertes (per seleccionar als tractaments)."""
    return jsonify(MESURES_SEGURETAT_PREDEFINIDES)


@api.route("/termini-opcions", methods=["GET"])
def termini_opcions():
    """Opcions preestablertes per al termini de conservació (predefinits + unitats per valor numèric)."""
    return jsonify({
        "predefinits": TERMINI_OPCIONS_PREDEFINIDES,
        "unitats": TERMINI_UNITATS,
    })


@api.route("/categories-dades", methods=["GET"])
def categories_dades():
    """Categories de dades personals preestablertes (per afegir als tractaments)."""
    return jsonify(CATEGORIES_DADES_PREDEFINIDES)


@api.route("/import/ropa", methods=["POST"])
def import_ropa():
    """Accepta JSON tipus ROPA i retorna dades en format intern."""
    try:
        body = request.get_json(force=True, silent=True)
        if not body:
            return jsonify({"error": "JSON invàlid o buit"}), 400
        internal = ropa_to_internal(body)
        # Validar que el model ho accepta
        DadesEntradaAuditoria.from_dict(internal)
        return jsonify(internal)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api.route("/dades", methods=["POST"])
def post_dades():
    """Valida i opcionalment desa les dades (body = JSON DadesEntradaAuditoria)."""
    try:
        d = request.get_json(force=True, silent=True)
        if not d:
            return jsonify({"error": "JSON invàlid o buit"}), 400
        DadesEntradaAuditoria.from_dict(d)
        # Opcional: desar a sessió per executar després (usant session_id al body o header)
        session_id = request.headers.get("X-Session-Id") or request.json.get("_session_id")
        if session_id:
            _dades_session[session_id] = d
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


def _gravetat_order(val):
    """Ordre per gravetat: els més greus primer (alt=0, mitja=1, baix=2, informat=3)."""
    v = (val or "").lower()
    return {"alt": 0, "mitja": 1, "baix": 2, "informat": 3}.get(v, 4)


def _ordenar_bloc_per_gravetat(bloc: dict) -> None:
    """Ordena riscos i recomanacions del bloc per gravetat (més greus a dalt). Modifica el bloc in-place."""
    if bloc.get("riscos"):
        bloc["riscos"] = sorted(bloc["riscos"], key=lambda r: _gravetat_order(r.get("nivell")))
    if bloc.get("recomanacions"):
        bloc["recomanacions"] = sorted(bloc["recomanacions"], key=lambda r: _gravetat_order(r.get("prioritat")))


def _te_tractament(item: dict) -> bool:
    """True si l'element (finding, risc o recomanació) té tractament_id o tractament_nom."""
    return bool(item.get("tractament_id") or item.get("tractament_nom"))


def _recalcular_resum_bloc(bloc: dict) -> dict:
    """Recalcula el resum a partir dels findings del bloc."""
    findings = bloc.get("findings", [])
    per_resultat = {}
    per_nivell = {}
    for f in findings:
        r = f.get("resultat")
        if r:
            per_resultat[r] = per_resultat.get(r, 0) + 1
        n = f.get("nivell_risc")
        if n:
            per_nivell[n] = per_nivell.get(n, 0) + 1
    resum = (bloc.get("resum") or {}).copy()
    resum["per_resultat"] = per_resultat
    resum["per_nivell_risc"] = per_nivell
    resum["total_criteris"] = len(findings)
    return {
        **bloc,
        "resum": resum,
        "findings": findings,
        "riscos": bloc.get("riscos", []),
        "recomanacions": bloc.get("recomanacions", []),
    }


def _filtrar_bloc_nomes_tractaments(bloc: dict) -> dict:
    """
    Deixa només els findings, riscos i recomanacions amb tractament_id (exclou generals).
    Recalcula el resum a partir dels findings filtrats.
    """
    findings = [f for f in bloc.get("findings", []) if _te_tractament(f)]
    riscos = [r for r in bloc.get("riscos", []) if _te_tractament(r)]
    recomanacions = [r for r in bloc.get("recomanacions", []) if _te_tractament(r)]
    return _recalcular_resum_bloc({
        **bloc,
        "findings": findings,
        "riscos": riscos,
        "recomanacions": recomanacions,
    })


def _build_informe(dades: DadesEntradaAuditoria) -> dict:
    """Construcció de l'informe: primera pestanya 'Totals' (avaluació global) i després una per tipus de dades."""
    # Pestanya "Totals": avaluació amb tots els tractaments
    resultat_totals = avaluar(dades)
    recomanacions_totals = generar_recomanacions(resultat_totals)
    bloc_totals = resultat_a_dict(resultat_totals, recomanacions_totals, dades)
    _ordenar_bloc_per_gravetat(bloc_totals)
    inf_dict = {
        "meta": bloc_totals["meta"],
        "tipus_dades": ["Totals"],
        "per_tipus": {
            "Totals": {
                "resum": bloc_totals["resum"],
                "findings": bloc_totals["findings"],
                "riscos": bloc_totals["riscos"],
                "recomanacions": bloc_totals["recomanacions"],
            },
        },
    }
    # Pestanyes per tipus de dades: només resultats explícits per tractament (sense generals)
    resultats_per_tipus = avaluar_per_tipus_dades(dades)
    for tipus in sorted(resultats_per_tipus.keys()):
        resultat = resultats_per_tipus[tipus]
        recomanacions = generar_recomanacions(resultat)
        bloc = resultat_a_dict(resultat, recomanacions, dades)
        _ordenar_bloc_per_gravetat(bloc)
        bloc = _filtrar_bloc_nomes_tractaments(bloc)
        inf_dict["tipus_dades"].append(tipus)
        inf_dict["per_tipus"][tipus] = {
            "resum": bloc["resum"],
            "findings": bloc["findings"],
            "riscos": bloc["riscos"],
            "recomanacions": bloc["recomanacions"],
        }
    return inf_dict


def _json_serializable(obj):
    """Converteix objectes no estàndard a tipus JSON-serialitzables."""
    if hasattr(obj, "value"):  # Enum
        return obj.value
    if hasattr(obj, "isoformat"):  # datetime/date
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


@api.route("/auditoria/executar", methods=["POST"])
def executar_auditoria():
    """Rep les dades al body, executa l'auditoria i retorna l'informe per tipus."""
    try:
        d = request.get_json(force=True, silent=True)
        if not d:
            return jsonify({"error": "Cal enviar les dades d'auditoria en JSON"}), 400
        dades = DadesEntradaAuditoria.from_dict(d)
        inf_dict = _build_informe(dades)
        inf_dict["dades_guardades"] = d
        informe_id = str(uuid.uuid4())
        _informes_guardats[informe_id] = inf_dict
        payload = {"informe_id": informe_id, "informe": inf_dict}
        body = json.dumps(payload, default=_json_serializable, ensure_ascii=False)
        return Response(body, status=200, mimetype="application/json; charset=utf-8")
    except Exception as e:
        tb = traceback.format_exc()
        try:
            err_body = json.dumps({"error": str(e), "traceback": tb}, ensure_ascii=False)
        except Exception:
            err_body = json.dumps({"error": str(e)})
        return Response(err_body, status=500, mimetype="application/json; charset=utf-8")


@api.route("/informe/<informe_id>", methods=["GET"])
def get_informe(informe_id: str):
    """Retorna l'informe guardat (per export o consulta)."""
    inf = _informes_guardats.get(informe_id)
    if not inf:
        return jsonify({"error": "Informe no trobat"}), 404
    return jsonify(inf)


def _generar_txt(inf: dict) -> str:
    """Genera text pla de l'informe segmentat per tipus de dades."""
    meta = inf.get("meta", {})
    per_tipus = inf.get("per_tipus", {}) or {"General": inf}
    lines = [
        "=" * 60,
        "INFORME D'AUDITORIA DE PRIVACITAT",
        "=" * 60,
        "",
        f"Organització: {meta.get('nom_organitzacio', '—')}",
        f"Data: {meta.get('data_auditoria', '—')}",
        "",
    ]
    for tipus in inf.get("tipus_dades", list(per_tipus.keys())):
        bloc = per_tipus.get(tipus, {})
        resum = bloc.get("resum", {})
        lines.extend([
            "", "=" * 60, f" TIPUS: {tipus.upper()} ", "=" * 60, "",
            "--- RESUM ---", "",
        ])
        for k, v in resum.get("per_resultat", {}).items():
            lines.append(f"  {k}: {v}")
        for k, v in resum.get("per_nivell_risc", {}).items():
            lines.append(f"  Risc {k}: {v}")
        lines.extend(["", "--- RESULTATS ---", ""])
        for f in bloc.get("findings", []):
            lines.append(f"[{f['resultat'].upper()}] {f['nom_criteri']}")
            lines.append(f"  {f['descripcio']}")
        lines.extend(["", "--- RISCOS ---", ""])
        for r in bloc.get("riscos", []):
            lines.append(f"- [{r['nivell'].upper()}] {r['titol']}")
            lines.append(f"  {r['descripcio']}")
        lines.extend(["", "--- RECOMANACIONS ---", ""])
        for rec in bloc.get("recomanacions", []):
            lines.append(f"- {rec['titol']} ({rec['prioritat']})")
            lines.append(f"  {rec['descripcio']}")
            for a in rec.get("accions", []):
                lines.append(f"  · {a}")
            lines.append("")
    return "\n".join(lines)


def _generar_html(inf: dict) -> str:
    """Genera HTML de l'informe segmentat per tipus de dades."""
    meta = inf.get("meta", {})
    per_tipus = inf.get("per_tipus", {}) or {"General": inf}
    def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    parts = [
        """<!DOCTYPE html><html lang="ca"><head><meta charset="utf-8"><title>Informe auditoria</title>
<style>body{font-family:system-ui,sans-serif;max-width:800px;margin:0 auto;padding:1rem;} .badge{display:inline-block;padding:.25rem .5rem;border-radius:4px;margin-right:.5rem;} .compleix{background:#c6f6d5;} .no_compleix{background:#fed7d7;} .finding{margin:.75rem 0;padding:.75rem;background:#f8fafc;border-radius:6px;} .tipus-section{margin-top:2rem;border-top:1px solid #e2e8f0;padding-top:1.5rem;}</style></head><body>""",
        f"<h1>Informe d'auditoria de privacitat</h1><p><strong>Organització:</strong> {esc(meta.get('nom_organitzacio','—'))} · <strong>Data:</strong> {esc(meta.get('data_auditoria','—'))}</p>",
    ]
    for tipus in inf.get("tipus_dades", list(per_tipus.keys())):
        bloc = per_tipus.get(tipus, {})
        resum = bloc.get("resum", {})
        parts.append(f'<div class="tipus-section"><h2>Tipus de dades: {esc(tipus)}</h2><p>')
        for k, v in resum.get("per_resultat", {}).items():
            cls = "compleix" if k == "compleix" else "no_compleix" if k == "no_compleix" else ""
            parts.append(f'<span class="badge {cls}">{esc(k)}: {v}</span>')
        for k, v in resum.get("per_nivell_risc", {}).items():
            parts.append(f'<span class="badge">{esc(k)}: {v}</span>')
        parts.append("</p><h3>Resultats</h3>")
        for f in bloc.get("findings", []):
            parts.append(f'<div class="finding"><strong>[{esc(f["resultat"])}]</strong> {esc(f["nom_criteri"])}<br>{esc(f["descripcio"])}</div>')
        parts.append("<h3>Riscos</h3>")
        for r in bloc.get("riscos", []):
            parts.append(f'<div class="finding"><strong>[{esc(r["nivell"])}]</strong> {esc(r["titol"])}<br>{esc(r["descripcio"])}</div>')
        parts.append("<h3>Recomanacions</h3>")
        for rec in bloc.get("recomanacions", []):
            parts.append(f'<div class="finding"><strong>{esc(rec["titol"])}</strong><br>{esc(rec["descripcio"])}<ul>')
            for a in rec.get("accions", []):
                parts.append(f"<li>{esc(a)}</li>")
            parts.append("</ul></div>")
        parts.append("</div>")
    parts.append("</body></html>")
    return "".join(parts)


@api.route("/informe/<informe_id>/export/<format_type>", methods=["GET"])
def export_informe(informe_id: str, format_type: str):
    """Exporta l'informe en JSON, TXT o HTML."""
    inf = _informes_guardats.get(informe_id)
    if not inf:
        return jsonify({"error": "Informe no trobat"}), 404
    if format_type == "json":
        buf = io.BytesIO()
        buf.write(json.dumps(inf, ensure_ascii=False, indent=2).encode("utf-8"))
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name="informe_auditoria.json", mimetype="application/json")
    if format_type == "txt":
        text = _generar_txt(inf)
        buf = io.BytesIO(text.encode("utf-8"))
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name="informe_auditoria.txt", mimetype="text/plain; charset=utf-8")
    if format_type == "html":
        html = _generar_html(inf)
        buf = io.BytesIO(html.encode("utf-8"))
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name="informe_auditoria.html", mimetype="text/html; charset=utf-8")
    return jsonify({"error": "Format no vàlid (json, txt, html)"}), 400
