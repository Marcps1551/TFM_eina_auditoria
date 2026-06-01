"""
Interfície per línia de comandes (CLI) per executar l'auditoria de privacitat.
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .model import DadesEntradaAuditoria, ValidacioDadesError, carregar_des_de_dict
from .evaluator import avaluar
from .recommendations import generar_recomanacions
from .reports import exportar_json, exportar_text, exportar_html


def main() -> int:
    """Punt d'entrada CLI: llegeix JSON, executa l'auditoria i exporta informes."""
    parser = argparse.ArgumentParser(
        description="Eina d'auditoria de privacitat en entorns empresarials (RGPD / LOPD-GDD)"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "entrada",
        nargs="?",
        help="Fitxer JSON amb les dades d'entrada de l'auditoria",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Fitxer de sortida (sense extensió: es generen .json, .txt i .html)",
    )
    parser.add_argument(
        "--json",
        metavar="FILE",
        help="Exportar només informe JSON",
    )
    parser.add_argument(
        "--txt",
        metavar="FILE",
        help="Exportar només informe text",
    )
    parser.add_argument(
        "--html",
        metavar="FILE",
        help="Exportar només informe HTML",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Imprimir l'informe en text a la consola",
    )
    args = parser.parse_args()

    if not args.entrada:
        parser.print_help()
        print("\nExemple: python -m eina_auditoria_priv.cli dades_exemple/cas_mixt_3_tractaments.json -o informe")
        return 0

    path_entrada = Path(args.entrada)
    if not path_entrada.exists():
        print(f"Error: no s'ha trobat el fitxer '{path_entrada}'", file=sys.stderr)
        return 1

    try:
        with open(path_entrada, "r", encoding="utf-8") as f:
            dades_dict = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error llegint JSON: {e}", file=sys.stderr)
        return 1

    try:
        dades = carregar_des_de_dict(dades_dict)
    except ValidacioDadesError as e:
        for err in e.errors:
            print(f"Error de validació: {err}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error interpretant les dades d'entrada: {e}", file=sys.stderr)
        return 1

    resultat = avaluar(dades)
    recomanacions = generar_recomanacions(resultat)

    base = args.output
    if base:
        base = Path(base)
        exportar_json(resultat, recomanacions, dades, base.with_suffix(".json"))
        exportar_text(resultat, recomanacions, dades, base.with_suffix(".txt"))
        exportar_html(resultat, recomanacions, dades, base.with_suffix(".html"))
        print(f"Informes generats: {base.with_suffix('.json')}, {base.with_suffix('.txt')}, {base.with_suffix('.html')}")

    if args.json:
        exportar_json(resultat, recomanacions, dades, args.json)
        print(f"JSON: {args.json}")
    if args.txt:
        exportar_text(resultat, recomanacions, dades, args.txt)
        print(f"Text: {args.txt}")
    if args.html:
        exportar_html(resultat, recomanacions, dades, args.html)
        print(f"HTML: {args.html}")

    if args.print or (not args.output and not args.json and not args.txt and not args.html):
        text = exportar_text(resultat, recomanacions, dades, path=None)
        print(text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
