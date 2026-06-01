"""
Criteris d'avaluació derivats del RGPD i la LOPD-GDD.
Cada criteri és un punt de control que l'eina avalua sobre les dades d'entrada.
Referència: RGPD arts. 5, 6, 13, 14, 30, 32; LOPD-GDD.

NOTA: L'eina NO valida nomenclatura. Comprova només:
- Presència/absència de valor (ex.: base legal "compleix" si hi ha qualsevol text).
- Respostes sí/no que l'usuari indica (formulari o CSV).
Podeu usar la vostra pròpia terminologia; l'eina no interpreta el significat legal.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from .model import DadesEntradaAuditoria, Tractament, PoliticaPrivacitat, ConfiguracioAcces
from . import constants


class NivellRisc(str, Enum):
    """Nivells de gravetat del risc associat a un finding."""
    ALT = "alt"
    MITJA = "mitja"
    BAIX = "baix"
    INFO = "informat"


class ResultatCriteri(str, Enum):
    """Resultat possible de l'avaluació d'un criteri normatiu."""
    COMPLEIX = "compleix"
    NO_COMPLEIX = "no_compleix"
    NO_APLICABLE = "no_aplicable"
    SENSE_DADES = "sense_dades"


# Cada criteri retorna una llista: (resultat, descripcio, nivell_risc, tractament_id, tractament_nom).
AvaluacioResult = list[tuple[ResultatCriteri, str, NivellRisc, Optional[str], Optional[str]]]


def _un(res: ResultatCriteri, desc: str, nivell: NivellRisc) -> AvaluacioResult:
    """Un sol resultat sense tractament (General)."""
    return [(res, desc, nivell, None, None)]


def _per_tractament_compleix(tractaments: list, msg: str, nivell: NivellRisc) -> AvaluacioResult:
    """Un resultat COMPLEIX per a cada tractament (sense fila General)."""
    return [
        (ResultatCriteri.COMPLEIX, msg, nivell, t.id, t.nom or t.id)
        for t in tractaments
    ]


def _partial_per_tractament(
    tractaments: list,
    failing: list,
    fail_msg: str,
    nivell_fail: NivellRisc,
    ok_msg: str,
    nivell_ok: NivellRisc = NivellRisc.BAIX,
) -> AvaluacioResult:
    """Incumpliments per tractament afectat i COMPLEIX per als que passen. Resum General només si hi ha parcial."""
    if not tractaments:
        return []
    failing_ids = {t.id for t in failing}
    ok = [t for t in tractaments if t.id not in failing_ids]
    if not failing:
        return _per_tractament_compleix(tractaments, ok_msg, nivell_ok)
    result: AvaluacioResult = []
    if ok:
        general_msg = (
            f"{len(ok)} de {len(tractaments)} tractaments compleixen. "
            f"Revisar {len(failing)} tractament(s) al detall per tractament."
        )
        result.append((ResultatCriteri.COMPLEIX, general_msg, nivell_ok, None, None))
        result.extend(
            (ResultatCriteri.COMPLEIX, ok_msg, nivell_ok, t.id, t.nom or t.id) for t in ok
        )
    result.extend(
        (ResultatCriteri.NO_COMPLEIX, fail_msg, nivell_fail, t.id, t.nom or t.id) for t in failing
    )
    return result


@dataclass
class Criteri:
    """Definició d'un criteri d'avaluació amb la seva funció d'avaluació."""
    id: str
    nom: str
    descripcio: str
    referencia_normativa: str
    nivell_risc_defecte: NivellRisc
    avaluar: Callable[[DadesEntradaAuditoria], AvaluacioResult]


def _criteri_base_legal(d: DadesEntradaAuditoria) -> AvaluacioResult:
    """RGPD art. 6: cada tractament ha de tenir almenys una base legal vàlida. Un finding per tractament sense base."""
    def te_base(t):
        bl = getattr(t, "base_legal", None)
        if isinstance(bl, list):
            return any(x and str(x).strip() for x in bl)
        if isinstance(bl, str) and bl.strip():
            return True
        return False
    sense_base = [t for t in d.tractaments if not te_base(t)]
    if not d.tractaments:
        return _un(ResultatCriteri.SENSE_DADES, "No s'han declarat tractaments.", NivellRisc.INFO)
    return _partial_per_tractament(
        d.tractaments,
        sense_base,
        "Sense base legal indicada. RGPD art. 6 requereix una base legal per a cada tractament.",
        NivellRisc.ALT,
        "Tots els tractaments declaren una base legal.",
    )


def _criteri_finalitat_definida(d: DadesEntradaAuditoria) -> AvaluacioResult:
    """RGPD art. 5.1.b: limitació de la finalitat. Un finding per tractament sense finalitat."""
    sense_finalitat = [t for t in d.tractaments if not (t.finalitat and t.finalitat.strip())]
    if not d.tractaments:
        return _un(ResultatCriteri.SENSE_DADES, "No s'han declarat tractaments.", NivellRisc.INFO)
    return _partial_per_tractament(
        d.tractaments,
        sense_finalitat,
        "Sense finalitat definida. La finalitat ha d'estar determinada i documentada (RGPD art. 5.1.b).",
        NivellRisc.MITJA,
        "Totes les finalitats estan definides.",
    )


def _criteri_termini_conservacio(d: DadesEntradaAuditoria) -> AvaluacioResult:
    """RGPD art. 5.1.e: limitació del termini. Un finding per tractament sense termini."""
    sense_termini = [t for t in d.tractaments if not (t.termini_conservacio and t.termini_conservacio.strip())]
    if not d.tractaments:
        return _un(ResultatCriteri.SENSE_DADES, "No s'han declarat tractaments.", NivellRisc.INFO)
    return _partial_per_tractament(
        d.tractaments,
        sense_termini,
        "Sense termini de conservació definit. Cal definir criteris de conservació i supressió (RGPD art. 5.1.e).",
        NivellRisc.MITJA,
        "Tots els tractaments tenen termini de conservació definit.",
    )


def _criteri_termini_adequacio(d: DadesEntradaAuditoria) -> AvaluacioResult:
    """Segons el termini: indefinit o molt llarg (> 10 anys) genera un finding informatiu (cal documentar)."""
    result = []
    for t in (d.tractaments or []):
        term = (t.termini_conservacio or "").strip().lower()
        if not term:
            continue
        # Termini indefinit: cal documentar garanties art. 89
        if term == "indefinit" or "indefinit" in term:
            result.append((
                ResultatCriteri.SENSE_DADES,
                "Termini indefinit: assegureu-vos de documentar les garanties de l'art. 89 RGPD (recerca, arxivat, estadístiques, etc.).",
                NivellRisc.INFO, t.id, t.nom or t.id
            ))
            continue
        # Termini numèric molt llarg (> 10 anys)
        anys = _termini_anys_numerics(t.termini_conservacio)
        if anys is not None and anys > 10:
            result.append((
                ResultatCriteri.SENSE_DADES,
                f"Termini de conservació llarg ({t.termini_conservacio}): verifiqueu que és justificat i documentat (RGPD art. 5.1.e).",
                NivellRisc.INFO, t.id, t.nom or t.id
            ))
    if result:
        return result
    return []


def _criteri_politica_privacitat(d: DadesEntradaAuditoria) -> AvaluacioResult:
    """RGPD arts. 13 i 14: deure d'informació; política de privacitat accessible i completa (General)."""
    if not d.politica_privacitat:
        return _un(ResultatCriteri.SENSE_DADES, "No s'ha indicat informació sobre la política de privacitat.", NivellRisc.INFO)
    pp = d.politica_privacitat
    if not pp.existeix:
        return _un(ResultatCriteri.NO_COMPLEIX, "No existeix política de privacitat. RGPD arts. 13/14 exigeixen informar les persones interessades.", NivellRisc.ALT)
    if not pp.accessible:
        return _un(ResultatCriteri.NO_COMPLEIX, "La política de privacitat no consta com a accessible. Ha d'estar fàcilment accessible (RGPD art. 12).", NivellRisc.MITJA)
    if not pp.contingut_deure_informacio:
        return _un(ResultatCriteri.NO_COMPLEIX, "La política no reflecteix tot el deure d'informació (identitat, finalitat, base legal, drets, etc.). Revisar RGPD arts. 13 i 14.", NivellRisc.MITJA)
    if not pp.actualitzada:
        return _un(ResultatCriteri.NO_COMPLEIX, "La política no consta com a actualitzada. Cal mantenir la informació al dia.", NivellRisc.BAIX)
    return _un(ResultatCriteri.COMPLEIX, "Política de privacitat existent, accessible i amb contingut adequat.", NivellRisc.BAIX)


def _criteri_registre_activitats(d: DadesEntradaAuditoria) -> AvaluacioResult:
    """RGPD art. 30: registre d'activitats de tractament (General)."""
    if not d.tractaments:
        return _un(ResultatCriteri.SENSE_DADES, "No s'han declarat tractaments (registre d'activitats).", NivellRisc.INFO)
    n = len(d.tractaments)
    return _un(ResultatCriteri.COMPLEIX, f"S'han declarat {n} activitat(s) de tractament (registre d'activitats art. 30).", NivellRisc.BAIX)


def _criteri_mesures_seguretat(d: DadesEntradaAuditoria) -> AvaluacioResult:
    """RGPD art. 32: mesures de seguretat. Un finding per tractament sense mesures."""
    sense_mesures = [t for t in d.tractaments if not t.mesures_seguretat]
    if not d.tractaments:
        return _un(ResultatCriteri.SENSE_DADES, "No s'han declarat tractaments.", NivellRisc.INFO)
    return _partial_per_tractament(
        d.tractaments,
        sense_mesures,
        "Sense mesures de seguretat documentades. RGPD art. 32 exigeix mesures tècniques i organitzatives adequades.",
        NivellRisc.MITJA,
        "Tots els tractaments tenen mesures de seguretat indicades.",
    )


def _criteri_acces_restringit(d: DadesEntradaAuditoria) -> AvaluacioResult:
    """Control d'accés (General). Es considera complert si configuració acces_restringit_per_rol o si algun tractament té la mesura."""
    # Casuística: si algun tractament té accés restringit per rol a les seves mesures, es considera complert
    for t in (d.tractaments or []):
        ms = _mesures_set(t)
        if "acces_restringit_rol" in ms or "acces restringit per rol" in ms or "acces_restringit per rol" in ms:
            return _un(ResultatCriteri.COMPLEIX, "L'accés consta restringit per rol (configuració o mesures dels tractaments).", NivellRisc.BAIX)
    if not d.configuracio_acces:
        return _un(ResultatCriteri.SENSE_DADES, "No s'ha indicat configuració d'accés ni mesures per tractament.", NivellRisc.INFO)
    ca = d.configuracio_acces
    if not ca.acces_restringit_per_rol:
        return _un(ResultatCriteri.NO_COMPLEIX, "L'accés a les dades no consta restringit per rol. Cal limitar l'accés al personal autoritzat (RGPD art. 32.4).", NivellRisc.MITJA)
    return _un(ResultatCriteri.COMPLEIX, "L'accés consta restringit per rol.", NivellRisc.BAIX)


def _criteri_registre_accions(d: DadesEntradaAuditoria) -> AvaluacioResult:
    """Registre d'accions (General)."""
    if not d.configuracio_acces:
        return _un(ResultatCriteri.SENSE_DADES, "No s'ha indicat configuració d'accés.", NivellRisc.INFO)
    if not d.configuracio_acces.registre_accions:
        return _un(ResultatCriteri.NO_COMPLEIX, "No consta registre d'accions sobre dades personals. Es recomana tenir traçabilitat (bones pràctiques RGPD/LOPD-GDD).", NivellRisc.MITJA)
    return _un(ResultatCriteri.COMPLEIX, "Consta registre d'accions.", NivellRisc.BAIX)


def _criteri_dpo(d: DadesEntradaAuditoria) -> AvaluacioResult:
    """RGPD arts. 37-39: DPO. Un finding per tractament sense DPO assignat (quan n'hi ha cap, un sol finding General)."""
    if not d.tractaments:
        return _un(ResultatCriteri.SENSE_DADES, "No s'han declarat tractaments.", NivellRisc.INFO)
    sense_dpo = [t for t in d.tractaments if not t.dpo_assignat]
    if len(sense_dpo) == len(d.tractaments):
        msg = "Tractament sense DPO assignat. Revisar si l'organització té obligació de designar DPO (RGPD art. 37)."
        return [
            (ResultatCriteri.NO_COMPLEIX, msg, NivellRisc.MITJA, t.id, t.nom or t.id)
            for t in sense_dpo
        ]
    return _partial_per_tractament(
        d.tractaments,
        sense_dpo,
        "Tractament sense DPO assignat. Revisar si cal designar DPO (RGPD art. 37).",
        NivellRisc.MITJA,
        "Tots els tractaments consten amb DPO assignat.",
    )


def _criteri_transferencies(d: DadesEntradaAuditoria) -> AvaluacioResult:
    """RGPD cap. V: transferències. Si hi ha transferències, es comprova si es documenten garanties (ex. contractes processadors)."""
    amb_transferencies = [t for t in (d.tractaments or []) if t.transferencies_internacionals]
    if not amb_transferencies:
        return _un(ResultatCriteri.COMPLEIX, "No es declaren transferències internacionals o no n'hi ha.", NivellRisc.BAIX)
    # Casuística: si algun tractament amb transferències té contractes_processadors (o similar), es considera documentat
    ids_garanties = {"contractes_processadors", "contractes processadors", "clàusules tipus", "clausules tipus"}
    sense_garanties = []
    for t in amb_transferencies:
        ms = _mesures_set(t)
        if not any(g in ms or g.replace("_", " ") in ms for g in ids_garanties):
            sense_garanties.append(t)
    if sense_garanties:
        return _partial_per_tractament(
            amb_transferencies,
            sense_garanties,
            "Transferències internacionals sense garanties documentades (contractes processadors, clàusules tipus, etc.). RGPD cap. V.",
            NivellRisc.MITJA,
            "Transferències internacionals declarades amb garanties documentades (contractes/clàusules).",
        )
    return _per_tractament_compleix(
        amb_transferencies,
        "Transferències internacionals declarades amb garanties documentades (contractes/clàusules).",
        NivellRisc.BAIX,
    )


def _mesures_set(tractament: Tractament) -> set[str]:
    """Retorna el conjunt d'ids de mesures del tractament (normalitzats a minúscules)."""
    out = set()
    for m in (getattr(tractament, "mesures_seguretat", None) or []):
        if m and str(m).strip():
            out.add(str(m).strip().lower())
    return out


def _categories_sensibles(tractament: Tractament) -> bool:
    """True si el tractament inclou categories que impliquen dades de categoria especial (art. 9)."""
    cats = getattr(constants, "CATEGORIES_SENSIBLES_IDS", set()) or set()
    if not cats:
        return False
    for c in (getattr(tractament, "categories_dades", None) or []):
        if not c:
            continue
        c_low = str(c).strip().lower()
        if c_low in cats:
            return True
        # Coincidència per paraula (ex. "dades de salut" conté "salut")
        for sid in cats:
            if sid in c_low or c_low in sid:
                return True
    return False


def _categories_altrisc_xifrat(tractament: Tractament) -> bool:
    """True si el tractament inclou categories d'alt risc que haurien de tenir xifrat (NIF, dades bancàries)."""
    altrisc = getattr(constants, "CATEGORIES_ALTRISC_XIFRAT", set()) or set()
    if not altrisc:
        return False
    for c in (getattr(tractament, "categories_dades", None) or []):
        if not c:
            continue
        c_low = str(c).strip().lower()
        if c_low in altrisc:
            return True
        for aid in altrisc:
            if aid in c_low or c_low in aid:
                return True
    return False


def _termini_anys_numerics(termini: Optional[str]) -> Optional[float]:
    """Si el termini és numèric en anys (ex. '5 anys', '18 mesos'), retorna els anys aproximats; altrament None."""
    if not termini or not str(termini).strip():
        return None
    s = str(termini).strip().lower()
    m = re.match(r"^(\d+)\s*(anys?|mesos|dies)$", s)
    if m:
        num, unit = int(m.group(1)), m.group(2)
        if "any" in unit:
            return float(num)
        if "mes" in unit:
            return round(num / 12.0, 2)
        if "di" in unit:
            return round(num / 365.0, 2)
    return None


def _avaluar_estructurat(control_id: str, d: DadesEntradaAuditoria, nivell_defecte: NivellRisc) -> Optional[AvaluacioResult]:
    """
    Avaluació només amb dades estructurades (categories_dades, termini_conservacio, mesures_seguretat,
    conte_dades_sensibles, transferencies_internacionals). Retorna resultat si la casuística permet
    decidir; None si cal checklist o resposta manual.

    Casuística implementada:
    - RGPD_ART12_MODALITATS: transparència i modalitats via política (existeix/accessible/contingut).
    - RGPD_ART5_PRINCIPIS: evidències mínimes via base_legal, finalitat i termini (exclou minimització/exactitud perquè en aquesta fase no es cobreixen del tot).
    - RGPD_ART5_2_RESPONSABILITAT: responsabilitat proactiva via traçabilitat i evidència operativa (registre d'accions o mesures d'avaluació).
    - RGPD_ART9_DADES_ESPECIALS / ISO27701_A_6.8: sensibles sense mesures reforçades → NO; sensibles amb reforç → COMPLEIX.
    - RGPD_ART35_PIA: tractaments de risc (sensibles o categories sensibles) sense avaluacio_riscos → NO.
    - ISO27701_A_6.4: sense termini de conservació → NO per tractament.
    - RGPD_ART5_MINIMITZACIO: sense categories de dades indicades → NO per tractament.
    - RGPD_ART32_MESURES: sense mesures → NO per tractament.
    - RGPD_ART28_PROCESSADOR: transferències sense contractes_processadors → NO per tractament.
    """
    tractaments = d.tractaments or []
    if not tractaments:
        return None

    # RGPD art. 12: transparència i modalitats (es considera via política de privacitat).
    if control_id == "RGPD_ART12_MODALITATS":
        pp = d.politica_privacitat
        if not pp or not pp.existeix:
            return _un(ResultatCriteri.NO_COMPLEIX, "No consta política de privacitat. RGPD art. 12 exigeix informació clara i accessible per exercir els drets.", nivell_defecte)
        if not pp.accessible:
            return _un(ResultatCriteri.NO_COMPLEIX, "La política de privacitat no consta com a accessible. RGPD art. 12 requereix informació accessible.", nivell_defecte)
        if not pp.contingut_deure_informacio:
            return _un(ResultatCriteri.NO_COMPLEIX, "La política de privacitat no reflecteix el contingut mínim per a l’exercici dels drets (deure d’informació). Revisar RGPD arts. 12, 13 i 14.", nivell_defecte)
        return _un(ResultatCriteri.COMPLEIX, "La política de privacitat és existent, accessible i amb el contingut mínim per facilitar l’exercici dels drets (RGPD art. 12).", nivell_defecte)

    # RGPD art. 5.1 i 5.2: principis del tractament amb evidències mínimes.
    if control_id == "RGPD_ART5_PRINCIPIS":
        sense_base = [t for t in tractaments if not getattr(t, "base_legal", None)]
        sense_finalitat = [t for t in tractaments if not (getattr(t, "finalitat", None) and str(t.finalitat).strip())]
        sense_termini = [t for t in tractaments if not (getattr(t, "termini_conservacio", None) and str(t.termini_conservacio).strip())]
        if sense_base or sense_finalitat or sense_termini:
            return _un(
                ResultatCriteri.NO_COMPLEIX,
                "No es disposa d’evidències mínimes sobre base_legal, finalitat i/o termini per sostenir el control de principis del tractament (RGPD art. 5).",
                nivell_defecte,
            )
        return _un(ResultatCriteri.COMPLEIX, "Hi ha evidències mínimes sobre principis del tractament (base legal, finalitat i termini) segons el model d’entrada.", nivell_defecte)

    # RGPD art. 5.2: responsabilitat proactiva
    if control_id == "RGPD_ART5_2_RESPONSABILITAT":
        # Traçabilitat a nivell d'organització
        ca = d.configuracio_acces
        if ca and ca.registre_accions:
            return _un(ResultatCriteri.COMPLEIX, "Consta registre d'accions (traçabilitat), suportant la responsabilitat proactiva (RGPD art. 5.2).", nivell_defecte)
        # Evidència operativa dins les mesures
        mesures_union: set[str] = set()
        for t in tractaments:
            for m in (getattr(t, "mesures_seguretat", None) or []):
                if m and str(m).strip():
                    mesures_union.add(str(m).strip().lower())
        if "registre_acces" in mesures_union or "avaluacio_riscos" in mesures_union:
            return _un(ResultatCriteri.COMPLEIX, "Hi ha traçabilitat o evidència operativa (p. ex. registre d'accés o avaluació de riscos) que dona suport a l'accountability (RGPD art. 5.2).", nivell_defecte)
        return _un(ResultatCriteri.NO_COMPLEIX, "No consta evidència mínima de responsabilitat proactiva (registre d'accions o mesures d'avaluació). Revisar RGPD art. 5.2.", nivell_defecte)

    # RGPD art. 9 / ISO 27701 A.6.8: dades especials
    if control_id in ("RGPD_ART9_DADES_ESPECIALS", "ISO27701_A_6.8"):
        sensibles_sense_reforc = []
        for t in tractaments:
            if getattr(t, "conte_dades_sensibles", False):
                ms = _mesures_set(t)
                if "dades_sensibles_reforç" not in ms and "dades_sensibles_reforc" not in ms:
                    sensibles_sense_reforc.append(t)
        if sensibles_sense_reforc:
            return [
                (ResultatCriteri.NO_COMPLEIX, "Tractament amb dades sensibles sense mesures reforçades documentades (RGPD art. 9 exigeix garanties adequades).", nivell_defecte, t.id, t.nom or t.id)
                for t in sensibles_sense_reforc
            ]
        if any(getattr(t, "conte_dades_sensibles", False) for t in tractaments):
            return _un(ResultatCriteri.COMPLEIX, "Tractaments amb dades sensibles tenen mesures reforçades indicades.", nivell_defecte)
        # Categories sensibles però no marcat conte_dades_sensibles: possible inconsistència
        if any(_categories_sensibles(t) for t in tractaments):
            return _un(ResultatCriteri.SENSE_DADES, "Algun tractament inclou categories que podrien ser dades especials (art. 9). Confirmeu si 'Conté dades sensibles' i documenteu les garanties.", NivellRisc.INFO)
        return None

    # RGPD art. 35: PIA quan hi ha risc (dades sensibles o categories sensibles)
    if control_id == "RGPD_ART35_PIA":
        de_risc_sense_pia = []
        for t in tractaments:
            sensibles = getattr(t, "conte_dades_sensibles", False) or _categories_sensibles(t)
            if sensibles:
                ms = _mesures_set(t)
                if "avaluacio_riscos" not in ms:
                    de_risc_sense_pia.append(t)
        if de_risc_sense_pia:
            return [
                (ResultatCriteri.NO_COMPLEIX, "Tractament amb dades sensibles o de risc sense avaluació de riscos/PIA documentada (RGPD art. 35).", nivell_defecte, t.id, t.nom or t.id)
                for t in de_risc_sense_pia
            ]
        if any(getattr(t, "conte_dades_sensibles", False) or _categories_sensibles(t) for t in tractaments):
            return _un(ResultatCriteri.COMPLEIX, "Tractaments de risc tenen avaluació de riscos indicada.", nivell_defecte)
        return None

    # ISO 27701 A.6.4: conservació i supressió (termini definit)
    if control_id == "ISO27701_A_6.4":
        sense_termini = [t for t in tractaments if not (t.termini_conservacio and str(t.termini_conservacio).strip())]
        if sense_termini:
            return [
                (ResultatCriteri.NO_COMPLEIX, "Sense termini de conservació definit. Cal definir criteris de conservació i supressió (ISO 27701 A.6.4).", nivell_defecte, t.id, t.nom or t.id)
                for t in sense_termini
            ]
        return _un(ResultatCriteri.COMPLEIX, "Tots els tractaments tenen termini de conservació definit.", nivell_defecte)

    # RGPD art. 5.1.c: minimització (categories de dades identificades)
    if control_id == "RGPD_ART5_MINIMITZACIO":
        sense_categories = [t for t in tractaments if not (getattr(t, "categories_dades", None) and len(t.categories_dades) > 0)]
        if sense_categories:
            return [
                (ResultatCriteri.NO_COMPLEIX, "No s'han indicat categories de dades. La minimització requereix identificar quines dades es tracten (RGPD art. 5.1.c).", nivell_defecte, t.id, t.nom or t.id)
                for t in sense_categories
            ]
        return _un(ResultatCriteri.COMPLEIX, "Tots els tractaments tenen categories de dades indicades (minimització documentada).", nivell_defecte)

    # RGPD art. 32: mesures de seguretat (presència i adequació bàsica); categories d'alt risc (NIF, bancàries) → es recomana xifrat
    if control_id == "RGPD_ART32_MESURES":
        sense_mesures = [t for t in tractaments if not (getattr(t, "mesures_seguretat", None) and len(t.mesures_seguretat) > 0)]
        if sense_mesures:
            return [
                (ResultatCriteri.NO_COMPLEIX, "Sense mesures de seguretat documentades. RGPD art. 32 exigeix mesures tècniques i organitzatives adequades.", nivell_defecte, t.id, t.nom or t.id)
                for t in sense_mesures
            ]
        # Segons categories: tractaments amb NIF/dades bancàries sense xifrat → NO_COMPLEIX
        altrisc_sense_xifrat = [t for t in tractaments if _categories_altrisc_xifrat(t) and "xifrat" not in _mesures_set(t)]
        if altrisc_sense_xifrat:
            return [
                (ResultatCriteri.NO_COMPLEIX, "Tractament amb dades identificatives o bancàries (NIF, IBAN, etc.) sense xifrat documentat. RGPD art. 32 recomana mesures adequades al risc.", nivell_defecte, t.id, t.nom or t.id)
                for t in altrisc_sense_xifrat
            ]
        return _un(ResultatCriteri.COMPLEIX, "Tots els tractaments tenen mesures de seguretat indicades (i els d'alt risc, xifrat).", nivell_defecte)

    # RGPD art. 28: contracte processador (tractaments amb transferències o destinataris externs)
    if control_id == "RGPD_ART28_PROCESSADOR":
        # Tractaments que probablement impliquen processadors: transferències o diversos destinataris
        amb_transf = [t for t in tractaments if t.transferencies_internacionals]
        sense_contracte = [t for t in amb_transf if "contractes_processadors" not in _mesures_set(t)]
        if sense_contracte:
            return [
                (ResultatCriteri.NO_COMPLEIX, "Transferències internacionals sense contractes amb processadors documentats (RGPD art. 28).", nivell_defecte, t.id, t.nom or t.id)
                for t in sense_contracte
            ]
        if amb_transf:
            return _un(ResultatCriteri.COMPLEIX, "Tractaments amb transferències tenen contractes amb processadors indicats.", nivell_defecte)
        return None

    return None


def _criteri_checklist(
    control_id: str,
    nom: str,
    descripcio_breu: str,
    referencia: str,
    nivell_defecte: NivellRisc,
) -> Callable[[DadesEntradaAuditoria], AvaluacioResult]:
    """Llegeix checklist_controls; si no hi ha resposta, avalua per dades estructurades i després per mesures."""
    def avaluar(d: DadesEntradaAuditoria) -> AvaluacioResult:
        ctrl = d.checklist_controls if d.checklist_controls else {}
        if isinstance(ctrl, dict) and ctrl:
            sample = next(iter(ctrl.values()), None)
            if isinstance(sample, bool):
                val = ctrl.get(control_id)
            else:
                val = ctrl.get("General", {}).get(control_id) if isinstance(sample, dict) else None
        else:
            val = None
        if val is True:
            return _un(ResultatCriteri.COMPLEIX, f"Segons el checklist: {nom} es compleix.", nivell_defecte)
        if val is False:
            return _un(ResultatCriteri.NO_COMPLEIX, f"Segons el checklist: {nom} no es compleix. Cal revisar i documentar.", nivell_defecte)
        # Sense resposta manual: primer avaluació estructurada (categories, termini, mesures, sensibles)
        resultat_estructurat = _avaluar_estructurat(control_id, d, nivell_defecte)
        if resultat_estructurat is not None:
            return resultat_estructurat
        # Després: si les mesures de seguretat dels tractaments satisfan el control
        mesures_union = set()
        for t in (d.tractaments or []):
            for m in (getattr(t, "mesures_seguretat", None) or []):
                if m and str(m).strip():
                    mesures_union.add(str(m).strip().lower())
        satisfet_per_mesura = getattr(constants, "CONTROL_SATISFET_PER_MESURA", {})
        if control_id in satisfet_per_mesura and mesures_union:
            for mid in satisfet_per_mesura[control_id]:
                if mid.lower() in mesures_union:
                    return _un(
                        ResultatCriteri.COMPLEIX,
                        f"Control considerat complert per les mesures de seguretat aplicades (ex.: {mid}).",
                        nivell_defecte,
                    )
        return _un(
            ResultatCriteri.SENSE_DADES,
            f"Aquest control no es pot avaluar amb les dades estructurades. Ompliu 'checklist_controls' amb '{control_id}': true/false o indiqueu les mesures/categories/terminis corresponents.",
            NivellRisc.INFO,
        )
    return avaluar


# Definició de tots els controls que es llegeixen del checklist (sense lògica automàtica).
# (id, nom, descripcio, referencia_normativa, nivell_risc_defecte)
_CONTROLS_CHECKLIST: list[tuple[str, str, str, str, NivellRisc]] = [
    # RGPD 1.1
    ("RGPD_ART5_PRINCIPIS", "Principis relatius al tractament", "Legalitat, leialtat, transparència; finalitat; minimització; exactitud; termini; integritat; responsabilitat proactiva.", "RGPD art. 5.1 i 5.2", NivellRisc.MITJA),
    ("RGPD_ART5_2_RESPONSABILITAT", "Responsabilitat proactiva", "El responsable ha de poder demostrar el compliment (accountability).", "RGPD art. 5.2", NivellRisc.MITJA),
    ("RGPD_ART7_CONSENTIMENT", "Condicions del consentiment", "Consentiment demostrable, retractable, específic, informat i inequívoc.", "RGPD art. 7", NivellRisc.ALT),
    ("RGPD_ART9_DADES_ESPECIALS", "Dades especials (categoria especial)", "Tractament de dades de salut, orígens, etc.: excepcions art. 9.2 documentades.", "RGPD art. 9", NivellRisc.ALT),
    # RGPD 1.2
    ("RGPD_ART12_MODALITATS", "Transparència i modalitats d'exercici dels drets", "Informació clara i accessible; facilitar l'exercici dels drets; termini de resposta (1 mes).", "RGPD art. 12", NivellRisc.MITJA),
    ("RGPD_ART15_ACCES", "Dret d'accés", "L'interessat pot obtenir confirmació i accedir a les seves dades i rebre còpia.", "RGPD art. 15", NivellRisc.ALT),
    ("RGPD_ART16_RECTIFICACIO", "Dret de rectificació", "Dret a obtenir la rectificació de dades inexactes o incompletes.", "RGPD art. 16", NivellRisc.MITJA),
    ("RGPD_ART17_SUPRESSIO", "Dret de supressió (oblit)", "Dret a obtenir la supressió de les dades en els supòsits de l'art. 17.", "RGPD art. 17", NivellRisc.ALT),
    ("RGPD_ART18_LIMITACIO", "Dret de limitació del tractament", "En determinades circumstàncies, les dades només es poden conservar o tractar de forma limitada.", "RGPD art. 18", NivellRisc.MITJA),
    ("RGPD_ART20_PORTABILITAT", "Dret a la portabilitat", "Dret a rebre les dades en format estructurat i a transmetre-les a un altre responsable.", "RGPD art. 20", NivellRisc.MITJA),
    ("RGPD_ART21_OBSECCIO", "Dret d'oposició", "Dret a oposar-se al tractament (en particular màrqueting directe).", "RGPD art. 21", NivellRisc.MITJA),
    # RGPD 1.3
    ("RGPD_ART33_NOTIFICACIO_VIOLACIO", "Notificació de violació a l'autoritat", "Notificar la violació a l'autoritat de control en 72 hores (si és possible).", "RGPD art. 33", NivellRisc.ALT),
    ("RGPD_ART34_COMUNICACIO_VIOLACIO", "Comunicació de la violació a l'interessat", "Comunicar la violació a l'interessat quan impliqui risc elevat.", "RGPD art. 34", NivellRisc.ALT),
    ("RGPD_ART35_PIA", "Avaluació d'impacte (PIA)", "Realitzar avaluació d'impacte quan el tractament comporti risc elevat (i documentar-la).", "RGPD art. 35", NivellRisc.ALT),
    # RGPD 1.4
    # RGPD 1.5
    ("RGPD_ART24_MESURES_COMPLIMENT", "Mesures per assegurar i demostrar el compliment", "Mesures tècniques i organitzatives per garantir i demostrar la conformitat amb el RGPD.", "RGPD art. 24", NivellRisc.MITJA),
    # RGPD 1.6
    # ISO 27701 Annex A
    ("ISO27701_A_6.1", "Condicions per a la recollida i el tractament (PII controller)", "Bases legals i finalitats documentades; tractament just i transparent.", "ISO 27701 Annex A", NivellRisc.MITJA),
    ("ISO27701_A_6.2", "Obligacions per a la recollida de PII", "Recollir només les PII necessàries; informar adequadament.", "ISO 27701 Annex A", NivellRisc.MITJA),
    ("ISO27701_A_6.3", "Tractament alineat amb objectius del responsable", "Tractament alineat amb finalitats declarades; no reutilització incompatible.", "ISO 27701 Annex A", NivellRisc.MITJA),
    ("ISO27701_A_6.4", "Conservació i supressió de PII", "Polítiques i procediments de conservació i supressió; termini determinat.", "ISO 27701 Annex A", NivellRisc.MITJA),
    ("ISO27701_A_6.5", "Drets dels interessats", "Procediments per atendre accés, rectificació, supressió, limitació, portabilitat, oposició.", "ISO 27701 Annex A", NivellRisc.ALT),
    ("ISO27701_A_6.6", "Informació a proporcionar als interessats", "Informació clara i accessible (identitat, finalitat, base legal, drets, etc.).", "ISO 27701 Annex A", NivellRisc.MITJA),
    ("ISO27701_A_6.7", "Consentiment i drets dels menors", "Condicions del consentiment; edat i autorització dels menors.", "ISO 27701 Annex A", NivellRisc.MITJA),
    ("ISO27701_A_6.8", "Dades especials (categoria especial)", "Identificar base legal i excepcions; mesures reforçades.", "ISO 27701 Annex A", NivellRisc.ALT),
    ("ISO27701_A_7", "Transferències de PII (controller)", "Garanties en transferències (contractes, clàusules, decisions d'adequació).", "ISO 27701 Annex A", NivellRisc.MITJA),
    ("ISO27701_A_8", "Registre de les activitats de tractament", "Mantenir registre de tractaments (finalitats, categories, destinataris, etc.).", "ISO 27701 Annex A", NivellRisc.MITJA),
    ("ISO27701_A_9", "Gestió del risc de privacitat i PIA", "Identificar i avaluar riscos; avaluació d'impacte quan correspongui.", "ISO 27701 Annex A", NivellRisc.ALT),
    ("ISO27701_A_10", "Governança i responsabilitat", "Rol del responsable; assignació de responsabilitats; DPO quan sigui aplicable.", "ISO 27701 Annex A", NivellRisc.MITJA),
    # ISO 27701 Annex B
    ("ISO27701_B_6.1", "Condicions per al tractament per compte del responsable", "Tractament només segons instruccions documentades; no ús per a finalitats pròpies incompatibles.", "ISO 27701 Annex B", NivellRisc.ALT),
    ("ISO27701_B_6.2", "Confidencialitat i suport als drets (processador)", "Confidencialitat del personal; suport al responsable per atendre drets.", "ISO 27701 Annex B", NivellRisc.MITJA),
    ("ISO27701_B_6.3", "Sub-processadors", "Garanties en la subcontratació; contractes i autorització del responsable.", "ISO 27701 Annex B", NivellRisc.MITJA),
    ("ISO27701_B_6.4", "Registre (processador)", "Registre de categories d'activitats de tractament per compte del responsable.", "ISO 27701 Annex B", NivellRisc.MITJA),
    ("ISO27701_B_7", "Transferències de PII (processador)", "Complir amb instruccions del responsable i normativa en transferències.", "ISO 27701 Annex B", NivellRisc.MITJA),
    ("ISO27701_B_8", "Seguretat i gestió d'incidents (processador)", "Mesures de seguretat adequades; notificació al responsable en cas de violació.", "ISO 27701 Annex B", NivellRisc.ALT),
]

# Mapa control_id -> base_legal per filtrar el checklist segons les bases dels tractaments.
# "general" = es mostra sempre; consentiment, interes_legitim, etc. = només si algun tractament té aquesta base.
CHECKLIST_BASE_LEGAL: dict[str, str] = {
    "RGPD_ART7_CONSENTIMENT": "consentiment",
    "RGPD_ART8_MENORS": "consentiment",
    "ISO27701_A_6.7": "consentiment",
    "RGPD_ART21_OBSECCIO": "interes_legitim",
    "RGPD_ART9_DADES_ESPECIALS": "general",
    "ISO27701_A_6.8": "general",
}


def get_checklist_metadata() -> list[dict]:
    """Retorna la llista de controls del checklist amb base_legal per filtrar per bases dels tractaments."""
    out = []
    for cid, nom, desc, ref, nivell in _CONTROLS_CHECKLIST:
        out.append({
            "id": cid,
            "nom": nom,
            "descripcio": desc,
            "referencia": ref,
            "nivell": nivell.value,
            "base_legal": CHECKLIST_BASE_LEGAL.get(cid, "general"),
        })
    return out


CRITERIS: list[Criteri] = [
    Criteri(
        id="RGPD_ART6_BASE_LEGAL",
        nom="Base legal del tractament",
        descripcio="Cada activitat de tractament ha de tenir una base legal vàlida (RGPD art. 6).",
        referencia_normativa="RGPD art. 6; LOPD-GDD",
        nivell_risc_defecte=NivellRisc.ALT,
        avaluar=_criteri_base_legal,
    ),
    Criteri(
        id="RGPD_ART5_FINALITAT",
        nom="Finalitat definida",
        descripcio="La finalitat del tractament ha d'estar determinada i documentada (limitació de la finalitat).",
        referencia_normativa="RGPD art. 5.1.b",
        nivell_risc_defecte=NivellRisc.MITJA,
        avaluar=_criteri_finalitat_definida,
    ),
    Criteri(
        id="RGPD_ART5_TERMINI",
        nom="Termini de conservació",
        descripcio="Cal definir el termini de conservació de les dades i criteris de supressió.",
        referencia_normativa="RGPD art. 5.1.e",
        nivell_risc_defecte=NivellRisc.MITJA,
        avaluar=_criteri_termini_conservacio,
    ),
    Criteri(
        id="RGPD_ART5_TERMINI_ADEQUACIO",
        nom="Adequació del termini (indefinit / molt llarg)",
        descripcio="Termini indefinit o molt llarg: cal documentar garanties (art. 89) o justificació.",
        referencia_normativa="RGPD art. 5.1.e, art. 89",
        nivell_risc_defecte=NivellRisc.INFO,
        avaluar=_criteri_termini_adequacio,
    ),
    Criteri(
        id="RGPD_ART30_REGISTRE",
        nom="Registre d'activitats de tractament",
        descripcio="Manteniment del registre d'activitats de tractament (art. 30).",
        referencia_normativa="RGPD art. 30",
        nivell_risc_defecte=NivellRisc.BAIX,
        avaluar=_criteri_registre_activitats,
    ),
    Criteri(
        id="RGPD_ART13_14_POLITICA",
        nom="Política de privacitat i deure d'informació",
        descripcio="Existència i adequació de la informació als interessats (arts. 13 i 14).",
        referencia_normativa="RGPD arts. 13, 14; LOPD-GDD",
        nivell_risc_defecte=NivellRisc.ALT,
        avaluar=_criteri_politica_privacitat,
    ),
    Criteri(
        id="RGPD_ART32_MESURES",
        nom="Mesures de seguretat",
        descripcio="Mesures tècniques i organitzatives adequades per garantir la seguretat de les dades.",
        referencia_normativa="RGPD art. 32",
        nivell_risc_defecte=NivellRisc.MITJA,
        avaluar=_criteri_mesures_seguretat,
    ),
    Criteri(
        id="RGPD_ACCES_RESTRINGIT",
        nom="Control d'accés per rol",
        descripcio="L'accés a les dades ha d'estar restringit al personal autoritzat.",
        referencia_normativa="RGPD art. 32.4; LOPD-GDD",
        nivell_risc_defecte=NivellRisc.MITJA,
        avaluar=_criteri_acces_restringit,
    ),
    Criteri(
        id="REGISTRE_ACCIONS",
        nom="Registre d'accions",
        descripcio="Traçabilitat d'accions sobre dades personals (bones pràctiques).",
        referencia_normativa="RGPD art. 5.2; bones pràctiques",
        nivell_risc_defecte=NivellRisc.MITJA,
        avaluar=_criteri_registre_accions,
    ),
    Criteri(
        id="RGPD_ART37_DPO",
        nom="Delegat de protecció de dades (DPO)",
        descripcio="Designació i comunicació del DPO quan és obligatori.",
        referencia_normativa="RGPD arts. 37, 38, 39",
        nivell_risc_defecte=NivellRisc.MITJA,
        avaluar=_criteri_dpo,
    ),
    Criteri(
        id="RGPD_CAP5_TRANSFERENCIES",
        nom="Transferències internacionals",
        descripcio="Garanties en cas de transferències a països tercers.",
        referencia_normativa="RGPD capítol V",
        nivell_risc_defecte=NivellRisc.MITJA,
        avaluar=_criteri_transferencies,
    ),
]
# Afegir tots els controls que es llegeixen del checklist (RGPD i ISO 27701)
for cid, nom, desc, ref, nivell in _CONTROLS_CHECKLIST:
    CRITERIS.append(Criteri(
        id=cid,
        nom=nom,
        descripcio=desc,
        referencia_normativa=ref,
        nivell_risc_defecte=nivell,
        avaluar=_criteri_checklist(cid, nom, desc, ref, nivell),
    ))
