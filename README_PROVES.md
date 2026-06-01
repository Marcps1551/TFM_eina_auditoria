# Bateria de proves — Eina d'auditoria de privacitat

Conjunt de **31 casos de prova** amb dades d'entrada JSON i **respostes esperades** generades pel motor d'avaluació. Serveix per validar el comportament de l'eina, reproduir escenaris concrets i documentar les casuístiques cobertes.

---

## Estructura de fitxers

```
dades_exemple/proves/
├── README_PROVES.md          ← aquest document
├── _plantilla_base.json      ← plantilla mínima reutilitzable
├── generar_esperades.py      ← regenera fitxers a esperades/
├── executar_proves.py        ← valida entrades vs esperades
├── entrada/                  ← 31 fitxers JSON d'entrada
│   ├── 01_complet_perfecte.json
│   ├── ...
│   └── 31_mixte_multiple_incumpliments.json
└── esperades/                ← 31 fitxers JSON de resposta esperada
    ├── 01_complet_perfecte.json
    └── ...
```

Cada parella `entrada/XX_*.json` + `esperades/XX_*.json` descriu un escenari d'auditoria i el resultat que el motor ha de produir.

---

## Com executar les proves

Des de la carpeta `eina_auditoria_priv/`:

```powershell
# Validar totes les proves (31 casos)
py dades_exemple/proves/executar_proves.py

# Regenerar respostes esperades després de canvis al motor
py dades_exemple/proves/generar_esperades.py
```

**Quan regenerar:** si modifiqueu `criteria.py`, `evaluator.py` o `recommendations.py`, executeu `generar_esperades.py` i reviseu el diff abans de commitar.

**Prova individual via CLI:**

```powershell
py -m eina_auditoria_priv.cli dades_exemple/proves/entrada/04_base_legal_parcial.json --print
```

---

## Format de la resposta esperada

Cada fitxer a `esperades/` conté:

| Camp | Descripció |
|------|------------|
| `fitxer_entrada` | Nom del JSON d'entrada associat |
| `resum` | Comptatge global per resultat (`compleix`, `no_compleix`, `sense_dades`) i nivell de risc |
| `num_riscos` | Nombre de riscos identificats (findings `no_compleix`) |
| `num_recomanacions` | Recomanacions generades |
| `findings_no_compleix` | Llista detallada de cada incumpliment |
| `findings_sense_dades` | Controls informatius sense dades suficients |
| `riscos` | Resum dels riscos (id, títol, nivell, tractament) |
| `per_tipus_dades` | Resum segmentat per `tipus_dades` de cada tractament |

---

## Resultats de la bateria (referència)

| # | Fitxer | no_compleix | riscos | Casuística principal |
|---|--------|-------------|--------|----------------------|
| 01 | `01_complet_perfecte` | 0 | 0 | Organització totalment conforme |
| 02 | `02_sense_tractaments` | 0 | 0 | Sense tractaments declarats |
| 03 | `03_sense_base_legal` | 3 | 3 | Cap base legal (art. 6 + principis) |
| 04 | `04_base_legal_parcial` | 1 | 1 | 2/3 compleixen; T003 sense base legal |
| 05 | `05_sense_finalitat` | 3 | 3 | Finalitat buida (art. 5.1.b + principis) |
| 06 | `06_sense_termini` | 5 | 5 | Termini buit (art. 5.1.e + ISO A.6.4 + principis) |
| 07 | `07_termini_indefinit` | 0 | 0 | Termini indefinit → avís informatiu |
| 08 | `08_termini_molt_llarg` | 0 | 0 | Termini >10 anys → avís informatiu |
| 09 | `09_politica_inexistent` | 4 | 4 | Sense política de privacitat |
| 10 | `10_politica_no_accessible` | 2 | 2 | Política no accessible |
| 11 | `11_politica_incompleta` | 2 | 2 | Deure d'informació incomplet |
| 12 | `12_politica_desactualitzada` | 1 | 1 | Política no actualitzada (risc baix) |
| 13 | `13_sense_mesures_seguretat` | 2 | 2 | Sense mesures de seguretat (art. 32) |
| 14 | `14_nif_sense_xifrat` | 0 | 0 | NIF sense xifrat — veure nota (*) |
| 15 | `15_acces_no_restringit` | 1 | 1 | Accés no restringit per rol |
| 16 | `16_sense_registre_accions` | 2 | 2 | Sense traçabilitat / accountability |
| 17 | `17_sense_dpo_tots` | 3 | 3 | Cap tractament amb DPO |
| 18 | `18_dpo_parcial` | 1 | 1 | DPO parcial (1 de 2) |
| 19 | `19_transferencies_sense_garanties` | 2 | 2 | Transferències sense contractes |
| 20 | `20_transferencies_conformes` | 0 | 0 | Transferències amb contractes_processadors |
| 21 | `21_dades_sensibles_sense_reforc` | 6 | 6 | Dades art. 9 sense mesures reforçades + PIA |
| 22 | `22_dades_sensibles_conformes` | 0 | 0 | Dades sensibles amb reforç i PIA |
| 23 | `23_pia_sense_avaluacio` | 6 | 6 | Tractament de risc sense avaluacio_riscos |
| 24 | `24_sense_categories_dades` | 0 | 0 | Categories buides — veure nota (*) |
| 25 | `25_checklist_compleix` | 0 | 0 | Checklist manual amb respostes `true` |
| 26 | `26_checklist_no_compleix` | 3 | 3 | Checklist manual amb respostes `false` |
| 27 | `27_checklist_per_tipus` | 0 | 0 | Checklist diferent per tipus_dades (**) |
| 28 | `28_acces_via_mesura_tractament` | 0 | 0 | Accés restringit via mesura del tractament |
| 29 | `29_categories_sensibles_inconsistent` | 2 | 2 | Categories sensibles sense flag marcat |
| 30 | `30_responsabilitat_via_mesures` | 1 | 1 | Accountability via avaluacio_riscos |
| 31 | `31_mixte_multiple_incumpliments` | 12 | 12 | Escenari mixte amb diversos tractaments |

(*) **Notes sobre limitacions del motor:**

- **Prova 14:** el criteri automàtic `RGPD_ART32_MESURES` comprova només que hi ha mesures documentades, no l'adequació del xifrat per a NIF/IBAN. Com que el tractament té mesures (`acces_restringit_rol`, `copies_seguretat`), el resultat és **COMPLEIX**. La lògica de xifrat per categories d'alt risc existeix a `_avaluar_estructurat` però requereix el control al checklist (no actiu per defecte).
- **Prova 24:** el control `RGPD_ART5_MINIMITZACIO` no forma part del checklist actiu per defecte; categories buides no generen `no_compleix` automàticament.

(**) **Prova 27:** el resum global pot ser 0 `no_compleix` perquè el checklist General té respostes `true`. Els incumpliments apareixen a la segmentació **`curriculums`** (`num_no_compleix=2` per supressió i limitació).

---

## Catàleg detallat per casuística

### A. Escenaris conformes (referència positiva)

#### 01 — Complet perfecte
- **Entrada:** 1 tractament laboral amb tots els camps, política completa, accés configurat, checklist parcial `true`.
- **Esperat:** 0 incumpliments, 0 riscos.
- **Valida:** base legal, finalitat, termini, mesures, DPO, política, accés, registre.

#### 20 — Transferències conformes
- **Entrada:** Transferència internacional amb `contractes_processadors` a les mesures.
- **Esperat:** COMPLEIX en `RGPD_CAP5_TRANSFERENCIES` i `RGPD_ART28_PROCESSADOR`.

#### 22 — Dades sensibles conformes
- **Entrada:** `conte_dades_sensibles=true` amb `dades_sensibles_reforç` i `avaluacio_riscos`.
- **Esperat:** COMPLEIX en art. 9, ISO A.6.8 i art. 35 (PIA).

---

### B. Registre d'activitats i tractaments

#### 02 — Sense tractaments
- **Entrada:** `tractaments: []`
- **Esperat:** `SENSE_DADES` informatiu en criteris per tractament; política i accés s'avaluen igualment.

#### 04 — Base legal parcial (prova guiada)
- **Entrada:** 3 tractaments; T003 sense `base_legal`.
- **Esperat:**
  - General `RGPD_ART6_BASE_LEGAL`: **COMPLEIX** («2 de 3 tractaments compleixen»)
  - T003: **NO_COMPLEIX** (risc alt)
- **Ús recomanat:** demostrar resum parcial a la pestanya «Generals» vs detall per tractament.

---

### C. RGPD art. 6 — Base legal

| Prova | Escenari | Criteri afectat | Resultat |
|-------|----------|-----------------|----------|
| 03 | Tots sense base legal | `RGPD_ART6_BASE_LEGAL`, `RGPD_ART5_PRINCIPIS` | NO_COMPLEIX |
| 04 | Un de tres sense base | `RGPD_ART6_BASE_LEGAL` | Parcial |

---

### D. RGPD art. 5 — Principis i terminis

| Prova | Escenari | Criteris | Resultat |
|-------|----------|----------|----------|
| 05 | Finalitat buida | `RGPD_ART5_FINALITAT`, `RGPD_ART5_PRINCIPIS` | NO_COMPLEIX |
| 06 | Termini buit | `RGPD_ART5_TERMINI`, `ISO27701_A_6.4`, `RGPD_ART5_PRINCIPIS` | NO_COMPLEIX |
| 07 | Termini «indefinit» | `RGPD_ART5_TERMINI_ADEQUACIO` | SENSE_DADES (informatiu) |
| 08 | Termini «15 anys» | `RGPD_ART5_TERMINI_ADEQUACIO` | SENSE_DADES (informatiu) |

---

### E. Política de privacitat (arts. 12–14)

| Prova | Condició | Resultat |
|-------|----------|----------|
| 09 | `existeix: false` | NO_COMPLEIX (política + modalitats art. 12) |
| 10 | `accessible: false` | NO_COMPLEIX |
| 11 | `contingut_deure_informacio: false` | NO_COMPLEIX |
| 12 | `actualitzada: false` | NO_COMPLEIX (risc baix) |

---

### F. Seguretat (art. 32) i accés

| Prova | Escenari | Resultat |
|-------|----------|----------|
| 13 | `mesures_seguretat: []` | NO_COMPLEIX (criteri automàtic + checklist) |
| 14 | Mesures sense xifrat per NIF | COMPLEIX (*) — només presència |
| 15 | `acces_restringit_per_rol: false` | NO_COMPLEIX |
| 28 | Accés via mesura `acces_restringit_rol` al tractament | COMPLEIX (malgrat config global false) |

---

### G. Traçabilitat i DPO

| Prova | Escenari | Resultat |
|-------|----------|----------|
| 16 | `registre_accions: false` | NO_COMPLEIX (`REGISTRE_ACCIONS`, `RGPD_ART5_2_RESPONSABILITAT`) |
| 30 | `registre_accions: false` però `avaluacio_riscos` al tractament | COMPLEIX accountability |
| 17 | Cap tractament amb DPO | NO_COMPLEIX per a cada tractament |
| 18 | DPO parcial | General parcial + T002 NO_COMPLEIX |

---

### H. Transferències internacionals (cap. V)

| Prova | Escenari | Resultat |
|-------|----------|----------|
| 19 | `transferencies_internacionals: true` sense contractes | NO_COMPLEIX |
| 20 | Amb `contractes_processadors` | COMPLEIX |

---

### I. Dades especials (art. 9) i PIA (art. 35)

| Prova | Escenari | Resultat |
|-------|----------|----------|
| 21 | `conte_dades_sensibles: true` sense reforç | NO_COMPLEIX (art. 9, ISO A.6.8, PIA) |
| 22 | Amb reforç i PIA | COMPLEIX |
| 23 | Sensibles sense `avaluacio_riscos` | NO_COMPLEIX múltiple |
| 29 | Categories `dades_salut` però `conte_dades_sensibles: false` | NO_COMPLEIX + avís inconsistència |

---

### J. Checklist manual i per tipus

| Prova | Escenari | Resultat |
|-------|----------|----------|
| 25 | Checklist `General` amb `true` | COMPLEIX als controls indicats |
| 26 | Checklist amb `false` | NO_COMPLEIX als controls indicats |
| 27 | Checklist per `tipus_dades` | Global OK; `curriculums` amb 2 NO_COMPLEIX |

**Format checklist per tipus:**

```json
"checklist_controls": {
  "General": { "RGPD_ART15_ACCES": true },
  "curriculums": { "RGPD_ART17_SUPRESSIO": false }
}
```

En avaluar per tipus, es fusiona `General` + el dict del tipus concret.

---

### K. Escenari mixte (integració)

#### 31 — Múltiples incumpliments
- **Entrada:** 5 tractaments amb errors diferents (transferències, base legal, mesures, sensibles, DPO).
- **Esperat:** 12 `no_compleix`, 12 riscos.
- **Valida:** segmentació per `tipus_dades` (`treballadors`, `màrqueting`, `curriculums`, `clients`, `salut_laboral`).

---

## Tipus de resultat

| Valor | Significat | Color a la UI |
|-------|------------|---------------|
| `compleix` | El criteri es considera satisfet | Verd |
| `no_compleix` | Incumpliment detectat; genera risc i recomanació | Vermell |
| `sense_dades` | No es pot avaluar o avís informatiu | Gris / informatiu |
| `no_aplicable` | Criteri no aplicable a l'escenari | — |

---

## Relació amb altres dades d'exemple

| Fitxer existent | Relació amb la bateria de proves |
|-----------------|----------------------------------|
| `auditoria_un_no_compleix_tractament.json` | Equivalent conceptual a la prova **04** |
| `auditoria_varietat_tractaments.json` | Similar a la prova **31** (més tractaments) |
| `cas_mixt_3_tractaments.json` | Cas general d'ús, no duplicat a `proves/` — vegeu [dades_exemple/README_DADES_EXEMPLE.md](dades_exemple/README_DADES_EXEMPLE.md) |

---

## Afegir una prova nova

1. Creeu `entrada/32_nom_descriptiu.json` seguint l'estructura de `_plantilla_base.json`.
2. Documenteu la casuística a `altres_notes` dins del JSON.
3. Executeu `py dades_exemple/proves/generar_esperades.py`.
4. Reviseu el fitxer generat a `esperades/`.
5. Executeu `py dades_exemple/proves/executar_proves.py` per validar.
6. Afegiu una fila a la taula d'aquest README.

---

## Avís

Les respostes esperades reflecteixen el comportament **actual** del motor d'avaluació. Tenen caràcter orientatiu i no constitueixen assessorament jurídic.
