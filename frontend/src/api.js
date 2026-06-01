/**
 * Client HTTP cap a l'API REST del backend Flask (/api).
 * Totes les funcions retornen JSON parsejat o llançen Error amb el missatge del servidor.
 */
const BASE = '/api'

/** @returns {Promise<Array<{id: string, nom: string, descripcio: string}>>} Llista de plantilles disponibles. */
export async function getPlantilles() {
  const r = await fetch(`${BASE}/plantilles`)
  if (!r.ok) throw new Error('Error carregant plantilles')
  return r.json()
}

/** @param {string} id @returns {Promise<object>} Dades d'auditoria de la plantilla. */
export async function getPlantilla(id) {
  const r = await fetch(`${BASE}/plantilles/${encodeURIComponent(id)}`)
  if (!r.ok) throw new Error('Plantilla no trobada')
  return r.json()
}

/** @param {object} json JSON tipus ROPA @returns {Promise<object>} Dades en format intern. */
export async function importRopa(json) {
  const r = await fetch(`${BASE}/import/ropa`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(json),
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(data.error || 'Error important ROPA')
  return data
}

/** @param {object} dades DadesEntradaAuditoria @returns {Promise<{informe_id: string, informe: object}>} */
export async function executarAuditoria(dades) {
  const r = await fetch(`${BASE}/auditoria/executar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dades),
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = data.error || r.statusText || 'Error executant auditoria'
    if (data.traceback) console.error('Traceback servidor:', data.traceback)
    throw new Error(msg)
  }
  return data
}

/** @param {string} informeId @param {'json'|'txt'|'html'} format @returns {string} URL d'exportació. */
export function exportUrl(informeId, format) {
  return `${BASE}/informe/${encodeURIComponent(informeId)}/export/${format}`
}

/** @returns {Promise<Array>} Metadades dels controls del checklist RGPD/ISO. */
export async function getChecklistMetadata() {
  const r = await fetch(`${BASE}/checklist-metadata`)
  if (!r.ok) throw new Error('Error carregant metadades del checklist')
  return r.json()
}

/** @returns {Promise<Array<{id: string, nom: string, descripcio: string}>>} Mesures de seguretat predefinides. */
export async function getMesuresSeguretat() {
  const r = await fetch(`${BASE}/mesures-seguretat`)
  if (!r.ok) throw new Error('Error carregant mesures de seguretat')
  return r.json()
}

/** @returns {Promise<{predefinits: Array, unitats: Array}>} Opcions de termini de conservació. */
export async function getTerminiOpcions() {
  const r = await fetch(`${BASE}/termini-opcions`)
  if (!r.ok) throw new Error('Error carregant opcions de termini')
  return r.json()
}

/** @returns {Promise<Array<{id: string, nom: string}>>} Categories de dades personals predefinides. */
export async function getCategoriesDades() {
  const r = await fetch(`${BASE}/categories-dades`)
  if (!r.ok) throw new Error('Error carregant categories de dades')
  return r.json()
}
