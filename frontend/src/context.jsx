/**
 * Context React per a l'estat global de l'auditoria.
 * Gestiona dades d'entrada, informe generat i funcions de càrrega/neteja.
 */

import { createContext, useContext, useState, useCallback } from 'react'

const DadesContext = createContext(null)

/** @returns {object} Estat inicial buit de dades d'auditoria. */
const defaultDades = () => ({
  nom_organitzacio: '',
  data_auditoria: new Date().toISOString().slice(0, 10),
  tractaments: [],
  politica_privacitat: null,
  configuracio_acces: null,
  checklist_controls: {},
  altres_notes: '',
})

/** Provider de l'estat global: dades, informe, loadDades, clearDades. */
export function DadesProvider({ children }) {
  const [dades, setDades] = useState(defaultDades)
  const [informe, setInforme] = useState(null) // { informe_id, informe }

  const loadDades = useCallback((d) => {
    const tractaments = Array.isArray(d?.tractaments) ? d.tractaments : []
    setDades({
      ...defaultDades(),
      ...d,
      tractaments,
      politica_privacitat: d.politica_privacitat || null,
      configuracio_acces: d.configuracio_acces || null,
      checklist_controls: d.checklist_controls || {},
    })
  }, [])

  const clearDades = useCallback(() => {
    setDades(defaultDades())
    setInforme(null)
  }, [])

  return (
    <DadesContext.Provider value={{ dades, setDades, loadDades, clearDades, informe, setInforme }}>
      {children}
    </DadesContext.Provider>
  )
}

/** Hook per accedir al context de dades. Cal estar dins de DadesProvider. */
export function useDades() {
  const ctx = useContext(DadesContext)
  if (!ctx) throw new Error('useDades must be used within DadesProvider')
  return ctx
}
