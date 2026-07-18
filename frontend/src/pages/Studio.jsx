import { useEffect, useState } from 'react'
import { api } from '../api'
import { AGENT_ICONE } from '../ui'

export default function Studio() {
  const [templates, setTemplates] = useState([])
  const [agents, setAgents] = useState([])
  const [workflow, setWorkflow] = useState(null)
  const [creation, setCreation] = useState(null) // template sélectionné pour le formulaire
  const [message, setMessage] = useState(null)

  const charger = async () => {
    const [t, a, w] = await Promise.all([
      api.listerTemplates(), api.listerAgents(), api.listerWorkflows(),
    ])
    setTemplates(t)
    setAgents(a)
    setWorkflow(w[0] ?? null)
  }

  useEffect(() => { charger() }, [])

  const agentsDuPipeline = new Set((workflow?.etapes ?? []).map((e) => e.agent_id))

  const agir = async (action, texteOk) => {
    setMessage(null)
    try {
      await action()
      await charger()
      setMessage({ ton: 'succes', texte: texteOk })
    } catch (e) {
      setMessage({ ton: 'erreur', texte: e.message })
    }
  }

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <h2 className="text-lg font-semibold">Studio d'agents</h2>
        <span className="text-sm text-slate-500">
          créer depuis un template métier — sans code, gouvernance incluse
        </span>
      </div>

      {message && (
        <div className={`mb-4 rounded-lg px-4 py-2 text-sm ${
          message.ton === 'succes'
            ? 'border border-emerald-200 bg-emerald-50 text-emerald-800'
            : 'border border-red-200 bg-red-50 text-red-700'
        }`}>
          {message.texte}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(280px,1fr)_minmax(0,1.6fr)]">
        {/* templates */}
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Templates métier
          </h3>
          <div className="grid gap-3">
            {templates.map((t) => (
              <div key={t.id} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{AGENT_ICONE[t.categorie] ?? '⚙️'}</span>
                  <span className="font-medium">{t.nom}</span>
                  <button
                    onClick={() => setCreation(t)}
                    className="ml-auto rounded-lg bg-slate-900 px-3 py-1 text-xs font-semibold text-white hover:bg-slate-700"
                  >
                    Créer un agent
                  </button>
                </div>
                <p className="mt-2 line-clamp-3 text-xs text-slate-500">{t.instructions_defaut}</p>
                {Object.keys(t.garde_fous_defaut ?? {}).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {Object.keys(t.garde_fous_defaut).map((g) => (
                      <span key={g} className="rounded bg-teal-50 px-1.5 py-0.5 text-[10px] font-medium text-teal-700">
                        🔒 {g}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {workflow && (
            <div className="mt-6">
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
                Pipeline live — {workflow.nom}
              </h3>
              <ol className="grid gap-1 rounded-xl border border-slate-200 bg-white p-3">
                {workflow.etapes.map((e, i) => {
                  const a = agents.find((x) => x.id === e.agent_id)
                  return (
                    <li key={i} className="flex items-center gap-2 text-sm">
                      <span className="w-5 text-right text-xs text-slate-400">{i + 1}.</span>
                      <span>{e.type === 'porte_humaine' ? '🛡️' : AGENT_ICONE[a?.categorie] ?? '⚙️'}</span>
                      <span>{a?.nom}</span>
                      <span className="text-xs text-slate-400">v{a?.version}</span>
                      {e.type === 'porte_humaine' && (
                        <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
                          porte humaine
                        </span>
                      )}
                    </li>
                  )
                })}
              </ol>
            </div>
          )}
        </div>

        {/* agents déployés */}
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Agents ({agents.length})
          </h3>
          <div className="grid gap-2">
            {agents.map((a) => (
              <CarteAgent
                key={a.id}
                agent={a}
                dansPipeline={agentsDuPipeline.has(a.id)}
                onPublier={() => agir(() => api.publierAgent(a.id), `« ${a.nom} » est maintenant live (tracé dans l'audit).`)}
                onBrancher={() =>
                  agir(
                    () => api.affecterAgent(workflow.id, a.id),
                    `« ${a.nom} » est branché dans le pipeline P5 — effectif immédiatement.`,
                  )
                }
                onSeuils={(seuils) =>
                  agir(
                    () => api.modifierAgent(a.id, { seuils }),
                    `Seuils de « ${a.nom} » mis à jour → nouvelle version, tracée dans l'audit.`,
                  )
                }
              />
            ))}
          </div>
        </div>
      </div>

      {creation && (
        <FormulaireCreation
          template={creation}
          onFermer={() => setCreation(null)}
          onCree={async (nom) => {
            setCreation(null)
            await charger()
            setMessage({ ton: 'succes', texte: `Agent « ${nom} » créé en brouillon — publiez-le pour l'utiliser.` })
          }}
        />
      )}
    </div>
  )
}

function CarteAgent({ agent: a, dansPipeline, onPublier, onBrancher, onSeuils }) {
  const [editionSeuil, setEditionSeuil] = useState(false)
  const [seuil, setSeuil] = useState(a.seuils?.seuil_validation ?? '')
  const aDesSeuils = a.seuils && Object.keys(a.seuils).length > 0

  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span>{AGENT_ICONE[a.categorie] ?? '⚙️'}</span>
        <span className="text-sm font-semibold">{a.nom}</span>
        <span className="text-xs text-slate-400">v{a.version}</span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
          a.statut === 'live' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'
        }`}>
          {a.statut}
        </span>
        {dansPipeline && (
          <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-800">
            dans le pipeline
          </span>
        )}
        {a.garde_fous?.deterministe && (
          <span className="rounded bg-teal-50 px-1.5 py-0.5 text-[10px] font-semibold text-teal-700">
            déterministe — pas de LLM
          </span>
        )}
        {a.garde_fous?.non_desactivable && (
          <span className="rounded bg-red-50 px-1.5 py-0.5 text-[10px] font-semibold text-red-700">
            🔒 non désactivable
          </span>
        )}
        <div className="ml-auto flex gap-2">
          {a.statut === 'draft' && (
            <button onClick={onPublier}
              className="rounded-lg bg-emerald-600 px-3 py-1 text-xs font-semibold text-white hover:bg-emerald-500">
              Publier
            </button>
          )}
          {a.statut === 'live' && !dansPipeline && (
            <button onClick={onBrancher}
              className="rounded-lg border border-sky-400 px-3 py-1 text-xs font-semibold text-sky-700 hover:bg-sky-50">
              Brancher au pipeline
            </button>
          )}
          {aDesSeuils && (
            <button onClick={() => setEditionSeuil(!editionSeuil)}
              className="rounded-lg border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50">
              Seuils
            </button>
          )}
        </div>
      </div>
      {aDesSeuils && !editionSeuil && (
        <div className="mt-1.5 text-xs text-slate-500">
          seuil de validation obligatoire : <b>{a.seuils.seuil_validation} DT</b>
          {a.seuils.plafond_auto != null && <> · plafond auto : <b>{a.seuils.plafond_auto} DT</b></>}
        </div>
      )}
      {editionSeuil && (
        <div className="mt-2 flex items-end gap-2 rounded-lg bg-slate-50 p-2">
          <label className="text-xs">
            <span className="uppercase tracking-wide text-slate-400">Seuil de validation (DT)</span>
            <input type="number" value={seuil} onChange={(e) => setSeuil(e.target.value)}
              className="mt-1 block w-32 rounded border border-slate-300 p-1.5 text-sm" />
          </label>
          <button
            onClick={() => { onSeuils({ ...a.seuils, seuil_validation: Number(seuil) }); setEditionSeuil(false) }}
            className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
          >
            Enregistrer (v{a.version + 1})
          </button>
          <span className="pb-1 text-[10px] text-slate-400">
            changement de gouvernance → versionné + audité
          </span>
        </div>
      )}
    </div>
  )
}

function FormulaireCreation({ template, onFermer, onCree }) {
  const [nom, setNom] = useState('')
  const [instructions, setInstructions] = useState(template.instructions_defaut)
  const [seuil, setSeuil] = useState('1000')
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState(null)
  const estIndemnite = template.categorie === 'indemnite'

  const soumettre = async () => {
    setEnvoi(true)
    setErreur(null)
    try {
      await api.creerAgent({
        nom,
        template_id: template.id,
        instructions,
        seuils: estIndemnite && seuil ? { seuil_validation: Number(seuil) } : {},
      })
      onCree(nom)
    } catch (e) {
      setErreur(e.message)
      setEnvoi(false)
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-900/50 p-4" onClick={onFermer}>
      <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold">Nouvel agent — {template.nom}</h3>
        <label className="mt-4 block text-sm">
          <span className="text-xs uppercase tracking-wide text-slate-400">Nom de l'agent</span>
          <input value={nom} onChange={(e) => setNom(e.target.value)}
            placeholder="ex. Règlement auto — bris de glace"
            className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-sm" />
        </label>
        <label className="mt-3 block text-sm">
          <span className="text-xs uppercase tracking-wide text-slate-400">Instructions</span>
          <textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} rows={4}
            className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-sm" />
        </label>
        {estIndemnite && (
          <label className="mt-3 block text-sm">
            <span className="text-xs uppercase tracking-wide text-slate-400">Seuil de validation humaine (DT)</span>
            <input type="number" value={seuil} onChange={(e) => setSeuil(e.target.value)}
              className="mt-1 w-40 rounded-lg border border-slate-300 p-2 text-sm" />
          </label>
        )}
        <div className="mt-3 rounded-lg bg-teal-50 p-2 text-xs text-teal-800">
          🔒 Garde-fous hérités du template (non désactivables) :{' '}
          {Object.keys(template.garde_fous_defaut ?? {}).join(', ') || 'aucun'}
        </div>
        {erreur && <p className="mt-2 text-sm text-red-600">{erreur}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onFermer} className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100">
            Annuler
          </button>
          <button onClick={soumettre} disabled={!nom || envoi}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50">
            {envoi ? 'Création…' : "Créer l'agent (draft)"}
          </button>
        </div>
      </div>
    </div>
  )
}
