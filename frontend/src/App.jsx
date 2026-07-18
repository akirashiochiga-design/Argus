import { useEffect, useState } from 'react'
import { api, VALIDATEUR } from './api'
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
  const [page, setPage] = useState('pipeline')
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

  const Page = PAGES.find((p) => p.id === page).composant

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="sticky top-0 z-20 bg-slate-900 text-white shadow-lg">
        <div className="mx-auto flex max-w-7xl items-center gap-8 px-6 py-3.5">
          <h1 className="text-xl font-bold tracking-tight">
            <span className="text-sky-400">◈</span> Argus
            <span className="ml-2 hidden text-xs font-normal text-slate-400 lg:inline">
              agents d'assurance gouvernés
            </span>
          </h1>
          <nav className="flex gap-1">
            {PAGES.map((p) => (
              <button
                key={p.id}
                onClick={() => setPage(p.id)}
                className={`relative rounded px-3 py-1.5 text-sm transition ${
                  page === p.id ? 'bg-white/15 font-medium' : 'text-slate-300 hover:bg-white/10'
                }`}
              >
                {p.label}
                {p.id === 'approbations' && enAttente > 0 && (
                  <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber-500 px-1 text-[10px] font-bold text-slate-900">
                    {enAttente}
                  </span>
                )}
              </button>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-4">
            <span
              className={`flex items-center gap-2 text-xs ${
                backendOk ? 'text-emerald-400' : 'text-red-400'
              }`}
            >
              <span className={`h-2 w-2 rounded-full bg-current ${backendOk === null ? 'animate-pulse' : ''}`} />
              {backendOk === null ? '…' : backendOk ? 'connecté' : 'backend hors ligne'}
            </span>
            <span className="hidden items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs md:flex">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-sky-500 text-[10px] font-bold">
                SG
              </span>
              {VALIDATEUR}
            </span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-6">
        <Page onNavigate={setPage} />
      </main>
    </div>
  )
}
