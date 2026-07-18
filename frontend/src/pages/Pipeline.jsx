import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { AGENT_ICONE, BadgeEtat, BadgeMode, dt } from '../ui'

const DELAI_ANIMATION_MS = 650

export default function Pipeline({ onNavigate }) {
  const [dossiers, setDossiers] = useState([])
  const [selection, setSelection] = useState(null) // {dossier, police, workflow, runs}
  const [agents, setAgents] = useState({})
  const [enExecution, setEnExecution] = useState(false)
  const [formulaire, setFormulaire] = useState(false)
  const [erreur, setErreur] = useState(null)
  const stopRef = useRef(false)

  const chargerListe = () => api.listerDossiers().then(setDossiers).catch((e) => setErreur(e.message))
  const chargerDetail = (id) => api.lireDossier(id).then(setSelection).catch((e) => setErreur(e.message))

  useEffect(() => {
    chargerListe()
    api.listerAgents().then((liste) => {
      const parId = {}
      liste.forEach((a) => (parId[a.id] = a))
      setAgents(parId)
    })
  }, [])

  useEffect(() => {
    if (!selection && dossiers.length) chargerDetail(dossiers[0].id)
  }, [dossiers]) // eslint-disable-line react-hooks/exhaustive-deps

  const executer = async () => {
    if (!selection || enExecution) return
    setEnExecution(true)
    setErreur(null)
    stopRef.current = false
    try {
      let resultat = 'etape_executee'
      while (resultat === 'etape_executee' && !stopRef.current) {
        const r = await api.executerEtape(selection.dossier.id)
        resultat = r.resultat
        await chargerDetail(selection.dossier.id)
        await chargerListe()
        if (resultat === 'etape_executee') {
          await new Promise((ok) => setTimeout(ok, DELAI_ANIMATION_MS))
        }
      }
    } catch (e) {
      setErreur(e.message)
    } finally {
      setEnExecution(false)
    }
  }

  const d = selection?.dossier

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      {/* ---- colonne dossiers ---- */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Dossiers</h2>
          <button
            onClick={() => setFormulaire(true)}
            className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
          >
            + Déclarer un sinistre
          </button>
        </div>
        <div className="grid gap-2">
          {dossiers.map((x) => (
            <button
              key={x.id}
              onClick={() => chargerDetail(x.id)}
              className={`rounded-xl border bg-white p-3 text-left transition hover:border-sky-400 ${
                d?.id === x.id ? 'border-sky-500 ring-2 ring-sky-100' : 'border-slate-200'
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-semibold">{x.ref}</span>
                <span className="ml-auto"><BadgeEtat etat={x.etat} /></span>
              </div>
              <div className="mt-1 text-sm text-slate-600">
                {x.assure_nom} · {x.formule?.replace('_', ' ')}
              </div>
              {x.montant_recommande != null && (
                <div className="mt-1 text-xs text-slate-500">
                  recommandé : <b>{dt(x.montant_recommande)}</b>
                  {x.montant_valide != null && <> · validé : <b className="text-emerald-700">{dt(x.montant_valide)}</b></>}
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* ---- détail + frise ---- */}
      <div className="min-w-0">
        {erreur && (
          <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}
        {d ? (
          <DetailDossier
            selection={selection}
            agents={agents}
            enExecution={enExecution}
            onExecuter={executer}
            onNavigate={onNavigate}
          />
        ) : (
          <p className="text-sm text-slate-500">Sélectionnez un dossier.</p>
        )}
      </div>

      {formulaire && (
        <FormulaireDeclaration
          onFermer={() => setFormulaire(false)}
          onCree={async (nouveau) => {
            setFormulaire(false)
            await chargerListe()
            await chargerDetail(nouveau.id)
          }}
        />
      )}
    </div>
  )
}

/* ================= détail d'un dossier ================= */

function DetailDossier({ selection, agents, enExecution, onExecuter, onNavigate }) {
  const { dossier: d, police, workflow, runs } = selection
  const etapes = workflow?.etapes ?? []
  const dernierRun = runs[runs.length - 1]
  const termine = ['regle', 'refuse', 'cloture'].includes(d.etat)

  return (
    <div className="grid gap-4">
      {/* entête */}
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-mono text-lg font-bold">{d.ref}</span>
          <BadgeEtat etat={d.etat} />
          <span className="text-sm text-slate-600">
            {police?.assure_nom} — {police?.numero} ({police?.formule?.replace('_', ' ')})
          </span>
          <span className="text-sm text-slate-500">
            {police?.vehicule?.marque} {police?.vehicule?.modele} · {police?.vehicule?.annee}
          </span>
          <div className="ml-auto flex items-center gap-4">
            {d.montant_recommande != null && (
              <div className="text-right">
                <div className="text-[11px] uppercase tracking-wide text-slate-400">recommandé (calcul)</div>
                <div className="text-xl font-bold text-slate-800">{dt(d.montant_recommande)}</div>
              </div>
            )}
            {d.montant_valide != null && (
              <div className="text-right">
                <div className="text-[11px] uppercase tracking-wide text-emerald-600">validé (humain)</div>
                <div className="text-xl font-bold text-emerald-700">{dt(d.montant_valide)}</div>
              </div>
            )}
          </div>
        </div>
        <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm italic text-slate-600">
          « {d.declaration_texte} »
        </p>
      </div>

      {/* frise du pipeline */}
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold">{workflow?.nom ?? 'Pipeline'}</h3>
          {!termine && d.etat !== 'attente_validation' && (
            <button
              onClick={onExecuter}
              disabled={enExecution}
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-sky-500 disabled:opacity-50"
            >
              {enExecution ? '⏳ Exécution en cours…' : '▶ Exécuter le pipeline'}
            </button>
          )}
        </div>
        <Frise etapes={etapes} agents={agents} dossier={d} runs={runs} enExecution={enExecution} />

        {d.etat === 'attente_validation' && (
          <div className="mt-4 flex items-center gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3">
            <span className="text-xl">🛡️</span>
            <div className="text-sm text-amber-900">
              <b>Pipeline suspendu — validation humaine requise.</b> Aucun règlement ne part sans
              décision explicite d'un gestionnaire.
            </div>
            <button
              onClick={() => onNavigate('approbations')}
              className="ml-auto whitespace-nowrap rounded-lg bg-amber-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-amber-400"
            >
              Ouvrir la file d'approbation →
            </button>
          </div>
        )}
      </div>

      {/* sortie du dernier agent exécuté */}
      {dernierRun && !termine && (
        <SortieRun run={dernierRun} agents={agents} titre="Dernière sortie d'agent" />
      )}

      {/* courrier final */}
      {termine && d.courrier?.corps && <Courrier courrier={d.courrier} etat={d.etat} />}

      {/* historique des runs */}
      {runs.length > 0 && (
        <details className="rounded-xl border border-slate-200 bg-white p-4" open={termine}>
          <summary className="cursor-pointer font-semibold">
            Trace d'exécution — {runs.length} run{runs.length > 1 ? 's' : ''} d'agents
          </summary>
          <div className="mt-3 grid gap-3">
            {runs.map((r) => (
              <SortieRun key={r.id} run={r} agents={agents} compact />
            ))}
          </div>
        </details>
      )}
    </div>
  )
}

function Frise({ etapes, agents, dossier, runs, enExecution }) {
  const agentsAyantTourne = new Set(runs.filter((r) => r.statut === 'succes').map((r) => r.agent_id))
  return (
    <div className="flex items-stretch gap-1 overflow-x-auto pb-2">
      {etapes.map((e, i) => {
        const agent = agents[e.agent_id]
        const porte = e.type === 'porte_humaine'
        const faite = i < dossier.etape_courante && (agentsAyantTourne.has(e.agent_id) || porte)
        const courante = i === dossier.etape_courante && !['regle', 'refuse'].includes(dossier.etat)
        const enAttente = porte && dossier.etat === 'attente_validation'
        return (
          <div key={i} className="flex items-center">
            <div
              className={`flex w-[108px] flex-col items-center gap-1 rounded-lg border-2 p-2 text-center transition-all ${
                enAttente
                  ? 'border-amber-400 bg-amber-50'
                  : faite
                    ? 'border-emerald-300 bg-emerald-50'
                    : courante
                      ? `border-sky-400 bg-sky-50 ${enExecution ? 'animate-pulse' : ''}`
                      : 'border-slate-200 bg-slate-50 opacity-60'
              }`}
            >
              <span className="text-xl">{porte ? '🛡️' : AGENT_ICONE[agent?.categorie] ?? '⚙️'}</span>
              <span className="text-[11px] font-medium leading-tight text-slate-700">
                {agent?.nom ?? '—'}
              </span>
              <span className="text-[10px] text-slate-400">
                {enAttente ? 'attente humain' : faite ? '✓ terminé' : courante ? 'prochain' : 'à venir'}
              </span>
            </div>
            {i < etapes.length - 1 && (
              <span className={`px-0.5 text-lg ${faite ? 'text-emerald-400' : 'text-slate-300'}`}>→</span>
            )}
          </div>
        )
      })}
    </div>
  )
}

/* ================= rendu des sorties par type d'agent ================= */

function SortieRun({ run, agents, titre, compact }) {
  const agent = agents[run.agent_id]
  const s = run.sorties ?? {}
  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-4 ${compact ? 'shadow-none' : ''}`}>
      <div className="mb-2 flex items-center gap-2">
        <span>{AGENT_ICONE[agent?.categorie] ?? '⚙️'}</span>
        <span className="text-sm font-semibold">{titre ?? agent?.nom ?? `agent ${run.agent_id}`}</span>
        {titre && <span className="text-xs text-slate-400">({agent?.nom})</span>}
        <BadgeMode mode={s.mode} />
        {run.confiance != null && (
          <span className="text-xs text-slate-400">confiance {(run.confiance * 100).toFixed(0)} %</span>
        )}
        <span className="ml-auto text-xs text-slate-400">
          {run.duree_ms} ms{run.cout > 0 && ` · $${run.cout.toFixed(4)}`}
        </span>
      </div>
      <CorpsSortie categorie={agent?.categorie} s={s} />
    </div>
  )
}

function CorpsSortie({ categorie, s }) {
  if (categorie === 'fnol' && s.donnees_fnol) {
    const f = s.donnees_fnol
    return (
      <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm md:grid-cols-3">
        <Champ nom="Type de sinistre" valeur={f.type_sinistre} fort />
        <Champ nom="Langue détectée" valeur={f.langue} />
        <Champ nom="Complétude" valeur={`${Math.round(f.completude * 100)} %`} />
        <Champ nom="Tiers identifié" valeur={f.tiers_identifie ? 'oui' : 'non'} />
        <Champ nom="Constat" valeur={f.constat_present ? 'présent' : 'absent'} />
        <Champ nom="Champs manquants" valeur={f.champs_manquants?.join(', ') || 'aucun'} />
        <div className="col-span-full"><Champ nom="Circonstances" valeur={f.circonstances} /></div>
      </div>
    )
  }
  if (categorie === 'extraction' && s.pieces) {
    return (
      <div className="grid gap-2">
        {s.pieces.filter((p) => p.extraction).map((p, i) => (
          <div key={i} className="rounded-lg bg-slate-50 p-2 text-sm">
            <div className="flex items-center gap-2">
              <b>{p.type}</b>
              <span className="text-xs text-slate-500">{p.extraction.emetteur}</span>
              {p.extraction.total != null && (
                <span className="ml-auto font-semibold">{dt(p.extraction.total)}</span>
              )}
            </div>
            {p.extraction.postes?.length > 0 && (
              <ul className="mt-1 text-xs text-slate-600">
                {p.extraction.postes.map((poste, j) => (
                  <li key={j} className="flex justify-between border-t border-slate-200 py-0.5">
                    <span>{poste.libelle}</span><span>{dt(poste.montant)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {s.montant_estime != null && (
          <div className="text-sm">
            Montant de référence retenu : <b>{dt(s.montant_estime)}</b>
          </div>
        )}
      </div>
    )
  }
  if (categorie === 'vision' && s.analyse_gravite) {
    const g = s.analyse_gravite
    const couleurs = { leger: 'bg-emerald-100 text-emerald-800', moyen: 'bg-amber-100 text-amber-800', lourd: 'bg-red-100 text-red-800' }
    return (
      <div className="text-sm">
        <span className={`rounded-full px-2.5 py-0.5 font-semibold ${couleurs[g.classe]}`}>
          gravité : {g.classe}
        </span>
        <span className="ml-3 text-slate-600">zones : {g.zones?.join(', ') || '—'}</span>
        <p className="mt-1 text-slate-500">{g.commentaire}</p>
      </div>
    )
  }
  if (categorie === 'garanties' && s.position_couverture) {
    const p = s.position_couverture
    return (
      <div className="text-sm">
        <div className={`mb-2 inline-block rounded-full px-2.5 py-0.5 font-semibold ${
          p.couvert ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
        }`}>
          {p.couvert ? `✓ couvert — garantie ${p.garantie}` : `✗ non couvert (${p.motif_refus})`}
        </div>
        <ul className="grid gap-1">
          {p.motivation?.map((m, i) => (
            <li key={i} className="rounded bg-slate-50 px-2 py-1">
              <span className="text-slate-700">{m.conclusion}</span>
              <span className="ml-2 text-xs italic text-slate-400">{m.clause}</span>
            </li>
          ))}
        </ul>
      </div>
    )
  }
  if (categorie === 'indemnite' && s.detail_calcul) {
    return (
      <table className="w-full text-sm">
        <tbody>
          {s.detail_calcul.map((l, i) => {
            const total = l.etape.startsWith('MONTANT')
            return (
              <tr key={i} className={total ? 'border-t-2 border-slate-300 font-bold' : 'border-t border-slate-100'}>
                <td className="py-1.5 pr-2">{l.etape}</td>
                <td className={`py-1.5 pr-2 text-right tabular-nums ${l.valeur < 0 ? 'text-red-600' : ''}`}>
                  {l.valeur != null ? dt(l.valeur) : '—'}
                </td>
                <td className="py-1.5 text-xs text-slate-400">{l.source}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    )
  }
  if (categorie === 'hitl') {
    return <p className="text-sm text-slate-700">🛡️ {s.routage}</p>
  }
  if (categorie === 'courrier' && s.courrier) {
    return <p className="text-sm text-slate-600">Courrier généré : « {s.courrier.objet} »</p>
  }
  return <pre className="max-h-40 overflow-auto rounded bg-slate-50 p-2 text-xs">{JSON.stringify(s, null, 2)}</pre>
}

const Champ = ({ nom, valeur, fort }) => (
  <div>
    <span className="text-xs uppercase tracking-wide text-slate-400">{nom}</span>
    <div className={fort ? 'font-semibold' : ''}>{String(valeur ?? '—')}</div>
  </div>
)

function Courrier({ courrier, etat }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center gap-2">
        <span>✉️</span>
        <span className="font-semibold">Email envoyé à l'assuré</span>
        <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-slate-600">
          envoi simulé
        </span>
        <BadgeMode mode={courrier.mode} />
        <span className="ml-auto"><BadgeEtat etat={etat} /></span>
      </div>
      <div className="rounded-lg border border-slate-100 bg-slate-50 p-4">
        <div className="border-b border-slate-200 pb-2 text-sm font-semibold">{courrier.objet}</div>
        <pre className="mt-2 whitespace-pre-wrap font-sans text-sm text-slate-700">{courrier.corps}</pre>
      </div>
    </div>
  )
}

/* ================= déclaration d'un nouveau sinistre ================= */

const EXEMPLE_DECLARATION =
  "Bonjour, ce matin sur la GP1 un camion a projeté un gravier qui a fissuré mon pare-brise. " +
  'Je joins le devis du poseur (380 DT). Mohamed Gharbi, police PA-2025-0212.'

function FormulaireDeclaration({ onFermer, onCree }) {
  const [texte, setTexte] = useState('')
  const [police, setPolice] = useState('PA-2025-0212')
  const [montant, setMontant] = useState('380')
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState(null)

  const soumettre = async () => {
    setEnvoi(true)
    setErreur(null)
    try {
      const nouveau = await api.declarerSinistre({
        declaration_texte: texte,
        police_numero: police,
        pieces: montant
          ? [{ type: 'devis', chemin: 'docs/samples/devis-parebrise.jpg', montant: Number(montant) }]
          : [],
      })
      onCree(nouveau)
    } catch (e) {
      setErreur(e.message)
      setEnvoi(false)
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-900/50 p-4" onClick={onFermer}>
      <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold">Déclarer un sinistre</h3>
        <p className="mt-1 text-sm text-slate-500">
          Texte libre, français ou darija — l'agent FNOL structure la déclaration.
        </p>
        <textarea
          value={texte}
          onChange={(e) => setTexte(e.target.value)}
          placeholder={EXEMPLE_DECLARATION}
          rows={5}
          className="mt-3 w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-sky-500 focus:outline-none"
        />
        <div className="mt-3 flex gap-3">
          <label className="flex-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-slate-400">N° de police</span>
            <input value={police} onChange={(e) => setPolice(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 p-2 font-mono text-sm" />
          </label>
          <label className="flex-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-slate-400">Montant devis joint (DT)</span>
            <input value={montant} onChange={(e) => setMontant(e.target.value)} type="number"
              className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-sm" />
          </label>
        </div>
        {erreur && <p className="mt-2 text-sm text-red-600">{erreur}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onFermer} className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100">
            Annuler
          </button>
          <button
            onClick={() => setTexte(EXEMPLE_DECLARATION)}
            className="rounded-lg px-4 py-2 text-sm text-sky-700 hover:bg-sky-50"
          >
            Remplir l'exemple
          </button>
          <button
            onClick={soumettre}
            disabled={!texte || !police || envoi}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {envoi ? 'Création…' : 'Créer le dossier'}
          </button>
        </div>
      </div>
    </div>
  )
}
