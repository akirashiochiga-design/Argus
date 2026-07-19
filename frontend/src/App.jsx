import { useEffect, useState } from 'react'
import { api } from './api'
import { deconnecter, initiales, lireSession, libelleValidateur } from './session'
import { Logo, Wordmark } from './ui'
import Login from './pages/Login'
import Studio from './pages/Studio'
import Pipeline from './pages/Pipeline'
import Approbations from './pages/Approbations'
import Dashboard from './pages/Dashboard'
import Integrations from './pages/Integrations'
import Marketplace from './pages/Marketplace'

const PAGES = [
  { id: 'pipeline', label: 'Sinistres', composant: Pipeline },
  { id: 'approbations', label: 'Approbations', composant: Approbations },
  { id: 'studio', label: 'Studio', composant: Studio },
  { id: 'marketplace', label: 'Marketplace', composant: Marketplace },
  { id: 'integrations', label: 'Intégrations', composant: Integrations },
  { id: 'dashboard', label: 'Supervision & Audit', composant: Dashboard },
]

export default function App() {
  const [session, setSession] = useState(() => lireSession())
  const [page, setPage] = useState('dashboard')
  const [backendOk, setBackendOk] = useState(null)
  const [enAttente, setEnAttente] = useState(0)
  const [menuCompte, setMenuCompte] = useState(false)
  const [reinitialisation, setReinitialisation] = useState(false)
  const [revision, setRevision] = useState(0)

  const rafraichirCompteur = () =>
    api.listerTaches('en_attente').then((t) => setEnAttente(t.length)).catch(() => {})

  useEffect(() => {
    api.health().then(() => setBackendOk(true)).catch(() => setBackendOk(false))
    rafraichirCompteur()
    const timer = setInterval(rafraichirCompteur, 4000)
    return () => clearInterval(timer)
  }, [])

  if (!session) {
    return (
      <Login
        onConnecte={(nouvelleSession) => {
          setSession(nouvelleSession)
          setPage('dashboard')
        }}
      />
    )
  }

  const seDeconnecter = () => {
    deconnecter()
    setSession(null)
  }

  const reinitialiserPlateforme = async () => {
    if (reinitialisation) return
    const confirme = window.confirm(
      "Restaurer les données de référence ? Les dossiers, décisions et modifications en cours seront remplacés."
    )
    if (!confirme) return
    setReinitialisation(true)
    try {
      await api.reseed()
      setPage('pipeline')
      setRevision((valeur) => valeur + 1)
      setMenuCompte(false)
      await rafraichirCompteur()
    } catch (erreur) {
      window.alert(`La réinitialisation a échoué : ${erreur.message}`)
    } finally {
      setReinitialisation(false)
    }
  }

  const Page = PAGES.find((p) => p.id === page).composant

  return (
    <div className="min-h-screen bg-creme text-encre">
      <header className="sticky top-0 z-40 bg-encre text-creme">
        <div className="mx-auto flex max-w-7xl items-center gap-6 px-6 py-3">
          <div className="flex items-center gap-2.5">
            <Logo size={30} />
            <Wordmark className="text-xl" />
            <span className="ml-2 hidden text-xs font-normal text-creme/45 lg:inline">
              Gestion des sinistres auto
            </span>
          </div>
          <nav className="ml-4 flex gap-1">
            {PAGES.map((p) => (
              <button
                key={p.id}
                onClick={() => setPage(p.id)}
                className={`relative rounded-md px-3 py-1.5 text-sm transition ${
                  page === p.id ? 'bg-creme/12 font-medium' : 'text-creme/70 hover:bg-creme/8'
                }`}
              >
                {p.label}
                {p.id === 'approbations' && enAttente > 0 && (
                  <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-terracotta px-1 text-[10px] font-bold text-white">
                    {enAttente}
                  </span>
                )}
              </button>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <span
              className={`flex items-center gap-2 text-xs ${
                backendOk ? 'text-ok' : 'text-terracotta'
              }`}
            >
              <span className={`h-2 w-2 rounded-full ${backendOk ? 'bg-ok' : 'bg-terracotta'} ${backendOk === null ? 'animate-pulse' : ''}`} />
              {backendOk === null ? '…' : backendOk ? 'connecté' : 'hors ligne'}
            </span>
            <div className="relative hidden md:block">
              <button
                onClick={() => setMenuCompte((ouvert) => !ouvert)}
                title="Ouvrir le menu du compte"
                aria-expanded={menuCompte}
                className="flex items-center gap-2 rounded-full bg-creme/10 px-3 py-1 text-xs transition hover:bg-creme/15"
              >
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-terracotta text-[10px] font-bold text-white">
                  {initiales(session.nom)}
                </span>
                <span className="text-creme/85">{libelleValidateur(session)}</span>
                <span className="text-[9px] text-creme/45">{menuCompte ? '▲' : '▼'}</span>
              </button>
              {menuCompte && (
                <div className="absolute right-0 top-full mt-2 w-64 overflow-hidden rounded-lg border border-line bg-surface text-encre shadow-xl">
                  <div className="border-b border-line px-4 py-3">
                    <div className="text-sm font-semibold">{session.nom}</div>
                    <div className="mt-0.5 truncate text-xs text-encre/50">{session.email}</div>
                  </div>
                  <div className="p-2">
                    <button
                      onClick={reinitialiserPlateforme}
                      disabled={reinitialisation}
                      className="w-full rounded-md px-3 py-2 text-left text-sm font-medium text-encre/70 transition hover:bg-surface-deep disabled:opacity-50"
                    >
                      {reinitialisation ? 'Restauration…' : 'Restaurer les données de référence'}
                    </button>
                    <button
                      onClick={seDeconnecter}
                      className="w-full rounded-md px-3 py-2 text-left text-sm font-medium text-bad transition hover:bg-bad-tint"
                    >
                      Se déconnecter
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>
      {menuCompte && (
        <button
          aria-label="Fermer le menu du compte"
          onClick={() => setMenuCompte(false)}
          className="fixed inset-0 z-30 cursor-default"
        />
      )}
      <main className="mx-auto max-w-7xl px-6 py-6">
        <Page key={`${page}-${revision}`} onNavigate={setPage} />
      </main>
    </div>
  )
}
