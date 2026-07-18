import { useEffect, useState } from 'react'
import { api } from '../api'
import { ETAT_STYLE, heure } from '../ui'

// Couleurs de statut sémantiques (barre de répartition) — toujours accompagnées
// du libellé + compte : la couleur seule ne porte jamais l'information.
const ETAT_BARRE = {
  regle: 'bg-emerald-500',
  refuse: 'bg-red-500',
  attente_validation: 'bg-amber-500',
  en_cours: 'bg-sky-500',
  recu: 'bg-slate-400',
  cloture: 'bg-slate-600',
}

export default function Dashboard() {
  const [kpi, setKpi] = useState(null)
  const [audit, setAudit] = useState([])
  const [filtre, setFiltre] = useState('')

  const charger = async (acteurType = filtre) => {
    const [k, a] = await Promise.all([
      api.lireKpi(),
      api.lireAudit(acteurType ? { acteur_type: acteurType, limit: 100 } : { limit: 100 }),
    ])
    setKpi(k)
    setAudit(a)
  }

  useEffect(() => { charger() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const changerFiltre = (v) => { setFiltre(v); charger(v) }

  if (!kpi) return <p className="text-sm text-slate-500">Chargement…</p>

  const total = kpi.dossiers_total || 1
  const repartition = Object.entries(kpi.dossiers_par_etat)

  return (
    <div className="grid gap-6">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold">Supervision</h2>
        <button onClick={() => charger()} className="rounded-lg border border-slate-300 px-3 py-1 text-xs text-slate-600 hover:bg-white">
          ⟳ Rafraîchir
        </button>
      </div>

      {/* tuiles KPI */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Tuile nom="Dossiers traités" valeur={kpi.dossiers_traites} sous={`sur ${kpi.dossiers_total} dossiers`} />
        <Tuile nom="Décisions humaines" valeur={kpi.decisions_humaines} sous="100 % des règlements" />
        <Tuile
          nom="Taux d'approbation"
          valeur={kpi.taux_approbation != null ? `${Math.round(kpi.taux_approbation * 100)} %` : '—'}
          sous="propositions des agents"
        />
        <Tuile
          nom="Taux de correction"
          valeur={`${(kpi.taux_correction * 100).toFixed(1)} %`}
          sous="écart humain vs agent"
        />
        <Tuile nom="Coût IA total" valeur={`$${kpi.cout_ia_usd.toFixed(2)}`} sous={`${kpi.runs_total} runs d'agents`} />
        <Tuile
          nom="Temps économisé"
          valeur={`${Math.floor(kpi.temps_economise_min / 60)} h ${kpi.temps_economise_min % 60} min`}
          sous="≈ 110 min / dossier (estim.)"
        />
      </div>

      {/* répartition par état */}
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Dossiers par état
        </h3>
        <div className="flex h-6 w-full gap-0.5 overflow-hidden rounded-lg">
          {repartition.map(([etat, n]) => (
            <div
              key={etat}
              className={`${ETAT_BARRE[etat] ?? 'bg-slate-300'} transition-all`}
              style={{ width: `${(n / total) * 100}%` }}
              title={`${ETAT_STYLE[etat]?.libelle ?? etat} : ${n}`}
            />
          ))}
        </div>
        <div className="mt-2 flex flex-wrap gap-4">
          {repartition.map(([etat, n]) => (
            <span key={etat} className="flex items-center gap-1.5 text-sm text-slate-600">
              <span className={`h-2.5 w-2.5 rounded-sm ${ETAT_BARRE[etat] ?? 'bg-slate-300'}`} />
              {ETAT_STYLE[etat]?.libelle ?? etat} — <b>{n}</b>
            </span>
          ))}
        </div>
      </div>

      {/* journal d'audit */}
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center gap-3">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
            Journal d'audit
          </h3>
          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-slate-500">
            append-only · horodaté · attribué
          </span>
          <div className="ml-auto flex gap-1 text-xs">
            {[['', 'tout'], ['humain', 'humains'], ['agent', 'agents']].map(([v, l]) => (
              <button key={v} onClick={() => changerFiltre(v)}
                className={`rounded-full px-3 py-1 ${filtre === v ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
                {l}
              </button>
            ))}
          </div>
        </div>
        <div className="max-h-[420px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-white text-left text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="py-2 pr-3">Heure</th>
                <th className="py-2 pr-3">Acteur</th>
                <th className="py-2 pr-3">Événement</th>
                <th className="py-2 pr-3">Objet</th>
                <th className="py-2">Détail</th>
              </tr>
            </thead>
            <tbody>
              {audit.map((e) => (
                <tr key={e.id} className="border-t border-slate-100 align-top">
                  <td className="py-1.5 pr-3 font-mono text-xs text-slate-500">{heure(e.horodatage)}</td>
                  <td className="py-1.5 pr-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      e.acteur_type === 'humain' ? 'bg-sky-100 text-sky-800' : 'bg-violet-100 text-violet-700'
                    }`}>
                      {e.acteur.replace(/^(humain|agent):/, '')}
                    </span>
                  </td>
                  <td className="py-1.5 pr-3 text-xs font-semibold text-slate-700">{e.type}</td>
                  <td className="py-1.5 pr-3 font-mono text-xs text-slate-500">{e.objet}</td>
                  <td className="py-1.5 text-xs text-slate-500">
                    {e.motif && <span className="italic">« {e.motif} » </span>}
                    <Resume avant={e.avant} apres={e.apres} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

const Tuile = ({ nom, valeur, sous }) => (
  <div className="rounded-xl border border-slate-200 bg-white p-4">
    <div className="text-xs font-medium uppercase tracking-wide text-slate-400">{nom}</div>
    <div className="mt-1 text-2xl font-bold tabular-nums text-slate-800">{valeur}</div>
    <div className="mt-0.5 text-xs text-slate-400">{sous}</div>
  </div>
)

function Resume({ avant, apres }) {
  const morceaux = []
  if (avant?.etat && apres?.etat) morceaux.push(`${avant.etat} → ${apres.etat}`)
  else if (apres?.decision) morceaux.push(`décision : ${apres.decision}${apres.montant_valide != null ? ` (${apres.montant_valide} DT)` : ''}`)
  else if (apres?.montant_recommande != null) morceaux.push(`montant recommandé : ${apres.montant_recommande} DT`)
  else if (apres?.statut) morceaux.push(`statut : ${apres.statut}`)
  else if (apres?.seuils) morceaux.push(`seuils : ${JSON.stringify(apres.seuils)}`)
  else if (apres?.nom) morceaux.push(apres.nom)
  return <span>{morceaux.join(' · ')}</span>
}
