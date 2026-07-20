import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { AGENT_ICONE, dt } from '../ui'

const CATEGORIES = ['Tous', 'Auto', 'Vision', 'Documents', 'Conformité']
const CATEGORIES_BIENTOT = ['Habitation', 'Santé', 'Vie']

export default function Marketplace({ onNavigate }) {
  const [agents, setAgents] = useState([])
  const [recherche, setRecherche] = useState('')
  const [categorie, setCategorie] = useState('Tous')
  const [achat, setAchat] = useState(null)
  const [message, setMessage] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [action, setAction] = useState(false)

  const charger = async () => {
    try {
      setAgents(await api.listerMarketplace())
    } catch (erreur) {
      setMessage({ ton: 'erreur', texte: erreur.message })
    } finally {
      setChargement(false)
    }
  }

  useEffect(() => { charger() }, [])

  const resultats = useMemo(() => {
    const terme = recherche.trim().toLocaleLowerCase('fr')
    return agents.filter((agent) => {
      const correspondCategorie = categorie === 'Tous' || agent.tags.includes(categorie)
      const contenu = `${agent.nom} ${agent.editeur} ${agent.description} ${agent.tags.join(' ')}`.toLocaleLowerCase('fr')
      return correspondCategorie && (!terme || contenu.includes(terme))
    })
  }, [agents, categorie, recherche])

  const confirmerAchat = async () => {
    setAction(true)
    try {
      const resultat = await api.installerMarketplace(achat.id)
      setAchat(null)
      await charger()
      setMessage({
        ton: 'succes',
        texte: `« ${resultat.agent.nom} » est maintenant live et prêt dans votre Studio.`,
        studio: true,
      })
    } catch (erreur) {
      setMessage({ ton: 'erreur', texte: erreur.message })
    } finally {
      setAction(false)
    }
  }

  if (chargement) return <p className="text-sm text-encre/50">Chargement de la Marketplace…</p>

  return (
    <div className="grid gap-6">
      <header className="overflow-hidden rounded-2xl bg-encre px-6 py-7 text-creme">
        <div className="flex flex-wrap items-end gap-5">
          <div className="max-w-2xl">
            <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-terracotta">
              Norix Marketplace
            </div>
            <h2 className="text-2xl font-semibold">Des agents métier prêts à intégrer vos parcours</h2>
            <p className="mt-2 text-sm leading-6 text-creme/60">
              Découvrez des modules spécialisés, évalués par la communauté assurance et compatibles avec le Studio Norix.
            </p>
          </div>
          <a
            href="/#editeur"
            target="_blank"
            rel="noreferrer"
            className="ml-auto rounded-md border border-creme/20 px-4 py-2.5 text-sm font-semibold text-creme/75 transition hover:bg-creme/10"
          >
            Portail éditeurs ↗
          </a>
        </div>
      </header>

      {message && (
        <div className={`flex items-center gap-2 rounded-lg border px-4 py-3 text-sm ${
          message.ton === 'erreur'
            ? 'border-bad/30 bg-bad-tint text-bad'
            : message.ton === 'info'
              ? 'border-line bg-surface-deep text-encre/60'
              : 'border-ok/30 bg-ok-tint text-ok'
        }`}>
          <span>{message.ton === 'erreur' ? '!' : message.ton === 'info' ? 'ℹ' : '✓'}</span>
          <span>{message.texte}</span>
          <div className="ml-auto flex items-center gap-2">
            {message.studio && (
              <button
                onClick={() => onNavigate('studio')}
                className="rounded-md bg-ok px-3 py-1.5 text-xs font-semibold text-white"
              >
                Ouvrir dans le Studio
              </button>
            )}
            <button onClick={() => setMessage(null)} className="text-lg opacity-60" aria-label="Fermer">×</button>
          </div>
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
        <div className="flex flex-wrap gap-1">
          {CATEGORIES_BIENTOT.map((item) => (
            <button
              key={item}
              type="button"
              title="Branche hors périmètre de ce pilote — à venir"
              onClick={() => setMessage({
                ton: 'info',
                texte: `Branche « ${item} » — roadmap, hors périmètre de ce pilote (auto uniquement).`,
              })}
              className="cursor-not-allowed rounded-md border border-dashed border-line px-3 py-1.5 text-xs font-medium text-encre/30"
            >
              {item} · bientôt
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
          const estAchete = agent.installe
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
            <div className="mt-2 flex justify-between text-encre/45"><span>Destination</span><span>Studio Norix</span></div>
          </div>
          <div className="mt-5 flex justify-end gap-2">
            <button onClick={() => setAchat(null)} className="rounded-md border border-line px-4 py-2 text-sm font-medium">Annuler</button>
            <button
              onClick={confirmerAchat}
              disabled={action}
              className="rounded-md bg-terracotta px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {action ? 'Installation…' : achat.prix ? `Acheter et installer — ${dt(achat.prix)}` : 'Installer'}
            </button>
          </div>
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
