import { useEffect, useState } from 'react'
import { api } from './api'
import { initiales, lireSession, libelleValidateur } from './session'
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

const PAGE_ACCUEIL = 'integrations'

export default function App() {
  const [session, setSession] = useState(() => lireSession())
  const [page, setPage] = useState(PAGE_ACCUEIL)
  const [backendOk, setBackendOk] = useState(null)
  const [enAttente, setEnAttente] = useState(0)

  const rafraichirCompteur = () =>
    api.listerTaches('en_attente').then((t) => setEnAttente(t.length)).catch(() => {})

  useEffect(() => {
    api.health().then(() => setBackendOk(true)).catch(() => setBackendOk(false))
    rafraichirCompteur()
    const timer = setInterval(rafraichirCompteur, 4000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    const afficherAccueil = () => {
      setPage(PAGE_ACCUEIL)
    }

    afficherAccueil()
    window.addEventListener('pageshow', afficherAccueil)
    return () => window.removeEventListener('pageshow', afficherAccueil)
  }, [])

  if (!session) {
    return (
      <Login
        onConnecte={(nouvelleSession) => {
          setSession(nouvelleSession)
          setPage(PAGE_ACCUEIL)
        }}
      />
    )
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
            <div className="hidden items-center gap-2 rounded-full bg-creme/10 px-3 py-1 text-xs md:flex">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-terracotta text-[10px] font-bold text-white">
                {initiales(session.nom)}
              </span>
              <span className="text-creme/85">{libelleValidateur(session)}</span>
            </div>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-6">
        <Page key={page} onNavigate={setPage} />
      </main>
    </div>
  )
}
