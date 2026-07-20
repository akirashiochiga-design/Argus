import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { deconnecterEditeur, lireSessionEditeur } from '../session'
import { AGENT_ICONE, dt, Logo, Wordmark } from '../ui'
import LoginEditeur from './LoginEditeur'

const TEMPLATE_DEMO = {
  nom: "Synthèse d'expertise carrosserie",
  categorie: 'courrier',
  description: (
    "Transforme les conclusions techniques de l'expert en une synthèse claire " +
    "et exploitable par le gestionnaire."
  ),
  instructions: (
    "Rédige une synthèse factuelle à partir du rapport d'expertise fourni. " +
    "Distingue les dommages observés, les réserves et les prochaines actions. " +
    "N'invente aucune information et ne décide jamais d'un montant."
  ),
  prix: 120,
  prixLocation: 25,
  tag: 'Expertise',
}

export default function Editeur() {
  const [session, setSession] = useState(() => lireSessionEditeur())
  const [listings, setListings] = useState([])
  const [chargement, setChargement] = useState(true)
  const [publication, setPublication] = useState(false)
  const [message, setMessage] = useState(null)

  const charger = async () => {
    if (!session) return
    try {
      setListings(await api.listerMarketplaceEditeur(session.nom))
    } catch (erreur) {
      setMessage({ ton: 'erreur', texte: erreur.message })
    } finally {
      setChargement(false)
    }
  }

  useEffect(() => {
    if (!session) return
    setChargement(true)
    charger()
  }, [session])

  const revenus = useMemo(
    () => listings.reduce(
      (total, listing) =>
        total + listing.prix * listing.installations + listing.prix_location * (listing.locations_actives ?? 0),
      0,
    ),
    [listings],
  )
  const locationsActives = useMemo(
    () => listings.reduce((total, listing) => total + (listing.locations_actives ?? 0), 0),
    [listings],
  )

  const publier = async (event) => {
    event.preventDefault()
    if (!session) return
    setPublication(true)
    setMessage(null)
    const donnees = new FormData(event.currentTarget)
    try {
      const listing = await api.soumettreMarketplace({
        nom: donnees.get('nom'),
        editeur: session.nom,
        description: donnees.get('description'),
        categorie: donnees.get('categorie'),
        prix: Number(donnees.get('prix')),
        prix_location: Number(donnees.get('prix_location') || 0),
        tags: [donnees.get('tag')].filter(Boolean),
        instructions: donnees.get('instructions'),
      })
      setMessage({
        ton: 'neutre',
        texte: 'Contrôles automatiques réussis. Revue Norix en cours…',
      })
      await new Promise((resolve) => window.setTimeout(resolve, 700))
      await api.validerMarketplace(listing.id)
      await charger()
      setMessage({
        ton: 'succes',
        texte: `« ${listing.nom} » est publié et visible dans la Marketplace assureur.`,
      })
    } catch (erreur) {
      setMessage({ ton: 'erreur', texte: erreur.message })
    } finally {
      setPublication(false)
    }
  }

  if (!session) {
    return <LoginEditeur onConnecte={setSession} />
  }

  return (
    <div className="min-h-screen bg-creme text-encre">
      <header className="border-b border-creme/10 bg-encre text-creme">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-6 py-4">
          <Logo size={32} />
          <Wordmark className="text-xl" />
          <span className="rounded-full bg-terracotta/20 px-3 py-1 text-xs font-semibold text-terracotta">
            Portail éditeurs
          </span>
          <a
            href="/"
            target="_blank"
            rel="noreferrer"
            className="ml-auto rounded-md border border-creme/20 px-3 py-2 text-xs font-semibold text-creme/75 transition hover:bg-creme/10"
          >
            Voir la Marketplace assureur ↗
          </a>
          <div className="hidden text-right md:block">
            <div className="text-xs font-semibold">{session.nom}</div>
            <div className="text-[10px] text-creme/45">{session.email}</div>
          </div>
          <button
            type="button"
            onClick={() => {
              deconnecterEditeur()
              setSession(null)
              setListings([])
              setMessage(null)
            }}
            className="rounded-md border border-creme/20 px-3 py-2 text-xs font-semibold text-creme/75 transition hover:bg-creme/10"
          >
            Déconnexion
          </button>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-6 px-6 py-7">
        <section className="overflow-hidden rounded-2xl bg-encre px-7 py-8 text-creme">
          <div className="max-w-2xl">
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-terracotta">
              Norix for Creators
            </div>
            <h1 className="mt-2 text-3xl font-semibold">Transformez votre expertise en agent métier</h1>
            <p className="mt-3 text-sm leading-6 text-creme/60">
              Publiez vos agents auprès des assureurs sans accéder à leurs données,
              connecteurs ou exécutions. Chaque installation devient un agent indépendant
              dans leur Studio.
            </p>
          </div>
        </section>

        <section className="grid gap-3 sm:grid-cols-4">
          <Kpi libelle="Agents publiés" valeur={listings.filter((item) => item.statut === 'publie').length} />
          <Kpi libelle="Achats" valeur={listings.reduce((total, item) => total + item.installations, 0)} />
          <Kpi libelle="Locations actives" valeur={locationsActives} />
          <Kpi libelle="Revenus simulés" valeur={dt(revenus)} />
        </section>

        {message && (
          <div className={`rounded-lg border px-4 py-3 text-sm ${
            message.ton === 'erreur'
              ? 'border-bad/30 bg-bad-tint text-bad'
              : message.ton === 'succes'
                ? 'border-ok/30 bg-ok-tint text-ok'
                : 'border-line bg-surface text-encre/65'
          }`}>
            {message.ton === 'succes' ? '✓ ' : ''}{message.texte}
          </div>
        )}

        <div className="grid items-start gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <section className="rounded-xl border border-line bg-surface p-6 shadow-sm">
            <div className="flex items-start gap-3">
              <div>
                <h2 className="text-lg font-semibold">Publier un agent</h2>
                <p className="mt-1 text-sm text-encre/50">
                  L’assureur l’achètera préconfiguré et prêt à l’emploi dans son Studio.
                </p>
              </div>
              <span className="ml-auto rounded-full bg-ok-tint px-2.5 py-1 text-[10px] font-semibold text-ok">
                Données client inaccessibles
              </span>
            </div>
            <div className="mt-5 grid grid-cols-4 gap-1 text-center text-[10px] font-semibold uppercase tracking-wide text-encre/45">
              {['Agent', 'Fiche de vente', 'Contrôles Norix', 'Marketplace'].map((etape, index) => (
                <div key={etape} className="rounded bg-surface-deep px-1 py-2">
                  <span className="text-terracotta">{index + 1}</span> {etape}
                </div>
              ))}
            </div>
            <form className="mt-5 grid gap-4" onSubmit={publier}>
              <Champ libelle="Nom de l’agent">
                <input name="nom" required defaultValue={TEMPLATE_DEMO.nom} className={inputClass} />
              </Champ>
              <Champ libelle="Description commerciale">
                <textarea name="description" required rows="3" defaultValue={TEMPLATE_DEMO.description} className={textareaClass} />
              </Champ>
              <Champ libelle="Instructions métier livrées à l’assureur">
                <textarea name="instructions" required rows="5" defaultValue={TEMPLATE_DEMO.instructions} className={textareaClass} />
              </Champ>
              <div className="grid gap-3 sm:grid-cols-4">
                <Champ libelle="Catégorie">
                  <select name="categorie" defaultValue={TEMPLATE_DEMO.categorie} className={inputClass}>
                    <option value="fnol">Qualification FNOL</option>
                    <option value="extraction">Documents</option>
                    <option value="vision">Vision</option>
                    <option value="courrier">Courrier</option>
                    <option value="assistant">Assistant métier</option>
                  </select>
                </Champ>
                <Champ libelle="Prix d’achat (DT)">
                  <input name="prix" type="number" min="0" defaultValue={TEMPLATE_DEMO.prix} className={inputClass} />
                </Champ>
                <Champ libelle="Prix de location (DT/mois)">
                  <input name="prix_location" type="number" min="0" defaultValue={TEMPLATE_DEMO.prixLocation} className={inputClass} />
                </Champ>
                <Champ libelle="Tag">
                  <input name="tag" defaultValue={TEMPLATE_DEMO.tag} className={inputClass} />
                </Champ>
              </div>
              <p className="-mt-1 text-xs text-encre/40">
                Laissez la location à 0 pour proposer votre agent uniquement à l’achat.
              </p>
              <div className="rounded-lg bg-surface-deep p-3 text-xs leading-5 text-encre/55">
                Norix vérifie l’absence de secrets et impose le garde-fou
                « aucune décision financière par le LLM » avant publication.
              </div>
              <button
                type="submit"
                disabled={publication}
                className="justify-self-end rounded-md bg-terracotta px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-terracotta-deep disabled:opacity-50"
              >
                {publication ? 'Contrôles et publication…' : 'Soumettre à Norix'}
              </button>
            </form>
          </section>

          <section className="rounded-xl border border-line bg-surface p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <div>
                <h2 className="text-lg font-semibold">Mes agents</h2>
                <p className="mt-1 text-sm text-encre/50">Versions proposées aux assureurs.</p>
              </div>
              <button onClick={charger} className="ml-auto rounded-md border border-line px-3 py-1.5 text-xs font-semibold text-encre/60">
                Actualiser
              </button>
            </div>
            {chargement ? (
              <p className="mt-6 text-sm text-encre/45">Chargement…</p>
            ) : listings.length === 0 ? (
              <div className="mt-6 rounded-lg border border-dashed border-line p-8 text-center text-sm text-encre/45">
                Aucun agent publié pour le moment.
              </div>
            ) : (
              <div className="mt-5 grid gap-3">
                {listings.map((listing) => (
                  <article key={listing.id} className="rounded-lg border border-line p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-deep text-lg">
                        {AGENT_ICONE[listing.categorie] ?? '✦'}
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold">{listing.nom}</h3>
                        <div className="mt-1 text-xs text-encre/45">
                          {dt(listing.prix)} · {listing.installations} achat(s)
                          {listing.prix_location > 0 && (
                            <> · {dt(listing.prix_location)}/mois · {listing.locations_actives ?? 0} location(s) active(s)</>
                          )}
                        </div>
                      </div>
                      <span className={`ml-auto rounded-full px-2 py-1 text-[10px] font-semibold ${
                        listing.statut === 'publie'
                          ? 'bg-ok-tint text-ok'
                          : 'bg-warn-tint text-warn'
                      }`}>
                        {listing.statut === 'publie' ? 'Publié' : 'En revue'}
                      </span>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  )
}

const inputClass = 'w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-encre outline-none focus:border-terracotta'
const textareaClass = `${inputClass} resize-none`

function Champ({ libelle, children }) {
  return (
    <label className="grid gap-1 text-xs font-medium text-encre/60">
      {libelle}
      {children}
    </label>
  )
}

function Kpi({ libelle, valeur }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-encre/40">{libelle}</div>
      <div className="mt-1 text-2xl font-bold">{valeur}</div>
    </div>
  )
}
