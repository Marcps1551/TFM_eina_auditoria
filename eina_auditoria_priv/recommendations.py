"""
Generació de recomanacions accionables a partir dels resultats de l'avaluació.
Cada tipus de no compliment es mapja a recomanacions concretes amb referència normativa.
"""

from dataclasses import dataclass
from typing import Optional

from .criteria import ResultatCriteri, NivellRisc
from .evaluator import Finding, ResultatAvaluacio


@dataclass
class Recomanacio:
    """Recomanació accionable per millorar el compliment. Opcionalment associada a un tractament."""
    id: str
    titol: str
    descripcio: str
    accions: list[str]
    referencia_normativa: str
    prioritat: NivellRisc
    criteri_origen: str = ""
    tractament_id: Optional[str] = None
    tractament_nom: Optional[str] = None


# Mapatge criteri_id (quan NO_COMPLEIX) -> recomanacions
MAPA_RECOMANACIONS: dict[str, list[dict]] = {
    "RGPD_ART6_BASE_LEGAL": [
        {
            "titol": "Definir la base legal de cada tractament",
            "descripcio": "Per a cada activitat de tractament, identifiqueu i documenteu una base legal vàlida (consentiment, execució del contracte, obligació legal, etc.).",
            "accions": [
                "Revisar cada tractament i assignar una base legal conforme a l'art. 6.1 RGPD.",
                "Documentar la base legal al registre d'activitats de tractament (art. 30).",
                "Assegurar que la informació als interessats (arts. 13/14) reflecteixi la base legal.",
            ],
            "referencia": "RGPD art. 6; LOPD-GDD.",
        },
    ],
    "RGPD_ART5_FINALITAT": [
        {
            "titol": "Documentar la finalitat de cada tractament",
            "descripcio": "La finalitat ha d'estar determinada, explícita i legítima, i documentada.",
            "accions": [
                "Incloure la finalitat concreta a la fitxa de cada tractament al registre d'activitats.",
                "Evitar tractaments amb finalitats massa genèriques; concretar-ne l'àmbit.",
            ],
            "referencia": "RGPD art. 5.1.b.",
        },
    ],
    "RGPD_ART5_TERMINI": [
        {
            "titol": "Establir terminis de conservació i criteris de supressió",
            "descripcio": "Cal definir per a cada tractament el termini de conservació i els criteris que permetin esborrar o anonimitzar les dades.",
            "accions": [
                "Definir terminis per tipus de dades i finalitat (ex.: 2 anys, fins a la baixa, obligació legal).",
                "Documentar-los al registre d'activitats i a les polítiques internes.",
                "Implementar processos de supressió o anonimització al final del termini.",
            ],
            "referencia": "RGPD art. 5.1.e.",
        },
    ],
    "RGPD_ART13_14_POLITICA": [
        {
            "titol": "Disposar d'una política de privacitat completa i accessible",
            "descripcio": "Heu d'informar les persones interessades de tots els elements exigits pels arts. 13 i 14 RGPD.",
            "accions": [
                "Redactar o actualitzar la política de privacitat amb: identitat del responsable, finalitats, base legal, destinataris, termini de conservació, drets (accés, rectificació, supressió, limitació, portabilitat, oposició, reclamació a l'AEPD), i dades de contacte del DPO si n'hi ha.",
                "Fer la política fàcilment accessible (enllaç visible, sense capes innecessàries).",
                "Revisar-la periòdicament i actualitzar-la quan canviïn els tractaments.",
            ],
            "referencia": "RGPD arts. 12, 13, 14; guies AEPD.",
        },
    ],
    "RGPD_ART32_MESURES": [
        {
            "titol": "Implementar i documentar mesures de seguretat",
            "descripcio": "Cal adoptar mesures tècniques i organitzatives adequades al risc per garantir la confidencialitat, integritat i disponibilitat de les dades. Per tractaments amb dades identificatives (NIF/NIE) o dades bancàries, es recomana especialment el xifrat.",
            "accions": [
                "Realitzar una avaluació de riscos (si escau) i documentar les mesures adoptades per a cada tractament o tipus de dades.",
                "Incloure, segons el cas: control d'accés, xifrat, pseudonimització, còpies de seguretat, procediments de resposta a incidents.",
                "Per tractaments amb NIF/NIE, IBAN o dades bancàries: implementar xifrat (en repòs i en trànsit) i documentar-ho.",
                "Revisar les mesures amb periodicitat i en canvis significatius.",
            ],
            "referencia": "RGPD art. 32; LOPD-GDD.",
        },
    ],
    "RGPD_ACCES_RESTRINGIT": [
        {
            "titol": "Restringir l'accés a les dades per rol",
            "descripcio": "Només el personal autoritzat ha de poder accedir a les dades personals necessàries per a les seves funcions.",
            "accions": [
                "Definir rols i permisos en funció de la necessitat de tractament.",
                "Configurar els sistemes (BBDD, aplicacions) per aplicar el principi de mínim accés.",
                "Revisar periòdicament qui té accés i retirar-lo quan deixi de ser necessari.",
            ],
            "referencia": "RGPD art. 32.4.",
        },
    ],
    "REGISTRE_ACCIONS": [
        {
            "titol": "Implementar registre d'accions sobre dades personals",
            "descripcio": "Es recomana tenir traçabilitat dels accesos o actuacions rellevants sobre dades personals.",
            "accions": [
                "Valorar l'activació de logs d'accés a sistemes que continguin dades personals.",
                "Definir una política de retenció dels logs i qui pot consultar-los.",
            ],
            "referencia": "RGPD art. 5.2; bones pràctiques.",
        },
    ],
    "RGPD_FORMACIO_OBLIGATORIA": [
        {
            "titol": "Implantar formació obligatòria en protecció de dades",
            "descripcio": "El personal que tracta dades personals ha de conèixer les obligacions de privacitat i seguretat aplicables.",
            "accions": [
                "Definir un pla de formació inicial i de reciclatge en RGPD i bones pràctiques de seguretat.",
                "Documentar l'assistència i el contingut de la formació per a qui accedeix a dades personals.",
                "Incloure la formació com a mesura de seguretat als tractaments rellevants del registre d'activitats.",
            ],
            "referencia": "RGPD art. 32; art. 39.",
        },
    ],
    "RGPD_CONFIDENCIALITAT_CONTRACTUAL": [
        {
            "titol": "Garantir confidencialitat contractual",
            "descripcio": "Qui accedeix a dades personals ha d'estar subjecte a un deure de confidencialitat.",
            "accions": [
                "Incloure clàusules de confidencialitat als contractes laborals i amb encarregats del tractament.",
                "Documentar acords de confidencialitat amb personal intern i extern amb accés a dades.",
                "Revisar periòdicament que els acords estiguin vigents i signats.",
            ],
            "referencia": "RGPD art. 32.4; art. 28.",
        },
    ],
    "RGPD_ART37_DPO": [
        {
            "titol": "Revisar la necessitat de designar un DPO",
            "descripcio": "Segons l'art. 37 RGPD, cal designar un delegat de protecció de dades en determinats supòsits (autoritat pública, tractament a gran escala, etc.).",
            "accions": [
                "Comprovar si l'organització està obligada a designar DPO (RGPD art. 37).",
                "Si cal, designar un DPO i comunicar les seves dades de contacte als interessats i a l'AEPD.",
                "Garantir que el DPO participa en totes les qüestions relatives a la protecció de dades.",
            ],
            "referencia": "RGPD arts. 37, 38, 39.",
        },
    ],
    "RGPD_CAP5_TRANSFERENCIES": [
        {
            "titol": "Garantir les transferències internacionals",
            "descripcio": "Les transferències de dades a països fora de l'EEE requereixen garanties adequades (decisió d'adequació, clàusules tipus, etc.).",
            "accions": [
                "Identificar tots els tractaments que impliquen transferències internacionals.",
                "Comprovar que existeix una base legal per a la transferència (decisió d'adequació, clàusules tipus, etc.) i documentar-la.",
                "Informer els interessats de les transferències i les garanties aplicables.",
            ],
            "referencia": "RGPD capítol V.",
        },
    ],
    "RGPD_ART5_TERMINI_ADEQUACIO": [
        {
            "titol": "Revisar terminis de conservació indefinits o molt llargs",
            "descripcio": "Els terminis indefinits o superiors a 10 anys requereixen justificació i, si escau, garanties addicionals (ex. art. 89 RGPD per arxivament, recerca).",
            "accions": [
                "Documentar la justificació del termini de conservació per a cada tractament amb termini indefinit o molt llarg.",
                "Si el tractament és per arxivament, recerca o estadística: assegurar garanties (pseudonimització, limitació d'accés) conforme a l'art. 89.",
                "Revisar periòdicament si el termini segueix sent necessari i proporcional.",
            ],
            "referencia": "RGPD art. 5.1.e; art. 89.",
        },
    ],
}


def generar_recomanacions(resultat: ResultatAvaluacio) -> list[Recomanacio]:
    """Genera una recomanació per cada finding NO_COMPLEIX (duplicat per tractament quan n'hi ha diversos).
    També afegeix recomanacions informatives per a criteris com RGPD_ART5_TERMINI_ADEQUACIO (terminis indefinits/llargs)."""
    recomanacions = []
    rec_index = 0
    # Recomanacions informatives (SENSE_DADES) per criteris amb entrada al mapa (ex. terminis indefinits/llargs)
    for f in resultat.findings:
        if f.resultat != ResultatCriteri.SENSE_DADES:
            continue
        if f.criteri_id != "RGPD_ART5_TERMINI_ADEQUACIO":
            continue
        blocs = MAPA_RECOMANACIONS.get(f.criteri_id, [])
        for i, b in enumerate(blocs):
            recomanacions.append(Recomanacio(
                id=f"REC_{f.criteri_id}_info_{rec_index}_{i}",
                titol=b["titol"],
                descripcio=b["descripcio"],
                accions=b["accions"],
                referencia_normativa=b["referencia"],
                prioritat=NivellRisc.INFO,
                criteri_origen=f.criteri_id,
                tractament_id=getattr(f, "tractament_id", None),
                tractament_nom=getattr(f, "tractament_nom", None),
            ))
        rec_index += 1
    # Recomanacions per NO_COMPLEIX
    for f in resultat.findings:
        if f.resultat != ResultatCriteri.NO_COMPLEIX:
            continue
        blocs = MAPA_RECOMANACIONS.get(f.criteri_id, [])
        if not blocs:
            recomanacions.append(Recomanacio(
                id=f"REC_{f.criteri_id}_{rec_index}",
                titol=f"Millorar: {f.nom_criteri}",
                descripcio=f.descripcio,
                accions=["Revisar el compliment del criteri i documentar les accions preses."],
                referencia_normativa=f.referencia_normativa,
                prioritat=f.nivell_risc,
                criteri_origen=f.criteri_id,
                tractament_id=getattr(f, "tractament_id", None),
                tractament_nom=getattr(f, "tractament_nom", None),
            ))
            rec_index += 1
            continue
        for i, b in enumerate(blocs):
            recomanacions.append(Recomanacio(
                id=f"REC_{f.criteri_id}_{rec_index}_{i}",
                titol=b["titol"],
                descripcio=b["descripcio"],
                accions=b["accions"],
                referencia_normativa=b["referencia"],
                prioritat=f.nivell_risc,
                criteri_origen=f.criteri_id,
                tractament_id=getattr(f, "tractament_id", None),
                tractament_nom=getattr(f, "tractament_nom", None),
            ))
        rec_index += 1
    return recomanacions
