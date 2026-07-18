import { useEffect, useState } from 'react'
import { api } from './api'
import Studio from './pages/Studio'
import Pipeline from './pages/Pipeline'
import Approbations from './pages/Approbations'
import Dashboard from './pages/Dashboard'

const PAGES = [
  { id: 'pipeline', label: 'Pipeline', composant: Pipeline },
  { id: 'approbations', label: 'Approbations', composant: Approbations },
  { id: 'studio', label: 'Studio', composant: Studio },
  { id: 'dashboard', label: 'Dashboard', composant: Dashboard },
]

export default function App() {
  const [page, setPage] = useState('pipeline')
  const [backendOk, setBackendOk] = useState(null)

  useEffect(() => {
    api.health().then(() => setBackendOk(true)).catch(() => setBackendOk(false))
  }, [])

  const Page = PAGES.find((p) => p.id === page).composant

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="bg-slate-900 text-white">
        <div className="mx-auto flex max-w-6xl items-center gap-8 px-6 py-4">
          <h1 className="text-xl font-bold tracking-tight">
            Argus
            <span className="ml-2 text-xs font-normal text-slate-400">
              agents d'assurance gouvernés
            </span>
          </h1>
          <nav className="flex gap-1">
            {PAGES.map((p) => (
              <button
                key={p.id}
                onClick={() => setPage(p.id)}
                className={`rounded px-3 py-1.5 text-sm ${
                  page === p.id
                    ? 'bg-white/15 font-medium'
                    : 'text-slate-300 hover:bg-white/10'
                }`}
              >
                {p.label}
              </button>
            ))}
          </nav>
          <span
            className={`ml-auto flex items-center gap-2 text-xs ${
              backendOk ? 'text-emerald-400' : 'text-red-400'
            }`}
          >
            <span className="h-2 w-2 rounded-full bg-current" />
            {backendOk === null ? '…' : backendOk ? 'backend connecté' : 'backend hors ligne'}
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Page />
      </main>
    </div>
  )
}
