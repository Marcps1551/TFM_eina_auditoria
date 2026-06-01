"""
Motor d'avaluació: aplica els criteris normatius a les dades d'entrada
i genera els resultats (findings) i riscos identificats.
Cada finding/risc/recomanació pot anar associat a un tractament o ser General.
"""

from dataclasses import dataclass, field
from typing import Optional

from .model import DadesEntradaAuditoria
from .criteria import CRITERIS, Criteri, ResultatCriteri, NivellRisc


@dataclass
class Finding:
    """Resultat d'avaluar un criteri. Opcionalment associat a un tractament."""
    criteri_id: str
    nom_criteri: str
    referencia_normativa: str
    resultat: ResultatCriteri
    descripcio: str
    nivell_risc: NivellRisc
    tractament_id: Optional[str] = None
    tractament_nom: Optional[str] = None


@dataclass
class RiscIdentificat:
    """Risc de privacitat identificat a partir dels findings."""
    id: str
    titol: str
    descripcio: str
    nivell: NivellRisc
    criteris_relacionats: list[str] = field(default_factory=list)
    referencia: str = ""
    tractament_id: Optional[str] = None
    tractament_nom: Optional[str] = None


@dataclass
class ResultatAvaluacio:
    """Resultat complet d'una avaluació."""
    findings: list[Finding] = field(default_factory=list)
    riscos: list[RiscIdentificat] = field(default_factory=list)
    resum: dict = field(default_factory=dict)  # comptatge per resultat i per nivell

    def _calcula_resum(self) -> None:
        """Calcula comptatges per resultat i per nivell de risc a partir dels findings."""
        per_resultat = {}
        per_nivell = {}
        for f in self.findings:
            per_resultat[f.resultat.value] = per_resultat.get(f.resultat.value, 0) + 1
            per_nivell[f.nivell_risc.value] = per_nivell.get(f.nivell_risc.value, 0) + 1
        self.resum = {
            "per_resultat": per_resultat,
            "per_nivell_risc": per_nivell,
            "total_criteris": len(self.findings),
        }


def avaluar(dades: DadesEntradaAuditoria) -> ResultatAvaluacio:
    """Executa tots els criteris; cada criteri pot retornar diversos findings (un per tractament quan correspongui).
    Quan un criteri retorna findings amb tractament_id, s'afegeix també un finding 'General' (tractament_id=None)
    perquè a Totals es mostrin tant el general com el concret; a la pestanya del tipus es filtra i només es veu el concret."""
    resultat = ResultatAvaluacio()
    for c in CRITERIS:
        items = list(c.avaluar(dades))
        # Si hi ha findings per tractament però cap General, afegir-ne un duplicat per Totals
        has_tractament = any(len(x) >= 4 and (x[3] or x[4]) for x in items)
        has_general = any(len(x) >= 4 and not (x[3] or x[4]) for x in items)
        if has_tractament and not has_general:
            first = items[0]
            res, desc, nivell = first[0], first[1], first[2]
            items = [(res, desc, nivell, None, None)] + items
        for res, desc, nivell, tractament_id, tractament_nom in items:
            resultat.findings.append(Finding(
                criteri_id=c.id,
                nom_criteri=c.nom,
                referencia_normativa=c.referencia_normativa,
                resultat=res,
                descripcio=desc,
                nivell_risc=nivell,
                tractament_id=tractament_id,
                tractament_nom=tractament_nom,
            ))
    resultat._calcula_resum()
    resultat.riscos = _identificar_riscos(resultat.findings)
    return resultat


def avaluar_per_tipus_dades(dades: DadesEntradaAuditoria) -> dict[str, ResultatAvaluacio]:
    """
    Avaluació segmentada per tipus de dades.
    Per a cada tipus_dades dels tractaments, executa l'avaluació només sobre els tractaments
    d'aquest tipus (politica, accés i checklist es mantenen iguals).
    Retorna un diccionari tipus_dades -> ResultatAvaluacio.
    Si no hi ha tractaments o cap té tipus_dades, es retorna una sola clau "General".
    """
    if not dades.tractaments:
        return {"General": avaluar(dades)}

    tipus_unic = set()
    for t in dades.tractaments:
        tipus_unic.add((t.tipus_dades or "").strip() or "Altres")

    resultats: dict[str, ResultatAvaluacio] = {}
    for tipus in sorted(tipus_unic):
        tractaments_tipus = [t for t in dades.tractaments if ((t.tipus_dades or "").strip() or "Altres") == tipus]
        # Checklist per tipus: fusionar "General" + respostes específiques d'aquest tipus
        checklist_raw = dades.checklist_controls
        if isinstance(checklist_raw, dict) and checklist_raw and isinstance(next(iter(checklist_raw.values())), dict):
            base = checklist_raw.get("General", {})
            per_tipus = checklist_raw.get(tipus, {})
            checklist_merged = {**base, **per_tipus}
        else:
            checklist_merged = checklist_raw if isinstance(checklist_raw, dict) else {}
        dades_tipus = DadesEntradaAuditoria(
            nom_organitzacio=dades.nom_organitzacio,
            data_auditoria=dades.data_auditoria,
            tractaments=tractaments_tipus,
            politica_privacitat=dades.politica_privacitat,
            configuracio_acces=dades.configuracio_acces,
            checklist_controls=checklist_merged,
            altres_notes=dades.altres_notes,
        )
        resultats[tipus] = avaluar(dades_tipus)
    return resultats


def _identificar_riscos(findings: list[Finding]) -> list[RiscIdentificat]:
    """A partir dels findings, genera riscos (un per finding NO_COMPLEIX, amb tractament si n'hi ha)."""
    riscos = []
    no_compleix = [f for f in findings if f.resultat == ResultatCriteri.NO_COMPLEIX]
    for i, f in enumerate(no_compleix):
        # Id únic quan hi ha diversos findings del mateix criteri (per tractament)
        rid = f"R_{f.criteri_id}" if len(no_compleix) == 1 else f"R_{f.criteri_id}_{i}"
        riscos.append(RiscIdentificat(
            id=rid,
            titol=f"No compliment: {f.nom_criteri}",
            descripcio=f.descripcio,
            nivell=f.nivell_risc,
            criteris_relacionats=[f.criteri_id],
            referencia=f.referencia_normativa,
            tractament_id=f.tractament_id,
            tractament_nom=f.tractament_nom,
        ))
    return riscos
