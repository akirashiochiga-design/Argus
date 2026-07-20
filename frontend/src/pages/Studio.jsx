import { useEffect, useState } from 'react'
import { api } from '../api'
import { BrandMark } from '../brandLogos'
import { AGENT_ICONE } from '../ui'

const LIBELLES_GARDE_FOU = {
  deterministe: 'Règles de gestion',
  non_desactivable: 'Contrôle obligatoire',
  hitl_obligatoire: 'Validation humaine obligatoire',
  pas_de_decision_argent: 'Aucune décision financière',
  montant_impose: 'Montant validé uniquement',
  pas_de_donnees_sensibles: 'Données sensibles protégées',
  langues: 'Langues prises en charge',
  bareme_vetuste: 'Barème de vétusté',
  vetuste_garanties: 'Garanties soumises à vétusté',
  origine: 'Configuration personnalisée',
  outils_autorises: 'Outils métier contrôlés',
  max_iterations_agent: "Limite d'itérations",
}

const libelleGardeFou = (cle) =>
  LIBELLES_GARDE_FOU[cle] ?? cle.replaceAll('_', ' ').replace(/^\w/, (lettre) => lettre.toUpperCase())

const OUTILS_PAR_CATEGORIE = {
  fnol: ['consulter_police', 'inventorier_pieces'],
  vision: ['consulter_vehicule_assure', 'consulter_circonstances', 'inventorier_pieces'],
}

const LIBELLES_OUTILS = {
  consulter_police: 'Police',
  inventorier_pieces: 'Pièces',
  consulter_vehicule_assure: 'Véhicule assuré',
  consulter_circonstances: 'Circonstances',
}

export default function Studio() {
  const [templates, setTemplates] = useState([])
  const [agents, setAgents] = useState([])
  const [workflows, setWorkflows] = useState([])
  const [workflow, setWorkflow] = useState(null)
  const [categories, setCategories] = useState({})
  const [creation, setCreation] = useState(null) // template pour le formulaire modal
  const [composeur, setComposeur] = useState(null)
  const [message, setMessage] = useState(null)
  const [connexionsAgent, setConnexionsAgent] = useState(null)

  const charger = async () => {
    const [t, a, w] = await Promise.all([
      api.listerTemplates(), api.listerAgents(), api.listerWorkflows(),
    ])
    setTemplates(t)
    setAgents(a)
    setWorkflows(w)
    setWorkflow((actuel) =>
      w.find((traitement) => traitement.id === actuel?.id)
      ?? w.find((traitement) => traitement.est_defaut)
      ?? w[0]
      ?? null
    )
  }

  useEffect(() => {
    charger()
    api.categoriesStudio().then(setCategories).catch(() => {})
  }, [])

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
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold">Studio métier</h2>
        <span className="text-sm text-encre/50">Configurez les modules, contrôles et seuils du parcours</span>
      </div>

      {message && (
        <div className={`mb-4 rounded-md px-4 py-2 text-sm ${
          message.ton === 'succes' ? 'border border-ok/30 bg-ok-tint text-ok' : 'border border-bad/30 bg-bad-tint text-bad'
        }`}>
          {message.texte}
        </div>
      )}

      {/* ---- création depuis un prompt (la vedette) ---- */}
      <CreateurPrompt
        categories={categories}
        onCree={async (nom) => {
          await charger()
          setMessage({ ton: 'succes', texte: `Module « ${nom} » créé — publiez-le pour l'utiliser.` })
        }}
      />

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(280px,1fr)_minmax(0,1.6fr)]">
        {/* templates */}
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-encre/40">
            Agents métier
          </h3>
          <div className="grid gap-3">
            {templates.map((t) => (
              <div key={t.id} className="rounded-lg border border-line bg-surface p-4">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{AGENT_ICONE[t.categorie] ?? '⚙️'}</span>
                  <span className="font-medium">{t.nom}</span>
                  <button onClick={() => setCreation(t)}
                    className="ml-auto rounded-md bg-encre px-3 py-1 text-xs font-semibold text-creme hover:bg-encre/85">
                    Créer
                  </button>
                </div>
                <p className="mt-2 line-clamp-3 text-xs text-encre/50">{t.instructions_defaut}</p>
                {Object.keys(t.garde_fous_defaut ?? {}).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {Object.keys(t.garde_fous_defaut).map((g) => (
                      <span key={g} className="rounded bg-ok-tint px-1.5 py-0.5 text-[10px] font-medium text-ok">🔒 {libelleGardeFou(g)}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="mt-6">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-encre/40">
                Traitements
              </h3>
              <button
                onClick={() => setComposeur({ mode: 'creation', workflow })}
                className="rounded-md bg-encre px-3 py-1 text-xs font-semibold text-creme"
              >
                + Nouveau
              </button>
            </div>
            <div className="grid gap-2">
              {workflows.map((traitement) => (
                <button
                  key={traitement.id}
                  onClick={() => setWorkflow(traitement)}
                  className={`rounded-lg border p-3 text-left ${
                    workflow?.id === traitement.id
                      ? 'border-terracotta bg-terracotta-tint/30'
                      : 'border-line bg-surface'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold">{traitement.nom}</span>
                    {traitement.est_defaut && (
                      <span className="rounded-full bg-ok-tint px-2 py-0.5 text-[10px] font-semibold text-ok">
                        Actif
                      </span>
                    )}
                    <span className="ml-auto text-xs text-encre/40">
                      {traitement.etapes.length} étapes
                    </span>
                  </div>
                  {traitement.description && (
                    <p className="mt-1 text-xs text-encre/50">{traitement.description}</p>
                  )}
                </button>
              ))}
            </div>
            {workflow && (
              <div className="mt-3 rounded-lg border border-line bg-surface p-3">
                <ol className="grid gap-1">
                  {workflow.etapes.map((e, i) => {
                    const a = agents.find((x) => x.id === e.agent_id)
                    return (
                      <li key={`${e.agent_id}-${i}`} className="flex items-center gap-2 text-sm">
                        <span className="w-5 text-right text-xs text-encre/40">{i + 1}.</span>
                        <span>{e.type === 'porte_humaine' ? '🛡️' : AGENT_ICONE[a?.categorie] ?? '⚙️'}</span>
                        <span>{a?.nom}</span>
                        {e.type === 'porte_humaine' && (
                          <span className="rounded bg-warn-tint px-1.5 py-0.5 text-[10px] font-semibold text-warn">
                            obligatoire
                          </span>
                        )}
                      </li>
                    )
                  })}
                </ol>
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => setComposeur({ mode: 'edition', workflow })}
                    className="rounded-md border border-line px-3 py-1.5 text-xs font-semibold text-encre/70"
                  >
                    Modifier les étapes
                  </button>
                  {!workflow.est_defaut && (
                    <button
                      onClick={() => agir(
                        () => api.activerWorkflow(workflow.id),
                        `« ${workflow.nom} » est maintenant le traitement actif.`,
                      )}
                      className="rounded-md bg-terracotta px-3 py-1.5 text-xs font-semibold text-white"
                    >
                      Définir comme actif
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* agents déployés */}
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-encre/40">Modules ({agents.length})</h3>
          <div className="grid gap-2">
            {agents.map((a) => (
              <CarteAgent key={a.id} agent={a} dansPipeline={agentsDuPipeline.has(a.id)}
                onPublier={() => agir(() => api.publierAgent(a.id), `« ${a.nom} » est publié et enregistré dans le journal d'audit.`)}
                onSeuils={(seuils) => agir(() => api.modifierAgent(a.id, { seuils }),
                  `Seuils de « ${a.nom} » mis à jour et enregistrés dans le journal d'audit.`)}
                onInstructions={(instructions) => agir(() => api.modifierAgent(a.id, { instructions }),
                  `Instructions de « ${a.nom} » mises à jour et enregistrées dans le journal d'audit.`)}
                onConnexions={() => setConnexionsAgent(a)}
              />
            ))}
          </div>
        </div>
      </div>

      {connexionsAgent && (
        <PanneauConnexionsMcp
          agent={connexionsAgent}
          onFermer={() => setConnexionsAgent(null)}
          onChange={async (texte) => {
            await charger()
            const maj = agents.find((x) => x.id === connexionsAgent.id)
            if (maj) {
              const fresh = (await api.listerAgents()).find((x) => x.id === connexionsAgent.id)
              if (fresh) setConnexionsAgent(fresh)
            }
            setMessage({ ton: 'succes', texte })
          }}
          onErreur={(texte) => setMessage({ ton: 'erreur', texte })}
        />
      )}

      {creation && (
        <FormulaireTemplate template={creation} onFermer={() => setCreation(null)}
          onCree={async (nom) => {
            setCreation(null)
            await charger()
            setMessage({ ton: 'succes', texte: `Module « ${nom} » créé en brouillon — publiez-le pour l'utiliser.` })
          }} />
      )}
      {composeur && (
        <ComposeurTraitement
          configuration={composeur}
          agents={agents}
          onFermer={() => setComposeur(null)}
          onEnregistre={async (traitement) => {
            setComposeur(null)
            await charger()
            setWorkflow(traitement)
            setMessage({
              ton: 'succes',
              texte: `Traitement « ${traitement.nom} » enregistré.`,
            })
          }}
        />
      )}
    </div>
  )
}

const ORDRE_MODULES = {
  fnol: 0,
  extraction: 1,
  vision: 2,
  garanties: 3,
  indemnite: 4,
  hitl: 5,
  courrier: 6,
}

function ComposeurTraitement({ configuration, agents, onFermer, onEnregistre }) {
  const creation = configuration.mode === 'creation'
  const base = configuration.workflow
  const [nom, setNom] = useState(creation ? '' : base.nom)
  const [description, setDescription] = useState(creation ? '' : base.description ?? '')
  const [agentIds, setAgentIds] = useState(() =>
    (base?.etapes ?? []).map((etape) => etape.agent_id)
  )
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState(null)

  const publies = agents.filter(
    (agent) => agent.statut === 'live' && ORDRE_MODULES[agent.categorie] !== undefined
  )
  const selectionnes = agentIds
    .map((id) => agents.find((agent) => agent.id === id))
    .filter(Boolean)
  const disponibles = publies.filter((agent) => !agentIds.includes(agent.id))

  const ajouter = (agent) => {
    const suivants = [...agentIds, agent.id]
    suivants.sort((a, b) => {
      const moduleA = agents.find((module) => module.id === a)
      const moduleB = agents.find((module) => module.id === b)
      return ORDRE_MODULES[moduleA.categorie] - ORDRE_MODULES[moduleB.categorie]
    })
    setAgentIds(suivants)
  }

  const deplacer = (index, direction) => {
    const cible = index + direction
    if (cible < 0 || cible >= agentIds.length) return
    const suivants = [...agentIds]
    ;[suivants[index], suivants[cible]] = [suivants[cible], suivants[index]]
    setAgentIds(suivants)
  }

  const enregistrer = async () => {
    setEnvoi(true)
    setErreur(null)
    try {
      const traitement = creation
        ? await api.creerWorkflow({ nom, description, agent_ids: agentIds })
        : await api.modifierEtapesWorkflow(base.id, agentIds)
      onEnregistre(traitement)
    } catch (e) {
      setErreur(e.message)
      setEnvoi(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-encre/55 p-4" onClick={onFermer}>
      <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-xl bg-surface p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start gap-3">
          <div>
            <h3 className="text-lg font-semibold">
              {creation ? 'Nouveau traitement' : `Modifier « ${base.nom} »`}
            </h3>
            <p className="mt-1 text-sm text-encre/50">
              Assemblez les modules puis vérifiez leur ordre d’exécution.
            </p>
          </div>
          <button onClick={onFermer} className="ml-auto text-xl text-encre/40">×</button>
        </div>

        {creation && (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <label className="text-sm">
              <span className="text-xs uppercase tracking-wide text-encre/40">Nom du traitement</span>
              <input value={nom} onChange={(e) => setNom(e.target.value)}
                placeholder="ex. Collision avec expertise renforcée"
                className="mt-1 w-full rounded-md border border-line bg-creme p-2.5" />
            </label>
            <label className="text-sm">
              <span className="text-xs uppercase tracking-wide text-encre/40">Description</span>
              <input value={description} onChange={(e) => setDescription(e.target.value)}
                placeholder="Objet et périmètre du traitement"
                className="mt-1 w-full rounded-md border border-line bg-creme p-2.5" />
            </label>
          </div>
        )}

        <div className="mt-5 grid gap-5 md:grid-cols-2">
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-encre/40">
              Étapes du traitement
            </h4>
            <ol className="grid gap-2">
              {selectionnes.map((agent, index) => {
                const obligatoire = agent.categorie === 'hitl'
                return (
                  <li key={agent.id} className="flex items-center gap-2 rounded-lg border border-line bg-creme p-2.5">
                    <span className="w-5 text-right text-xs text-encre/40">{index + 1}</span>
                    <span>{AGENT_ICONE[agent.categorie] ?? '⚙️'}</span>
                    <span className="min-w-0 flex-1 truncate text-sm font-medium">{agent.nom}</span>
                    {obligatoire && (
                      <span className="rounded bg-warn-tint px-1.5 py-0.5 text-[10px] font-semibold text-warn">
                        obligatoire
                      </span>
                    )}
                    <button onClick={() => deplacer(index, -1)} disabled={index === 0}
                      className="px-1 text-encre/45 disabled:opacity-20" title="Monter">↑</button>
                    <button onClick={() => deplacer(index, 1)} disabled={index === selectionnes.length - 1}
                      className="px-1 text-encre/45 disabled:opacity-20" title="Descendre">↓</button>
                    {!obligatoire && (
                      <button onClick={() => setAgentIds(agentIds.filter((id) => id !== agent.id))}
                        className="px-1 text-bad" title="Retirer">×</button>
                    )}
                  </li>
                )
              })}
            </ol>
          </div>

          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-encre/40">
              Modules disponibles
            </h4>
            <div className="grid gap-2">
              {disponibles.map((agent) => (
                <div key={agent.id} className="flex items-center gap-2 rounded-lg bg-surface-deep p-2.5">
                  <span>{AGENT_ICONE[agent.categorie] ?? '⚙️'}</span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{agent.nom}</div>
                    <div className="text-xs text-encre/40">{agent.categorie.replace('_', ' ')}</div>
                  </div>
                  <button onClick={() => ajouter(agent)}
                    className="rounded-md border border-line bg-surface px-2.5 py-1 text-xs font-semibold">
                    Ajouter
                  </button>
                </div>
              ))}
              {disponibles.length === 0 && (
                <p className="rounded-lg bg-surface-deep p-3 text-sm text-encre/45">
                  Tous les modules publiés sont utilisés.
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-md bg-warn-tint px-3 py-2 text-xs text-warn">
          La validation gestionnaire est obligatoire avant tout règlement.
        </div>
        {erreur && <p className="mt-3 text-sm text-bad">{erreur}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onFermer} className="rounded-md px-4 py-2 text-sm text-encre/55">
            Annuler
          </button>
          <button onClick={enregistrer}
            disabled={envoi || (creation && !nom.trim())}
            className="rounded-md bg-encre px-4 py-2 text-sm font-semibold text-creme disabled:opacity-50">
            {envoi ? 'Enregistrement…' : 'Enregistrer le traitement'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ============ créateur d'agent depuis un prompt (assisté IA) ============ */

// Rôles qui correspondent à une étape réelle du pipeline P5 : un agent créé
// dans l'un de ces rôles peut être publié PUIS ajouté au pipeline — il vient
// s'insérer comme une étape SUPPLÉMENTAIRE, juste après l'étape de même
// catégorie ; il ne remplace jamais l'agent déjà en place. "assistant" n'a
// aucune étape correspondante — volontairement hors pipeline (voir CLAUDE.md
// §3 : pas de nouvelle étape métier improvisée depuis un prompt).
const ROLES_BRANCHABLES = new Set(['fnol', 'extraction', 'vision', 'courrier'])
const EXEMPLE_BRIEF = 'Contrôle de cohérence entre la déclaration et les photos'

function CreateurPrompt({ categories, onCree }) {
  const [brief, setBrief] = useState(EXEMPLE_BRIEF)
  const [nom, setNom] = useState('')
  const [categorie, setCategorie] = useState('vision')
  const [instructions, setInstructions] = useState('')
  const [genere, setGenere] = useState(false)
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState(null)

  const generer = async () => {
    if (!brief.trim()) return
    setGenere(true)
    setErreur(null)
    try {
      const r = await api.genererInstructions(brief)
      setInstructions(r.instructions)
      if (!nom) setNom(brief.trim().charAt(0).toUpperCase() + brief.trim().slice(1, 40))
    } catch (e) {
      setErreur(e.message)
    } finally {
      setGenere(false)
    }
  }

  const creer = async () => {
    setEnvoi(true)
    setErreur(null)
    try {
      const a = await api.creerAgentPersonnalise({ nom, categorie, instructions })
      onCree(a.nom)
      setBrief(EXEMPLE_BRIEF); setNom(''); setInstructions('')
    } catch (e) {
      setErreur(e.message)
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <div className="rounded-xl border-2 border-terracotta/30 bg-terracotta-tint/40 p-5">
      <div className="flex items-center gap-2">
        <span className="text-lg text-terracotta">✦</span>
        <h3 className="font-semibold">Créer un module sur mesure</h3>
        <span className="text-xs text-encre/50">Décrivez le contrôle ou le traitement attendu</span>
      </div>

      <div className="mt-3 flex flex-col gap-2 md:flex-row">
        <input
          value={brief}
          onChange={(e) => setBrief(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && generer()}
          placeholder="ex. contrôler la cohérence entre la déclaration et les photos"
          className="flex-1 rounded-md border border-line bg-surface p-2.5 text-sm focus:border-terracotta focus:outline-none"
        />
        <button
          onClick={generer}
          disabled={!brief.trim() || genere}
          className="whitespace-nowrap rounded-md bg-terracotta px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-terracotta-deep disabled:opacity-50"
        >
          {genere ? 'Préparation…' : 'Préparer les instructions'}
        </button>
      </div>

      {instructions && (
        <div className="mt-3 grid gap-3 rounded-lg border border-line bg-surface p-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-encre/40">Instructions proposées</span>
            <span className="text-[11px] text-encre/40">modifiables avant création</span>
          </div>
          <textarea
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            rows={7}
            className="w-full rounded-md border border-line bg-creme p-3 text-sm leading-relaxed focus:border-terracotta focus:outline-none"
          />
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex-1 text-sm">
              <span className="text-xs uppercase tracking-wide text-encre/40">Nom du module</span>
              <input value={nom} onChange={(e) => setNom(e.target.value)}
                className="mt-1 w-full rounded-md border border-line bg-creme p-2 text-sm" />
            </label>
            <label className="text-sm">
              <span className="text-xs uppercase tracking-wide text-encre/40">Rôle dans la plateforme</span>
              <select value={categorie} onChange={(e) => setCategorie(e.target.value)}
                className="mt-1 block w-64 rounded-md border border-line bg-creme p-2 text-sm">
                {Object.entries(categories).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </label>
            <button onClick={creer} disabled={!nom || !instructions || envoi}
              className="rounded-md bg-encre px-4 py-2 text-sm font-semibold text-creme hover:bg-encre/85 disabled:opacity-50">
              {envoi ? 'Création…' : 'Créer en brouillon'}
            </button>
          </div>
          {ROLES_BRANCHABLES.has(categorie) ? (
            <p className="text-xs text-encre/50">
              Une fois publié, ce module pourra être ajouté au parcours sinistre.
            </p>
          ) : (
            <p className="text-xs text-encre/50">
              Ce rôle reste indépendant du parcours sinistre.
            </p>
          )}
          <div className="rounded-md bg-ok-tint px-3 py-2 text-xs text-ok">
            Toute décision de règlement requiert une validation gestionnaire.
          </div>
        </div>
      )}
      {erreur && <p className="mt-2 text-sm text-bad">{erreur}</p>}
    </div>
  )
}

/* ============ carte d'un agent déployé ============ */

function CarteAgent({ agent: a, dansPipeline, onPublier, onSeuils, onInstructions, onConnexions }) {
  const [editionSeuil, setEditionSeuil] = useState(false)
  const [editionInstructions, setEditionInstructions] = useState(false)
  const [seuil, setSeuil] = useState(a.seuils?.seuil_validation ?? '')
  const [instructions, setInstructions] = useState(a.instructions)
  const aDesSeuils = a.seuils && Object.keys(a.seuils).length > 0
  const perso = a.garde_fous?.origine === 'prompt_studio'
  const marketplace = a.garde_fous?.origine === 'marketplace'
  const outils = a.garde_fous?.outils_autorises ?? OUTILS_PAR_CATEGORIE[a.categorie] ?? []
  const connexions = Object.keys(a.garde_fous?.connexions_mcp ?? {})

  return (
    <div className={`rounded-lg border bg-surface px-4 py-3 ${perso || marketplace ? 'border-terracotta/40' : 'border-line'}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span>{AGENT_ICONE[a.categorie] ?? '⚙️'}</span>
        <span className="text-sm font-semibold">{a.nom}</span>
        <span className="text-xs text-encre/40">v{a.version}</span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
          a.statut === 'live' ? 'bg-ok-tint text-ok' : 'bg-surface-deep text-encre/60'
        }`}>{a.statut === 'live' ? 'Publié' : 'Brouillon'}</span>
        {perso && <span className="rounded-full bg-terracotta-tint px-2 py-0.5 text-xs font-medium text-terracotta-deep">Personnalisé</span>}
        {marketplace && (
          <span className="rounded-full bg-terracotta-tint px-2 py-0.5 text-xs font-medium text-terracotta-deep">
            Marketplace · {a.garde_fous.editeur}
          </span>
        )}
        {dansPipeline && <span className="rounded-full bg-surface-deep px-2 py-0.5 text-xs font-medium text-encre/70">Dans le parcours</span>}
        {connexions.length > 0 && (
          <span className="rounded-full bg-surface-deep px-2 py-0.5 text-[10px] font-semibold text-encre/60">
            {connexions.length} app{connexions.length > 1 ? 's' : ''}
          </span>
        )}
        {a.garde_fous?.non_desactivable && (
          <span className="rounded bg-bad-tint px-1.5 py-0.5 text-[10px] font-semibold text-bad">🔒 Obligatoire</span>
        )}
        <div className="ml-auto flex gap-2">
          {a.statut === 'draft' && (
            <button onClick={onPublier} className="rounded-md bg-terracotta px-3 py-1 text-xs font-semibold text-white hover:bg-terracotta-deep">
              Publier
            </button>
          )}
          <button onClick={onConnexions}
            className="rounded-md border border-line px-3 py-1 text-xs font-semibold text-encre/60 hover:bg-surface-deep">
            Connexions
          </button>
          <button onClick={() => setEditionInstructions(!editionInstructions)}
            className="rounded-md border border-line px-3 py-1 text-xs font-semibold text-encre/60 hover:bg-surface-deep">
            ✎ Instructions
          </button>
          {aDesSeuils && (
            <button onClick={() => setEditionSeuil(!editionSeuil)}
              className="rounded-md border border-line px-3 py-1 text-xs font-semibold text-encre/60 hover:bg-surface-deep">
              Seuils
            </button>
          )}
        </div>
      </div>
      {connexions.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-encre/50">
          <span className="font-semibold">Apps :</span>
          {connexions.map((slug) => (
            <span key={slug} className="rounded bg-surface-deep px-2 py-0.5 capitalize text-encre/70">
              {slug.replaceAll('_', ' ')}
            </span>
          ))}
        </div>
      )}
      {outils.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-encre/50">
          <span className="font-semibold">Sources consultées :</span>
          {outils.map((outil) => (
            <span key={outil} className="rounded bg-terracotta-tint px-2 py-0.5 text-terracotta-deep">
              {LIBELLES_OUTILS[outil] ?? outil}
            </span>
          ))}
          <span className="text-encre/35">consultation seule</span>
        </div>
      )}
      {aDesSeuils && !editionSeuil && (
        <div className="mt-1.5 text-xs text-encre/50">
          seuil de validation obligatoire : <b>{a.seuils.seuil_validation} DT</b>
          {a.seuils.plafond_auto != null && <> · plafond auto : <b>{a.seuils.plafond_auto} DT</b></>}
        </div>
      )}
      {editionSeuil && (
        <div className="mt-2 flex flex-wrap items-end gap-2 rounded-md bg-surface-deep p-2">
          <label className="text-xs">
            <span className="uppercase tracking-wide text-encre/40">Seuil de validation (DT)</span>
            <input type="number" value={seuil} onChange={(e) => setSeuil(e.target.value)}
              className="mt-1 block w-32 rounded border border-line bg-creme p-1.5 text-sm" />
          </label>
          <button onClick={() => { onSeuils({ ...a.seuils, seuil_validation: Number(seuil) }); setEditionSeuil(false) }}
            className="rounded-md bg-encre px-3 py-1.5 text-xs font-semibold text-creme">
            Enregistrer (v{a.version + 1})
          </button>
          <span className="pb-1 text-[10px] text-encre/40">Modification enregistrée dans le journal d'audit</span>
        </div>
      )}
      {editionInstructions && (
        <div className="mt-2 grid gap-2 rounded-md bg-surface-deep p-2">
          <span className="text-xs uppercase tracking-wide text-encre/40">
            Instructions de « {a.nom} » — modification du module existant
          </span>
          <textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} rows={4}
            className="w-full rounded border border-line bg-creme p-2 text-sm" />
          <div className="flex items-center gap-2">
            <button onClick={() => { onInstructions(instructions); setEditionInstructions(false) }}
              className="rounded-md bg-encre px-3 py-1.5 text-xs font-semibold text-creme">
              Enregistrer (v{a.version + 1})
            </button>
            <button onClick={() => { setInstructions(a.instructions); setEditionInstructions(false) }}
              className="rounded-md px-3 py-1.5 text-xs text-encre/50 hover:bg-line">
              Annuler
            </button>
            <span className="text-[10px] text-encre/40">Nouvelle version enregistrée dans le journal d'audit</span>
          </div>
        </div>
      )}
    </div>
  )
}

/* ============ création depuis un template (modal) ============ */

function FormulaireTemplate({ template, onFermer, onCree }) {
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
        nom, template_id: template.id, instructions,
        seuils: estIndemnite && seuil ? { seuil_validation: Number(seuil) } : {},
      })
      onCree(nom)
    } catch (e) {
      setErreur(e.message)
      setEnvoi(false)
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-encre/50 p-4" onClick={onFermer}>
      <div className="w-full max-w-xl rounded-xl bg-surface p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold">Nouveau module — {template.nom}</h3>
        <label className="mt-4 block text-sm">
          <span className="text-xs uppercase tracking-wide text-encre/40">Nom du module</span>
          <input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="ex. Règlement auto — bris de glace"
            className="mt-1 w-full rounded-md border border-line bg-creme p-2 text-sm" />
        </label>
        <label className="mt-3 block text-sm">
          <span className="text-xs uppercase tracking-wide text-encre/40">Instructions</span>
          <textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} rows={4}
            className="mt-1 w-full rounded-md border border-line bg-creme p-2 text-sm" />
        </label>
        {estIndemnite && (
          <label className="mt-3 block text-sm">
            <span className="text-xs uppercase tracking-wide text-encre/40">Seuil de validation humaine (DT)</span>
            <input type="number" value={seuil} onChange={(e) => setSeuil(e.target.value)}
              className="mt-1 w-40 rounded-md border border-line bg-creme p-2 text-sm" />
          </label>
        )}
        <div className="mt-3 rounded-md bg-ok-tint p-2 text-xs text-ok">
          Contrôles de l’agent :{' '}
          {Object.keys(template.garde_fous_defaut ?? {}).map(libelleGardeFou).join(', ') || 'aucun'}
        </div>
        {erreur && <p className="mt-2 text-sm text-bad">{erreur}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onFermer} className="rounded-md px-4 py-2 text-sm text-encre/60 hover:bg-surface-deep">Annuler</button>
          <button onClick={soumettre} disabled={!nom || envoi}
            className="rounded-md bg-encre px-4 py-2 text-sm font-semibold text-creme hover:bg-encre/85 disabled:opacity-50">
            {envoi ? 'Création…' : 'Créer en brouillon'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ============ connexions MCP par agent (style console Anthropic) ============ */

function PanneauConnexionsMcp({ agent, onFermer, onChange, onErreur }) {
  const [plateformes, setPlateformes] = useState([])
  const [chargement, setChargement] = useState(true)
  const [action, setAction] = useState(null)

  const charger = async () => {
    setChargement(true)
    try {
      const data = await api.listerConnexionsAgent(agent.id)
      setPlateformes(data.plateformes)
    } catch (e) {
      onErreur(e.message)
    } finally {
      setChargement(false)
    }
  }

  useEffect(() => {
    charger()
  }, [agent.id])

  const basculer = async (slug, connecte) => {
    setAction(slug)
    try {
      if (connecte) {
        await api.deconnecterPlateformeAgent(agent.id, slug)
        await onChange(`Déconnecté de ${slug.replaceAll('_', ' ')}`)
      } else {
        const res = await api.connecterPlateformeAgent(agent.id, slug)
        await onChange(
          `Connecté à ${slug.replaceAll('_', ' ')} (${res.connexion.compte})`
        )
      }
      await charger()
    } catch (e) {
      onErreur(e.message)
    } finally {
      setAction(null)
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-encre/45 p-4" onClick={onFermer}>
      <div
        className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-surface shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold">Connexions — {agent.nom}</h3>
            </div>
            <p className="mt-1 text-xs leading-5 text-encre/45">
              Activez les apps que cet agent peut utiliser.
            </p>
          </div>
          <button type="button" onClick={onFermer} className="text-encre/40 hover:text-encre">×</button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {chargement ? (
            <p className="px-4 py-10 text-center text-sm text-encre/40">Chargement…</p>
          ) : (
            <ul className="divide-y divide-line">
              {plateformes.map((p) => (
                <li key={p.slug} className="flex items-center gap-3 px-4 py-3.5">
                  <BrandMark slug={p.slug} size={40} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold">{p.nom}</span>
                      <span className="text-[11px] text-encre/40">{p.editeur}</span>
                      {p.connecte && (
                        <span className="rounded-full bg-ok-tint px-2 py-0.5 text-[10px] font-semibold text-ok">
                          Connecté
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-encre/45">{p.description}</p>
                    <p className="mt-1 text-[11px] text-encre/35">
                      {p.connecte
                        ? `${p.connexion.compte} · ${p.connexion.tools.join(' · ')}`
                        : p.tools.join(' · ')}
                    </p>
                  </div>
                  <button
                    type="button"
                    disabled={action !== null}
                    onClick={() => basculer(p.slug, p.connecte)}
                    className={`shrink-0 rounded-md px-3 py-1.5 text-xs font-semibold disabled:opacity-50 ${
                      p.connecte
                        ? 'border border-line text-encre/60 hover:bg-surface-deep'
                        : 'bg-encre text-creme hover:bg-encre/85'
                    }`}
                  >
                    {action === p.slug ? '…' : p.connecte ? 'Déconnecter' : 'Se connecter'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
