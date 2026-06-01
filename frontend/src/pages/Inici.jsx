import { useNavigate } from 'react-router-dom'
import { useRef, useState, useEffect } from 'react'
import { useDades } from '../context'
import { getPlantilla, importRopa, validarDades } from '../api'

/**
 * Pàgina d'inici: importació de JSON, ROPA, selecció de plantilles o començar des de zero.
 */
export default function Inici() {
  const navigate = useNavigate()
  const { loadDades } = useDades()
  const fileJsonRef = useRef(null)
  const fileRopaRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handlePlantilla = async (id) => {
    setError('')
    setLoading(true)
    try {
      const d = await getPlantilla(id)
      loadDades(d)
      navigate('/dades')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleFileJson = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    setError('')
    const reader = new FileReader()
    reader.onload = async () => {
      try {
        const d = JSON.parse(reader.result)
        setLoading(true)
        await validarDades(d)
        loadDades(d)
        navigate('/dades')
      } catch (err) {
        setError(err.message || 'JSON invàlid')
      } finally {
        setLoading(false)
      }
    }
    reader.readAsText(f, 'UTF-8')
    e.target.value = ''
  }

  const handleFileRopa = async (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    setError('')
    setLoading(true)
    const reader = new FileReader()
    reader.onload = async () => {
      try {
        const json = JSON.parse(reader.result)
        const d = await importRopa(json)
        loadDades(d)
        navigate('/dades')
      } catch (err) {
        setError(err.message || 'Error important ROPA')
      } finally {
        setLoading(false)
      }
    }
    reader.readAsText(f, 'UTF-8')
    e.target.value = ''
  }

  return (
    <div className="space-y-8">
      <div className="text-center max-w-2xl mx-auto">
        <h2 className="text-2xl font-semibold text-slate-900 mb-2">
          Auditeu la privacitat de les vostres dades
        </h2>
        <p className="text-slate-600">
          Carregueu les dades del registre d'activitats (ROPA), trieu una plantilla o importeu un JSON.
          Després executeu l'auditoria i consulteu l'informe per tipus de dades.
        </p>
      </div>

      {error && (
        <div className="card border-l-4 border-red-500 bg-red-50 text-red-800 text-sm p-4">
          {error}
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-4">
        <label className="card cursor-pointer hover:shadow-card-hover transition block">
          <input
            type="file"
            accept=".json,application/json"
            className="hidden"
            ref={fileJsonRef}
            onChange={handleFileJson}
          />
          <div className="font-medium text-slate-900 mb-1">Importar JSON</div>
          <p className="text-sm text-slate-500">Fitxer en format intern (p. ex. cas_mixt_3_tractaments.json)</p>
          <button
            type="button"
            onClick={() => fileJsonRef.current?.click()}
            className="mt-3 btn btn-secondary text-sm"
          >
            Seleccionar fitxer
          </button>
        </label>

        <label className="card cursor-pointer hover:shadow-card-hover transition block">
          <input
            type="file"
            accept=".json,application/json"
            className="hidden"
            ref={fileRopaRef}
            onChange={handleFileRopa}
            disabled={loading}
          />
          <div className="font-medium text-slate-900 mb-1">Importar ROPA</div>
          <p className="text-sm text-slate-500">Registre d'activitats (format ROPA / UROPA compatible)</p>
          <button
            type="button"
            onClick={() => fileRopaRef.current?.click()}
            className="mt-3 btn btn-secondary text-sm"
            disabled={loading}
          >
            {loading ? 'Important…' : 'Seleccionar fitxer ROPA'}
          </button>
        </label>
      </div>

      <PlantillesSection onSelect={handlePlantilla} loading={loading} />

      <div className="card border border-slate-200 bg-slate-50/50">
        <button
          type="button"
          onClick={() => { loadDades({ tractaments: [] }); navigate('/dades') }}
          className="btn btn-secondary"
        >
          Començar des de zero
        </button>
        <p className="text-sm text-slate-500 mt-2">Obriu el formulari sense dades i ompliu-ho manualment.</p>
      </div>
    </div>
  )
}

/** Secció que llista i permet seleccionar plantilles des de l'API. */
function PlantillesSection({ onSelect, loading }) {
  const [list, setList] = useState([])
  useEffect(() => {
    fetch('/api/plantilles')
      .then(r => r.json())
      .then(setList)
      .catch(() => setList([]))
  }, [])

  if (list.length === 0) return null

  return (
    <div>
      <h3 className="text-lg font-medium text-slate-900 mb-3">Començar des de plantilla</h3>
      <div className="grid sm:grid-cols-2 gap-3">
        {list.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => onSelect(p.id)}
            disabled={loading}
            className="card text-left hover:shadow-card-hover transition disabled:opacity-60"
          >
            <div className="font-medium text-slate-900">{p.nom}</div>
            {p.descripcio && <p className="text-sm text-slate-500 mt-1">{p.descripcio}</p>}
          </button>
        ))}
      </div>
    </div>
  )
}
