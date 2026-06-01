"""
Constants compartides: mesures de seguretat preestablertes i mapa amb els controls
que es consideren complerts quan un tractament té determinades mesures aplicades.
"""

# Mesures de seguretat preestablertes (id, nom, descripció). L'usuari en selecciona les que aplica.
MESURES_SEGURETAT_PREDEFINIDES: list[dict] = [
    {"id": "xifrat", "nom": "Xifrat de dades", "descripcio": "Xifrat en repòs i/o en trànsit (RGPD art. 32)."},
    {"id": "acces_restringit_rol", "nom": "Accés restringit per rol", "descripcio": "Control d'accés segons necessitat (mínim accés)."},
    {"id": "pseudonimitzacio", "nom": "Pseudonimització", "descripcio": "Dades pseudonimitzades quan és possible."},
    {"id": "copies_seguretat", "nom": "Còpies de seguretat", "descripcio": "Còpies de seguretat regulars i recuperació."},
    {"id": "registre_acces", "nom": "Registre d'accés", "descripcio": "Registre (logs) d'accés a les dades."},
    {"id": "control_acces_fisic", "nom": "Control d'accés físic", "descripcio": "Restriccions d'accés a instal·lacions/suports."},
    {"id": "politica_contrasenyes", "nom": "Política de contrasenyes", "descripcio": "Requisits de contrasenya (complexitat, renovació)."},
    {"id": "anonimitzacio", "nom": "Anonimització", "descripcio": "Anonimització quan la finalitat ho permet."},
    {"id": "dades_sensibles_reforç", "nom": "Mesures reforçades (dades sensibles)", "descripcio": "Mesures addicionals per a dades de categoria especial (art. 9)."},
    {"id": "avaluacio_riscos", "nom": "Avaluació de riscos", "descripcio": "Avaluació de riscos de privacitat documentada."},
    {"id": "formacio", "nom": "Formació del personal", "descripcio": "Formació en protecció de dades i seguretat."},
    {"id": "contractes_processadors", "nom": "Contractes amb processadors", "descripcio": "Contractes/encàrrecs amb garanties (art. 28)."},
    {"id": "acords_confidencialitat", "nom": "Acords de confidencialitat", "descripcio": "Acords o clàusules de confidencialitat amb qui accedeix a les dades."},
    {"id": "registre_consentiments", "nom": "Registre de consentiments", "descripcio": "Registre de consentiments (prova, revocació)."},
    {"id": "supressio_programada", "nom": "Supressió programada", "descripcio": "Procediment o automatisme de supressió de dades al final del termini."},
    {"id": "cartell_informatiu", "nom": "Cartell informatiu (art. 12 LOPD-GDD)", "descripcio": "Informació als afectats (videovigilància, etc.)."},
    {"id": "link_baixa", "nom": "Link de baixa / unsub", "descripcio": "Possibilitat de donar-se de baixa de comunicacions comercials."},
]

# Categories de dades que impliquen tractament de categoria especial (RGPD art. 9).
# Si un tractament inclou alguna i no s'ha marcat conte_dades_sensibles, l'avaluació pot indicar inconsistència.
CATEGORIES_SENSIBLES_IDS: set[str] = {
    "dades_salut", "ideologia_sindical", "biometria", "genetics", "salut", "origen",
    "dades_salut_mental", "vida_sexual", "religio", "etnic",
}

# Categories que, per risc, haurien de tenir xifrat (NIF, dades bancàries, etc.). Donen resultat diferent a l'avaluació.
CATEGORIES_ALTRISC_XIFRAT: set[str] = {
    "nif_nie", "dades_bancaries", "nif", "nie", "iban", "dades bancàries",
}

# Terminis de conservació preestablerts considerats adequats (presència documentada).
TERMINI_IDS_ADEQUATS: set[str] = {"fins_baixa", "fins_renovacio", "obligacio_legal", "indefinit"}

# Quan un tractament té una d'aquestes mesures, els controls indicats es consideren complerts
# (a la avaluació es fusiona el checklist manual amb aquests).
# Clau = id_control del checklist; valor = llista d'ids de mesures que el satisfan.
CONTROL_SATISFET_PER_MESURA: dict[str, list[str]] = {
    "RGPD_ART25_PROTECCIO_DISSENY": ["xifrat", "pseudonimitzacio", "anonimitzacio"],
    "RGPD_ART24_MESURES_COMPLIMENT": ["avaluacio_riscos", "registre_acces"],
    "RGPD_ART32_MESURES": ["xifrat", "acces_restringit_rol", "copies_seguretat", "registre_acces", "politica_contrasenyes"],
    "ISO27701_A_9": ["avaluacio_riscos"],
    "RGPD_ART28_PROCESSADOR": ["contractes_processadors"],
    "RGPD_ART9_DADES_ESPECIALS": ["dades_sensibles_reforç"],
    "ISO27701_A_6.8": ["dades_sensibles_reforç"],
    "RGPD_ART35_PIA": ["avaluacio_riscos"],
    "RGPD_ART5_MINIMITZACIO": ["pseudonimitzacio", "anonimitzacio"],
    "RGPD_ART5_EXACTITUD": ["registre_acces"],
    "RGPD_ART15_ACCES": ["registre_acces"],
    "RGPD_ART16_RECTIFICACIO": ["registre_acces"],
    "RGPD_ART17_SUPRESSIO": ["registre_acces"],
    "ISO27701_A_6.5": ["registre_acces"],
}

# Opcions preestablertes per al termini de conservació (per triar a la UI).
TERMINI_OPCIONS_PREDEFINIDES: list[dict] = [
    {"id": "fins_baixa", "nom": "Fins a la baixa / fi de la relació", "descripcio": "Conservació mentre hi hagi relació laboral o contractual."},
    {"id": "fins_renovacio", "nom": "Fins a revocació / renovació del consentiment", "descripcio": "Mentre l'interessat no revoqui."},
    {"id": "obligacio_legal", "nom": "Segons obligació legal", "descripcio": "Termini imposat per normativa (ex. fiscal, laboral)."},
    {"id": "indefinit", "nom": "Indefinit (documentació històrica)", "descripcio": "Arxivat, recerca, etc. amb garanties art. 89."},
]
TERMINI_UNITATS: list[dict] = [
    {"id": "dies", "nom": "Dies"},
    {"id": "mesos", "nom": "Mesos"},
    {"id": "anys", "nom": "Anys"},
]

# Categories de dades personals preestablertes (per triar i afegir als tractaments).
CATEGORIES_DADES_PREDEFINIDES: list[dict] = [
    {"id": "nom", "nom": "Nom i cognoms"},
    {"id": "email", "nom": "Correu electrònic"},
    {"id": "telefon", "nom": "Telèfon"},
    {"id": "nif_nie", "nom": "NIF / NIE"},
    {"id": "adreca", "nom": "Adreça postal"},
    {"id": "data_naixement", "nom": "Data de naixement"},
    {"id": "dades_bancaries", "nom": "Dades bancàries (IBAN, etc.)"},
    {"id": "dades_salut", "nom": "Dades de salut"},
    {"id": "dades_laborals", "nom": "Dades laborals (contracte, nòmina, etc.)"},
    {"id": "curriculum", "nom": "Currículum / formació acadèmica"},
    {"id": "imatge", "nom": "Imatge / fotografia"},
    {"id": "videovigilancia", "nom": "Imatges de videovigilància"},
    {"id": "ip_navegacio", "nom": "IP / dades de navegació"},
    {"id": "cookies", "nom": "Cookies / preferències"},
    {"id": "ideologia_sindical", "nom": "Ideologia, sindicació"},
    {"id": "dades_contacte", "nom": "Dades de contacte"},
    {"id": "dades_economiques", "nom": "Dades econòmiques / nòmines"},
    {"id": "dades_facturacio", "nom": "Dades de facturació"},
    {"id": "preferencies_comunicacio", "nom": "Preferències de comunicació"},
    {"id": "formacio_experiencia", "nom": "Formació i experiència professional"},
    {"id": "registre_acces_visitants", "nom": "Registre d'accés (visitants)"},
    {"id": "historial_comercial", "nom": "Historial comercial"},
    {"id": "missatge", "nom": "Missatge / contingut (formulari)"},
    {"id": "altres", "nom": "Altres (especificar a les notes)"},
]
