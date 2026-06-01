# Dades d'exemple — guia d'ús i comportament esperat

Aquest directori conté fitxers per provar la càrrega de dades i l'auditoria fora de la bateria formal de [`proves/`](proves/) (31 casos amb respostes esperades).

Cada JSON d'auditoria inclou un bloc `_meta` (ignorat pel motor) amb la descripció del cas.

## Com executar

Des de la carpeta `eina_auditoria_priv/`:

```powershell
py -m eina_auditoria_priv.cli dades_exemple/<fitxer>.json --print
```

Importació ROPA (no usar «Importar JSON»):

```powershell
# Via API amb backend en marxa, o React Inici → Importar ROPA
```

CSV: només interfície Flask (`http://127.0.0.1:5000` → Importar CSV), fitxer `tractaments_exemple.csv`.

## Resum dels fitxers

| Fitxer | Carrega | Com usar-lo | Comportament esperat |
|--------|---------|-------------|----------------------|
| `cas_error_tractaments_no_llista.json` | **Error** | Importar JSON / CLI | Validació: `tractaments` ha de ser una **llista**. Exit code 1. |
| `cas_dades_incompletes.json` | OK | CLI / JSON | Molts incumpliments: sense base legal, termini, mesures, política, accés. |
| `cas_mixt_3_tractaments.json` | OK | CLI / JSON | T001 i T002 OK; **T003** sense base legal. |
| `cas_checklist_per_tipus.json` | OK | CLI / JSON | 5 tractaments; checklist General + overrides `curriculums` / `videovigilància`. |
| `auditoria_un_no_compleix_tractament.json` | OK | CLI / JSON | Només **T003** en vermell (base legal); T001/T002 conformes. |
| `auditoria_varietat_tractaments.json` | OK | CLI / JSON | 10 tractaments; T001+T009 referència; diversos motius a `notes`. |
| `cas_import_ropa.json` | OK (ROPA) | **Importar ROPA** | 3 activitats; sense política/accés fins omplir formulari. |
| `tractaments_exemple.csv` | OK (CSV) | Flask import CSV | 3 tractaments; T003 sense mesures i sense DPO. |

## Comptadors de referència (motor actual)

Valors de `resum.per_resultat` a l'avaluació global (**Totals**), generats amb el motor en vigor. Si canvieu `criteria.py`, torneu a mesurar.

| Fitxer | compleix | no_compleix | sense_dades |
|--------|----------|-------------|-------------|
| `cas_dades_incompletes.json` | 4 | 16 | 29 |
| `cas_mixt_3_tractaments.json` | 25 | 4 | 29 |
| `cas_checklist_per_tipus.json` | 65 | 4 | 0 |
| `auditoria_un_no_compleix_tractament.json` | 28 | 1 | 29 |
| `auditoria_varietat_tractaments.json` | 63 | 16 | 18 |
| `cas_import_ropa` (després import) | — | 4 | 31 |
| `tractaments_exemple.csv` (3 tract.) | — | 4 | — |

### Detall per cas

**`cas_error_tractaments_no_llista.json`** — `tractaments` és un objecte, no un array. No arriba a executar-se l'auditoria.

**`cas_dades_incompletes.json`** — Un tractament amb camps buits i política inexistent; útil per capturar incidències a la UI.

**`cas_mixt_3_tractaments.json`** — Escenari didàctic: incumpliment localitzat al tractament T003 (`RGPD_ART6_BASE_LEGAL`).

**`cas_checklist_per_tipus.json`** — T002: transferències internacionals sense `contractes_processadors` documentats. T003/T004: `conte_dades_sensibles` sense mesura `dades_sensibles_reforç`. Checklist només amb IDs definits al motor (vegeu `get_checklist_metadata`).

**`auditoria_un_no_compleix_tractament.json`** — Ideal per la demo «2 de 3 compleixen» a la pestanya General.

**`auditoria_varietat_tractaments.json`** — Politica `actualitzada: false`; incidències per transferències, base legal, mesures, DPO, finalitat, termini, etc. (vegeu `notes` de cada tractament).

**`cas_import_ropa.json`** — Format anglès (`processingActivities`, `legalBasis`, …). Després de importar: ompliu política i accés abans d'esperar compliment en aquests criteris.

**`tractaments_exemple.csv`** — Separador `;`. T003: sense mesures de seguretat i DPO assignat = No → findings art. 32 i art. 37.

## Relació amb `proves/`

La bateria de regressió (31 casos) viu a `dades_exemple/proves/` amb fitxers `entrada/` i `esperades/`. Els fitxers d'aquest directori són **escenaris manuals** per demos i documentació, no substitueixen `executar_proves.py`.

## Validació automàtica

```powershell
py -m unittest tests.test_validacio_tractaments
py dades_exemple/proves/executar_proves.py
```
