/**
 * Pàgina d'informe: pestanyes per tipus de dades i, dins de cada una,
 * pestanyes secundàries per Resultats / Riscos / Recomanacions.
 */
import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDades } from '../context'
import { exportUrl } from '../api'

const ORDER_OPTIONS = [
  { value: '', label: 'Sense ordenar' },
  { value: 'compleix_first', label: 'Compleixen primer' },
  { value: 'no_compleix_first', label: 'No compleixen primer' },
  { value: 'sense_dades_last', label: 'Sense dades al final' },
]

const FILTER_RESULT_OPTIONS = [
  { value: '', label: 'Tots' },
  { value: 'compleix', label: 'Compleix' },
  { value: 'no_compleix', label: 'No compleix' },
  { value: 'sense_dades', label: 'Sense dades' },
]

function tipusTabLabel(s) {
  if (!s) return '—'
  const t = String(s)
  const labels = {
    Totals: 'Totals', Generals: 'Generals', treballadors: 'Treballadors',
    màrqueting: 'Màrqueting', curriculums: 'Curriculums', videovigilància: 'Videovigilància',
    clients: 'Clients', contacte_web: 'Contacte web', salut: 'Salut', altres: 'Altres',
  }
  return labels[t] || t.charAt(0).toUpperCase() + t.slice(1).replace(/_/g, ' ')
}

const RESULTAT_LABELS = { compleix: 'Compleix', no_compleix: 'No compleix', sense_dades: 'Sense dades' }
const RISC_LABELS = { alt: 'Alt', mitja: 'Mitjà', baix: 'Baix', informat: 'Informat' }
function resultatLabel(k) {
  return (k && RESULTAT_LABELS[k]) || (k ? String(k).charAt(0).toUpperCase() + String(k).slice(1).replace(/_/g, ' ') : '—')
}
function riscLabel(k) {
  return (k && RISC_LABELS[k]) || (k ? String(k).charAt(0).toUpperCase() + String(k).slice(1) : '—')
}

const SECTION_TABS = [
  { id: 'resultats', label: 'Resultats' },
  { id: 'no_compleix', label: 'No compleix' },
  { id: 'compleix', label: 'Compleix' },
  { id: 'riscos', label: 'Riscos' },
  { id: 'recomanacions', label: 'Recomanacions' },
]

/** Ordenació de findings: sense_dades sempre al final; la resta segons l'ordre triat. */
function sortFindings(findings, order) {
  if (!findings?.length) return findings || []
  const rank = (r) => {
    if (r === 'sense_dades') return 2
    if (order === 'no_compleix_first') {
      return r === 'no_compleix' ? 0 : 1
    }
    if (order === 'compleix_first' || order === 'sense_dades_last') {
      return r === 'compleix' ? 0 : 1
    }
    return 0
  }
  return [...findings].sort((a, b) => rank(a.resultat) - rank(b.resultat))
}

function filterFindings(findings, filterResult, filterText) {
  let out = findings || []
  if (filterResult) out = out.filter(f => f.resultat === filterResult)
  if (filterText?.trim()) {
    const q = filterText.trim().toLowerCase()
    out = out.filter(f =>
      (f.nom_criteri || '').toLowerCase().includes(q) ||
      (f.descripcio || '').toLowerCase().includes(q)
    )
  }
  return out
}

function isGeneralItem(item) {
  return !item?.tractament_id && !item?.tractament_nom
}

function getBlocForTab(perTipus, tabName) {
  if (tabName === 'Generals') {
    const totals = perTipus['Totals'] || {}
    const filterGeneral = (items) => (items || []).filter(isGeneralItem)
    const findings = filterGeneral(totals.findings)
    const perResultat = {}
    const perNivell = {}
    for (const f of findings) {
      if (f.resultat) perResultat[f.resultat] = (perResultat[f.resultat] || 0) + 1
      if (f.nivell_risc) perNivell[f.nivell_risc] = (perNivell[f.nivell_risc] || 0) + 1
    }
    return {
      resum: { per_resultat: perResultat, per_nivell_risc: perNivell, total_criteris: findings.length },
      findings,
      riscos: filterGeneral(totals.riscos),
      recomanacions: filterGeneral(totals.recomanacions),
    }
  }
  const key = tabName === 'Totals' ? 'Totals' : tabName
  return perTipus[key] || { resum: {}, findings: [], riscos: [], recomanacions: [] }
}

export default function Informe() {
  const { informe } = useDades()
  const navigate = useNavigate()
  const [tab, setTab] = useState(0)
  const [sectionTab, setSectionTab] = useState('resultats')
  const [sortOrder, setSortOrder] = useState('no_compleix_first')
  const [filterResult, setFilterResult] = useState('')
  const [filterText, setFilterText] = useState('')

  const informeData = informe?.informe
  const meta = informeData?.meta
  const tipus_dades = informeData?.tipus_dades || []
  const per_tipus = informeData?.per_tipus || {}

  const tabsRaw = tipus_dades.length ? tipus_dades : Object.keys(per_tipus)
  const tabs = tabsRaw[0] === 'Totals'
    ? ['Totals', 'Generals', ...tabsRaw.slice(1)]
    : ['Generals', ...tabsRaw]

  const currentTab = tabs[tab] || tabs[0] || 'Totals'

  const bloc = useMemo(
    () => getBlocForTab(per_tipus, currentTab),
    [per_tipus, currentTab]
  )

  const rawFindings = bloc.findings || []
  const riscos = bloc.riscos || []
  const recomanacions = bloc.recomanacions || []

  const filteredFindings = useMemo(
    () => filterFindings(rawFindings, filterResult, filterText),
    [rawFindings, filterResult, filterText]
  )

  const displayedFindings = useMemo(() => {
    let base = filteredFindings
    if (sectionTab === 'no_compleix') base = base.filter(f => f.resultat === 'no_compleix')
    else if (sectionTab === 'compleix') base = base.filter(f => f.resultat === 'compleix')
    return sortFindings(base, sortOrder)
  }, [filteredFindings, sectionTab, sortOrder])

  if (!informeData) {
    return (
      <div className="card text-center py-12">
        <p className="text-slate-600 mb-4">No hi ha cap informe. Executeu primer l'auditoria des de Dades.</p>
        <button type="button" onClick={() => navigate('/dades')} className="btn btn-primary">
          Anar a Dades i executar
        </button>
      </div>
    )
  }

  const showFindings = sectionTab === 'resultats' || sectionTab === 'no_compleix' || sectionTab === 'compleix'
  const showRiscos = sectionTab === 'riscos'
  const showRecomanacions = sectionTab === 'recomanacions'

  const handlePrimaryTab = (index) => {
    setTab(index)
    setSectionTab('resultats')
    setFilterResult('')
    setFilterText('')
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Informe d'auditoria</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {meta?.nom_organitzacio || '—'} · {meta?.data_auditoria || '—'}
          </p>
        </div>
        <div className="flex gap-2">
          <a href={exportUrl(informe.informe_id, 'json')} className="btn btn-secondary text-sm" download>JSON</a>
          <a href={exportUrl(informe.informe_id, 'txt')} className="btn btn-secondary text-sm" download>TXT</a>
          <a href={exportUrl(informe.informe_id, 'html')} className="btn btn-secondary text-sm" download>HTML</a>
        </div>
      </div>

      <div className="space-y-0">
        {tabs.length > 0 && (
          <div className="border-b border-slate-200">
            <nav className="flex flex-wrap gap-1" role="tablist" aria-label="Tipus de dades">
              {tabs.map((t, i) => (
                <button
                  key={t}
                  type="button"
                  role="tab"
                  aria-selected={i === tab}
                  onClick={() => handlePrimaryTab(i)}
                  className={`px-4 py-2.5 text-sm font-medium rounded-t-lg border-b-2 transition ${
                    i === tab
                      ? 'border-primary-600 text-primary-700 bg-white'
                      : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  {tipusTabLabel(t)}
                </button>
              ))}
            </nav>
          </div>
        )}

        <div className="border-b border-slate-200 bg-white/80">
          <nav className="flex flex-wrap gap-1" role="tablist" aria-label="Secció de l'informe">
            {SECTION_TABS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={sectionTab === id}
                onClick={() => setSectionTab(id)}
                className={`px-3 py-2 text-sm font-medium rounded-t-lg border-b-2 transition ${
                  sectionTab === id
                    ? 'border-primary-500 text-primary-700 bg-white'
                    : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <div className="card">
        <h3 className="font-medium text-slate-900 mb-3">Resum — {tipusTabLabel(currentTab)}</h3>
        <div className="flex flex-wrap gap-2 mb-6">
          {Object.entries(bloc.resum?.per_resultat || {}).map(([k, v]) => (
            <span key={k} className={`badge badge-${k}`}>{resultatLabel(k)}: {v}</span>
          ))}
          {Object.entries(bloc.resum?.per_nivell_risc || {}).map(([k, v]) => (
            <span key={k} className={`badge badge-risc-${k}`}>Risc {riscLabel(k)}: {v}</span>
          ))}
        </div>

        {showFindings && (
          <>
            <h3 className="font-medium text-slate-900 mb-2">Resultats per criteri</h3>
            <div className="flex flex-wrap gap-3 mb-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-600 whitespace-nowrap">Ordenar:</span>
                <select value={sortOrder} onChange={e => setSortOrder(e.target.value)} className="select-inline max-w-[200px]">
                  {ORDER_OPTIONS.map(o => (
                    <option key={o.value || 'none'} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-600 whitespace-nowrap">Filtrar per resultat:</span>
                <select value={filterResult} onChange={e => setFilterResult(e.target.value)} className="select-inline max-w-[140px]">
                  {FILTER_RESULT_OPTIONS.map(o => (
                    <option key={o.value || 'none'} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2 flex-1 min-w-[220px]">
                <span className="text-sm text-slate-600 whitespace-nowrap">Cercar:</span>
                <input
                  type="text"
                  value={filterText}
                  onChange={e => setFilterText(e.target.value)}
                  placeholder="Nom o descripció del criteri..."
                  className="input-inline flex-1"
                />
              </div>
            </div>
            {(filterText || filterResult) && (
              <p className="text-sm text-slate-500 mb-2">
                Es mostren {displayedFindings.length} de {rawFindings.length} criteris.
              </p>
            )}
            <ul className="space-y-2 mb-6">
              {displayedFindings.length === 0 ? (
                <li className="text-slate-500 text-sm py-4">Cap criteri coincideix amb el filtre.</li>
              ) : (
                displayedFindings.map((f, i) => (
                  <li
                    key={`${f.criteri_id}-${f.tractament_id || ''}-${i}`}
                    className={`p-3 rounded-lg border-l-4 ${
                      f.resultat === 'compleix' ? 'bg-emerald-50 border-emerald-500' :
                      f.resultat === 'no_compleix' ? 'bg-red-50 border-red-500' : 'bg-slate-50 border-slate-300'
                    }`}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`font-medium shrink-0 px-2 py-0.5 rounded text-sm badge badge-${f.resultat}`}>
                        {resultatLabel(f.resultat)}
                      </span>
                      <span className="font-medium text-slate-900">{f.nom_criteri}</span>
                      {(f.tractament_id || f.tractament_nom) ? (
                        <span className="text-xs px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                          {f.tractament_nom || f.tractament_id}
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-500">General</span>
                      )}
                    </div>
                    <p className="text-sm text-slate-600 mt-1">{f.descripcio}</p>
                  </li>
                ))
              )}
            </ul>
          </>
        )}

        {showRiscos && (
          <>
            <h3 className="font-medium text-slate-900 mb-2">Riscos identificats</h3>
            {!riscos.length ? (
              <p className="text-slate-500 text-sm mb-6">No s'han identificat riscos addicionals.</p>
            ) : (
              <ul className="space-y-2 mb-6">
                {riscos.map((r, i) => {
                  const niv = (r.nivell || '').toLowerCase()
                  const riscClass = niv === 'alt' ? 'bg-red-50 border-red-500'
                    : niv === 'mitja' ? 'bg-amber-50 border-amber-500'
                    : niv === 'baix' ? 'bg-emerald-50 border-emerald-500'
                    : 'bg-slate-50 border-slate-400'
                  return (
                    <li key={r.id || i} className={`p-3 rounded-lg border-l-4 ${riscClass}`}>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`font-medium shrink-0 px-2 py-0.5 rounded text-sm badge badge-risc-${niv}`}>
                          {riscLabel(r.nivell)}
                        </span>
                        <span className="font-medium text-slate-900">{r.titol}</span>
                        {(r.tractament_id || r.tractament_nom) ? (
                          <span className="text-xs px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                            {r.tractament_nom || r.tractament_id}
                          </span>
                        ) : (
                          <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-500">General</span>
                        )}
                      </div>
                      <p className="text-sm text-slate-600 mt-1">{r.descripcio}</p>
                    </li>
                  )
                })}
              </ul>
            )}
          </>
        )}

        {showRecomanacions && (
          <>
            <h3 className="font-medium text-slate-900 mb-2">Recomanacions</h3>
            {!recomanacions.length ? (
              <p className="text-slate-500 text-sm">No hi ha recomanacions pendents.</p>
            ) : (
              <ul className="space-y-3">
                {recomanacions.map((rec, i) => (
                  <li key={rec.id || i} className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-slate-900">{rec.titol}</span>
                      <span className={`badge badge-risc-${(rec.prioritat || '').toLowerCase()}`}>
                        {riscLabel(rec.prioritat)}
                      </span>
                      {(rec.tractament_id || rec.tractament_nom) ? (
                        <span className="text-xs px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                          {rec.tractament_nom || rec.tractament_id}
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-500">General</span>
                      )}
                    </div>
                    <p className="text-sm text-slate-600 mt-1">{rec.descripcio}</p>
                    {rec.accions?.length > 0 && (
                      <ul className="list-disc list-inside text-sm text-slate-600 mt-2 space-y-1">
                        {rec.accions.map((a, j) => <li key={j}>{a}</li>)}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </div>
  )
}
