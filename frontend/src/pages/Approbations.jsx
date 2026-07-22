import { useEffect, useState } from 'react'
import { api } from '../api'
import { lireSession, libelleValidateur } from '../session'
import { GaleriePieces, dt } from '../ui'

export default function Approbations({ onNavigate }) {
  const [enAttente, setEnAttente] = useState([])
  const [decidees, setDecidees] = useState([])
  const [message, setMessage] = useState(null)
  const [surveillance, setSurveillance] = useState({ active: false, verifieLe: null })
  const validateur = libelleValidateur(lireSession())

  const charger = async () => {
    const [attente, faites] = await Promise.all([
      api.listerTaches('en_attente'),
      api.listerTaches('decidee'),
    ])
    setEnAttente(attente)
    setDecidees(faites)
  }

  const verifierPieces = async () => {
    let active = false
    try {
      await api.surveillerPieces()
      active = true
    } catch {
      // Le connecteur n'est peut-être pas encore activé dans Intégrations.
    }
    await charger()
    setSurveillance({ active, verifieLe: new Date() })
  }

  useEffect(() => {
    verifierPieces()
    const intervalle = window.setInterval(verifierPieces, 8000)
    return () => window.clearInterval(intervalle)
  }, [])

  const decider = async (tache, decision, montant, motif) => {
    setMessage(null)
    try {
      const r = await api.deciderTache(tache.id, {
        decision, validateur,
        montant: montant != null ? Number(montant) : null,
        motif: motif || null,
      })
      let resultat = 'etape_executee'
      while (resultat === 'etape_executee') {
        const etape = await api.executerEtape(r.dossier.id)
        resultat = etape.resultat
      }
      const refus = decision === 'refuser' || (tache.type === 'validation_refus' && decision === 'approuver')
      let texte
      if (decision === 'sans_suite') {
        texte = `Dossier ${tache.dossier_ref} clôturé sans suite — courrier de clôture enregistré.`
      } else if (refus) {
        texte = `Dossier ${tache.dossier_ref} refusé — courrier de refus enregistré.`
      } else {
        texte = `Dossier ${tache.dossier_ref} réglé (${dt(montant ?? tache.montant)}) — courrier émis.`
      }
      setMessage({ ton: decision === 'sans_suite' ? 'neutre' : refus ? 'neutre' : 'succes', texte })
      await charger()
    } catch (e) {
      setMessage({ ton: 'erreur', texte: e.message })
    }
  }

  const relancerAssure = async (tache) => {
    setMessage(null)
    try {
      await api.relancerTache(tache.id, validateur)
      await charger()
    } catch (e) {
      setMessage({ ton: 'erreur', texte: e.message })
    }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold">File d'approbation</h2>
        <span className="text-sm text-encre/50">
          {enAttente.length} tâche{enAttente.length !== 1 ? 's' : ''} en attente — décideur : {validateur}
        </span>
        <span className={`ml-auto text-xs ${surveillance.active ? 'text-ok' : 'text-encre/40'}`}>
          {surveillance.active ? '● Suivi automatique des pièces actif' : '○ Connectez SharePoint pour le suivi automatique'}
          {surveillance.verifieLe && ` · vérifié à ${surveillance.verifieLe.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`}
        </span>
      </div>

      {message && (
        <div className={`mb-4 rounded-md px-4 py-3 text-sm ${
          message.ton === 'succes' ? 'border border-ok/30 bg-ok-tint text-ok'
          : message.ton === 'erreur' ? 'border border-bad/30 bg-bad-tint text-bad'
          : 'border border-line bg-surface text-encre/75'
        }`}>
          {message.texte}
          <button onClick={() => onNavigate('pipeline')} className="ml-3 font-semibold underline">
            Voir le dossier →
          </button>
        </div>
      )}

      {enAttente.length === 0 && (
        <div className="rounded-lg border border-dashed border-line bg-surface p-10 text-center text-sm text-encre/50">
          Aucune validation en attente.
        </div>
      )}

      <div className="grid gap-4">
        {enAttente.map((t) => (
          <CarteTache key={t.id} tache={t} onDecision={decider} onRelancer={relancerAssure} />
        ))}
      </div>

      {decidees.length > 0 && (
        <details className="mt-6">
          <summary className="cursor-pointer text-sm font-semibold text-encre/60">
            Décisions rendues ({decidees.length})
          </summary>
          <div className="mt-2 grid gap-2">
            {decidees.map((t) => (
              <div key={t.id} className="flex flex-wrap items-center gap-3 rounded-md border border-line bg-surface px-4 py-2 text-sm">
                <span className="font-mono font-semibold">{t.dossier_ref}</span>
                <span className="text-encre/50">{t.assure_nom}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  t.decision === 'refuser' || t.type === 'validation_refus' ? 'bg-bad-tint text-bad' : 'bg-ok-tint text-ok'
                }`}>
                  {t.decision === 'approuver' ? 'Approuvé' : t.decision === 'refuser' ? 'Refusé' : 'Sans suite'}
                </span>
                <span className="tabular-nums">{dt(t.montant)}</span>
                {t.motif && <span className="truncate text-xs italic text-encre/40">« {t.motif} »</span>}
                <span className="ml-auto text-xs text-encre/40">par {t.validateur}</span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}

const dateCourte = (iso) =>
  new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })

function CarteTache({ tache: t, onDecision, onRelancer }) {
  const [mode, setMode] = useState(null) // null | 'modifier' | 'refuser' | 'sans_suite'
  const [montant, setMontant] = useState(t.piece_chiffree?.montant ?? t.montant)
  const [motif, setMotif] = useState('')
  const [envoi, setEnvoi] = useState(false)
  const [envoiRelance, setEnvoiRelance] = useState(false)
  const [voirRelances, setVoirRelances] = useState(false)
  const p = t.proposition ?? {}
  const refus = t.type === 'validation_refus'
  const demandePiece = t.type === 'demande_piece'
  const pieceRecue = demandePiece && t.piece_chiffree_recue
  const relances = t.relances ?? []
  const signauxAlerte = (p.signaux ?? []).filter((s) => s.statut === 'incoherent')

  const lancer = async (decision, m, mo) => {
    setEnvoi(true)
    await onDecision(t, decision, m, mo)
    setEnvoi(false)
  }

  const relancer = async () => {
    setEnvoiRelance(true)
    await onRelancer(t)
    setEnvoiRelance(false)
  }

  const ouvrirClotureSansSuite = () => {
    setMotif(
      relances.length > 0
        ? `Relance envoyée le ${dateCourte(relances[relances.length - 1].horodatage)}, aucune réponse sous 15 jours.`
        : ''
    )
    setMode('sans_suite')
  }

  return (
    <div className={`rounded-lg border-2 bg-surface p-5 ${
      signauxAlerte.length > 0 ? 'border-bad/50'
      : refus ? 'border-bad/30' : demandePiece ? 'border-encre/25' : 'border-warn/40'
    }`}>
      <div className="flex flex-wrap items-center gap-3">
        <span className="font-mono text-lg font-bold">{t.dossier_ref}</span>
        <span className="text-sm text-encre/60">{t.assure_nom} · {t.police_numero}</span>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
          demandePiece ? 'bg-surface-deep text-encre/70'
          : refus ? 'bg-bad-tint text-bad'
          : p.sous_seuil ? 'bg-surface-deep text-encre/70' : 'bg-warn-tint text-warn'
        }`}>
          {pieceRecue ? '✓ pièce reçue automatiquement' : demandePiece ? '📎 pièce manquante' : refus ? 'refus à confirmer' : p.sous_seuil ? 'proposition sous seuil' : 'validation obligatoire'}
        </span>
        {p.gravite && <span className="text-xs text-encre/50">gravité : {p.gravite}</span>}
        <div className="ml-auto text-right">
          <div className="text-[11px] uppercase tracking-wide text-encre/40">
            {demandePiece ? 'montant' : refus ? 'indemnité proposée' : 'montant recommandé'}
          </div>
          <div className="text-2xl font-bold tabular-nums">{demandePiece ? '— à déterminer' : dt(t.montant)}</div>
        </div>
      </div>
      <p className="mt-1 text-xs text-encre/50">🛡️ {p.routage}</p>
      {signauxAlerte.length > 0 && (
        <div className="mt-2 rounded-md border border-bad/40 bg-bad-tint px-3 py-2 text-xs text-bad">
          <p className="font-semibold">
            ⚠ {signauxAlerte.length} signal{signauxAlerte.length > 1 ? 'aux' : ''} d'incohérence à vérifier
          </p>
          <ul className="mt-1 list-disc pl-4">
            {signauxAlerte.map((s, i) => <li key={i}>{s.motif}</li>)}
          </ul>
        </div>
      )}
      <GaleriePieces pieces={t.pieces} className="mt-3" hauteur="h-28" />
      {demandePiece && (
        <div className="mt-2 rounded-md bg-surface-deep px-3 py-2 text-xs text-encre/70">
          {pieceRecue ? (
            <p className="font-medium text-ok">
              Facture ou devis détecté automatiquement
              {t.piece_chiffree?.source_nom && ` : ${t.piece_chiffree.source_nom}`}
              {t.piece_chiffree?.recu_le && ` — reçu le ${dateCourte(t.piece_chiffree.recu_le)}`}.
              Vérifiez le montant extrait avant de confirmer.
            </p>
          ) : (
            <p>
              Aucune facture ni devis chiffré n'a pu être extrait du dossier. Le connecteur documentaire
              vérifie automatiquement si l'assuré transmet la pièce.
            </p>
          )}
          {relances.length > 0 && (
            <button onClick={() => setVoirRelances(!voirRelances)} className="mt-1.5 font-semibold underline">
              📧 {relances.length} relance{relances.length > 1 ? 's' : ''} envoyée{relances.length > 1 ? 's' : ''}
              {' '}— dernière le {dateCourte(relances[relances.length - 1].horodatage)} ({voirRelances ? 'masquer' : 'voir'})
            </button>
          )}
          {voirRelances && (
            <div className="mt-2 grid gap-2">
              {relances.map((r, i) => (
                <div key={i} className="rounded border border-line bg-surface p-2">
                  <div className="flex items-center gap-2 text-[11px] text-encre/40">
                    <span>{dateCourte(r.horodatage)}</span>
                  </div>
                  <div className="mt-0.5 font-semibold text-encre/80">{r.objet}</div>
                  <p className="mt-0.5 whitespace-pre-wrap text-encre/60">{r.corps}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div className="rounded-md bg-surface-deep p-3">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-encre/40">
            Position de couverture
          </div>
          <ul className="grid gap-1 text-sm">
            {(p.position_couverture?.motivation ?? []).map((m, i) => (
              <li key={i}>
                <span className="text-encre/80">{m.conclusion}</span>
                <span className="ml-1 text-xs italic text-encre/40">— {m.clause}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-md bg-surface-deep p-3">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-encre/40">
            Détail du calcul indemnitaire
          </div>
          <table className="w-full text-sm">
            <tbody>
              {(p.detail_calcul ?? []).map((l, i) => (
                <tr key={i} className={l.etape.startsWith('MONTANT') ? 'font-bold' : ''}>
                  <td className="py-0.5 pr-2">{l.etape}</td>
                  <td className={`py-0.5 text-right tabular-nums ${l.valeur < 0 ? 'text-bad' : ''}`}>
                    {l.valeur != null ? dt(l.valeur) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {mode === null ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {!demandePiece && (
            <button
              onClick={() => lancer('approuver', null, refus ? 'Refus conforme à la position de couverture' : null)}
              disabled={envoi}
              className="rounded-md bg-terracotta px-4 py-2 text-sm font-semibold text-white transition hover:bg-terracotta-deep disabled:opacity-50"
            >
              {envoi ? '…' : refus ? '✓ Confirmer le refus' : `✓ Approuver ${dt(t.montant)}`}
            </button>
          )}
          <button onClick={() => setMode('modifier')} disabled={envoi}
            className="rounded-md border border-warn/50 px-4 py-2 text-sm font-semibold text-warn transition hover:bg-warn-tint">
            {pieceRecue ? '✓ Traiter la pièce reçue' : demandePiece ? '✎ Saisir une pièce reçue manuellement' : '✎ Modifier le montant'}
          </button>
          {!refus && !demandePiece && (
            <button onClick={() => setMode('refuser')} disabled={envoi}
              className="rounded-md border border-bad/40 px-4 py-2 text-sm font-semibold text-bad transition hover:bg-bad-tint">
              ✗ Refuser
            </button>
          )}
          {demandePiece && !pieceRecue && (
            <button onClick={relancer} disabled={envoiRelance || envoi}
              className="rounded-md border border-terracotta/40 px-4 py-2 text-sm font-semibold text-terracotta-deep transition hover:bg-terracotta-tint">
              {envoiRelance ? '…' : '📧 Relancer l\'assuré'}
            </button>
          )}
          {demandePiece && !pieceRecue && (
            <button onClick={ouvrirClotureSansSuite} disabled={envoi}
              className="rounded-md border border-encre/30 px-4 py-2 text-sm font-semibold text-encre/70 transition hover:bg-surface-deep">
              🚫 Clôturer sans suite (assuré non-répondant)
            </button>
          )}
        </div>
      ) : (
        <div className="mt-4 flex flex-wrap items-end gap-3 rounded-md border border-line bg-surface-deep p-3">
          {mode === 'modifier' && (
            <label className="text-sm">
              <span className="text-xs uppercase tracking-wide text-encre/40">
                {demandePiece ? 'Montant de la pièce reçue (DT)' : 'Nouveau montant (DT)'}
              </span>
              <input type="number" value={montant} onChange={(e) => setMontant(e.target.value)}
                className="mt-1 block w-36 rounded-md border border-line bg-creme p-2 text-sm" />
            </label>
          )}
          <label className="flex-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-encre/40">
              Motif {mode === 'refuser' || mode === 'sans_suite' ? '(obligatoire)' : '(recommandé)'}
            </span>
            <input value={motif} onChange={(e) => setMotif(e.target.value)}
              placeholder={
                mode === 'refuser' ? 'ex. incohérence photos / déclaration'
                : mode === 'sans_suite' ? 'ex. relance envoyée le 12/07, aucune réponse sous 15 jours'
                : 'ex. vétusté du joint non indemnisable'
              }
              className="mt-1 block w-full rounded-md border border-line bg-creme p-2 text-sm" />
          </label>
          <button
            onClick={() => lancer(mode, mode === 'modifier' ? montant : null, motif)}
            disabled={envoi || ((mode === 'refuser' || mode === 'sans_suite') && !motif)}
            className="rounded-md bg-encre px-4 py-2 text-sm font-semibold text-creme hover:bg-encre/85 disabled:opacity-50"
          >
            {envoi ? '…' : 'Confirmer la décision'}
          </button>
          <button onClick={() => setMode(null)} className="rounded-md px-3 py-2 text-sm text-encre/50 hover:bg-line">
            Annuler
          </button>
        </div>
      )}
    </div>
  )
}
