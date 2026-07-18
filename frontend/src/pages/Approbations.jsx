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
      // La décision humaine relance le pipeline : on déroule jusqu'au courrier.
      let resultat = 'etape_executee'
      while (resultat === 'etape_executee') {
        const etape = await api.executerEtape(r.dossier.id)
        resultat = etape.resultat
      }
      setMessage({
        ton: decision === 'refuser' || tache.type === 'validation_refus' ? 'neutre' : 'succes',
        texte:
          decision === 'refuser' || (tache.type === 'validation_refus' && decision === 'approuver')
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
      <div className="mb-4 flex items-center gap-3">
        <h2 className="text-lg font-semibold">File d'approbation</h2>
        <span className="text-sm text-slate-500">
          {enAttente.length} tâche{enAttente.length !== 1 ? 's' : ''} en attente — décideur : {VALIDATEUR}
        </span>
      </div>

      {message && (
        <div className={`mb-4 rounded-lg px-4 py-3 text-sm ${
          message.ton === 'succes' ? 'border border-emerald-200 bg-emerald-50 text-emerald-800'
          : message.ton === 'erreur' ? 'border border-red-200 bg-red-50 text-red-700'
          : 'border border-slate-200 bg-white text-slate-700'
        }`}>
          {message.texte}
          <button onClick={() => onNavigate('pipeline')} className="ml-3 font-semibold underline">
            Voir le dossier →
          </button>
        </div>
      )}

      {enAttente.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
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
          <summary className="cursor-pointer text-sm font-semibold text-slate-600">
            Décisions rendues ({decidees.length})
          </summary>
          <div className="mt-2 grid gap-2">
            {decidees.map((t) => (
              <div key={t.id} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm">
                <span className="font-mono font-semibold">{t.dossier_ref}</span>
                <span className="text-slate-500">{t.assure_nom}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  t.decision === 'refuser' || t.type === 'validation_refus'
                    ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'
                }`}>
                  {t.decision}
                </span>
                <span className="tabular-nums">{dt(t.montant)}</span>
                {t.motif && <span className="truncate text-xs italic text-slate-400">« {t.motif} »</span>}
                <span className="ml-auto text-xs text-slate-400">par {t.validateur}</span>
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
    <div className={`rounded-xl border-2 bg-white p-5 ${refus ? 'border-red-200' : 'border-amber-200'}`}>
      <div className="flex flex-wrap items-center gap-3">
        <span className="font-mono text-lg font-bold">{t.dossier_ref}</span>
        <span className="text-sm text-slate-600">{t.assure_nom} · {t.police_numero}</span>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
          refus ? 'bg-red-100 text-red-800'
          : p.sous_seuil ? 'bg-sky-100 text-sky-800' : 'bg-amber-100 text-amber-800'
        }`}>
          {refus ? 'refus à confirmer' : p.sous_seuil ? 'sous le seuil — proposé' : 'validation obligatoire'}
        </span>
        {p.gravite && <span className="text-xs text-slate-500">gravité : {p.gravite}</span>}
        <div className="ml-auto text-right">
          <div className="text-[11px] uppercase tracking-wide text-slate-400">
            {refus ? 'indemnité proposée' : 'montant recommandé'}
          </div>
          <div className="text-2xl font-bold tabular-nums">{dt(t.montant)}</div>
        </div>
      </div>
      <p className="mt-1 text-xs text-slate-500">🛡️ {p.routage}</p>

      {/* synthèse pour décision éclairée */}
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Position de couverture
          </div>
          <ul className="grid gap-1 text-sm">
            {(p.position_couverture?.motivation ?? []).map((m, i) => (
              <li key={i}>
                <span className="text-slate-700">{m.conclusion}</span>
                <span className="ml-1 text-xs italic text-slate-400">— {m.clause}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Détail du calcul (déterministe)
          </div>
          <table className="w-full text-sm">
            <tbody>
              {(p.detail_calcul ?? []).map((l, i) => (
                <tr key={i} className={l.etape.startsWith('MONTANT') ? 'font-bold' : ''}>
                  <td className="py-0.5 pr-2">{l.etape}</td>
                  <td className={`py-0.5 text-right tabular-nums ${l.valeur < 0 ? 'text-red-600' : ''}`}>
                    {l.valeur != null ? dt(l.valeur) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* actions */}
      {mode === null ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            onClick={() => lancer('approuver', null, refus ? 'Refus conforme à la position de couverture' : null)}
            disabled={envoi}
            className={`rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 ${
              refus ? 'bg-red-600 hover:bg-red-500' : 'bg-emerald-600 hover:bg-emerald-500'
            }`}
          >
            {envoi ? '…' : refus ? '✓ Confirmer le refus' : `✓ Approuver ${dt(t.montant)}`}
          </button>
          <button
            onClick={() => setMode('modifier')}
            disabled={envoi}
            className="rounded-lg border border-amber-400 px-4 py-2 text-sm font-semibold text-amber-700 hover:bg-amber-50"
          >
            ✎ Modifier le montant
          </button>
          {!refus && (
            <button
              onClick={() => setMode('refuser')}
              disabled={envoi}
              className="rounded-lg border border-red-300 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"
            >
              ✗ Refuser
            </button>
          )}
        </div>
      ) : (
        <div className="mt-4 flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
          {mode === 'modifier' && (
            <label className="text-sm">
              <span className="text-xs uppercase tracking-wide text-slate-400">Nouveau montant (DT)</span>
              <input type="number" value={montant} onChange={(e) => setMontant(e.target.value)}
                className="mt-1 block w-36 rounded-lg border border-slate-300 p-2 text-sm" />
            </label>
          )}
          <label className="flex-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-slate-400">
              Motif {mode === 'refuser' ? '(obligatoire)' : '(recommandé)'}
            </span>
            <input value={motif} onChange={(e) => setMotif(e.target.value)}
              placeholder={mode === 'refuser' ? 'ex. incohérence photos / déclaration' : 'ex. vétusté du joint non indemnisable'}
              className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-sm" />
          </label>
          <button
            onClick={() => lancer(mode, mode === 'modifier' ? montant : null, motif)}
            disabled={envoi || (mode === 'refuser' && !motif)}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {envoi ? '…' : 'Confirmer la décision'}
          </button>
          <button onClick={() => setMode(null)} className="rounded-lg px-3 py-2 text-sm text-slate-500 hover:bg-slate-200">
            Annuler
          </button>
        </div>
      )}
    </div>
  )
}
