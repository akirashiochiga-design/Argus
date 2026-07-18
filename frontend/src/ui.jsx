// Composants et tokens partagés, alignés sur le brand book Argus.
// Encre / crème / terracotta ; états en teintes terreuses désaturées.

// Le signe : « huit yeux, un seul regard ». Une lentille — pupille terracotta.
// Trait unique, hérite de la couleur du texte (currentColor).
export function Logo({ size = 28, className = '' }) {
  const ticks = Array.from({ length: 8 }, (_, i) => {
    const a = (i * Math.PI) / 4
    const cx = 16, cy = 16
    return (
      <line key={i}
        x1={cx + 11 * Math.cos(a)} y1={cy + 11 * Math.sin(a)}
        x2={cx + 8.4 * Math.cos(a)} y2={cy + 8.4 * Math.sin(a)} />
    )
  })
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" className={className} aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
        <circle cx="16" cy="16" r="12" />
        <circle cx="16" cy="16" r="6" />
        {ticks}
      </g>
      <circle cx="16" cy="16" r="3.1" fill="#D97757" />
    </svg>
  )
}

// Le wordmark : « argus. » bas de casse, point terracotta.
export function Wordmark({ className = '' }) {
  return (
    <span className={`font-semibold tracking-tight ${className}`}>
      argus<span className="text-terracotta">.</span>
    </span>
  )
}

export const ETAT_STYLE = {
  recu: { chip: 'bg-surface-deep text-encre/70', barre: 'bg-[#B8AF9E]', libelle: 'reçu' },
  en_cours: { chip: 'bg-[#E4DCCB] text-encre', barre: 'bg-[#8A8072]', libelle: 'en cours' },
  attente_validation: { chip: 'bg-warn-tint text-warn', barre: 'bg-warn', libelle: 'attente validation' },
  regle: { chip: 'bg-ok-tint text-ok', barre: 'bg-ok', libelle: 'réglé' },
  refuse: { chip: 'bg-bad-tint text-bad', barre: 'bg-bad', libelle: 'refusé' },
  cloture: { chip: 'bg-encre text-creme', barre: 'bg-encre', libelle: 'clôturé' },
}

export function BadgeEtat({ etat }) {
  const s = ETAT_STYLE[etat] ?? ETAT_STYLE.recu
  return (
    <span className={`whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${s.chip}`}>
      {s.libelle}
    </span>
  )
}

export const AGENT_ICONE = {
  fnol: '📝', extraction: '📄', vision: '📷',
  garanties: '📐', indemnite: '🧮', hitl: '🛡️', courrier: '✉️', assistant: '✦',
}

export function BadgeMode({ mode }) {
  if (!mode) return null
  const styles = {
    llm: 'bg-terracotta-tint text-terracotta-deep',
    mixte: 'bg-terracotta-tint text-terracotta-deep',
    simulation: 'bg-surface-deep text-encre/50',
    deterministe: 'bg-ok-tint text-ok',
  }
  const libelles = { llm: 'IA', simulation: 'simulé', mixte: 'IA partiel', deterministe: 'déterministe' }
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
