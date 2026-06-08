/**
 * Utilitats per al checklist de controls RGPD/ISO.
 */

/** Extreu el mapa General del format pla o per tipus. */
export function getGeneralChecklistMap(raw) {
  const src = raw && typeof raw === 'object' ? raw : {}
  if (src.General && typeof src.General === 'object') {
    return { ...src.General }
  }
  if (!Object.prototype.hasOwnProperty.call(src, 'General')) {
    return { ...src }
  }
  return {}
}

/** Bases legals declarades als tractaments. */
export function basesLegalsFromTractaments(tractaments) {
  const set = new Set()
  ;(tractaments || []).forEach(t => {
    const bl = t?.base_legal
    if (Array.isArray(bl)) bl.forEach(b => b && set.add(String(b).trim()))
    else if (bl && typeof bl === 'string') set.add(bl.trim())
  })
  return set
}

/** IDs de controls rellevants segons metadades i bases legals. */
export function relevantChecklistIds(checklistMeta, tractaments, showAllChecklist) {
  if (!checklistMeta?.length) return []
  const basesUsed = basesLegalsFromTractaments(tractaments)
  const filtered = showAllChecklist
    ? checklistMeta
    : checklistMeta.filter(c => c.base_legal === 'general' || basesUsed.has(c.base_legal))
  return filtered.map(c => c.id)
}

/**
 * Omple amb true els controls visibles que encara no tenen resposta (undefined).
 * No sobreescriu false ni true ja definits.
 */
export function applyDefaultChecklistTrue(checklistControls, checklistMeta, tractaments, showAllChecklist) {
  const raw = checklistControls && typeof checklistControls === 'object' ? checklistControls : {}
  const generalMap = getGeneralChecklistMap(raw)
  const ids = relevantChecklistIds(checklistMeta, tractaments, showAllChecklist)
  let changed = false
  const nextGeneral = { ...generalMap }
  for (const id of ids) {
    if (nextGeneral[id] === undefined) {
      nextGeneral[id] = true
      changed = true
    }
  }
  if (!changed) return checklistControls
  return { ...raw, General: nextGeneral }
}
