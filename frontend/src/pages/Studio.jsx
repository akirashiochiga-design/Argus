import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Studio() {
  const [templates, setTemplates] = useState([])
  const [agents, setAgents] = useState([])

  useEffect(() => {
    api.listerTemplates().then(setTemplates).catch(() => {})
    api.listerAgents().then(setAgents).catch(() => {})
  }, [])

  return (
    <div className="grid gap-8 md:grid-cols-2">
      <div>
        <h2 className="mb-4 text-lg font-semibold">Templates métier</h2>
        <div className="grid gap-3">
          {templates.map((t) => (
            <div key={t.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="font-medium">{t.nom}</div>
              <p className="mt-1 line-clamp-3 text-sm text-slate-500">{t.instructions_defaut}</p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-slate-400">
          Formulaire de création d'agent depuis template — étape 4 du plan.
        </p>
      </div>
      <div>
        <h2 className="mb-4 text-lg font-semibold">Agents déployés</h2>
        <div className="grid gap-2">
          {agents.map((a) => (
            <div
              key={a.id}
              className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-2.5"
            >
              <span className="text-sm font-medium">{a.nom}</span>
              <span className="text-xs text-slate-400">v{a.version}</span>
              <span
                className={`ml-auto rounded-full px-2 py-0.5 text-xs ${
                  a.statut === 'live'
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-slate-200 text-slate-600'
                }`}
              >
                {a.statut}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
