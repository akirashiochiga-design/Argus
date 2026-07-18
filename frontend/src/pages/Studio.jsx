import { useEffect, useState } from 'react'
import { api } from '../api'
import { AGENT_ICONE, BadgeMode } from '../ui'

export default function Studio() {
  const [templates, setTemplates] = useState([])
  const [agents, setAgents] = useState([])
  const [workflow, setWorkflow] = useState(null)
  const [categories, setCategories] = useState({})
  const [creation, setCreation] = useState(null) // template pour le formulaire modal
  const [message, setMessage] = useState(null)

  const charger = async () => {
    const [t, a, w] = await Promise.all([
      api.listerTemplates(), api.listerAgents(), api.listerWorkflows(),
    ])
    setTemplates(t)
    setAgents(a)
    setWorkflow(w[0] ?? null)
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
        <h2 className="text-lg font-semibold">Studio d'agents</h2>
        <span className="text-sm text-encre/50">décris un agent, il se construit — sans code, gouvernance incluse</span>
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
          setMessage({ ton: 'succes', texte: `Agent « ${nom} » créé depuis votre description — publiez-le pour l'utiliser.` })
        }}
      />

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(280px,1fr)_minmax(0,1.6fr)]">
        {/* templates */}
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-encre/40">
            Ou partez d'un template métier
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
                      <span key={g} className="rounded bg-ok-tint px-1.5 py-0.5 text-[10px] font-medium text-ok">🔒 {g}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {workflow && (
            <div className="mt-6">
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-encre/40">
                Pipeline live — {workflow.nom}
              </h3>
              <ol className="grid gap-1 rounded-lg border border-line bg-surface p-3">
                {workflow.etapes.map((e, i) => {
                  const a = agents.find((x) => x.id === e.agent_id)
                  return (
                    <li key={i} className="flex items-center gap-2 text-sm">
                      <span className="w-5 text-right text-xs text-encre/40">{i + 1}.</span>
                      <span>{e.type === 'porte_humaine' ? '🛡️' : AGENT_ICONE[a?.categorie] ?? '⚙️'}</span>
                      <span>{a?.nom}</span>
                      <span className="text-xs text-encre/40">v{a?.version}</span>
                      {e.type === 'porte_humaine' && (
                        <span className="rounded bg-warn-tint px-1.5 py-0.5 text-[10px] font-semibold text-warn">porte humaine</span>
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
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-encre/40">Agents ({agents.length})</h3>
          <div className="grid gap-2">
            {agents.map((a) => (
              <CarteAgent key={a.id} agent={a} dansPipeline={agentsDuPipeline.has(a.id)}
                onPublier={() => agir(() => api.publierAgent(a.id), `« ${a.nom} » est maintenant live (tracé dans l'audit).`)}
                onBrancher={() => agir(() => api.affecterAgent(workflow.id, a.id),
                  `« ${a.nom} » est branché dans le pipeline P5 — effectif immédiatement.`)}
                onSeuils={(seuils) => agir(() => api.modifierAgent(a.id, { seuils }),
                  `Seuils de « ${a.nom} » mis à jour → nouvelle version, tracée dans l'audit.`)}
              />
            ))}
          </div>
        </div>
      </div>

      {creation && (
        <FormulaireTemplate template={creation} onFermer={() => setCreation(null)}
          onCree={async (nom) => {
            setCreation(null)
            await charger()
            setMessage({ ton: 'succes', texte: `Agent « ${nom} » créé en brouillon — publiez-le pour l'utiliser.` })
          }} />
      )}
    </div>
  )
}

/* ============ créateur d'agent depuis un prompt (assisté IA) ============ */

// Rôles qui correspondent à une étape réelle du pipeline P5 : un agent créé
// dans l'un de ces rôles peut être publié PUIS branché, et remplace alors
// vraiment l'agent de cette étape à la prochaine exécution. "assistant" n'a
// aucune étape correspondante — volontairement hors pipeline (voir CLAUDE.md
// §3 : pas de nouvelle étape métier improvisée depuis un prompt).
const ROLES_BRANCHABLES = new Set(['fnol', 'extraction', 'vision', 'courrier'])

function CreateurPrompt({ categories, onCree }) {
  const [brief, setBrief] = useState('')
  const [nom, setNom] = useState('')
  const [categorie, setCategorie] = useState('vision')
  const [instructions, setInstructions] = useState('')
  const [mode, setMode] = useState(null) // 'llm' | 'simulation'
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
      setMode(r.mode)
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
      setBrief(''); setNom(''); setInstructions(''); setMode(null)
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
        <h3 className="font-semibold">Créer un agent personnalisé</h3>
        <span className="text-xs text-encre/50">décrivez ce que l'agent doit faire, l'IA rédige la consigne</span>
      </div>

      <div className="mt-3 flex flex-col gap-2 md:flex-row">
        <input
          value={brief}
          onChange={(e) => setBrief(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && generer()}
          placeholder="ex. un agent qui détecte les incohérences entre la déclaration et les photos"
          className="flex-1 rounded-md border border-line bg-surface p-2.5 text-sm focus:border-terracotta focus:outline-none"
        />
        <button
          onClick={generer}
          disabled={!brief.trim() || genere}
          className="whitespace-nowrap rounded-md bg-terracotta px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-terracotta-deep disabled:opacity-50"
        >
          {genere ? '✦ Génération…' : '✦ Générer les instructions'}
        </button>
      </div>

      {instructions && (
        <div className="mt-3 grid gap-3 rounded-lg border border-line bg-surface p-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-encre/40">Instructions proposées</span>
            <BadgeMode mode={mode} />
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
              <span className="text-xs uppercase tracking-wide text-encre/40">Nom de l'agent</span>
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
              {envoi ? 'Création…' : "Créer l'agent (draft)"}
            </button>
          </div>
          {ROLES_BRANCHABLES.has(categorie) ? (
            <p className="text-xs text-encre/50">
              ✓ Une fois publié, ce rôle peut être <b>branché au pipeline</b> — il remplacera alors
              vraiment l'agent de cette étape à la prochaine exécution.
            </p>
          ) : (
            <p className="text-xs text-encre/50">
              ℹ️ Rôle libre, <b>hors pipeline P5</b> : cet agent sera créé et visible ici, mais n'aura
              pas de bouton « Brancher » et ne s'exécutera jamais dans le parcours du dossier.
            </p>
          )}
          <div className="rounded-md bg-ok-tint px-3 py-2 text-xs text-ok">
            🔒 Garde-fou imposé : cet agent ne peut ni décider d'un montant, ni contourner la validation
            humaine — quelle que soit la consigne saisie. Les rôles « garanties », « indemnité » et la porte
            de validation ne sont pas créables depuis un prompt.
          </div>
        </div>
      )}
      {erreur && <p className="mt-2 text-sm text-bad">{erreur}</p>}
    </div>
  )
}

/* ============ carte d'un agent déployé ============ */

function CarteAgent({ agent: a, dansPipeline, onPublier, onBrancher, onSeuils }) {
  const [editionSeuil, setEditionSeuil] = useState(false)
  const [seuil, setSeuil] = useState(a.seuils?.seuil_validation ?? '')
  const aDesSeuils = a.seuils && Object.keys(a.seuils).length > 0
  const perso = a.garde_fous?.origine === 'prompt_studio'

  return (
    <div className={`rounded-lg border bg-surface px-4 py-3 ${perso ? 'border-terracotta/40' : 'border-line'}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span>{AGENT_ICONE[a.categorie] ?? '⚙️'}</span>
        <span className="text-sm font-semibold">{a.nom}</span>
        <span className="text-xs text-encre/40">v{a.version}</span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
          a.statut === 'live' ? 'bg-ok-tint text-ok' : 'bg-surface-deep text-encre/60'
        }`}>{a.statut}</span>
        {perso && <span className="rounded-full bg-terracotta-tint px-2 py-0.5 text-xs font-medium text-terracotta-deep">✦ perso</span>}
        {dansPipeline && <span className="rounded-full bg-surface-deep px-2 py-0.5 text-xs font-medium text-encre/70">dans le pipeline</span>}
        {a.garde_fous?.deterministe && (
          <span className="rounded bg-ok-tint px-1.5 py-0.5 text-[10px] font-semibold text-ok">déterministe — pas de LLM</span>
        )}
        {a.garde_fous?.non_desactivable && (
          <span className="rounded bg-bad-tint px-1.5 py-0.5 text-[10px] font-semibold text-bad">🔒 non désactivable</span>
        )}
        <div className="ml-auto flex gap-2">
          {a.statut === 'draft' && (
            <button onClick={onPublier} className="rounded-md bg-terracotta px-3 py-1 text-xs font-semibold text-white hover:bg-terracotta-deep">
              Publier
            </button>
          )}
          {a.statut === 'live' && !dansPipeline && ['fnol', 'extraction', 'vision', 'garanties', 'indemnite', 'courrier'].includes(a.categorie) && (
            <button onClick={onBrancher} className="rounded-md border border-line px-3 py-1 text-xs font-semibold text-encre/70 hover:bg-surface-deep">
              Brancher au pipeline
            </button>
          )}
          {aDesSeuils && (
            <button onClick={() => setEditionSeuil(!editionSeuil)}
              className="rounded-md border border-line px-3 py-1 text-xs font-semibold text-encre/60 hover:bg-surface-deep">
              Seuils
            </button>
          )}
        </div>
      </div>
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
          <span className="pb-1 text-[10px] text-encre/40">changement de gouvernance → versionné + audité</span>
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
        <h3 className="text-lg font-semibold">Nouvel agent — {template.nom}</h3>
        <label className="mt-4 block text-sm">
          <span className="text-xs uppercase tracking-wide text-encre/40">Nom de l'agent</span>
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
          🔒 Garde-fous hérités du template (non désactivables) :{' '}
          {Object.keys(template.garde_fous_defaut ?? {}).join(', ') || 'aucun'}
        </div>
        {erreur && <p className="mt-2 text-sm text-bad">{erreur}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onFermer} className="rounded-md px-4 py-2 text-sm text-encre/60 hover:bg-surface-deep">Annuler</button>
          <button onClick={soumettre} disabled={!nom || envoi}
            className="rounded-md bg-encre px-4 py-2 text-sm font-semibold text-creme hover:bg-encre/85 disabled:opacity-50">
            {envoi ? 'Création…' : "Créer l'agent (draft)"}
          </button>
        </div>
      </div>
    </div>
  )
}
