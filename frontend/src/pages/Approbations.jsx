import { useEffect, useState } from 'react'
import { api, VALIDATEUR } from '../api'
import { dt } from '../ui'

export default function Approbations({ onNavigate }) {
  const [enAttente, setEnAttente] = useState([])
  const [decidees, setDecidees] = useState([])
  const [message, setMessage] = useState(null)

  const charger = async () => {
    const [attente, faites] = await Promise.all([
      api.listerTaches('en_attente'),
      api.listerTaches('decidee'),
    ])
    setEnAttente(attente)
    setDecidees(faites)
  }

  useEffect(() => { charger() }, [])

  const decider = async (tache, decision, montant, motif) => {
    setMessage(null)
    try {
      const r = await api.deciderTache(tache.id, {
        decision, validateur: VALIDATEUR,
        montant: montant != null ? Number(montant) : null,
        motif: motif || null,
      })
      let resultat = 'etape_executee'
      while (resultat === 'etape_executee') {
        const etape = await api.executerEtape(r.dossier.id)
        resultat = etape.resultat
      }
      const refus = decision === 'refuser' || (tache.type === 'validation_refus' && decision === 'approuver')
      setMessage({
        ton: refus ? 'neutre' : 'succes',
        texte: refus
          ? `Dossier ${tache.dossier_ref} refusé — courrier de refus généré et tracé.`
          : `Dossier ${tache.dossier_ref} réglé (${dt(montant ?? tache.montant)}) — courrier envoyé (simulé).`,
      })
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
          {enAttente.length} tâche{enAttente.length !== 1 ? 's' : ''} en attente — décideur : {VALIDATEUR}
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
          Aucune validation en attente. Exécutez un dossier dans le Pipeline : il s'arrêtera ici
          dès qu'une décision d'argent est en jeu.
        </div>
      )}

      <div className="grid gap-4">
        {enAttente.map((t) => (
          <CarteTache key={t.id} tache={t} onDecision={decider} />
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
                  {t.decision}
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

function CarteTache({ tache: t, onDecision }) {
  const [mode, setMode] = useState(null) // null | 'modifier' | 'refuser'
  const [montant, setMontant] = useState(t.montant)
  const [motif, setMotif] = useState('')
  const [envoi, setEnvoi] = useState(false)
  const p = t.proposition ?? {}
  const refus = t.type === 'validation_refus'

  const lancer = async (decision, m, mo) => {
    setEnvoi(true)
    await onDecision(t, decision, m, mo)
    setEnvoi(false)
  }

  return (
    <div className={`rounded-lg border-2 bg-surface p-5 ${refus ? 'border-bad/30' : 'border-warn/40'}`}>
      <div className="flex flex-wrap items-center gap-3">
        <span className="font-mono text-lg font-bold">{t.dossier_ref}</span>
        <span className="text-sm text-encre/60">{t.assure_nom} · {t.police_numero}</span>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
          refus ? 'bg-bad-tint text-bad' : p.sous_seuil ? 'bg-surface-deep text-encre/70' : 'bg-warn-tint text-warn'
        }`}>
          {refus ? 'refus à confirmer' : p.sous_seuil ? 'sous le seuil — proposé' : 'validation obligatoire'}
        </span>
        {p.gravite && <span className="text-xs text-encre/50">gravité : {p.gravite}</span>}
        <div className="ml-auto text-right">
          <div className="text-[11px] uppercase tracking-wide text-encre/40">
            {refus ? 'indemnité proposée' : 'montant recommandé'}
          </div>
          <div className="text-2xl font-bold tabular-nums">{dt(t.montant)}</div>
        </div>
      </div>
      <p className="mt-1 text-xs text-encre/50">🛡️ {p.routage}</p>

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
            Détail du calcul (déterministe)
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
          <button
            onClick={() => lancer('approuver', null, refus ? 'Refus conforme à la position de couverture' : null)}
            disabled={envoi}
            className="rounded-md bg-terracotta px-4 py-2 text-sm font-semibold text-white transition hover:bg-terracotta-deep disabled:opacity-50"
          >
            {envoi ? '…' : refus ? '✓ Confirmer le refus' : `✓ Approuver ${dt(t.montant)}`}
          </button>
          <button onClick={() => setMode('modifier')} disabled={envoi}
            className="rounded-md border border-warn/50 px-4 py-2 text-sm font-semibold text-warn transition hover:bg-warn-tint">
            ✎ Modifier le montant
          </button>
          {!refus && (
            <button onClick={() => setMode('refuser')} disabled={envoi}
              className="rounded-md border border-bad/40 px-4 py-2 text-sm font-semibold text-bad transition hover:bg-bad-tint">
              ✗ Refuser
            </button>
          )}
        </div>
      ) : (
        <div className="mt-4 flex flex-wrap items-end gap-3 rounded-md border border-line bg-surface-deep p-3">
          {mode === 'modifier' && (
            <label className="text-sm">
              <span className="text-xs uppercase tracking-wide text-encre/40">Nouveau montant (DT)</span>
              <input type="number" value={montant} onChange={(e) => setMontant(e.target.value)}
                className="mt-1 block w-36 rounded-md border border-line bg-creme p-2 text-sm" />
            </label>
          )}
          <label className="flex-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-encre/40">
              Motif {mode === 'refuser' ? '(obligatoire)' : '(recommandé)'}
            </span>
            <input value={motif} onChange={(e) => setMotif(e.target.value)}
              placeholder={mode === 'refuser' ? 'ex. incohérence photos / déclaration' : 'ex. vétusté du joint non indemnisable'}
              className="mt-1 block w-full rounded-md border border-line bg-creme p-2 text-sm" />
          </label>
          <button
            onClick={() => lancer(mode, mode === 'modifier' ? montant : null, motif)}
            disabled={envoi || (mode === 'refuser' && !motif)}
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
