# Eina d'auditoria de privacitat

Prototip per a l'autoavaluació de compliment de privacitat (RGPD, LOPD-GDD, ISO 27701).

Aquesta carpeta conté el **codi executable** de l'aplicació, les dades d'exemple i la documentació tècnica.

---

## Com executar l'aplicació (pas a pas)

L'aplicació té **dues parts** que cal tenir en marxa alhora:

| Part | Què fa | On s'executa | URL |
|------|--------|----------------|-----|
| **Backend** | API Python (Flask) + motor d'auditoria | Carpeta `eina_auditoria_priv/` | http://127.0.0.1:5000 |
| **Frontend** | Interfície web React (la que heu d'obrir al navegador) | Carpeta `eina_auditoria_priv/frontend/` | http://localhost:5173 |

**Important:** obriu sempre el navegador a **http://localhost:5173** (frontend).  
No utilitzeu http://127.0.0.1:5000 per a la interfície principal — aquella és la UI Flask antiga o només l'API.

### 1. Instal·lació (només la primera vegada)

Obriu PowerShell o terminal **a l'arrel del projecte** — la carpeta `eina_auditoria_priv/` on hi ha aquest README i `requirements.txt`.

Si el repositori està dins una altra carpeta (per exemple el TFM), primer hi entreu:

```powershell
cd eina_auditoria_priv
```

Instal·leu dependències **Python** (backend):

```powershell
pip install -r requirements.txt
```

Instal·leu dependències **Node.js** (frontend):

```powershell
cd frontend
npm install
cd ..
```

### 2. Arrencar l'aplicació (cada vegada que la voleu usar)

Cal **dues terminals obertes**. Primer el backend, després el frontend.

#### Terminal 1 — Backend

Des de l'arrel del projecte (`eina_auditoria_priv/`):

```powershell
py -m eina_auditoria_priv.webapp
```

Heu de veure algo com:

```
 * Running on http://127.0.0.1:5000
```

Deixeu aquesta terminal **oberta** mentre feu servir l'app.

#### Terminal 2 — Frontend

Des de l'arrel del projecte, entreu a `frontend/`:

```powershell
cd frontend
npm run dev
```

Heu de veure algo com:

```
  ➜  Local:   http://localhost:5173/
```

#### 3. Obrir al navegador

Aneu a: **http://localhost:5173**

Flux d'ús:

1. **Inici** — Importar JSON, ROPA, triar plantilla o començar des de zero.
2. **Dades i auditoria** — Omplir dades i clicar «Executar auditoria».
3. **Informe** — Veure resultats per pestanyes (Totals, Generals, per tipus de dades), filtrar i exportar.

---

## Resum visual

```
┌─────────────────────────────────────────────────────────┐
│  Navegador  →  http://localhost:5173  (FRONTEND React)  │
└──────────────────────────┬──────────────────────────────┘
                           │ peticions /api/*
                           ▼
┌─────────────────────────────────────────────────────────┐
│  http://127.0.0.1:5000  (BACKEND Flask)                 │
│  Motor d'auditoria + API REST                           │
└─────────────────────────────────────────────────────────┘
```

---

## Requisits del sistema

- **Python** 3.10 o superior (`py --version`)
- **Node.js** 18 o superior (`node --version`)
- **pip** i **npm** (venen amb Python i Node)

---

## Mode CLI (sense interfície web)

Només backend, des de `eina_auditoria_priv/`:

```powershell
py -m eina_auditoria_priv.cli dades_exemple/cas_mixt_3_tractaments.json -o informe
```

Genera `informe.json`, `informe.txt` i `informe.html` a la carpeta actual.

---

## UI Flask legacy (opcional)

Si obriu http://127.0.0.1:5000 directament veureu la interfície HTML antiga (importació CSV, etc.).  
La interfície **recomanada** és la de React (port 5173).

---

## Solució de problemes

| Què veieu | Què fer |
|-----------|---------|
| `[vite] http proxy error` / `ECONNREFUSED 127.0.0.1:5000` | El **backend no està en marxa**. Obriu la Terminal 1 i executeu `py -m eina_auditoria_priv.webapp`. |
| Pantalla sense colors / sense pestanyes | Esteu al port 5000 en lloc del 5173, o cal `npm install` + `npm run dev` al frontend. |
| `ModuleNotFoundError: No module named 'flask'` | Executeu `pip install -r requirements.txt` des de `eina_auditoria_priv/`. |
| Plantilles buides a Inici | El backend s'ha d'executar des de **`eina_auditoria_priv/`**, no des d'una altra carpeta. |
| Canvis al codi no es veuen | Refresqueu el navegador amb **Ctrl+F5**. Si cal, pareu i torneu a executar `npm run dev`. |
| `npm : no se reconoce...` | Instal·leu Node.js 18+ des de [nodejs.org](https://nodejs.org/). |

---

## Dades d'exemple

Vegeu **[dades_exemple/README_DADES_EXEMPLE.md](dades_exemple/README_DADES_EXEMPLE.md)** per al comportament esperat, comandes CLI i comptadors de referència.

| Fitxer | Propòsit |
|--------|----------|
| `dades_exemple/cas_error_tractaments_no_llista.json` | **Error de validació:** `tractaments` no és una llista |
| `dades_exemple/cas_dades_incompletes.json` | Dades incompletes; molts `no_compleix` |
| `dades_exemple/cas_mixt_3_tractaments.json` | 3 tractaments; T003 sense base legal |
| `dades_exemple/cas_checklist_per_tipus.json` | Checklist General i per tipus de dades |
| `dades_exemple/auditoria_un_no_compleix_tractament.json` | **Prova guiada:** només T003 no compleix |
| `dades_exemple/auditoria_varietat_tractaments.json` | 10 tractaments amb incidències diverses |
| `dades_exemple/cas_import_ropa.json` | Importació ROPA (no JSON intern directe) |
| `dades_exemple/tractaments_exemple.csv` | Import CSV (UI Flask, port 5000) |
| `dades_exemple/plantilles/*.json` | Plantilles des del menú Inici |
| `dades_exemple/proves/` | **Bateria de 31 proves** — [README_PROVES.md](README_PROVES.md) |

---

## Documentació del codi

Consulteu [DOCUMENTACIO_CODI.md](DOCUMENTACIO_CODI.md) per a la referència de cada arxiu, funció i endpoint API.

---

## Avís legal

Les recomanacions generades tenen caràcter orientatiu i **no constitueixen assessorament jurídic**.
