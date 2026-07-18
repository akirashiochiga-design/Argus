import { useEffect, useState } from 'react'
import { api } from '../api'
import { ETAT_STYLE, heure } from '../ui'

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

  if (!kpi) return <p className="text-sm text-encre/50">Chargement…</p>

  const total = kpi.dossiers_total || 1
  const repartition = Object.entries(kpi.dossiers_par_etat)

  return (
    <div className="grid gap-6">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold">Supervision</h2>
        <button onClick={() => charger()} className="rounded-md border border-line px-3 py-1 text-xs text-encre/60 hover:bg-surface">
          ⟳ Rafraîchir
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Tuile nom="Dossiers traités" valeur={kpi.dossiers_traites} sous={`sur ${kpi.dossiers_total} dossiers`} />
        <Tuile nom="Décisions humaines" valeur={kpi.decisions_humaines} sous="100 % des règlements" />
        <Tuile nom="Taux d'approbation"
          valeur={kpi.taux_approbation != null ? `${Math.round(kpi.taux_approbation * 100)} %` : '—'}
          sous="propositions des agents" />
        <Tuile nom="Taux de correction" valeur={`${(kpi.taux_correction * 100).toFixed(1)} %`} sous="écart humain vs agent" />
        <Tuile nom="Coût IA total" valeur={`$${kpi.cout_ia_usd.toFixed(2)}`} sous={`${kpi.runs_total} runs d'agents`} accent />
        <Tuile nom="Temps économisé"
          valeur={`${Math.floor(kpi.temps_economise_min / 60)} h ${kpi.temps_economise_min % 60} min`}
          sous="≈ 110 min / dossier (estim.)" />
      </div>

      <div className="rounded-lg border border-line bg-surface p-4">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-encre/40">Dossiers par état</h3>
        <div className="flex h-6 w-full gap-0.5 overflow-hidden rounded-md">
          {repartition.map(([etat, n]) => (
            <div key={etat} className={`${ETAT_STYLE[etat]?.barre ?? 'bg-line'} transition-all`}
              style={{ width: `${(n / total) * 100}%` }}
              title={`${ETAT_STYLE[etat]?.libelle ?? etat} : ${n}`} />
          ))}
        </div>
        <div className="mt-2 flex flex-wrap gap-4">
          {repartition.map(([etat, n]) => (
            <span key={etat} className="flex items-center gap-1.5 text-sm text-encre/60">
              <span className={`h-2.5 w-2.5 rounded-sm ${ETAT_STYLE[etat]?.barre ?? 'bg-line'}`} />
              {ETAT_STYLE[etat]?.libelle ?? etat} — <b>{n}</b>
            </span>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-line bg-surface p-4">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-encre/40">Journal d'audit</h3>
          <span className="rounded bg-surface-deep px-1.5 py-0.5 text-[10px] font-semibold uppercase text-encre/50">
            append-only · horodaté · attribué
          </span>
          <div className="ml-auto flex gap-1 text-xs">
            {[['', 'tout'], ['humain', 'humains'], ['agent', 'agents']].map(([v, l]) => (
              <button key={v} onClick={() => changerFiltre(v)}
                className={`rounded-full px-3 py-1 ${filtre === v ? 'bg-encre text-creme' : 'bg-surface-deep text-encre/60 hover:bg-line'}`}>
                {l}
              </button>
            ))}
          </div>
        </div>
        <div className="max-h-[420px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-surface text-left text-xs uppercase tracking-wide text-encre/40">
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
                <tr key={e.id} className="border-t border-line align-top">
                  <td className="py-1.5 pr-3 font-mono text-xs text-encre/50">{heure(e.horodatage)}</td>
                  <td className="py-1.5 pr-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      e.acteur_type === 'humain' ? 'bg-surface-deep text-encre' : 'bg-terracotta-tint text-terracotta-deep'
                    }`}>
                      {e.acteur.replace(/^(humain|agent):/, '')}
                    </span>
                  </td>
                  <td className="py-1.5 pr-3 text-xs font-semibold text-encre/75">{e.type}</td>
                  <td className="py-1.5 pr-3 font-mono text-xs text-encre/50">{e.objet}</td>
                  <td className="py-1.5 text-xs text-encre/50">
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

const Tuile = ({ nom, valeur, sous, accent }) => (
  <div className="rounded-lg border border-line bg-surface p-4">
    <div className="text-xs font-medium uppercase tracking-wide text-encre/40">{nom}</div>
    <div className={`mt-1 text-2xl font-bold tabular-nums ${accent ? 'text-terracotta-deep' : ''}`}>{valeur}</div>
    <div className="mt-0.5 text-xs text-encre/40">{sous}</div>
  </div>
)

function Resume({ avant, apres }) {
  const m = []
  if (avant?.etat && apres?.etat) m.push(`${avant.etat} → ${apres.etat}`)
  else if (apres?.decision) m.push(`décision : ${apres.decision}${apres.montant_valide != null ? ` (${apres.montant_valide} DT)` : ''}`)
  else if (apres?.montant_recommande != null) m.push(`montant recommandé : ${apres.montant_recommande} DT`)
  else if (apres?.statut) m.push(`statut : ${apres.statut}`)
  else if (apres?.seuils) m.push(`seuils : ${JSON.stringify(apres.seuils)}`)
  else if (apres?.nom) m.push(apres.nom)
  return <span>{m.join(' · ')}</span>
}
