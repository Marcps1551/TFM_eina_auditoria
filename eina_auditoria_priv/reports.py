"""
Generació d'informes d'auditoria: JSON, text i HTML.
"""

import json
from datetime import datetime
from pathlib import Path

from .evaluator import ResultatAvaluacio, Finding, RiscIdentificat
from .recommendations import Recomanacio, generar_recomanacions
from .model import DadesEntradaAuditoria


def resultat_a_dict(
    resultat: ResultatAvaluacio,
    recomanacions: list[Recomanacio],
    dades: DadesEntradaAuditoria,
) -> dict:
    """Converteix el resultat complet a un diccionari serialitzable (JSON)."""
    return {
        "meta": {
            "nom_organitzacio": str(dades.nom_organitzacio or ""),
            "data_auditoria": str(dades.data_auditoria or datetime.now().strftime("%Y-%m-%d")),
            "data_informe": datetime.now().isoformat(),
        },
        "resum": resultat.resum,
        "findings": [
            {
                "criteri_id": f.criteri_id,
                "nom_criteri": f.nom_criteri,
                "referencia_normativa": f.referencia_normativa,
                "resultat": f.resultat.value,
                "descripcio": f.descripcio,
                "nivell_risc": f.nivell_risc.value,
                "tractament_id": getattr(f, "tractament_id", None),
                "tractament_nom": getattr(f, "tractament_nom", None),
            }
            for f in resultat.findings
        ],
        "riscos": [
            {
                "id": r.id,
                "titol": r.titol,
                "descripcio": r.descripcio,
                "nivell": r.nivell.value,
                "criteris_relacionats": r.criteris_relacionats,
                "referencia": r.referencia,
                "tractament_id": getattr(r, "tractament_id", None),
                "tractament_nom": getattr(r, "tractament_nom", None),
            }
            for r in resultat.riscos
        ],
        "recomanacions": [
            {
                "id": r.id,
                "titol": r.titol,
                "descripcio": r.descripcio,
                "accions": r.accions,
                "referencia_normativa": r.referencia_normativa,
                "prioritat": r.prioritat.value,
                "criteri_origen": r.criteri_origen,
                "tractament_id": getattr(r, "tractament_id", None),
                "tractament_nom": getattr(r, "tractament_nom", None),
            }
            for r in recomanacions
        ],
    }


def exportar_json(
    resultat: ResultatAvaluacio,
    recomanacions: list[Recomanacio],
    dades: DadesEntradaAuditoria,
    path: str | Path,
) -> None:
    """Exporta l'informe complet en JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    d = resultat_a_dict(resultat, recomanacions, dades)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def exportar_text(
    resultat: ResultatAvaluacio,
    recomanacions: list[Recomanacio],
    dades: DadesEntradaAuditoria,
    path: str | Path | None = None,
) -> str:
    """Genera l'informe en text pla. Si path és donat, escriu al fitxer."""
    lines = [
        "=" * 60,
        "INFORME D'AUDITORIA DE PRIVACITAT",
        "=" * 60,
        "",
        f"Organització: {dades.nom_organitzacio or '(no indicada)'}",
        f"Data auditoria: {dades.data_auditoria or '(no indicada)'}",
        f"Data informe: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "--- RESUM ---",
        "",
    ]
    r = resultat.resum
    for k, v in r.get("per_resultat", {}).items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    for k, v in r.get("per_nivell_risc", {}).items():
        lines.append(f"  Risc {k}: {v}")
    lines.extend(["", "--- RESULTATS PER CRITERI ---", ""])
    for f in resultat.findings:
        tractament_info = (getattr(f, "tractament_nom", None) or getattr(f, "tractament_id", None)) or "General"
        lines.append(f"[{f.resultat.value.upper()}] {f.nom_criteri} ({f.criteri_id}) — Tractament: {tractament_info}")
        lines.append(f"  {f.descripcio}")
        lines.append(f"  Referència: {f.referencia_normativa}")
        lines.append("")
    lines.extend(["", "--- RISCOS IDENTIFICATS ---", ""])
    for r in resultat.riscos:
        tractament_info = (getattr(r, "tractament_nom", None) or getattr(r, "tractament_id", None)) or "General"
        lines.append(f"- [{r.nivell.value.upper()}] {r.titol} — Tractament: {tractament_info}")
        lines.append(f"  {r.descripcio}")
        lines.append("")
    lines.extend(["", "--- RECOMANACIONS ---", ""])
    for rec in recomanacions:
        tractament_info = (getattr(rec, "tractament_nom", None) or getattr(rec, "tractament_id", None)) or "General"
        lines.append(f"- {rec.titol} (prioritat: {rec.prioritat.value}) — Tractament: {tractament_info}")
        lines.append(f"  {rec.descripcio}")
        for a in rec.accions:
            lines.append(f"  · {a}")
        lines.append(f"  Referència: {rec.referencia_normativa}")
        lines.append("")
    lines.append("=" * 60)
    text = "\n".join(lines)
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return text


def exportar_html(
    resultat: ResultatAvaluacio,
    recomanacions: list[Recomanacio],
    dades: DadesEntradaAuditoria,
    path: str | Path,
) -> None:
    """Genera un informe HTML senzill i llegible."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    r = resultat.resum
    per_resultat = r.get("per_resultat", {})
    per_nivell = r.get("per_nivell_risc", {})

    html_parts = [
        """<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Informe d'auditoria de privacitat</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 1rem; background: #f5f5f5; }
    h1 { color: #1a365d; border-bottom: 2px solid #2b6cb0; }
    h2 { color: #2d3748; margin-top: 1.5rem; }
    .meta { color: #718096; font-size: 0.95rem; margin-bottom: 1.5rem; }
    .resum { display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0; }
    .badge { padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.85rem; }
    .compleix { background: #c6f6d5; color: #22543d; }
    .no_compleix { background: #fed7d7; color: #742a2a; }
    .sense_dades { background: #e2e8f0; color: #2d3748; }
    .alt { background: #fed7d7; }
    .mitja { background: #feebc8; }
    .baix { background: #c6f6d5; }
    .finding { margin: 0.75rem 0; padding: 0.75rem; background: #fff; border-radius: 6px; border-left: 4px solid #cbd5e0; }
    .finding.no_compleix { border-left-color: #e53e3e; }
    .finding.compleix { border-left-color: #38a169; }
    .referencia { font-size: 0.85rem; color: #718096; margin-top: 0.25rem; }
    ul.accions { margin: 0.5rem 0; padding-left: 1.25rem; }
    footer { margin-top: 2rem; font-size: 0.85rem; color: #718096; }
  </style>
</head>
<body>
  <h1>Informe d'auditoria de privacitat</h1>
  <div class="meta">
    <strong>Organització:</strong> """,
        esc(dades.nom_organitzacio or "—"),
        " &middot; <strong>Data auditoria:</strong> ",
        esc(dades.data_auditoria or "—"),
        " &middot; <strong>Data informe:</strong> ",
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        """
  </div>
  <h2>Resum</h2>
  <div class="resum">""",
    ]
    for k, v in per_resultat.items():
        cls = "compleix" if k == "compleix" else ("no_compleix" if k == "no_compleix" else "sense_dades")
        html_parts.append(f'<span class="badge {cls}">{esc(k)}: {v}</span>')
    for k, v in per_nivell.items():
        html_parts.append(f'<span class="badge {k}">Risc {esc(k)}: {v}</span>')
    html_parts.append("""
  </div>
  <h2>Resultats per criteri</h2>""")
    for f in resultat.findings:
        tractament_info = (getattr(f, "tractament_nom", None) or getattr(f, "tractament_id", None)) or "General"
        cls = "compleix" if f.resultat.value == "compleix" else ("no_compleix" if f.resultat.value == "no_compleix" else "")
        html_parts.append(f'  <div class="finding {cls}">')
        html_parts.append(f'    <strong>[{esc(f.resultat.value)}]</strong> {esc(f.nom_criteri)} <span class="tractament">— {esc(tractament_info)}</span><br>')
        html_parts.append(f'    {esc(f.descripcio)}')
        html_parts.append(f'    <div class="referencia">Referència: {esc(f.referencia_normativa)}</div>')
        html_parts.append("  </div>")
    html_parts.append("  <h2>Riscos identificats</h2>")
    for r in resultat.riscos:
        tractament_info = (getattr(r, "tractament_nom", None) or getattr(r, "tractament_id", None)) or "General"
        html_parts.append(f'  <div class="finding no_compleix">')
        html_parts.append(f'    <strong>[{esc(r.nivell.value)}]</strong> {esc(r.titol)} <span class="tractament">— {esc(tractament_info)}</span><br>')
        html_parts.append(f'    {esc(r.descripcio)}')
        html_parts.append("  </div>")
    html_parts.append("  <h2>Recomanacions</h2>")
    for rec in recomanacions:
        tractament_info = (getattr(rec, "tractament_nom", None) or getattr(rec, "tractament_id", None)) or "General"
        html_parts.append(f'  <div class="finding">')
        html_parts.append(f'    <strong>{esc(rec.titol)}</strong> <span class="badge {rec.prioritat.value}">{esc(rec.prioritat.value)}</span> <span class="tractament">— {esc(tractament_info)}</span><br>')
        html_parts.append(f'    {esc(rec.descripcio)}')
        html_parts.append('    <ul class="accions">')
        for a in rec.accions:
            html_parts.append(f'      <li>{esc(a)}</li>')
        html_parts.append("    </ul>")
        html_parts.append(f'    <div class="referencia">Referència: {esc(rec.referencia_normativa)}</div>')
        html_parts.append("  </div>")
    html_parts.append("""
  <footer>
    Informe generat per l'eina d'auditoria de privacitat (TFM – Màster Ciberseguretat).
    Les recomanacions tenen caràcter orientatiu i no constitueixen assessorament jurídic.
  </footer>
</body>
</html>""")
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(html_parts))
