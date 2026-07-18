import { useEffect, useState } from 'react'
import { api } from '../api'

const ETATS = {
  recu: 'bg-slate-200 text-slate-700',
  en_cours: 'bg-blue-100 text-blue-800',
  attente_validation: 'bg-amber-100 text-amber-800',
  regle: 'bg-emerald-100 text-emerald-800',
  refuse: 'bg-red-100 text-red-800',
  cloture: 'bg-slate-300 text-slate-600',
}

export default function Pipeline() {
  const [dossiers, setDossiers] = useState([])
  const [erreur, setErreur] = useState(null)

  useEffect(() => {
    api.listerDossiers().then(setDossiers).catch((e) => setErreur(e.message))
  }, [])

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold">Dossiers sinistres</h2>
      {erreur && <p className="text-sm text-red-600">{erreur}</p>}
      <div className="grid gap-3">
        {dossiers.map((d) => (
          <div key={d.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm font-semibold">{d.ref}</span>
              <span className="text-sm text-slate-600">
                {d.assure_nom} — {d.formule?.replace('_', ' ')}
              </span>
              <span
                className={`ml-auto rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  ETATS[d.etat] ?? ETATS.recu
                }`}
              >
                {d.etat.replace('_', ' ')}
              </span>
            </div>
            <p className="mt-2 line-clamp-2 text-sm text-slate-500">{d.declaration_texte}</p>
          </div>
        ))}
      </div>
      <p className="mt-6 text-xs text-slate-400">
        Vue frise du pipeline P5 (étape 2 du plan) — le dossier avancera ici agent par agent.
      </p>
    </div>
  )
}
