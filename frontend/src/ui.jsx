// Petits composants partagés : badges d'état, icônes d'agents, formatage.

export const ETAT_STYLE = {
  recu: { classe: 'bg-slate-200 text-slate-700', libelle: 'reçu' },
  en_cours: { classe: 'bg-blue-100 text-blue-800', libelle: 'en cours' },
  attente_validation: { classe: 'bg-amber-100 text-amber-800', libelle: 'attente validation' },
  regle: { classe: 'bg-emerald-100 text-emerald-800', libelle: 'réglé' },
  refuse: { classe: 'bg-red-100 text-red-800', libelle: 'refusé' },
  cloture: { classe: 'bg-slate-300 text-slate-600', libelle: 'clôturé' },
}

export function BadgeEtat({ etat }) {
  const s = ETAT_STYLE[etat] ?? ETAT_STYLE.recu
  return (
    <span className={`whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${s.classe}`}>
      {s.libelle}
    </span>
  )
}

export const AGENT_ICONE = {
  fnol: '📝', extraction: '📄', vision: '📷',
  garanties: '📐', indemnite: '🧮', hitl: '🛡️', courrier: '✉️',
}

export function BadgeMode({ mode }) {
  if (!mode) return null
  const styles = {
    llm: 'bg-violet-100 text-violet-700',
    simulation: 'bg-slate-200 text-slate-600',
    mixte: 'bg-violet-50 text-violet-600',
    deterministe: 'bg-teal-100 text-teal-700',
  }
  const libelles = { llm: 'LLM', simulation: 'simulé', mixte: 'LLM partiel', deterministe: 'déterministe' }
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${styles[mode] ?? ''}`}>
      {libelles[mode] ?? mode}
    </span>
  )
}

export const dt = (montant) =>
  montant === null || montant === undefined
    ? '—'
    : `${Number(montant).toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })} DT`

export const heure = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
  return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
