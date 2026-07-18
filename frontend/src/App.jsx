import { useEffect, useState } from 'react'
import { api } from './api'
import { deconnecter, initiales, lireSession, libelleValidateur } from './session'
import { Logo, Wordmark } from './ui'
import Login from './pages/Login'
import Studio from './pages/Studio'
import Pipeline from './pages/Pipeline'
import Approbations from './pages/Approbations'
import Dashboard from './pages/Dashboard'

const PAGES = [
  { id: 'pipeline', label: 'Pipeline', composant: Pipeline },
  { id: 'approbations', label: 'Approbations', composant: Approbations },
  { id: 'studio', label: 'Studio', composant: Studio },
  { id: 'dashboard', label: 'Dashboard & Audit', composant: Dashboard },
]

export default function App() {
  const [session, setSession] = useState(() => lireSession())
  const [page, setPage] = useState('pipeline')
  const [backendOk, setBackendOk] = useState(null)
  const [enAttente, setEnAttente] = useState(0)
  const [reset, setReset] = useState(false)
  const [rev, setRev] = useState(0) // force un remount des pages après reset

  const rafraichirCompteur = () =>
    api.listerTaches('en_attente').then((t) => setEnAttente(t.length)).catch(() => {})

  useEffect(() => {
    api.health().then(() => setBackendOk(true)).catch(() => setBackendOk(false))
    rafraichirCompteur()
    const timer = setInterval(rafraichirCompteur, 4000)
    return () => clearInterval(timer)
  }, [])

  const resetDemo = async () => {
    if (reset) return
    if (!window.confirm('Réinitialiser la démo ? Les 3 dossiers calibrés reviennent à zéro.')) return
    setReset(true)
    try {
      await api.reseed()
      setRev((r) => r + 1)
      setPage('pipeline')
      await rafraichirCompteur()
    } catch {
      /* silencieux */
    } finally {
      setReset(false)
    }
  }

  if (!session) {
    return <Login onConnecte={setSession} />
  }

  const seDeconnecter = () => {
    deconnecter()
    setSession(null)
  }

  const Page = PAGES.find((p) => p.id === page).composant

  return (
    <div className="min-h-screen bg-creme text-encre">
      <header className="sticky top-0 z-20 bg-encre text-creme">
        <div className="mx-auto flex max-w-7xl items-center gap-6 px-6 py-3">
          <div className="flex items-center gap-2.5">
            <Logo size={30} />
            <Wordmark className="text-xl" />
            <span className="ml-2 hidden text-xs font-normal text-creme/45 lg:inline">
              l'usine à agents pour l'assurance
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
            <button
              onClick={resetDemo}
              disabled={reset}
              title="Réinitialiser le dataset de démo"
              className="rounded-md border border-creme/20 px-3 py-1.5 text-xs font-medium text-creme/80 transition hover:bg-creme/10 disabled:opacity-50"
            >
              {reset ? '↻ …' : '↻ Reset démo'}
            </button>
            <span
              className={`flex items-center gap-2 text-xs ${
                backendOk ? 'text-ok' : 'text-terracotta'
              }`}
            >
              <span className={`h-2 w-2 rounded-full ${backendOk ? 'bg-ok' : 'bg-terracotta'} ${backendOk === null ? 'animate-pulse' : ''}`} />
              {backendOk === null ? '…' : backendOk ? 'connecté' : 'hors ligne'}
            </span>
            <button
              onClick={seDeconnecter}
              title="Se déconnecter"
              className="hidden items-center gap-2 rounded-full bg-creme/10 px-3 py-1 text-xs transition hover:bg-creme/15 md:flex"
            >
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-terracotta text-[10px] font-bold text-white">
                {initiales(session.nom)}
              </span>
              <span className="text-creme/85">{libelleValidateur(session)}</span>
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-6">
        <Page key={`${page}-${rev}`} onNavigate={setPage} />
      </main>
    </div>
  )
}
