"""
Importació de dades tipus ROPA (Registre d'activitats de tractament) cap al model intern.
Accepta JSON amb estructura flexible (UROPA-like o similar) i el converteix a DadesEntradaAuditoria.
"""

from __future__ import annotations

from .model import DadesEntradaAuditoria, Tractament, PoliticaPrivacitat, ConfiguracioAcces
from .constants import MESURES_SEGURETAT_PREDEFINIDES, CATEGORIES_DADES_PREDEFINIDES


# Mapatge de noms típics en JSON ROPA → camp del nostre model (Tractament)
_NOM_TRACTAMENT = (
    "name", "nom", "title", "processingActivityName", "activityName", "nom_tractament"
)
_FINALITAT = (
    "purpose", "finalitat", "purposes", "processingPurpose", "finality", "objectiu"
)
_BASE_LEGAL = (
    "legalBasis", "base_legal", "lawfulBasis", "legal_basis", "baseLegal", "legitimacio"
)
_CATEGORIES = (
    "categoriesOfPersonalData", "categories_dades", "dataCategories", "categories",
    "personalDataCategories", "categories_dades_personals"
)
_DESTINATARIS = (
    "recipients", "destinataris", "recipient", "dataRecipients", "destinatari"
)
_TERMINI = (
    "retention", "termini_conservacio", "retentionPeriod", "storagePeriod",
    "termini", "conservacio", "retentionPeriodDescription"
)
_MESURES = (
    "securityMeasures", "mesures_seguretat", "technicalAndOrganisationalMeasures",
    "mesures", "security", "mesures_tecnicas"
)
_TRANSFERENCIES = (
    "internationalTransfers", "transferencies_internacionals", "thirdCountryTransfers",
    "transferencies", "transfers"
)
_DPO = ("dpoAssigned", "dpo_assignat", "hasDPO", "dataProtectionOfficer")
_TIPUS = ("category", "tipus_dades", "dataType", "type", "sector", "businessArea")
_ID = ("id", "internalId", "reference", "codigo")


def _first_key(obj: dict, keys: tuple[str, ...], default=None):
    """Retorna el valor de la primera clau que existeixi a obj."""
    if not obj or not isinstance(obj, dict):
        return default
    for k in keys:
        if k in obj:
            val = obj[k]
            if val is not None and val != "":
                return val
    return default


def _list_value(val) -> list:
    """Normalitza a llista (strings es parteixen per comes si cal)."""
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if x]
    if isinstance(val, str):
        return [x.strip() for x in val.split(",") if x.strip()]
    return [str(val)]


def _bool_value(val) -> bool:
    """Normalitza a booleà."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "sí", "si", "s")
    return bool(val)


# Mapes text → id per normalitzar a llistats predefinits
_IDS_MESURES = {m["id"]: m["id"] for m in MESURES_SEGURETAT_PREDEFINIDES}
_IDS_CATEGORIES = {c["id"]: c["id"] for c in CATEGORIES_DADES_PREDEFINIDES}

_MAP_TEXT_MESURA = {
    "accés restringit per rol": "acces_restringit_rol", "accés restringit": "acces_restringit_rol",
    "accés per rol": "acces_restringit_rol", "xifrat en repòs": "xifrat", "xifrat": "xifrat",
    "còpies de seguretat": "copies_seguretat", "còpies": "copies_seguretat",
    "acords de confidencialitat": "acords_confidencialitat", "acord de confidencialitat": "acords_confidencialitat",
    "confidencialitat contractual": "acords_confidencialitat", "auditoria d'accés": "registre_acces",
    "registre de consentiments": "registre_consentiments", "registre consentiments": "registre_consentiments",
    "link de baixa": "link_baixa", "link baixa": "link_baixa", "llegenda unsub": "link_baixa",
    "clàusules tipus": "contractes_processadors", "supressió programada": "supressio_programada",
    "suport en local": "control_acces_fisic", "cartell informatiu": "cartell_informatiu",
}
for m in MESURES_SEGURETAT_PREDEFINIDES:
    _MAP_TEXT_MESURA[m["id"]] = m["id"]
    _MAP_TEXT_MESURA[m["nom"].lower()] = m["id"]

_MAP_TEXT_CATEGORIA = {
    "dades d'empleat": "dades_laborals", "dades econòmiques": "dades_economiques", "dades economiques": "dades_economiques",
    "nif/nie": "nif_nie", "dades de contacte": "dades_contacte", "contacte": "dades_contacte",
    "email": "email", "nom": "nom", "preferències": "preferencies_comunicacio", "preferències de comunicació": "preferencies_comunicacio",
    "dades de currículum": "curriculum", "currículum": "curriculum",
    "formació": "formacio_experiencia", "experiència professional": "formacio_experiencia", "experiència": "formacio_experiencia",
    "imatges": "imatge", "registre d'accés": "registre_acces_visitants", "dades de facturació": "dades_facturacio",
    "facturació": "dades_facturacio", "historial comercial": "historial_comercial", "historial": "historial_comercial",
    "missatge": "missatge",
}
for c in CATEGORIES_DADES_PREDEFINIDES:
    _MAP_TEXT_CATEGORIA[c["id"]] = c["id"]
    _MAP_TEXT_CATEGORIA[c["nom"].lower()] = c["id"]


def _normalitzar_mesures(raw: list) -> list[str]:
    """Retorna només ids del llistat predefinit (mapejant text conegut si cal)."""
    out = []
    seen = set()
    for x in raw:
        key = str(x).strip().lower()
        id_val = _MAP_TEXT_MESURA.get(key) or _IDS_MESURES.get(key) or _IDS_MESURES.get(key.replace(" ", "_"))
        if id_val and id_val not in seen:
            seen.add(id_val)
            out.append(id_val)
    return out


def _normalitzar_categories(raw: list) -> list[str]:
    """Retorna només ids del llistat predefinit (mapejant text conegut si cal)."""
    out = []
    seen = set()
    for x in raw:
        key = str(x).strip().lower()
        id_val = _MAP_TEXT_CATEGORIA.get(key) or _IDS_CATEGORIES.get(key) or _IDS_CATEGORIES.get(key.replace(" ", "_").replace("'", "_"))
        if id_val and id_val not in seen:
            seen.add(id_val)
            out.append(id_val)
    return out


def _inferir_tipus(nom: str, finalitat: str, category: str | None) -> str | None:
    """Inferir tipus_dades a partir de nom, finalitat o category."""
    text = f" {nom or ''} {finalitat or ''} {category or ''} ".lower()
    if any(x in text for x in ("hr", "rrhh", "nòmina", "nomina", "treballador", "employee", "laboral")):
        return "treballadors"
    if any(x in text for x in ("marketing", "màrqueting", "newsletter", "comunicació")):
        return "màrqueting"
    if any(x in text for x in ("candidat", "curriculum", "currículum", "recruitment", "selecció")):
        return "curriculums"
    if any(x in text for x in ("video", "càmera", "vigilància", "accés", "control accés")):
        return "videovigilància"
    if any(x in text for x in ("client", "customer", "crm", "facturació", "comercial")):
        return "clients"
    if any(x in text for x in ("salut", "health", "pacient", "clínica")):
        return "salut"
    return None


def ropa_to_internal(ropa: dict) -> dict:
    """
    Converteix un JSON tipus ROPA (registre d'activitats) al format intern DadesEntradaAuditoria.
    Accepta estructures com:
    - { "processingActivities": [ {...}, ... ], "organisation": "...", ... }
    - { "activities": [ {...}, ... ] }
    - { "items": [ {...}, ... ] }
    - [ {...}, {...} ]  (array directe de tractaments)
    """
    activities = (
        ropa.get("processingActivities")
        or ropa.get("activities")
        or ropa.get("items")
        or ropa.get("treatments")
        or ropa.get("tractaments")
    )
    if activities is None and isinstance(ropa, list):
        activities = ropa
    if not isinstance(activities, list):
        raise ValueError(
            "El fitxer JSON no sembla un format ROPA-like compatible. "
            "Revisa que contingui una llista d'activitats a 'processingActivities', 'activities', 'items', "
            "'treatments' o 'tractaments' (o bé un array directe de tractaments). "
            "Si no encaixa, utilitza una plantilla o una entrada alternativa (p. ex. CSV amb mapatge)."
        )
    if not activities:
        raise ValueError(
            "No s'han trobat activitats dins el JSON ROPA-like. "
            "Per poder importar, cal que hi hagi almenys un element d'activitat (processing/activities/items...). "
            "Si el teu export no encaja, utilitza una plantilla o normalitza la informació abans d'importar."
        )

    tractaments = []
    for i, item in enumerate(activities):
        if not isinstance(item, dict):
            continue
        nom = _first_key(item, _NOM_TRACTAMENT) or f"Tractament {i+1}"
        finalitat = _first_key(item, _FINALITAT) or ""
        raw_base = _first_key(item, _BASE_LEGAL)
        if isinstance(raw_base, list):
            base_legal = [str(x).strip().lower().replace(" ", "_")[:50] for x in raw_base if x and str(x).strip()]
        elif raw_base and isinstance(raw_base, str):
            base_legal = [raw_base.strip().lower().replace(" ", "_")[:50]]
        else:
            base_legal = []
        categories = _normalitzar_categories(_list_value(_first_key(item, _CATEGORIES)))
        destinataris = _list_value(_first_key(item, _DESTINATARIS))
        termini = _first_key(item, _TERMINI)
        mesures = _normalitzar_mesures(_list_value(_first_key(item, _MESURES)))
        transferencies = _bool_value(_first_key(item, _TRANSFERENCIES, False))
        dpo = _bool_value(_first_key(item, _DPO, False))
        tipus = _first_key(item, _TIPUS) or _inferir_tipus(
            nom, finalitat, _first_key(item, ("category", "type"))
        )
        if tipus and isinstance(tipus, str):
            tipus = tipus.strip() or None
        tid = _first_key(item, _ID) or f"T{i+1:03d}"

        # Inferir dades sensibles si les categories inclouen salut / especial
        _cat_str = " ".join(str(c).lower() for c in categories) if categories else ""
        # categories i mesures ja estan normalitzats als ids predefinits
        conte_sensibles = _bool_value(_first_key(item, ("sensitiveData", "conte_dades_sensibles", "specialCategoryData"))) or (
            "salut" in _cat_str or "health" in _cat_str or "especial" in _cat_str or "special" in _cat_str
        )
        tractaments.append({
            "id": str(tid),
            "nom": str(nom),
            "finalitat": str(finalitat),
            "base_legal": base_legal,
            "categories_dades": categories,
            "destinataris": destinataris,
            "transferencies_internacionals": transferencies,
            "termini_conservacio": termini,
            "mesures_seguretat": mesures,
            "dpo_assignat": dpo,
            "tipus_dades": tipus,
            "conte_dades_sensibles": conte_sensibles,
            "notes": "",
        })
    if not tractaments:
        raise ValueError(
            "El JSON s'ha llegit, però no s'ha pogut convertir cap activitat al format intern. "
            "Assegura't que cada element de la llista d'activitats sigui un objecte (dict) amb camps mínims "
            "com nom i finalitat (o almenys un identificador). Si no encaixa, utilitza una plantilla o normalitza la informació."
        )

    nom_org = (
        ropa.get("organisation")
        or ropa.get("nom_organitzacio")
        or ropa.get("organizationName")
        or ropa.get("dataController", {}).get("name") if isinstance(ropa.get("dataController"), dict) else None
        or ""
    )
    if isinstance(nom_org, dict):
        nom_org = nom_org.get("name", "") or ""
    data_aud = ropa.get("data_auditoria") or ropa.get("auditDate") or ropa.get("lastUpdated") or ""

    return {
        "nom_organitzacio": str(nom_org) if nom_org else "",
        "data_auditoria": str(data_aud)[:10] if data_aud else "",
        "tractaments": tractaments,
        "politica_privacitat": None,
        "configuracio_acces": None,
        "checklist_controls": {},
        "altres_notes": "Importat des de format ROPA.",
    }
