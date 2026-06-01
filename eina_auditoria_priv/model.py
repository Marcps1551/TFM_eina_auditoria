"""
Model de dades per a l'entrada de l'auditoria de privacitat.
Defineix l'estructura que ha de tenir la informació que introdueix l'empresa
per ser avaluada (configuracions, pràctiques, tractaments).
Referència: RGPD arts. 5, 6, 13/14, 30; LOPD-GDD.
"""

from dataclasses import dataclass, field
from typing import Optional


# Checklist: id_control -> True/False. Pot ser global (un sol dict) o per tipus_dades (dict de dicts).
# Per tipus: primer clau = "General" o nom del tipus (ex. "curriculums"); segon clau = id_control.
# En avaluar per tipus es fusiona "General" + el dict del tipus concret.


@dataclass
class Tractament:
    """Activitat de tractament de dades personals (registre d'activitats)."""
    id: str
    nom: str
    finalitat: str
    base_legal: list[str] = field(default_factory=list)  # una o més bases (RGPD art. 6.1): consentiment, contracte, obligacio_legal, etc.
    categories_dades: list[str] = field(default_factory=list)
    destinataris: list[str] = field(default_factory=list)
    transferencies_internacionals: bool = False
    termini_conservacio: Optional[str] = None  # ex: "2 anys", "fins baixa"
    mesures_seguretat: list[str] = field(default_factory=list)  # IDs de MESURES_SEGURETAT_PREDEFINIDES o text lliure (compatibilitat)
    dpo_assignat: bool = False
    tipus_dades: Optional[str] = None  # ex: "curriculums", "treballadors", "clients" — per segmentar l'informe
    conte_dades_sensibles: bool = False  # RGPD art. 9: dades de salut, orígens, etc.
    notes: str = ""

    def to_dict(self) -> dict:
        """Serialització a diccionari (per JSON / sessió)."""
        return {
            "id": self.id,
            "nom": self.nom,
            "finalitat": self.finalitat,
            "base_legal": self.base_legal,
            "categories_dades": self.categories_dades,
            "destinataris": self.destinataris,
            "transferencies_internacionals": self.transferencies_internacionals,
            "termini_conservacio": self.termini_conservacio,
            "mesures_seguretat": self.mesures_seguretat,
            "dpo_assignat": self.dpo_assignat,
            "tipus_dades": self.tipus_dades,
            "conte_dades_sensibles": self.conte_dades_sensibles,
            "notes": self.notes,
        }


@dataclass
class PoliticaPrivacitat:
    """Existència i contingut de la política de privacitat / informació."""
    existeix: bool = False
    accessible: bool = False
    contingut_deure_informacio: bool = False  # identitat, finalitat, base legal, drets, etc.
    actualitzada: bool = False
    idiomes: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        """Serialitza la política de privacitat a diccionari."""
        return {
            "existeix": self.existeix,
            "accessible": self.accessible,
            "contingut_deure_informacio": self.contingut_deure_informacio,
            "actualitzada": self.actualitzada,
            "idiomes": self.idiomes,
            "notes": self.notes,
        }


@dataclass
class ConfiguracioAcces:
    """Control d'accés i permisos als dades."""
    acces_restringit_per_rol: bool = False
    registre_accions: bool = False
    formacio_obligatoria: bool = False
    confidencialitat_contractual: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        """Serialitza la configuració d'accés a diccionari."""
        return {
            "acces_restringit_per_rol": self.acces_restringit_per_rol,
            "registre_accions": self.registre_accions,
            "formacio_obligatoria": self.formacio_obligatoria,
            "confidencialitat_contractual": self.confidencialitat_contractual,
            "notes": self.notes,
        }


@dataclass
class DadesEntradaAuditoria:
    """Conjunt de dades d'entrada per a una auditoria."""
    nom_organitzacio: str = ""
    data_auditoria: str = ""
    tractaments: list[Tractament] = field(default_factory=list)
    politica_privacitat: Optional[PoliticaPrivacitat] = None
    configuracio_acces: Optional[ConfiguracioAcces] = None
    # id_control -> bool (format pla, un sol bloc) O tipus_dades -> { id_control -> bool } (per grup)
    checklist_controls: dict = field(default_factory=dict)
    altres_notes: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "DadesEntradaAuditoria":
        """Construcció des d'un diccionari (p. ex. JSON)."""
        def _normalize_base_legal(val):
            if val is None:
                return []
            if isinstance(val, list):
                return [str(x).strip() for x in val if x and str(x).strip()]
            if isinstance(val, str) and val.strip():
                return [val.strip()]
            return []

        def _bool(val):
            if val is None:
                return False
            if isinstance(val, bool):
                return val
            return str(val).strip().lower() in ("true", "1", "yes", "sí", "si")

        def _to_list(val, default=None):
            if default is None:
                default = []
            if val is None:
                return default
            if isinstance(val, list):
                return [str(x).strip() for x in val if x is not None and str(x).strip()]
            if isinstance(val, str):
                return [s.strip() for s in val.replace(";", ",").split(",") if s.strip()]
            return default

        def _termini_str(val):
            """Normalitza termini a string per emmagatzemar (accepta objecte estructurat o string)."""
            if val is None:
                return None
            if isinstance(val, str):
                return val.strip() or None
            if isinstance(val, dict):
                predef = val.get("predefinit") or val.get("predef")
                if predef:
                    return str(predef).strip()
                v, u = val.get("valor"), val.get("unitat") or val.get("unit")
                if v is not None and u:
                    return f"{v} {u}"
            return None

        tractaments_raw = d.get("tractaments")
        if not isinstance(tractaments_raw, list):
            tractaments_raw = []
        tractaments = []
        for t in tractaments_raw:
            if not isinstance(t, dict):
                continue
            tractaments.append(Tractament(
                id=str(t.get("id", "")),
                nom=str(t.get("nom", "")),
                finalitat=str(t.get("finalitat", "")),
                base_legal=_normalize_base_legal(t.get("base_legal")),
                categories_dades=_to_list(t.get("categories_dades")),
                destinataris=_to_list(t.get("destinataris")),
                transferencies_internacionals=_bool(t.get("transferencies_internacionals")),
                termini_conservacio=_termini_str(t.get("termini_conservacio")),
                mesures_seguretat=_to_list(t.get("mesures_seguretat")),
                dpo_assignat=_bool(t.get("dpo_assignat")),
                tipus_dades=str(t.get("tipus_dades", "")).strip() or None,
                conte_dades_sensibles=_bool(t.get("conte_dades_sensibles")),
                notes=str(t.get("notes", "")),
            ))
        pp = d.get("politica_privacitat")
        if not isinstance(pp, dict):
            pp = None
        politica = PoliticaPrivacitat(
            existeix=bool(pp.get("existeix", False)),
            accessible=bool(pp.get("accessible", False)),
            contingut_deure_informacio=bool(pp.get("contingut_deure_informacio", False)),
            actualitzada=bool(pp.get("actualitzada", False)),
            idiomes=_to_list(pp.get("idiomes", [])) if pp.get("idiomes") else [],
            notes=str(pp.get("notes") or ""),
        ) if pp else None
        ca = d.get("configuracio_acces")
        if not isinstance(ca, dict):
            ca = None
        acces = ConfiguracioAcces(
            acces_restringit_per_rol=bool(ca.get("acces_restringit_per_rol", False)),
            registre_accions=bool(ca.get("registre_accions", False)),
            formacio_obligatoria=bool(ca.get("formacio_obligatoria", False)),
            confidencialitat_contractual=bool(ca.get("confidencialitat_contractual", False)),
            notes=str(ca.get("notes") or ""),
        ) if ca else None
        raw_checklist = d.get("checklist_controls")
        if raw_checklist is None or not isinstance(raw_checklist, dict):
            checklist = {}
        else:
            # Format per tipus: keys = "General" o tipus_dades, values = { id_control -> bool }
            if all(isinstance(v, dict) for v in raw_checklist.values()):
                checklist = {k: {kk: vv for kk, vv in v.items() if isinstance(vv, bool)} for k, v in raw_checklist.items()}
            else:
                # Format antic (pla): id_control -> bool → es guarda com a "General"
                checklist = {"General": {k: v for k, v in raw_checklist.items() if isinstance(v, bool)}}
        return cls(
            nom_organitzacio=d.get("nom_organitzacio", ""),
            data_auditoria=d.get("data_auditoria", ""),
            tractaments=tractaments,
            politica_privacitat=politica,
            configuracio_acces=acces,
            checklist_controls=checklist,
            altres_notes=d.get("altres_notes", ""),
        )

    def to_dict(self) -> dict:
        """Serialització a diccionari (per JSON / sessió)."""
        return {
            "nom_organitzacio": self.nom_organitzacio,
            "data_auditoria": self.data_auditoria,
            "tractaments": [t.to_dict() for t in self.tractaments],
            "politica_privacitat": self.politica_privacitat.to_dict() if self.politica_privacitat else None,
            "configuracio_acces": self.configuracio_acces.to_dict() if self.configuracio_acces else None,
            "checklist_controls": self.checklist_controls,
            "altres_notes": self.altres_notes,
        }
