import { useMemo, useState } from 'react'
import { AGENT_ICONE, dt } from '../ui'

const AGENTS = [
  {
    id: 1,
    nom: 'Lecture de constat auto',
    categorie: 'extraction',
    editeur: 'North Africa Claims Lab',
    description: 'Extrait les conducteurs, véhicules, circonstances et signatures depuis un constat amiable.',
    prix: 240,
    note: 4.9,
    installations: 128,
    tags: ['Auto', 'Documents'],
    verifie: true,
  },
  {
    id: 2,
    nom: 'Évaluation dégâts carrosserie',
    categorie: 'vision',
    editeur: 'Vision Assur',
    description: 'Classe les dommages visibles et prépare une synthèse exploitable par le gestionnaire.',
    prix: 390,
    note: 4.8,
    installations: 94,
    tags: ['Auto', 'Vision'],
    verifie: true,
  },
  {
    id: 3,
    nom: 'Assistant déclaration FNOL',
    categorie: 'fnol',
    editeur: 'Tunis Digital Insurance',
    description: 'Transforme une déclaration en français ou en darija en dossier sinistre structuré.',
    prix: 180,
    note: 4.7,
    installations: 211,
    tags: ['Auto', 'FNOL'],
    verifie: true,
  },
  {
    id: 4,
    nom: 'Contrôle de complétude',
    categorie: 'assistant',
    editeur: 'OpsFlow',
    description: 'Vérifie les pièces obligatoires et indique clairement les éléments encore manquants.',
    prix: 95,
    note: 4.6,
    installations: 76,
    tags: ['Documents', 'Contrôle'],
    verifie: false,
  },
  {
    id: 5,
    nom: 'Rédaction décision assurée',
    categorie: 'courrier',
    editeur: 'ClearClaim',
    description: 'Rédige un courrier de décision clair à partir des clauses et montants déjà validés.',
    prix: 150,
    note: 4.8,
    installations: 163,
    tags: ['Courrier', 'Conformité'],
    verifie: true,
  },
  {
    id: 6,
    nom: 'Contrôle qualité dossier',
    categorie: 'assistant',
    editeur: 'Argus Community',
    description: 'Relit le dossier avant validation humaine et signale les incohérences de traitement.',
    prix: 0,
    note: 4.5,
    installations: 302,
    tags: ['Qualité', 'Audit'],
    verifie: false,
  },
]

const CATEGORIES = ['Tous', 'Auto', 'Vision', 'Documents', 'Conformité']

export default function Marketplace() {
  const [recherche, setRecherche] = useState('')
  const [categorie, setCategorie] = useState('Tous')
  const [achetes, setAchetes] = useState([])
  const [achat, setAchat] = useState(null)
  const [publication, setPublication] = useState(false)
  const [message, setMessage] = useState(null)

  const resultats = useMemo(() => {
    const terme = recherche.trim().toLocaleLowerCase('fr')
    return AGENTS.filter((agent) => {
      const correspondCategorie = categorie === 'Tous' || agent.tags.includes(categorie)
      const contenu = `${agent.nom} ${agent.editeur} ${agent.description} ${agent.tags.join(' ')}`.toLocaleLowerCase('fr')
      return correspondCategorie && (!terme || contenu.includes(terme))
    })
  }, [categorie, recherche])

  const confirmerAchat = () => {
    setAchetes((liste) => [...liste, achat.id])
    setMessage(`« ${achat.nom} » a été ajouté à votre espace Studio.`)
    setAchat(null)
  }

  return (
    <div className="grid gap-6">
      <header className="overflow-hidden rounded-2xl bg-encre px-6 py-7 text-creme">
        <div className="flex flex-wrap items-end gap-5">
          <div className="max-w-2xl">
            <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-terracotta">
              Argus Marketplace
            </div>
            <h2 className="text-2xl font-semibold">Des agents métier prêts à intégrer vos parcours</h2>
            <p className="mt-2 text-sm leading-6 text-creme/60">
              Découvrez des modules spécialisés, évalués par la communauté assurance et compatibles avec le Studio Argus.
            </p>
          </div>
          <button
            onClick={() => setPublication(true)}
            className="ml-auto rounded-md bg-terracotta px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-terracotta-deep"
          >
            Publier un agent
          </button>
        </div>
      </header>

      {message && (
        <div className="flex items-center gap-2 rounded-lg border border-ok/30 bg-ok-tint px-4 py-3 text-sm text-ok">
          <span>✓</span>
          <span>{message}</span>
          <button onClick={() => setMessage(null)} className="ml-auto text-lg opacity-60" aria-label="Fermer">×</button>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <label className="relative min-w-64 flex-1">
          <span className="pointer-events-none absolute left-3 top-2.5 text-sm text-encre/35">⌕</span>
          <input
            value={recherche}
            onChange={(event) => setRecherche(event.target.value)}
            placeholder="Rechercher un agent, un éditeur…"
            className="w-full rounded-lg border border-line bg-surface py-2 pl-9 pr-3 text-sm outline-none transition focus:border-terracotta"
          />
        </label>
        <div className="flex flex-wrap gap-1 rounded-lg bg-surface-deep p-1">
          {CATEGORIES.map((item) => (
            <button
              key={item}
              onClick={() => setCategorie(item)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                categorie === item ? 'bg-encre text-creme' : 'text-encre/55 hover:bg-surface'
              }`}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-encre/40">
          Agents disponibles
        </h3>
        <span className="text-xs text-encre/40">{resultats.length} résultat{resultats.length > 1 ? 's' : ''}</span>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {resultats.map((agent) => {
          const estAchete = achetes.includes(agent.id)
          return (
            <article key={agent.id} className="flex min-h-72 flex-col rounded-xl border border-line bg-surface p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-surface-deep text-xl">
                  {AGENT_ICONE[agent.categorie] ?? '✦'}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <h4 className="truncate font-semibold">{agent.nom}</h4>
                    {agent.verifie && <span className="text-xs text-ok" title="Éditeur vérifié">●</span>}
                  </div>
                  <p className="text-xs text-encre/45">par {agent.editeur}</p>
                </div>
              </div>

              <p className="mt-4 text-sm leading-5 text-encre/60">{agent.description}</p>

              <div className="mt-3 flex flex-wrap gap-1.5">
                {agent.tags.map((tag) => (
                  <span key={tag} className="rounded-full bg-surface-deep px-2.5 py-1 text-[10px] font-medium text-encre/55">
                    {tag}
                  </span>
                ))}
              </div>

              <div className="mt-auto flex items-end gap-3 border-t border-line pt-4">
                <div>
                  <div className="text-xs text-encre/40">★ {agent.note} · {agent.installations} installations</div>
                  <div className="mt-1 font-semibold">{agent.prix ? dt(agent.prix) : 'Gratuit'}</div>
                </div>
                <button
                  onClick={() => !estAchete && setAchat(agent)}
                  disabled={estAchete}
                  className={`ml-auto rounded-md px-3 py-2 text-xs font-semibold transition ${
                    estAchete
                      ? 'cursor-default bg-ok-tint text-ok'
                      : 'bg-encre text-creme hover:bg-encre/85'
                  }`}
                >
                  {estAchete ? '✓ Dans mon Studio' : agent.prix ? 'Acheter' : 'Installer'}
                </button>
              </div>
            </article>
          )
        })}
      </section>

      {resultats.length === 0 && (
        <div className="rounded-xl border border-dashed border-line py-14 text-center text-sm text-encre/45">
          Aucun agent ne correspond à votre recherche.
        </div>
      )}

      {achat && (
        <Modal onFermer={() => setAchat(null)}>
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-surface-deep text-xl">
              {AGENT_ICONE[achat.categorie] ?? '✦'}
            </div>
            <div>
              <h3 className="font-semibold">{achat.prix ? 'Confirmer l’achat' : 'Installer cet agent'}</h3>
              <p className="text-sm text-encre/50">{achat.nom}</p>
            </div>
          </div>
          <div className="mt-5 rounded-lg bg-surface-deep p-4 text-sm">
            <div className="flex justify-between"><span>Licence d’utilisation</span><b>{achat.prix ? dt(achat.prix) : 'Gratuit'}</b></div>
            <div className="mt-2 flex justify-between text-encre/45"><span>Destination</span><span>Studio Argus</span></div>
          </div>
          <p className="mt-3 text-xs text-encre/40">Cette action est simulée dans l’environnement de démonstration.</p>
          <div className="mt-5 flex justify-end gap-2">
            <button onClick={() => setAchat(null)} className="rounded-md border border-line px-4 py-2 text-sm font-medium">Annuler</button>
            <button onClick={confirmerAchat} className="rounded-md bg-terracotta px-4 py-2 text-sm font-semibold text-white">
              {achat.prix ? `Payer ${dt(achat.prix)}` : 'Installer'}
            </button>
          </div>
        </Modal>
      )}

      {publication && (
        <Modal onFermer={() => setPublication(false)}>
          <h3 className="text-lg font-semibold">Publier un agent</h3>
          <p className="mt-1 text-sm text-encre/50">Renseignez les informations visibles dans la marketplace.</p>
          <form
            className="mt-5 grid gap-4"
            onSubmit={(event) => {
              event.preventDefault()
              const donnees = new FormData(event.currentTarget)
              setPublication(false)
              setMessage(`« ${donnees.get('nom')} » a été soumis pour publication.`)
            }}
          >
            <label className="grid gap-1 text-xs font-medium text-encre/60">
              Nom de l’agent
              <input name="nom" required placeholder="Ex. Assistant expertise auto" className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-encre outline-none focus:border-terracotta" />
            </label>
            <label className="grid gap-1 text-xs font-medium text-encre/60">
              Description
              <textarea name="description" required rows="3" placeholder="Décrivez sa valeur métier…" className="resize-none rounded-md border border-line bg-surface px-3 py-2 text-sm text-encre outline-none focus:border-terracotta" />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="grid gap-1 text-xs font-medium text-encre/60">
                Catégorie
                <select name="categorie" className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-encre">
                  <option>Gestion de sinistres</option>
                  <option>Documents</option>
                  <option>Vision</option>
                  <option>Conformité</option>
                </select>
              </label>
              <label className="grid gap-1 text-xs font-medium text-encre/60">
                Prix de la licence (DT)
                <input name="prix" type="number" min="0" defaultValue="0" className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-encre outline-none focus:border-terracotta" />
              </label>
            </div>
            <div className="mt-1 flex justify-end gap-2">
              <button type="button" onClick={() => setPublication(false)} className="rounded-md border border-line px-4 py-2 text-sm font-medium">Annuler</button>
              <button type="submit" className="rounded-md bg-terracotta px-4 py-2 text-sm font-semibold text-white">Soumettre</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

function Modal({ children, onFermer }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-encre/55 p-4" onMouseDown={onFermer}>
      <div
        role="dialog"
        aria-modal="true"
        className="w-full max-w-lg rounded-xl border border-line bg-surface p-6 shadow-2xl"
        onMouseDown={(event) => event.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}
