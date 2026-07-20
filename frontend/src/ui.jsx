import { useState } from 'react'
import { assetUrl } from './api'

// Composants et tokens partagés, alignés sur le brand book Norix.
// Encre / crème / terracotta ; états en teintes terreuses désaturées.

// Le signe officiel du brand book : « huit yeux, un seul regard ».
// Huit lentilles (pas des lignes) disposées en rosace autour d'une pupille
// terracotta centrale. Trait unique, hérite de la couleur du texte
// (currentColor) ; la pupille reste toujours terracotta.
const PETALE = 'M120 107 Q101 66 120 25 Q139 66 120 107 Z'
const ANGLES = [0, 45, 90, 135, 180, 225, 270, 315]

export function Logo({ size = 28, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 240 240" className={className} aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="8" strokeLinejoin="round">
        {ANGLES.map((deg) => (
          <path key={deg} d={PETALE} transform={`rotate(${deg} 120 120)`} />
        ))}
      </g>
      <circle cx="120" cy="120" r="13" fill="#D97757" />
    </svg>
  )
}

// Le wordmark : « norix. » bas de casse, point terracotta.
export function Wordmark({ className = '' }) {
  return (
    <span className={`font-semibold tracking-tight ${className}`}>
      norix<span className="text-terracotta">.</span>
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

export function BadgeMode() {
  return null
}

export const dt = (montant) =>
  montant === null || montant === undefined
    ? '—'
    : `${Number(montant).toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })} DT`

const libellePiece = (type = '') =>
  type.replaceAll('_', ' ').replace(/^\w/, (lettre) => lettre.toUpperCase())

function ApercuPiece({ piece, index, hauteur = 'h-32' }) {
  const [indisponible, setIndisponible] = useState(false)
  const estPhoto = piece.type === 'photo_degats'

  return (
    <div className="overflow-hidden rounded-lg border border-line bg-surface-deep">
      {!indisponible ? (
        <img
          src={assetUrl(piece.chemin)}
          alt={`${libellePiece(piece.type)} ${index + 1}`}
          className={`${hauteur} w-full object-cover`}
          loading="lazy"
          onError={() => setIndisponible(true)}
        />
      ) : (
        <div className={`${hauteur} flex items-center justify-center bg-line/35 text-3xl`} aria-hidden="true">
          {estPhoto ? '📷' : '📄'}
        </div>
      )}
      <div className="p-2 text-xs text-encre/60">
        <div className="font-semibold">{libellePiece(piece.type)}</div>
        {piece.montant != null && <div className="text-encre/40">{dt(piece.montant)}</div>}
      </div>
    </div>
  )
}

export function GaleriePieces({ pieces = [], photosSeulement = false, className = '', hauteur }) {
  const visibles = photosSeulement ? pieces.filter((piece) => piece.type === 'photo_degats') : pieces
  if (visibles.length === 0) return null

  return (
    <div className={`grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 ${className}`}>
      {visibles.map((piece, index) => (
        <ApercuPiece key={`${piece.chemin}-${index}`} piece={piece} index={index} hauteur={hauteur} />
      ))}
    </div>
  )
}

export const heure = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
  return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
