/**
 * Pàgina de dades i auditoria: formulari d'organització, tractaments, política,
 * configuració d'accés, checklist de controls i execució de l'auditoria.
 */
import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { getGeneralChecklistMap, applyDefaultChecklistTrue } from '../checklistUtils'
import { useDades } from '../context'
import { executarAuditoria, getChecklistMetadata, getMesuresSeguretat, getTerminiOpcions, getCategoriesDades } from '../api'

/** Objecte buit per a un tractament nou. */
const defaultTractament = () => ({
  id: '',
  nom: '',
  finalitat: '',
  base_legal: [],
  categories_dades: [],
  destinataris: [],
  transferencies_internacionals: false,
  termini_conservacio: '',
  mesures_seguretat: [],
  dpo_assignat: false,
  tipus_dades: '',
  conte_dades_sensibles: false,
  termini_unitat: 'anys',
  notes: '',
})

const BASES_LEGALS = [
  { value: 'consentiment', label: 'Consentiment (art. 6.1 a)' },
  { value: 'execucio_contracte', label: 'Execució de contracte (art. 6.1 b)' },
  { value: 'obligacio_legal', label: 'Obligació legal (art. 6.1 c)' },
  { value: 'interes_legitim', label: 'Interès legítim (art. 6.1 f)' },
  { value: 'vital', label: 'Protecció d\'interessos vitals (art. 6.1 d)' },
  { value: 'altre', label: 'Altre' },
]

const TIPUS_DADES = ['treballadors', 'màrqueting', 'curriculums', 'videovigilància', 'clients', 'contacte_web', 'salut', 'altres']
const TIPUS_DADES_LABELS = {
  treballadors: 'Treballadors',
  màrqueting: 'Màrqueting',
  curriculums: 'Curriculums',
  videovigilància: 'Videovigilància',
  clients: 'Clients',
  contacte_web: 'Contacte web',
  salut: 'Salut',
  altres: 'Altres',
}
const tipusLabel = (v) => (v && TIPUS_DADES_LABELS[v]) || (v ? String(v).charAt(0).toUpperCase() + String(v).slice(1).replace(/_/g, ' ') : '—')

// Llistats per defecte (es mostren si la API no respon o està buida)
const DEFAULT_MESURES_SEGURETAT = [
  { id: 'xifrat', nom: 'Xifrat de dades', descripcio: 'Xifrat en repòs i/o en trànsit (RGPD art. 32).' },
  { id: 'acces_restringit_rol', nom: 'Accés restringit per rol', descripcio: 'Control d\'accés segons necessitat.' },
  { id: 'pseudonimitzacio', nom: 'Pseudonimització', descripcio: 'Dades pseudonimitzades quan és possible.' },
  { id: 'copies_seguretat', nom: 'Còpies de seguretat', descripcio: 'Còpies de seguretat regulars i recuperació.' },
  { id: 'registre_acces', nom: 'Registre d\'accés', descripcio: 'Registre (logs) d\'accés a les dades.' },
  { id: 'control_acces_fisic', nom: 'Control d\'accés físic', descripcio: 'Restriccions d\'accés a instal·lacions.' },
  { id: 'politica_contrasenyes', nom: 'Política de contrasenyes', descripcio: 'Requisits de contrasenya.' },
  { id: 'anonimitzacio', nom: 'Anonimització', descripcio: 'Anonimització quan la finalitat ho permet.' },
  { id: 'dades_sensibles_reforç', nom: 'Mesures reforçades (dades sensibles)', descripcio: 'Mesures addicionals art. 9.' },
  { id: 'avaluacio_riscos', nom: 'Avaluació de riscos', descripcio: 'Avaluació de riscos documentada.' },
  { id: 'formacio', nom: 'Formació del personal', descripcio: 'Formació en protecció de dades.' },
  { id: 'contractes_processadors', nom: 'Contractes amb processadors', descripcio: 'Contractes amb garanties (art. 28).' },
  { id: 'acords_confidencialitat', nom: 'Acords de confidencialitat', descripcio: 'Acords o clàusules de confidencialitat.' },
  { id: 'registre_consentiments', nom: 'Registre de consentiments', descripcio: 'Registre de consentiments (prova, revocació).' },
  { id: 'supressio_programada', nom: 'Supressió programada', descripcio: 'Procediment de supressió al final del termini.' },
  { id: 'cartell_informatiu', nom: 'Cartell informatiu (art. 12 LOPD-GDD)', descripcio: 'Informació als afectats (videovigilància).' },
  { id: 'link_baixa', nom: 'Link de baixa / unsub', descripcio: 'Possibilitat de donar-se de baixa.' },
]
const DEFAULT_TERMINI_OPCIONS = {
  predefinits: [
    { id: 'fins_baixa', nom: 'Fins a la baixa / fi de la relació', descripcio: 'Conservació mentre hi hagi relació laboral o contractual.' },
    { id: 'fins_renovacio', nom: 'Fins a revocació / renovació del consentiment', descripcio: 'Mentre l\'interessat no revoqui.' },
    { id: 'obligacio_legal', nom: 'Segons obligació legal', descripcio: 'Termini imposat per normativa (ex. fiscal, laboral).' },
    { id: 'indefinit', nom: 'Indefinit (documentació històrica)', descripcio: 'Arxivat, recerca, etc. amb garanties art. 89.' },
  ],
  unitats: [
    { id: 'dies', nom: 'Dies' },
    { id: 'mesos', nom: 'Mesos' },
    { id: 'anys', nom: 'Anys' },
  ],
}
const DEFAULT_CATEGORIES_DADES = [
  { id: 'nom', nom: 'Nom i cognoms' },
  { id: 'email', nom: 'Correu electrònic' },
  { id: 'telefon', nom: 'Telèfon' },
  { id: 'nif_nie', nom: 'NIF / NIE' },
  { id: 'adreca', nom: 'Adreça postal' },
  { id: 'data_naixement', nom: 'Data de naixement' },
  { id: 'dades_bancaries', nom: 'Dades bancàries (IBAN, etc.)' },
  { id: 'dades_salut', nom: 'Dades de salut' },
  { id: 'dades_laborals', nom: 'Dades laborals (contracte, nòmina, etc.)' },
  { id: 'curriculum', nom: 'Currículum / formació acadèmica' },
  { id: 'imatge', nom: 'Imatge / fotografia' },
  { id: 'videovigilancia', nom: 'Imatges de videovigilància' },
  { id: 'ip_navegacio', nom: 'IP / dades de navegació' },
  { id: 'cookies', nom: 'Cookies / preferències' },
  { id: 'ideologia_sindical', nom: 'Ideologia, sindicació' },
  { id: 'dades_contacte', nom: 'Dades de contacte' },
  { id: 'dades_economiques', nom: 'Dades econòmiques / nòmines' },
  { id: 'dades_facturacio', nom: 'Dades de facturació' },
  { id: 'preferencies_comunicacio', nom: 'Preferències de comunicació' },
  { id: 'formacio_experiencia', nom: 'Formació i experiència professional' },
  { id: 'registre_acces_visitants', nom: "Registre d'accés (visitants)" },
  { id: 'historial_comercial', nom: 'Historial comercial' },
  { id: 'missatge', nom: 'Missatge / contingut (formulari)' },
  { id: 'altres', nom: 'Altres (especificar a les notes)' },
]

// Ids i paraules clau que impliquen dades de categoria especial (RGPD art. 9). Si s'afegeix alguna, es marca "Conté dades sensibles".
const SENSIBLE_CATEGORY_IDS = new Set(['dades_salut', 'ideologia_sindical', 'biometria', 'genetics', 'salut', 'origen', 'dades_salut_mental', 'vida_sexual', 'religio', 'etnic'])
const SENSIBLE_KEYWORDS = ['salut', 'ideologia', 'sindical', 'biometria', 'genètic', 'genetic', 'origen', 'ètn', 'etnic', 'religió', 'religio', 'vida sexual']

/** True si alguna categoria implica dades de categoria especial (RGPD art. 9). */
function hasSensitiveCategory(categoriesList) {
  if (!Array.isArray(categoriesList) || !categoriesList.length) return false
  for (const c of categoriesList) {
    const id = String(c).trim().toLowerCase()
    if (SENSIBLE_CATEGORY_IDS.has(id)) return true
    for (const kw of SENSIBLE_KEYWORDS) {
      if (id.includes(kw)) return true
    }
  }
  return false
}

const BASE_LEGAL_LABELS = {
  general: 'General (tots els tractaments)',
  consentiment: 'Consentiment',
  interes_legitim: 'Interès legítim',
}

/** Secció del checklist de controls RGPD/ISO, filtrada per bases legals dels tractaments. */
function ChecklistSection({ dades, update, checklistMeta, showAllChecklist, setShowAllChecklist, tractaments }) {
  const basesUsed = useMemo(() => {
    const set = new Set()
    ;(tractaments || []).forEach(t => {
      const bl = t.base_legal
      if (Array.isArray(bl)) bl.forEach(b => b && set.add(b.trim()))
      else if (bl && typeof bl === 'string') set.add(bl.trim())
    })
    return set
  }, [tractaments])

  const filteredMeta = useMemo(() => {
    if (!checklistMeta.length) return []
    if (showAllChecklist) return checklistMeta
    return checklistMeta.filter(c => c.base_legal === 'general' || basesUsed.has(c.base_legal))
  }, [checklistMeta, showAllChecklist, basesUsed])

  const raw = dades.checklist_controls || {}
  const generalMap = getGeneralChecklistMap(raw)

  const setCheck = (controlId, value) => {
    const nextGeneral = { ...generalMap, [controlId]: value }
    update('checklist_controls', { ...raw, General: nextGeneral })
  }

  if (!checklistMeta.length) return null

  const byBase = filteredMeta.reduce((acc, c) => {
    const k = c.base_legal || 'general'
    if (!acc[k]) acc[k] = []
    acc[k].push(c)
    return acc
  }, {})

  return (
    <div className="card space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium text-slate-900">Checklist de controls (segons bases legals)</h3>
        <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-600">
          <input
            type="checkbox"
            checked={showAllChecklist}
            onChange={e => setShowAllChecklist(e.target.checked)}
            className="rounded border-slate-300 text-primary-600"
          />
          Mostrar tots els controls
        </label>
      </div>
      <p className="text-sm text-slate-600">
        Es mostren els controls rellevants per a les bases legals dels vostres tractaments. Marqueu si es compleixen o no.
      </p>
      <div className="space-y-4 max-h-[320px] overflow-y-auto">
        {Object.keys(byBase)
          .sort((a, b) => (a === 'general' ? -1 : b === 'general' ? 1 : (a || '').localeCompare(b || '')))
          .map(base => (
          <div key={base}>
            <h4 className="text-sm font-medium text-slate-700 mb-2">{BASE_LEGAL_LABELS[base] || BASES_LEGALS?.find(x => x.value === base)?.label || base}</h4>
            <ul className="space-y-2">
              {(byBase[base] || []).map(c => (
                <li key={c.id}>
                  <label className="flex items-start gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={generalMap[c.id] === true}
                      onChange={e => setCheck(c.id, e.target.checked)}
                      className="rounded border-slate-300 text-primary-600 mt-0.5"
                    />
                    <span className="text-sm text-slate-700">{c.nom}</span>
                  </label>
                  {generalMap[c.id] === false && (
                    <span className="text-xs text-amber-600 ml-6">No compleix</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}

/** Converteix string separat per comes/punt-i-coma en array. */
function parseList(str) {
  if (!str || typeof str !== 'string') return []
  return str.split(/[,;]/).map(s => s.trim()).filter(Boolean)
}

/** Converteix array en string separat per comes. */
function formatList(arr) {
  return Array.isArray(arr) ? arr.join(', ') : ''
}

/** Component principal: formulari de dades, checklist i botó d'executar auditoria. */
export default function Dades() {
  const { dades, setDades, setInforme } = useDades()
  const navigate = useNavigate()
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingIndex, setEditingIndex] = useState(null)
  const [form, setForm] = useState(defaultTractament)
  const [checklistMeta, setChecklistMeta] = useState([])
  const [showAllChecklist, setShowAllChecklist] = useState(false)
  const [mesuresSeguretat, setMesuresSeguretat] = useState(DEFAULT_MESURES_SEGURETAT)
  const [terminiOpcions, setTerminiOpcions] = useState(DEFAULT_TERMINI_OPCIONS)
  const [categoriesDades, setCategoriesDades] = useState(DEFAULT_CATEGORIES_DADES)

  useEffect(() => {
    getChecklistMetadata().then(setChecklistMeta).catch(() => setChecklistMeta([]))
  }, [])
  useEffect(() => {
    getMesuresSeguretat().then(data => Array.isArray(data) && data.length > 0 && setMesuresSeguretat(data)).catch(() => {})
  }, [])
  useEffect(() => {
    getTerminiOpcions().then(data => {
      if (data && ((data.predefinits && data.predefinits.length > 0) || (data.unitats && data.unitats.length > 0))) setTerminiOpcions(data)
    }).catch(() => {})
  }, [])
  useEffect(() => {
    getCategoriesDades().then(data => Array.isArray(data) && data.length > 0 && setCategoriesDades(data)).catch(() => {})
  }, [])

  // Checklist: per defecte «compleix» (true) per als controls visibles sense resposta prèvia
  useEffect(() => {
    if (!checklistMeta.length) return
    setDades(prev => {
      const nextChecklist = applyDefaultChecklistTrue(
        prev.checklist_controls,
        checklistMeta,
        prev.tractaments,
        showAllChecklist,
      )
      if (nextChecklist === prev.checklist_controls) return prev
      return { ...prev, checklist_controls: nextChecklist }
    })
  }, [checklistMeta, showAllChecklist, setDades, dades.tractaments])

  const update = (path, value) => {
    setDades(prev => {
      const next = { ...prev }
      if (path === 'nom_organitzacio') next.nom_organitzacio = value
      else if (path === 'data_auditoria') next.data_auditoria = value
      else if (path === 'politica') next.politica_privacitat = { ...(prev.politica_privacitat || {}), ...value }
      else if (path === 'acces') next.configuracio_acces = { ...(prev.configuracio_acces || {}), ...value }
      else if (path === 'checklist_controls') next.checklist_controls = value
      else if (path === 'altres_notes') next.altres_notes = value
      else next[path] = value
      return next
    })
  }

  const nextId = () => {
    const list = dades.tractaments || []
    const nums = list.map(t => { const m = (t.id || '').match(/T?(\d+)/); return m ? parseInt(m[1], 10) : 0 })
    const max = nums.length ? Math.max(...nums) : 0
    return `T${String(max + 1).padStart(3, '0')}`
  }

  const openAdd = () => {
    setEditingIndex(null)
    setForm({ ...defaultTractament(), id: nextId() })
    setShowForm(true)
  }

  const openEdit = (t, index) => {
    setEditingIndex(index)
    const bl = t.base_legal
    const validCatIds = new Set((categoriesDades || []).map(c => c.id))
    const validMsIds = new Set((mesuresSeguretat || []).map(m => m.id))
    const cats = (t.categories_dades || []).filter(id => validCatIds.has(id))
    const ms = (t.mesures_seguretat || []).filter(id => validMsIds.has(id))
    const conteSensibles = !!t.conte_dades_sensibles || hasSensitiveCategory(cats)
    setForm({
      id: t.id || nextId(),
      nom: t.nom || '',
      finalitat: t.finalitat || '',
      base_legal: Array.isArray(bl) ? [...bl] : (bl ? [bl] : []),
      categories_dades: [...cats],
      destinataris: t.destinataris || [],
      transferencies_internacionals: !!t.transferencies_internacionals,
      termini_conservacio: t.termini_conservacio || '',
      mesures_seguretat: [...ms],
      dpo_assignat: !!t.dpo_assignat,
      tipus_dades: t.tipus_dades || '',
      conte_dades_sensibles: conteSensibles,
      notes: t.notes || '',
      termini_unitat: (() => {
        const s = t.termini_conservacio || ''
        const m = s.match(/^\d+\s*(dies|mesos|anys)$/i)
        return m ? m[1].toLowerCase() : 'anys'
      })(),
    })
    setShowForm(true)
  }

  const closeForm = () => {
    setShowForm(false)
    setEditingIndex(null)
    setForm(defaultTractament())
  }

  const saveTractament = () => {
    if (!form.nom?.trim()) {
      setError('El nom del tractament és obligatori.')
      return
    }
    const baseLegalList = Array.isArray(form.base_legal) ? form.base_legal.filter(Boolean).map(s => (s && typeof s === 'string' ? s.trim() : String(s)).trim()).filter(Boolean) : []
    const validCatIds = new Set((categoriesDades || []).map(c => c.id))
    const validMsIds = new Set((mesuresSeguretat || []).map(m => m.id))
    const rawCats = Array.isArray(form.categories_dades) ? form.categories_dades : parseList(form.categories_dades)
    const rawMs = Array.isArray(form.mesures_seguretat) ? form.mesures_seguretat : parseList(form.mesures_seguretat)
    const t = {
      id: form.id?.trim() || nextId(),
      nom: form.nom.trim(),
      finalitat: form.finalitat.trim(),
      base_legal: baseLegalList,
      categories_dades: rawCats.filter(id => validCatIds.has(id)),
      destinataris: Array.isArray(form.destinataris) ? form.destinataris : parseList(form.destinataris),
      transferencies_internacionals: !!form.transferencies_internacionals,
      termini_conservacio: form.termini_conservacio?.trim() || null,
      mesures_seguretat: rawMs.filter(id => validMsIds.has(id)),
      dpo_assignat: !!form.dpo_assignat,
      tipus_dades: form.tipus_dades?.trim() || null,
      conte_dades_sensibles: !!form.conte_dades_sensibles,
      notes: form.notes?.trim() || '',
    }
    setDades(prev => {
      const tractaments = [...(prev.tractaments || [])]
      if (editingIndex !== null) {
        tractaments[editingIndex] = t
      } else {
        tractaments.push(t)
      }
      return { ...prev, tractaments }
    })
    setError('')
    closeForm()
  }

  const removeTractament = (index) => {
    if (!window.confirm('Eliminar aquest tractament?')) return
    setDades(prev => {
      const tractaments = (prev.tractaments || []).filter((_, i) => i !== index)
      return { ...prev, tractaments }
    })
  }

  const buildPayload = () => {
    const tractaments = (dades.tractaments || []).map(t => ({
      id: t.id,
      nom: t.nom,
      finalitat: t.finalitat,
      base_legal: Array.isArray(t.base_legal) ? t.base_legal : (t.base_legal ? [t.base_legal] : []),
      categories_dades: Array.isArray(t.categories_dades) ? t.categories_dades : parseList(t.categories_dades),
      destinataris: Array.isArray(t.destinataris) ? t.destinataris : parseList(t.destinataris),
      transferencies_internacionals: !!t.transferencies_internacionals,
      termini_conservacio: t.termini_conservacio || null,
      mesures_seguretat: Array.isArray(t.mesures_seguretat) ? t.mesures_seguretat : parseList(t.mesures_seguretat),
      dpo_assignat: !!t.dpo_assignat,
      tipus_dades: t.tipus_dades || null,
      conte_dades_sensibles: !!t.conte_dades_sensibles,
      notes: t.notes || '',
    }))
    return {
      nom_organitzacio: dades.nom_organitzacio || '',
      data_auditoria: dades.data_auditoria || '',
      tractaments,
      politica_privacitat: dades.politica_privacitat && typeof dades.politica_privacitat === 'object' ? dades.politica_privacitat : {},
      configuracio_acces: dades.configuracio_acces && typeof dades.configuracio_acces === 'object' ? dades.configuracio_acces : {},
      checklist_controls: dades.checklist_controls && typeof dades.checklist_controls === 'object' ? dades.checklist_controls : {},
      altres_notes: dades.altres_notes || '',
    }
  }

  const handleExecutar = async () => {
    setError('')
    setRunning(true)
    try {
      const payload = buildPayload()
      const res = await executarAuditoria(payload)
      setInforme({ informe_id: res.informe_id, informe: res.informe })
      navigate('/informe')
    } catch (e) {
      setError(e.message || 'Error executant l\'auditoria')
    } finally {
      setRunning(false)
    }
  }

  const pp = dades.politica_privacitat || {}
  const ca = dades.configuracio_acces || {}
  const tractaments = Array.isArray(dades.tractaments) ? dades.tractaments : []

  return (
    <div className="space-y-8">
      <h2 className="text-xl font-semibold text-slate-900">Dades d'auditoria</h2>

      {error && (
        <div className="card border-l-4 border-red-500 bg-red-50 text-red-800 text-sm p-4">
          {error}
        </div>
      )}

      <div className="card space-y-4">
        <h3 className="font-medium text-slate-900">Organització</h3>
        <div>
          <label className="label">Nom de l'organització</label>
          <input
            type="text"
            className="input"
            value={dades.nom_organitzacio}
            onChange={e => update('nom_organitzacio', e.target.value)}
            placeholder="Ex: La meva empresa S.L."
          />
        </div>
        <div>
          <label className="label">Data de l'auditoria</label>
          <input
            type="date"
            className="input max-w-xs"
            value={dades.data_auditoria}
            onChange={e => update('data_auditoria', e.target.value)}
          />
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between gap-4 mb-3">
          <h3 className="font-medium text-slate-900">Tractaments ({tractaments.length})</h3>
          <button type="button" onClick={openAdd} className="btn btn-primary text-sm">
            + Afegir tractament
          </button>
        </div>
        {tractaments.length === 0 && !showForm ? (
          <p className="text-slate-500 text-sm">No hi ha tractaments. Afegiu-ne des del formulari o importeu JSON, ROPA o una plantilla des d'Inici.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {tractaments.map((t, i) => (
              <li key={t.id || i} className="py-3 first:pt-0 flex items-start justify-between gap-2">
                <button type="button" onClick={() => openEdit(t, i)} className="text-left flex-1 min-w-0">
                  <div className="font-medium text-slate-800">{t.nom}</div>
                  <div className="text-sm text-slate-500">
                    {t.tipus_dades && <span className="badge bg-slate-100 text-slate-600 mr-2">{tipusLabel(t.tipus_dades)}</span>}
                    {t.conte_dades_sensibles && <span className="badge bg-amber-100 text-amber-800 mr-2">Dades sensibles</span>}
                    {Array.isArray(t.base_legal) && t.base_legal.length > 0 && (
                      <span className="text-slate-500 mr-2">Bases: {t.base_legal.join(', ')}</span>
                    )}
                    {!Array.isArray(t.base_legal) && t.base_legal && <span className="text-slate-500 mr-2">{t.base_legal}</span>}
                    {(t.mesures_seguretat?.length > 0) && <span className="text-slate-500 mr-2">Mesures: {t.mesures_seguretat.slice(0, 3).join(', ')}{t.mesures_seguretat.length > 3 ? '…' : ''}</span>}
                    {t.finalitat?.slice(0, 80)}{t.finalitat?.length > 80 ? '…' : ''}
                  </div>
                </button>
                <button type="button" onClick={() => removeTractament(i)} className="text-slate-400 hover:text-red-600 text-sm px-2" title="Eliminar">
                  Eliminar
                </button>
              </li>
            ))}
          </ul>
        )}

        {showForm && (
          <div className="mt-6 p-4 bg-slate-50 rounded-lg border border-slate-200">
            <h4 className="font-medium text-slate-900 mb-3">{editingIndex !== null ? 'Editar tractament' : 'Nou tractament'}</h4>
            <TractamentForm form={form} setForm={setForm} mesuresSeguretat={mesuresSeguretat} terminiOpcions={terminiOpcions} categoriesDades={categoriesDades} />
            <div className="flex gap-2 mt-4">
              <button type="button" onClick={saveTractament} className="btn btn-primary">
                {editingIndex !== null ? 'Desar canvis' : 'Afegir'}
              </button>
              <button type="button" onClick={closeForm} className="btn btn-secondary">
                Cancel·lar
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="card space-y-4">
        <h3 className="font-medium text-slate-900">Política de privacitat</h3>
        <p className="text-sm text-slate-600">Aquests punts es comproven a l'informe (obligació d'informació arts. 13/14 RGPD).</p>
        <div className="flex flex-wrap gap-4">
          {['existeix', 'accessible', 'contingut_deure_informacio', 'actualitzada'].map(key => (
            <label key={key} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!pp[key]}
                onChange={e => update('politica', { [key]: e.target.checked })}
                className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-slate-700">{labelsPolitica[key] || key}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="card space-y-4">
        <h3 className="font-medium text-slate-900">Configuració d'accés</h3>
        <p className="text-sm text-slate-600">Mesures organitzatives que poden fer complir alguns controls de l'auditoria.</p>
        <div className="flex flex-wrap gap-4">
          {['acces_restringit_per_rol', 'registre_accions', 'formacio_obligatoria', 'confidencialitat_contractual'].map(key => (
            <label key={key} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!ca[key]}
                onChange={e => update('acces', { [key]: e.target.checked })}
                className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-slate-700">{labelsAcces[key] || key}</span>
            </label>
          ))}
        </div>
      </div>

      <ChecklistSection
        dades={dades}
        update={update}
        checklistMeta={checklistMeta}
        showAllChecklist={showAllChecklist}
        setShowAllChecklist={setShowAllChecklist}
        tractaments={tractaments}
      />

      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={handleExecutar}
          disabled={running || !tractaments.length}
          className="btn btn-primary"
        >
          {running ? 'Executant…' : 'Executar auditoria'}
        </button>
        <p className="text-sm text-slate-500">
          Es generarà l'informe per tipus de dades. Cal almenys un tractament.
        </p>
      </div>
    </div>
  )
}

/** Formulari d'edició d'un tractament (bases legals, categories, mesures, termini, etc.). */
function TractamentForm({ form, setForm, mesuresSeguretat = [], terminiOpcions = { predefinits: [], unitats: [] }, categoriesDades = [] }) {
  const update = (field, value) => setForm(prev => ({ ...prev, [field]: value }))
  const msList = Array.isArray(form.mesures_seguretat) ? form.mesures_seguretat : []
  const predefinedMsIds = new Set((mesuresSeguretat || []).map(m => m.id))
  const selectedPredefined = msList.filter(id => predefinedMsIds.has(id))

  const addMesura = (id) => {
    if (id && !selectedPredefined.includes(id)) update('mesures_seguretat', [...selectedPredefined, id])
  }
  const removeMesura = (id) => {
    update('mesures_seguretat', selectedPredefined.filter(x => x !== id))
  }

  const predefinits = terminiOpcions.predefinits || []
  const unitats = terminiOpcions.unitats || []
  const termStr = form.termini_conservacio || ''
  const termPredef = predefinits.find(p => p.id === termStr)
  const termNumericMatch = termStr.match(/^(\d+)\s*(dies|mesos|anys)$/i)
  const termMode = termPredef ? 'predefinit' : (termNumericMatch ? 'numeric' : (termStr ? 'altres' : ''))

  const setTermini = (mode, predefId, valor, unitat) => {
    if (mode === 'predefinit') update('termini_conservacio', predefId || '')
    else if (mode === 'numeric' && valor != null && unitat) update('termini_conservacio', `${valor} ${unitat}`)
    else if (mode === 'altres') update('termini_conservacio', valor || '')
  }

  const catList = Array.isArray(form.categories_dades) ? form.categories_dades : []
  const catIds = new Set((categoriesDades || []).map(c => c.id))
  const selectedCats = catList.filter(id => catIds.has(id))

  const addCategoria = (id) => {
    if (catList.includes(id)) return
    const newList = [...catList, id]
    setForm(prev => ({
      ...prev,
      categories_dades: newList,
      conte_dades_sensibles: hasSensitiveCategory(newList) ? true : prev.conte_dades_sensibles,
    }))
  }
  const removeCategoria = (id) => {
    const newList = catList.filter(x => x !== id)
    setForm(prev => ({
      ...prev,
      categories_dades: newList,
      conte_dades_sensibles: hasSensitiveCategory(newList) ? true : false,
    }))
  }

  return (
    <div className="grid sm:grid-cols-2 gap-4">
      <div className="sm:col-span-2 flex flex-wrap gap-4 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="label">Nom del tractament *</label>
          <input type="text" className="input" value={form.nom} onChange={e => update('nom', e.target.value)} placeholder="Ex: Gestió de nòmines" required />
        </div>
        <div className="w-28">
          <label className="label text-slate-500">ID</label>
          <input type="text" className="input" value={form.id} onChange={e => update('id', e.target.value)} placeholder="T001" title="Opcional; es genera automàticament si es deixa buit" />
        </div>
      </div>
      <div className="sm:col-span-2">
        <label className="label">Finalitat</label>
        <textarea className="input min-h-[80px]" value={form.finalitat} onChange={e => update('finalitat', e.target.value)} placeholder="Descripció de la finalitat del tractament (art. 5.1.b RGPD)" rows={2} />
      </div>
      <div className="sm:col-span-2">
        <label className="label">Bases legals (podeu triar més d'una)</label>
        <div className="flex flex-wrap gap-3 pt-1">
          {BASES_LEGALS.map(o => {
            const arr = Array.isArray(form.base_legal) ? form.base_legal : []
            const checked = arr.includes(o.value)
            return (
              <label key={o.value} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => {
                    const next = checked ? arr.filter(v => v !== o.value) : [...arr, o.value]
                    update('base_legal', next)
                  }}
                  className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-slate-700">{o.label}</span>
              </label>
            )
          })}
        </div>
      </div>
      <div>
        <label className="label">Tipus de dades</label>
        <select className="input" value={form.tipus_dades} onChange={e => update('tipus_dades', e.target.value)}>
          <option value="">— Triar —</option>
          {TIPUS_DADES.map(t => <option key={t} value={t}>{tipusLabel(t)}</option>)}
        </select>
        <p className="text-xs text-slate-500 mt-0.5">Segmenta l'informe en pestanyes.</p>
      </div>
      <div className="sm:col-span-2">
        <label className="label">Categories de dades</label>
        <p className="text-xs text-slate-500 mb-2">Afegiu de la llista; influeixen en l'auditoria. Si n'hi ha de sensibles (salut, ideologia, etc.), es marcarà sol «Conté dades sensibles».</p>
        <div className="flex flex-wrap gap-2 mb-2">
          {selectedCats.map(id => {
            const c = (categoriesDades || []).find(x => x.id === id)
            return (
              <span key={id} className="inline-flex items-center gap-1 px-2 py-1 rounded bg-primary-100 text-primary-800 text-sm">
                {c?.nom || id}
                <button type="button" onClick={() => removeCategoria(id)} className="text-primary-600 hover:text-primary-800" aria-label="Treure">×</button>
              </span>
            )
          })}
        </div>
        <select className="input max-w-xs" value="" onChange={e => { const v = e.target.value; if (v) addCategoria(v); e.target.value = '' }}>
          <option value="">— Afegir de la llista —</option>
          {(categoriesDades || []).filter(c => !catList.includes(c.id)).map(c => (
            <option key={c.id} value={c.id}>{c.nom}</option>
          ))}
        </select>
      </div>
      <div className="sm:col-span-2">
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={!!form.conte_dades_sensibles} onChange={e => update('conte_dades_sensibles', e.target.checked)} className="rounded border-slate-300 text-primary-600" />
          <span className="text-sm font-medium text-slate-700">Conté dades sensibles (RGPD art. 9)</span>
        </label>
        <p className="text-xs text-slate-500 mt-0.5">Es marca sol si afegiu categories sensibles (salut, orígens, ideologia…). Podeu desmarcar-ho manualment si no apliquen.</p>
      </div>
      <div>
        <label className="label">Destinataris</label>
        <input type="text" className="input" value={formatList(form.destinataris)} onChange={e => update('destinataris', e.target.value)} placeholder="Ex: RRHH, Gestoria externa" />
      </div>
      <div className="sm:col-span-2">
        <label className="label">Termini de conservació</label>
        <p className="text-xs text-slate-500 mb-2">Predefinit o valor numèric amb unitat (anys, mesos, dies).</p>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <span className="text-sm text-slate-600 mr-2">Predefinit:</span>
            <select className="input" value={termMode === 'predefinit' ? termStr : ''} onChange={e => setTermini('predefinit', e.target.value, null, null)}>
              <option value="">— Triar —</option>
              {predefinits.map(p => (
                <option key={p.id} value={p.id}>{p.nom}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-600">O valor:</span>
            <input type="number" min="1" className="input w-20" placeholder="N" value={termNumericMatch ? termNumericMatch[1] : ''} onChange={e => setTermini('numeric', null, e.target.value || null, form.termini_unitat || 'anys')} />
            <select className="input w-24" value={termNumericMatch ? termNumericMatch[2] : (form.termini_unitat || 'anys')} onChange={e => { update('termini_unitat', e.target.value); const n = termNumericMatch ? termNumericMatch[1] : ''; if (n) setTermini('numeric', null, n, e.target.value) }}>
              {unitats.map(u => <option key={u.id} value={u.id}>{u.nom}</option>)}
            </select>
          </div>
          {termStr && !termPredef && !termNumericMatch && (
            <input type="text" className="input flex-1 min-w-[120px]" value={termStr} onChange={e => setTermini('altres', null, e.target.value, null)} placeholder="Ex: fins revocació" />
          )}
        </div>
      </div>
      <div className="sm:col-span-2">
        <label className="label">Mesures de seguretat</label>
        <p className="text-xs text-slate-500 mb-2">Afegiu de la llista; segons les mesures aplicades, alguns controls es poden donar per complerts.</p>
        <div className="flex flex-wrap gap-2 mb-2">
          {selectedPredefined.map(id => {
            const m = (mesuresSeguretat || []).find(x => x.id === id)
            return (
              <span key={id} className="inline-flex items-center gap-1 px-2 py-1 rounded bg-emerald-100 text-emerald-800 text-sm">
                {m?.nom || id}
                <button type="button" onClick={() => removeMesura(id)} className="text-emerald-600 hover:text-emerald-800" aria-label="Treure">×</button>
              </span>
            )
          })}
        </div>
        <select className="input max-w-md" value="" onChange={e => { const v = e.target.value; if (v) addMesura(v); e.target.value = '' }}>
          <option value="">— Afegir mesura de la llista —</option>
          {(mesuresSeguretat || []).filter(m => !selectedPredefined.includes(m.id)).map(m => (
            <option key={m.id} value={m.id}>{m.nom}</option>
          ))}
        </select>
      </div>
      <div className="sm:col-span-2 flex flex-wrap gap-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={form.transferencies_internacionals} onChange={e => update('transferencies_internacionals', e.target.checked)} className="rounded border-slate-300 text-primary-600" />
          <span className="text-sm text-slate-700">Transferències internacionals</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer" title="En organitzacions amb DPO, sol ser el mateix per a tots els tractaments.">
          <input type="checkbox" checked={form.dpo_assignat} onChange={e => update('dpo_assignat', e.target.checked)} className="rounded border-slate-300 text-primary-600" />
          <span className="text-sm text-slate-700">DPO assignat a aquest tractament</span>
        </label>
      </div>
      <p className="sm:col-span-2 text-xs text-slate-500 -mt-2">Marqueu si el tractament té delegat de protecció de dades assignat (en organitzacions amb DPO, sol ser el mateix per a tots).</p>
      <div className="sm:col-span-2">
        <label className="label">Notes</label>
        <textarea className="input min-h-[60px]" value={form.notes} onChange={e => update('notes', e.target.value)} placeholder="Notes opcionals per a aquest tractament" rows={2} />
      </div>
    </div>
  )
}

const labelsPolitica = {
  existeix: "Existeix política de privacitat",
  accessible: "És accessible",
  contingut_deure_informacio: "Inclou el deure d'informació (arts. 13/14 RGPD)",
  actualitzada: "Actualitzada",
}

const labelsAcces = {
  acces_restringit_per_rol: "Accés restringit per rol",
  registre_accions: "Registre d'accions",
  formacio_obligatoria: "Formació obligatòria",
  confidencialitat_contractual: "Confidencialitat contractual",
}
