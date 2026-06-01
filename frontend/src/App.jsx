import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { DadesProvider } from './context'
import Inici from './pages/Inici'
import Dades from './pages/Dades'
import Informe from './pages/Informe'

const nav = [
  { path: '/', label: 'Inici' },
  { path: '/dades', label: 'Dades i auditoria' },
  { path: '/informe', label: 'Informe' },
]

/**
 * Component arrel: layout, navegació i rutes principals.
 * Envoltat de DadesProvider per a l'estat global de l'auditoria.
 */
export default function App() {
  const loc = useLocation()
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-slate-900 font-sans">
                Eina d'auditoria de privacitat
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">RGPD · LOPD-GDD · ISO 27701</p>
            </div>
            <nav className="flex gap-1">
              {nav.map(({ path, label }) => (
                <Link
                  key={path}
                  to={path}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition ${
                    loc.pathname === path
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`}
                >
                  {label}
                </Link>
              ))}
            </nav>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
        <DadesProvider>
          <Routes>
            <Route path="/" element={<Inici />} />
            <Route path="/dades" element={<Dades />} />
            <Route path="/informe" element={<Informe />} />
          </Routes>
        </DadesProvider>
      </main>
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-sm text-slate-500">
        Les recomanacions tenen caràcter orientatiu i no constitueixen assessorament jurídic. · TFM Màster Ciberseguretat
      </footer>
    </div>
  )
}
