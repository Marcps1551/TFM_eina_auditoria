"""
Interfície web (Flask) per a l'eina d'auditoria de privacitat.
Permet importar JSON/CSV, mapar columnes del CSV i executar l'auditoria.
"""

import io
import json
import tempfile
import uuid
from pathlib import Path
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    flash,
)
from werkzeug.utils import secure_filename

from .model import DadesEntradaAuditoria, Tractament, PoliticaPrivacitat, ConfiguracioAcces
from .csv_import import (
    llegir_csv_raw,
    construir_tractaments_des_de_csv,
    CAMPOS_TRACTAMENT,
)
from .api_routes import _build_informe, api as api_blueprint


# Emmagatzematge al servidor dels informes (evita superar la mida màxima de la cookie de sessió)
_informes_guardats: dict[str, dict] = {}


def create_app() -> Flask:
    """
    Crea i configura l'aplicació Flask.

    Registra l'API REST (/api), CORS per al frontend React, sessions per a la UI legacy
    i les rutes HTML d'importació JSON/CSV, formulari de dades i informe.
    """
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.secret_key = "tfm-auditoria-privacitat-secret-key-canviar-en-produccio"
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB
    app.register_blueprint(api_blueprint)
    # CORS per al frontend React (desenvolupament)
    @app.after_request
    def _cors(resp):
        orig = getattr(request, "origin", None) or "*"
        resp.headers["Access-Control-Allow-Origin"] = orig
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Session-Id"
        return resp

    def get_dades_session() -> dict | None:
        """Retorna les dades d'auditoria emmagatzemades a la sessió Flask."""
        return session.get("dades_auditoria")

    def set_dades_session(d: dict) -> None:
        """Desa les dades d'auditoria a la sessió Flask."""
        session["dades_auditoria"] = d

    @app.route("/")
    def index():
        """Pàgina d'inici de la UI Flask legacy."""
        return render_template("index.html")

    @app.route("/importar-json", methods=["GET", "POST"])
    def importar_json():
        """Importa un fitxer JSON amb dades d'auditoria i les desa a sessió."""
        if request.method != "POST":
            return render_template("importar_json.html")
        f = request.files.get("fitxer_json")
        if not f or not f.filename:
            flash("Seleccioneu un fitxer JSON.", "error")
            return redirect(url_for("importar_json"))
        try:
            text = f.read().decode("utf-8")
            d = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            flash(f"Error llegint el JSON: {e}", "error")
            return redirect(url_for("importar_json"))
        try:
            DadesEntradaAuditoria.from_dict(d)
        except Exception as e:
            flash(f"Format no vàlid: {e}", "error")
            return redirect(url_for("importar_json"))
        set_dades_session(d)
        flash("Dades importades correctament.")
        return redirect(url_for("dades"))

    @app.route("/importar-csv", methods=["GET", "POST"])
    def importar_csv():
        """Pas 1 de la importació CSV: puja el fitxer i guarda capçaleres i files a sessió."""
        if request.method == "GET":
            return render_template("importar_csv_pas1.html", camps=CAMPOS_TRACTAMENT)
        # POST = pujada de fitxer
        f = request.files.get("fitxer_csv")
        if not f or not f.filename:
            flash("Seleccioneu un fitxer CSV.", "error")
            return redirect(url_for("importar_csv"))
        try:
            contingut = f.read()
            headers, rows = llegir_csv_raw(contingut)
        except Exception as e:
            flash(f"Error llegint el CSV: {e}", "error")
            return redirect(url_for("importar_csv"))
        if not headers:
            flash("El CSV no té capçaleres.", "error")
            return redirect(url_for("importar_csv"))
        session["csv_headers"] = headers
        session["csv_rows"] = rows
        session["csv_filename"] = secure_filename(f.filename)
        return redirect(url_for("mapejar_csv"))

    @app.route("/importar-csv/mapejar", methods=["GET", "POST"])
    def mapejar_csv():
        """Pas 2 de la importació CSV: mapatge de columnes i creació de tractaments."""
        headers = session.get("csv_headers")
        rows = session.get("csv_rows")
        if not headers or rows is None:
            flash("Primer pugeu un fitxer CSV.", "error")
            return redirect(url_for("importar_csv"))
        if request.method == "GET":
            return render_template(
                "importar_csv_pas2.html",
                headers=headers,
                rows=rows[:10],
                total_rows=len(rows),
                camps=CAMPOS_TRACTAMENT,
            )
        # POST = mapping enviat
        mapping = {k: v for k, v in request.form.items() if k.startswith("camp_") and v}
        mapping_clean = {k.replace("camp_", ""): v for k, v in mapping.items()}
        if not mapping_clean.get("nom") and not mapping_clean.get("id"):
            flash("Assigneu almenys la columna 'Nom' o 'ID' del tractament.", "error")
            return render_template(
                "importar_csv_pas2.html",
                headers=headers,
                rows=rows[:10],
                total_rows=len(rows),
                camps=CAMPOS_TRACTAMENT,
            )
        tractaments = construir_tractaments_des_de_csv(headers, rows, mapping_clean)
        dades = {
            "nom_organitzacio": "",
            "data_auditoria": datetime.now().strftime("%Y-%m-%d"),
            "tractaments": [t.to_dict() for t in tractaments],
            "politica_privacitat": None,
            "configuracio_acces": None,
            "altres_notes": "",
        }
        set_dades_session(dades)
        session.pop("csv_headers", None)
        session.pop("csv_rows", None)
        session.pop("csv_filename", None)
        flash(f"S'han importat {len(tractaments)} tractament(s). Completeu les dades de l'organització i política.")
        return redirect(url_for("dades"))

    @app.route("/dades", methods=["GET", "POST"])
    def dades():
        """Formulari de dades d'auditoria (organització, política, accés)."""
        d = get_dades_session()
        if not d:
            d = {
                "nom_organitzacio": "",
                "data_auditoria": datetime.now().strftime("%Y-%m-%d"),
                "tractaments": [],
                "politica_privacitat": None,
                "configuracio_acces": None,
                "altres_notes": "",
            }
        if request.method == "GET":
            return render_template(
                "dades.html",
                dades=d,
                bases_legals=["consentiment", "contracte", "obligacio_legal", "legitim_interes", "vital", "public", "altre"],
            )
        # POST = desar canvis del formulari
        d["nom_organitzacio"] = request.form.get("nom_organitzacio", "").strip()
        d["data_auditoria"] = request.form.get("data_auditoria", "").strip()
        d["altres_notes"] = request.form.get("altres_notes", "").strip()
        # Política
        pp = d.get("politica_privacitat") or {}
        pp["existeix"] = request.form.get("politica_existeix") == "1"
        pp["accessible"] = request.form.get("politica_accessible") == "1"
        pp["contingut_deure_informacio"] = request.form.get("politica_contingut") == "1"
        pp["actualitzada"] = request.form.get("politica_actualitzada") == "1"
        pp["idiomes"] = [x.strip() for x in request.form.get("politica_idiomes", "").split(",") if x.strip()]
        d["politica_privacitat"] = pp
        # Accés
        ca = d.get("configuracio_acces") or {}
        ca["acces_restringit_per_rol"] = request.form.get("acces_rol") == "1"
        ca["registre_accions"] = request.form.get("registre_accions") == "1"
        ca["formacio_obligatoria"] = request.form.get("formacio") == "1"
        ca["confidencialitat_contractual"] = request.form.get("confidencialitat") == "1"
        d["configuracio_acces"] = ca
        # Tractaments: rebre com a JSON o des de form (simplificat: mantenir els que tenim i només actualitzar org/data/politica/acces)
        # Opció: afegir/editar tractaments via form. Per ara només guardem org, data, política, accés.
        set_dades_session(d)
        flash("Dades desades.")
        return redirect(url_for("dades"))

    @app.route("/executar-auditoria", methods=["POST"])
    def executar_auditoria():
        """Executa l'auditoria amb les dades de sessió i redirigeix a l'informe."""
        d = get_dades_session()
        if not d:
            flash("No hi ha dades. Importeu JSON/CSV o introduïu les dades.", "error")
            return redirect(url_for("index"))
        try:
            dades = DadesEntradaAuditoria.from_dict(d)
        except Exception as e:
            flash(f"Error en les dades: {e}", "error")
            return redirect(url_for("dades"))
        inf_dict = _build_informe(dades)
        inf_dict["dades_guardades"] = d
        informe_id = str(uuid.uuid4())
        _informes_guardats[informe_id] = inf_dict
        session["informe_id"] = informe_id
        return redirect(url_for("informe"))

    @app.route("/informe")
    def informe():
        """Mostra l'informe d'auditoria segmentat per tipus de dades."""
        informe_id = session.get("informe_id")
        inf_dict = _informes_guardats.get(informe_id) if informe_id else None
        if not inf_dict:
            flash("Executeu primer l'auditoria.", "error")
            return redirect(url_for("dades"))
        # Informe segmentat per tipus de dades (pastanyetes)
        tipus_dades = inf_dict.get("tipus_dades", ["General"])
        per_tipus = inf_dict.get("per_tipus", {})
        if not per_tipus and "resum" in inf_dict:
            # Compatibilitat amb informes antics sense per_tipus
            tipus_dades = ["General"]
            per_tipus = {
                "General": {
                    "resum": inf_dict.get("resum", {}),
                    "findings": inf_dict.get("findings", []),
                    "riscos": inf_dict.get("riscos", []),
                    "recomanacions": inf_dict.get("recomanacions", []),
                }
            }
        meta = inf_dict.get("meta", {})
        return render_template(
            "informe.html",
            meta=meta,
            tipus_dades=tipus_dades,
            per_tipus=per_tipus,
        )

    @app.route("/descarrega/<format>")
    def descarregar(format: str):
        """Descarrega l'informe en JSON, TXT o HTML."""
        informe_id = session.get("informe_id")
        inf = _informes_guardats.get(informe_id) if informe_id else None
        if not inf or format not in ("json", "txt", "html"):
            flash("No hi ha informe o format no vàlid.", "error")
            return redirect(url_for("index"))
        if format == "json":
            buf = io.BytesIO()
            buf.write(json.dumps(inf, ensure_ascii=False, indent=2).encode("utf-8"))
            buf.seek(0)
            return send_file(buf, as_attachment=True, download_name="informe_auditoria.json", mimetype="application/json")
        if format == "txt":
            text = _generar_txt_des_de_informe(inf)
            buf = io.BytesIO(text.encode("utf-8"))
            buf.seek(0)
            return send_file(buf, as_attachment=True, download_name="informe_auditoria.txt", mimetype="text/plain; charset=utf-8")
        if format == "html":
            html = _html_des_de_informe(inf)
            buf = io.BytesIO(html.encode("utf-8"))
            buf.seek(0)
            return send_file(buf, as_attachment=True, download_name="informe_auditoria.html", mimetype="text/html; charset=utf-8")
        return redirect(url_for("index"))

    def _informe_a_dades(inf: dict) -> dict:
        return {
            "nom_organitzacio": inf.get("meta", {}).get("nom_organitzacio", ""),
            "data_auditoria": inf.get("meta", {}).get("data_auditoria", ""),
            "tractaments": [],
            "politica_privacitat": None,
            "configuracio_acces": None,
            "altres_notes": "",
        }

    def _generar_txt_des_de_informe(inf: dict) -> str:
        meta = inf.get("meta", {})
        per_tipus = inf.get("per_tipus", {})
        if not per_tipus:
            per_tipus = {
                "General": {
                    "resum": inf.get("resum", {}),
                    "findings": inf.get("findings", []),
                    "riscos": inf.get("riscos", []),
                    "recomanacions": inf.get("recomanacions", []),
                }
            }
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
                "",
                "=" * 60,
                f" TIPUS DE DADES: {tipus.upper()} ",
                "=" * 60,
                "",
                "--- RESUM ---",
                "",
            ])
            for k, v in resum.get("per_resultat", {}).items():
                lines.append(f"  {k}: {v}")
            lines.append("")
            for k, v in resum.get("per_nivell_risc", {}).items():
                lines.append(f"  Risc {k}: {v}")
            lines.extend(["", "--- RESULTATS ---", ""])
            for f in bloc.get("findings", []):
                lines.append(f"[{f['resultat'].upper()}] {f['nom_criteri']}")
                lines.append(f"  {f['descripcio']}")
                lines.append("")
            lines.extend(["", "--- RISCOS ---", ""])
            for r in bloc.get("riscos", []):
                lines.append(f"- [{r['nivell'].upper()}] {r['titol']}")
                lines.append(f"  {r['descripcio']}")
                lines.append("")
            lines.extend(["", "--- RECOMANACIONS ---", ""])
            for rec in bloc.get("recomanacions", []):
                lines.append(f"- {rec['titol']} ({rec['prioritat']})")
                lines.append(f"  {rec['descripcio']}")
                for a in rec.get("accions", []):
                    lines.append(f"  · {a}")
                lines.append("")
        return "\n".join(lines)

    def _html_des_de_informe(inf: dict) -> str:
        meta = inf.get("meta", {})
        per_tipus = inf.get("per_tipus", {})
        if not per_tipus:
            per_tipus = {
                "General": {
                    "resum": inf.get("resum", {}),
                    "findings": inf.get("findings", []),
                    "riscos": inf.get("riscos", []),
                    "recomanacions": inf.get("recomanacions", []),
                }
            }
        def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        parts = [
            """<!DOCTYPE html><html lang="ca"><head><meta charset="utf-8"><title>Informe auditoria</title>
<style>body{font-family:system-ui,sans-serif;max-width:800px;margin:0 auto;padding:1rem;} .badge{display:inline-block;padding:.25rem .5rem;border-radius:4px;margin-right:.5rem;} .compleix{background:#c6f6d5;} .no_compleix{background:#fed7d7;} .finding{margin:.75rem 0;padding:.75rem;background:#f8fafc;border-radius:6px;} .tipus-section{margin-top:2rem;border-top:1px solid #e2e8f0;padding-top:1.5rem;}</style></head><body>""",
            f"<h1>Informe d'auditoria de privacitat</h1><p><strong>Organització:</strong> {esc(meta.get('nom_organitzacio','—'))} · <strong>Data:</strong> {esc(meta.get('data_auditoria','—'))}</p>",
        ]
        for tipus in inf.get("tipus_dades", list(per_tipus.keys())):
            bloc = per_tipus.get(tipus, {})
            resum = bloc.get("resum", {})
            per_resultat = resum.get("per_resultat", {})
            per_nivell = resum.get("per_nivell_risc", {})
            parts.append(f'<div class="tipus-section"><h2>Tipus de dades: {esc(tipus)}</h2><p>')
            for k, v in per_resultat.items():
                cls = "compleix" if k == "compleix" else "no_compleix" if k == "no_compleix" else ""
                parts.append(f'<span class="badge {cls}">{esc(k)}: {v}</span>')
            for k, v in per_nivell.items():
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

    return app


# Per poder executar: python -m eina_auditoria_priv.webapp
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
