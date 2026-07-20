import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { AGENT_ICONE, BadgeEtat, GaleriePieces, dt } from '../ui'

const DELAI_ANIMATION_MS = 650

export default function Pipeline({ onNavigate }) {
  const [dossiers, setDossiers] = useState([])
  const [selection, setSelection] = useState(null) // {dossier, police, workflow, runs}
  const [agents, setAgents] = useState({})
  const [workflows, setWorkflows] = useState([])
  const [occupe, setOccupe] = useState(false)
  const [formulaire, setFormulaire] = useState(false)
  const [erreur, setErreur] = useState(null)
  const stopRef = useRef(false)

  const chargerListe = () => api.listerDossiers().then(setDossiers).catch((e) => setErreur(e.message))
  const chargerDetail = (id) => api.lireDossier(id).then(setSelection).catch((e) => setErreur(e.message))

  useEffect(() => {
    chargerListe()
    api.listerAgents().then((liste) => {
      const parId = {}
      liste.forEach((a) => (parId[a.id] = a))
      setAgents(parId)
    })
    api.listerWorkflows().then(setWorkflows).catch((e) => setErreur(e.message))
  }, [])

  useEffect(() => {
    if (!selection && dossiers.length) chargerDetail(dossiers[0].id)
  }, [dossiers]) // eslint-disable-line react-hooks/exhaustive-deps

  const executer = async () => {
    if (!selection || occupe) return
    setOccupe(true)
    setErreur(null)
    stopRef.current = false
    try {
      let resultat = 'etape_executee'
      while (resultat === 'etape_executee' && !stopRef.current) {
        const r = await api.executerEtape(selection.dossier.id)
        resultat = r.resultat
        await chargerDetail(selection.dossier.id)
        await chargerListe()
        if (resultat === 'etape_executee') await new Promise((ok) => setTimeout(ok, DELAI_ANIMATION_MS))
      }
    } catch (e) {
      setErreur(e.message)
    } finally {
      setOccupe(false)
    }
  }

  const choisirTraitement = async (workflowId) => {
    if (!selection || occupe) return
    setOccupe(true)
    setErreur(null)
    try {
      await api.choisirTraitement(selection.dossier.id, workflowId)
      await chargerDetail(selection.dossier.id)
      await chargerListe()
    } catch (e) {
      setErreur(e.message)
    } finally {
      setOccupe(false)
    }
  }

  const d = selection?.dossier

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      {/* ---- colonne dossiers ---- */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Dossiers</h2>
          <button
            onClick={() => setFormulaire(true)}
            className="rounded-md bg-encre px-3 py-1.5 text-sm font-medium text-creme transition hover:bg-encre/85"
          >
            + Déclarer
          </button>
        </div>
        <div className="grid gap-2">
          {dossiers.length === 0 && (
            <div className="rounded-lg border border-dashed border-line bg-surface p-4 text-sm text-encre/50">
              Aucun dossier synchronisé.
            </div>
          )}
          {dossiers.map((x) => (
            <button
              key={x.id}
              onClick={() => chargerDetail(x.id)}
              className={`rounded-lg border bg-surface p-3 text-left transition hover:border-terracotta/50 ${
                d?.id === x.id ? 'border-terracotta ring-2 ring-terracotta-tint' : 'border-line'
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-semibold">{x.ref}</span>
                <span className="ml-auto"><BadgeEtat etat={x.etat} /></span>
              </div>
              <div className="mt-1 text-sm text-encre/60">
                {x.assure_nom} · {x.formule?.replace('_', ' ')}
              </div>
              {x.montant_recommande != null && (
                <div className="mt-1 text-xs text-encre/50">
                  recommandé : <b className="text-encre/70">{dt(x.montant_recommande)}</b>
                  {x.montant_valide != null && <> · validé : <b className="text-ok">{dt(x.montant_valide)}</b></>}
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* ---- détail + frise ---- */}
      <div className="min-w-0">
        {erreur && (
          <div className="mb-3 rounded-lg border border-bad/30 bg-bad-tint px-4 py-2 text-sm text-bad">
            {erreur}
          </div>
        )}
        {d ? (
          <DetailDossier
            selection={selection}
            agents={agents}
            workflows={workflows}
            occupe={occupe}
            onExecuter={executer}
            onChoisirTraitement={choisirTraitement}
            onNavigate={onNavigate}
          />
        ) : (
          <div className="rounded-lg border border-line bg-surface p-6 text-sm text-encre/55">
            Connectez puis synchronisez la base assurance depuis l’onglet Intégrations.
          </div>
        )}
      </div>

      {formulaire && (
        <FormulaireDeclaration
          onFermer={() => setFormulaire(false)}
          onCree={async (nouveau) => {
            setFormulaire(false)
            await chargerListe()
            await chargerDetail(nouveau.id)
          }}
        />
      )}
    </div>
  )
}

/* ================= détail d'un dossier ================= */

function traitementRecommande(dossier, workflows) {
  const contenu = [
    dossier.declaration_texte,
    ...(dossier.pieces ?? []).map((piece) => `${piece.type ?? ''} ${piece.nom ?? ''}`),
  ].join(' ')
  const brisDeGlace = /\b(pare[- ]?brise|vitre|vitrage|bris de glace)\b/i.test(contenu)
  if (brisDeGlace) {
    return workflows.find((traitement) => /bris de glace/i.test(traitement.nom))
  }
  return workflows.find((traitement) => traitement.est_defaut) ?? workflows[0]
}

function DetailDossier({
  selection,
  agents,
  workflows,
  occupe,
  onExecuter,
  onChoisirTraitement,
  onNavigate,
}) {
  const { dossier: d, police, workflow, runs } = selection
  const etapes = workflow?.etapes ?? []
  const dernierRun = runs[runs.length - 1]
  const termine = ['regle', 'refuse', 'cloture'].includes(d.etat)
  const recommande = traitementRecommande(d, workflows)
  const peutChanger = d.etat === 'recu' && d.etape_courante === 0 && runs.length === 0
  return (
    <div className="grid gap-4">
      {/* entête */}
      <div className="rounded-lg border border-line bg-surface p-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-mono text-lg font-bold">{d.ref}</span>
          <BadgeEtat etat={d.etat} />
          <span className="text-sm text-encre/60">
            {police?.assure_nom} — {police?.numero} ({police?.formule?.replace('_', ' ')})
          </span>
          <span className="text-sm text-encre/45">
            {police?.vehicule?.marque} {police?.vehicule?.modele} · {police?.vehicule?.annee}
          </span>
          <div className="ml-auto flex items-center gap-5">
            {d.montant_recommande != null && (
              <div className="text-right">
                <div className="text-[11px] uppercase tracking-wide text-encre/40">Montant proposé</div>
                <div className="text-xl font-bold">{dt(d.montant_recommande)}</div>
              </div>
            )}
            {d.montant_valide != null && (
              <div className="text-right">
                <div className="text-[11px] uppercase tracking-wide text-ok">Montant validé</div>
                <div className="text-xl font-bold text-ok">{dt(d.montant_valide)}</div>
              </div>
            )}
          </div>
        </div>
        <p className="mt-3 rounded-md bg-surface-deep p-3 text-sm italic text-encre/70">
          « {d.declaration_texte} »
        </p>
        {d.pieces && d.pieces.length > 0 && (
          <GaleriePieces pieces={d.pieces} className="mt-4" />
        )}
      </div>

      {/* frise du parcours */}
      <div className="rounded-lg border border-line bg-surface p-4">
        <div className="mb-2 flex items-center gap-2">
          <h3 className="font-semibold">Traitement du dossier</h3>
          {!peutChanger && (
            <span className="text-xs text-encre/40">choix verrouillé après lancement</span>
          )}
        </div>
        <div className="grid gap-2 md:grid-cols-2">
          {workflows.map((traitement) => {
            const selectionne = workflow?.id === traitement.id
            const estRecommande = recommande?.id === traitement.id
            return (
              <button
                key={traitement.id}
                onClick={() => !selectionne && onChoisirTraitement(traitement.id)}
                disabled={!peutChanger || occupe}
                className={`rounded-lg border p-3 text-left transition ${
                  selectionne
                    ? 'border-terracotta bg-terracotta-tint/35'
                    : 'border-line bg-surface-deep hover:border-terracotta/40'
                } disabled:cursor-default disabled:opacity-80`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold">{traitement.nom}</span>
                  {estRecommande && (
                    <span className="rounded-full bg-ok-tint px-2 py-0.5 text-[10px] font-semibold text-ok">
                      Recommandé
                    </span>
                  )}
                  {selectionne && (
                    <span className="ml-auto text-xs font-semibold text-terracotta-deep">
                      Sélectionné
                    </span>
                  )}
                </div>
                {traitement.description && (
                  <p className="mt-1 text-xs text-encre/50">{traitement.description}</p>
                )}
              </button>
            )
          })}
        </div>
        <div className="mb-4 mt-4 flex flex-wrap items-center gap-2">
          <h3 className="font-semibold">{workflow?.nom ?? 'Parcours de traitement'}</h3>
          <div className="ml-auto flex items-center gap-2">
            {!termine && d.etat !== 'attente_validation' && (
              <button
                onClick={onExecuter}
                disabled={occupe}
                className="rounded-md bg-terracotta px-4 py-2 text-sm font-semibold text-white transition hover:bg-terracotta-deep disabled:opacity-50"
              >
                {occupe ? '⏳ Traitement…' : '▶ Lancer le traitement'}
              </button>
            )}
          </div>
        </div>
        <Frise etapes={etapes} agents={agents} dossier={d} runs={runs} occupe={occupe} />

        {d.etat === 'attente_validation' && (
          <div className="mt-4 flex flex-wrap items-center gap-3 rounded-md border border-warn/40 bg-warn-tint px-4 py-3">
            <span className="text-xl">🛡️</span>
            <div className="text-sm text-encre/80">
              <b>Traitement suspendu — validation requise.</b> Aucun règlement ne part sans
              décision explicite d'un gestionnaire.
            </div>
            <button
              onClick={() => onNavigate('approbations')}
              className="ml-auto whitespace-nowrap rounded-md bg-terracotta px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-terracotta-deep"
            >
              Ouvrir la file d'approbation →
            </button>
          </div>
        )}
      </div>

      {dernierRun && !termine && (
        <SortieRun run={dernierRun} agents={agents} pieces={d.pieces} titre="Dernière étape exécutée" />
      )}

      {termine && d.courrier?.corps && <Courrier courrier={d.courrier} etat={d.etat} />}

      {runs.length > 0 && (
        <details className="rounded-lg border border-line bg-surface p-4" open={termine}>
          <summary className="cursor-pointer font-semibold">
            Historique du traitement — {runs.length} étape{runs.length > 1 ? 's' : ''}
          </summary>
          <div className="mt-3 grid gap-3">
            {runs.map((r) => (
              <SortieRun key={r.id} run={r} agents={agents} pieces={d.pieces} compact />
            ))}
          </div>
        </details>
      )}
    </div>
  )
}

function Frise({ etapes, agents, dossier, runs, occupe }) {
  const agentsAyantTourne = new Set(runs.filter((r) => r.statut === 'succes').map((r) => r.agent_id))
  return (
    <div className="flex items-stretch gap-1 overflow-x-auto pb-2">
      {etapes.map((e, i) => {
        const agent = agents[e.agent_id]
        const porte = e.type === 'porte_humaine'
        const faite = i < dossier.etape_courante && (agentsAyantTourne.has(e.agent_id) || porte)
        const courante = i === dossier.etape_courante && !['regle', 'refuse'].includes(dossier.etat)
        const enAttente = porte && dossier.etat === 'attente_validation'
        return (
          <div key={i} className="flex items-center">
            <div
              className={`flex w-[108px] flex-col items-center gap-1 rounded-md border-2 p-2 text-center transition-all ${
                enAttente
                  ? 'border-warn bg-warn-tint'
                  : faite
                    ? 'border-ok/40 bg-ok-tint'
                    : courante
                      ? `border-terracotta bg-terracotta-tint ${occupe ? 'animate-pulse' : ''}`
                      : 'border-line bg-surface-deep opacity-55'
              }`}
            >
              <span className="text-xl">{porte ? '🛡️' : AGENT_ICONE[agent?.categorie] ?? '⚙️'}</span>
              <span className="text-[11px] font-medium leading-tight">{agent?.nom ?? '—'}</span>
              <span className="text-[10px] text-encre/40">
                {enAttente ? 'validation requise' : faite ? '✓ terminé' : courante ? 'prochain' : 'à venir'}
              </span>
            </div>
            {i < etapes.length - 1 && (
              <span className={`px-0.5 text-lg ${faite ? 'text-ok' : 'text-encre/20'}`}>→</span>
            )}
          </div>
        )
      })}
    </div>
  )
}

/* ================= rendu des sorties par type d'agent ================= */

function SortieRun({ run, agents, pieces, titre, compact }) {
  const agent = agents[run.agent_id]
  const s = run.sorties ?? {}
  return (
    <div className={`rounded-lg border border-line bg-surface p-4 ${compact ? '' : ''}`}>
      <div className="mb-2 flex items-center gap-2">
        <span>{AGENT_ICONE[agent?.categorie] ?? '⚙️'}</span>
        <span className="text-sm font-semibold">{titre ?? agent?.nom ?? `Étape ${run.agent_id}`}</span>
        {titre && <span className="text-xs text-encre/40">({agent?.nom})</span>}
      </div>
      <TraceActions trace={s.trace} compact={compact} />
      <CorpsSortie categorie={agent?.categorie} s={s} pieces={pieces} />
    </div>
  )
}

const LIBELLES_OUTILS = {
  consulter_police: 'Consulter la police',
  inventorier_pieces: 'Inventorier les pièces',
  consulter_vehicule_assure: 'Consulter le véhicule assuré',
  consulter_circonstances: 'Consulter les circonstances',
  regles_locales: 'Appliquer le barème interne',
}

function resumeResultat(resultat = {}) {
  if (resultat.erreur) return resultat.erreur
  if (resultat.motif) return resultat.motif
  if (resultat.vehicule) {
    const v = resultat.vehicule
    return [v.marque, v.modele, v.annee].filter(Boolean).join(' ')
  }
  if (resultat.marque || resultat.modele) {
    return [resultat.marque, resultat.modele, resultat.annee].filter(Boolean).join(' ')
  }
  if (resultat.nombre != null) return `${resultat.nombre} pièce${resultat.nombre > 1 ? 's' : ''}`
  if (resultat.type_sinistre) return `Sinistre ${resultat.type_sinistre}`
  return 'Informations consultées'
}

function TraceActions({ trace, compact }) {
  const actions = trace?.actions ?? []
  if (actions.length === 0) return null
  return (
    <details className="mb-3 rounded-md border border-line bg-surface-deep px-3 py-2" open={!compact}>
      <summary className="cursor-pointer text-xs font-semibold text-encre/70">
        Journal de traitement — {actions.length} étape{actions.length > 1 ? 's' : ''}
      </summary>
      <div className="mt-2 border-l-2 border-terracotta/25 pl-3">
        <p className="mb-2 text-xs text-encre/50">Objectif : {trace.objectif}</p>
        {actions.map((action, index) => (
          <div key={`${action.outil}-${index}`} className="mb-2 flex items-start gap-2 text-xs last:mb-0">
            <span className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[9px] font-bold ${
              action.statut === 'refuse' ? 'bg-bad-tint text-bad' : 'bg-ok-tint text-ok'
            }`}>
              {index + 1}
            </span>
            <div>
              <div className="font-semibold text-encre/75">
                {LIBELLES_OUTILS[action.outil] ?? action.outil}
              </div>
              <div className="text-encre/45">{resumeResultat(action.resultat)}</div>
            </div>
          </div>
        ))}
      </div>
    </details>
  )
}

function CorpsSortie({ categorie, s, pieces = [] }) {
  if (categorie === 'fnol' && s.donnees_fnol) {
    const f = s.donnees_fnol
    return (
      <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm md:grid-cols-3">
        <Champ nom="Type de sinistre" valeur={f.type_sinistre} fort />
        <Champ nom="Langue de la déclaration" valeur={f.langue} />
        <Champ nom="Complétude du dossier" valeur={`${Math.round(f.completude * 100)} %`} />
        <Champ nom="Tiers identifié" valeur={f.tiers_identifie ? 'oui' : 'non'} />
        <Champ nom="Constat" valeur={f.constat_present ? 'présent' : 'absent'} />
        <Champ nom="Champs manquants" valeur={f.champs_manquants?.join(', ') || 'aucun'} />
        <div className="col-span-full"><Champ nom="Circonstances" valeur={f.circonstances} /></div>
      </div>
    )
  }
  if (categorie === 'extraction' && s.pieces) {
    const piecesExtraites = s.pieces.filter((p) => p.extraction)
    return (
      <div className="grid gap-2">
        <GaleriePieces pieces={piecesExtraites} hauteur="h-24" />
        {piecesExtraites.map((p, i) => (
          <div key={i} className="rounded-md bg-surface-deep p-2 text-sm">
            <div className="flex items-center gap-2">
              <b>{p.type}</b>
              <span className="text-xs text-encre/50">{p.extraction.emetteur}</span>
              {p.extraction.total != null && (
                <span className="ml-auto font-semibold">{dt(p.extraction.total)}</span>
              )}
            </div>
            {p.extraction.postes?.length > 0 && (
              <ul className="mt-1 text-xs text-encre/60">
                {p.extraction.postes.map((poste, j) => (
                  <li key={j} className="flex justify-between border-t border-line py-0.5">
                    <span>{poste.libelle}</span><span>{dt(poste.montant)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {s.montant_estime != null && (
          <div className="text-sm">Montant de référence retenu : <b>{dt(s.montant_estime)}</b></div>
        )}
      </div>
    )
  }
  if (categorie === 'vision' && s.analyse_gravite) {
    const g = s.analyse_gravite
    if (g.analyse_disponible === false || !g.classe) {
      return (
        <div className="text-sm">
          <GaleriePieces pieces={pieces} photosSeulement hauteur="h-28" className="mb-3" />
          <span className="rounded-full bg-surface-deep px-2.5 py-0.5 font-semibold text-encre/60">
            analyse visuelle non réalisée
          </span>
          <p className="mt-1 text-encre/50">{g.commentaire}</p>
        </div>
      )
    }
    const couleurs = { leger: 'bg-ok-tint text-ok', moyen: 'bg-warn-tint text-warn', lourd: 'bg-bad-tint text-bad' }
    return (
      <div className="text-sm">
        <GaleriePieces pieces={pieces} photosSeulement hauteur="h-28" className="mb-3" />
        <span className={`rounded-full px-2.5 py-0.5 font-semibold ${couleurs[g.classe]}`}>gravité : {g.classe}</span>
        <span className="ml-3 text-encre/60">zones : {g.zones?.join(', ') || '—'}</span>
        <p className="mt-1 text-encre/50">{g.commentaire}</p>
      </div>
    )
  }
  if (categorie === 'vision' && s.analyse_coherence) {
    const c = s.analyse_coherence
    const indeterminable = c.coherence_declaration == null
    return (
      <div className="text-sm">
        <GaleriePieces pieces={pieces} photosSeulement hauteur="h-28" className="mb-3" />
        <span className={`rounded-full px-2.5 py-0.5 font-semibold ${
          indeterminable
            ? 'bg-surface-deep text-encre/60'
            : c.coherence_declaration ? 'bg-ok-tint text-ok' : 'bg-bad-tint text-bad'
        }`}>
          {indeterminable
            ? 'contrôle visuel non réalisé'
            : c.coherence_declaration
              ? '✓ photos cohérentes avec la déclaration'
              : '⚠ photos incohérentes avec la déclaration'}
        </span>
        {(indeterminable || !c.coherence_declaration) && (
          <>
            <p className="mt-1 text-encre/50">{c.commentaire}</p>
            {!indeterminable && c.verification_vehicule && (
              <div className="mt-2 rounded-md bg-bad-tint px-3 py-2 text-xs text-bad">
                <b>Véhicule : </b>incohérence détectée
                {' — '}{c.verification_vehicule.motif}
              </div>
            )}
          </>
        )}
      </div>
    )
  }
  if (categorie === 'garanties' && s.position_couverture) {
    const p = s.position_couverture
    return (
      <div className="text-sm">
        <div className={`mb-2 inline-block rounded-full px-2.5 py-0.5 font-semibold ${
          p.couvert ? 'bg-ok-tint text-ok' : 'bg-bad-tint text-bad'
        }`}>
          {p.couvert ? `✓ couvert — garantie ${p.garantie}` : `✗ non couvert (${p.motif_refus})`}
        </div>
        <ul className="grid gap-1">
          {p.motivation?.map((m, i) => (
            <li key={i} className="rounded bg-surface-deep px-2 py-1">
              <span className="text-encre/80">{m.conclusion}</span>
              <span className="ml-2 text-xs italic text-encre/40">{m.clause}</span>
            </li>
          ))}
        </ul>
      </div>
    )
  }
  if (categorie === 'indemnite' && s.detail_calcul) {
    return (
      <table className="w-full text-sm">
        <tbody>
          {s.detail_calcul.map((l, i) => {
            const total = l.etape.startsWith('MONTANT')
            return (
              <tr key={i} className={total ? 'border-t-2 border-encre/25 font-bold' : 'border-t border-line'}>
                <td className="py-1.5 pr-2">{l.etape}</td>
                <td className={`py-1.5 pr-2 text-right tabular-nums ${l.valeur < 0 ? 'text-bad' : ''}`}>
                  {l.valeur != null ? dt(l.valeur) : '—'}
                </td>
                <td className="py-1.5 text-xs text-encre/40">{l.source}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    )
  }
  if (categorie === 'hitl') return <p className="text-sm text-encre/80">🛡️ {s.routage}</p>
  if (categorie === 'courrier' && s.courrier)
    return <p className="text-sm text-encre/60">Courrier de décision : « {s.courrier.objet} »</p>
  return <p className="text-sm text-encre/50">Détail non disponible pour cette étape.</p>
}

const Champ = ({ nom, valeur, fort }) => (
  <div>
    <span className="text-xs uppercase tracking-wide text-encre/40">{nom}</span>
    <div className={fort ? 'font-semibold' : ''}>{String(valeur ?? '—')}</div>
  </div>
)

function Courrier({ courrier, etat }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <div className="mb-2 flex items-center gap-2">
        <span>✉️</span>
        <span className="font-semibold">Courrier de décision</span>
        <span className="ml-auto"><BadgeEtat etat={etat} /></span>
      </div>
      <div className="rounded-md border border-line bg-surface-deep p-4">
        <div className="border-b border-line pb-2 text-sm font-semibold">{courrier.objet}</div>
        <pre className="mt-2 whitespace-pre-wrap font-sans text-sm text-encre/75">{courrier.corps}</pre>
      </div>
    </div>
  )
}

/* ================= déclaration d'un nouveau sinistre ================= */

const EXEMPLE_DECLARATION =
  "Bonjour, ce matin sur la GP1 un camion a projeté un gravier qui a fissuré mon pare-brise. " +
  'Je joins le devis du poseur (380 DT). Mohamed Gharbi, police PA-2025-0212.'

// Import e-constat électronique préstructuré.
const CONSTAT_ELECTRONIQUE = {
  texte:
    "Constat électronique reçu, référence CE-2026-88213 : collision entre 2 " +
    "véhicules le 17/07/2026 à 18h20, avenue Mohamed V, Tunis. Véhicule A (assuré) : Volkswagen Golf 8, " +
    "immatriculation 225 TU 4817. Le véhicule B a heurté l'arrière du véhicule A à l'arrêt à un feu rouge ; " +
    "torts reconnus par B (case 8 cochée). Police PA-2024-1183, Ahmed Ben Salah. Le devis de réparation " +
    "sera transmis séparément par le garage.",
  police: 'PA-2024-1183',
  piece: { type: 'constat', chemin: 'docs/samples/constat.jpg', montant: null },
}

function FormulaireDeclaration({ onFermer, onCree }) {
  const [texte, setTexte] = useState('')
  const [police, setPolice] = useState('PA-2025-0212')
  const [montant, setMontant] = useState('380')
  const [pieceFtusa, setPieceFtusa] = useState(null)
  const [recuperation, setRecuperation] = useState(false)
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState(null)

  const recupererFtusa = () => {
    setRecuperation(true)
    setErreur(null)
    setTimeout(() => {
      setTexte(CONSTAT_ELECTRONIQUE.texte)
      setPolice(CONSTAT_ELECTRONIQUE.police)
      setPieceFtusa(CONSTAT_ELECTRONIQUE.piece)
      setMontant('')
      setRecuperation(false)
    }, 900)
  }

  const soumettre = async () => {
    setEnvoi(true)
    setErreur(null)
    try {
      const pieces = pieceFtusa
        ? [pieceFtusa]
        : montant
          ? [{ type: 'devis', chemin: 'docs/samples/devis-parebrise.jpg', montant: Number(montant) }]
          : []
      const nouveau = await api.declarerSinistre({ declaration_texte: texte, police_numero: police, pieces })
      onCree(nouveau)
    } catch (e) {
      setErreur(e.message)
      setEnvoi(false)
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-encre/50 p-4" onClick={onFermer}>
      <div className="w-full max-w-xl rounded-xl bg-surface p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold">Déclarer un sinistre</h3>
        <p className="mt-1 text-sm text-encre/50">
          Saisissez la déclaration en français ou en darija.
        </p>

        <button
          onClick={recupererFtusa}
          disabled={recuperation}
          className="mt-3 flex w-full items-center gap-2 rounded-md border border-dashed border-terracotta/40 bg-terracotta-tint/40 px-3 py-2 text-sm font-medium text-terracotta-deep transition hover:bg-terracotta-tint disabled:opacity-60"
        >
          <span>📡</span>
          {recuperation ? 'Import en cours…' : 'Importer un constat électronique'}
        </button>

        <textarea
          value={texte}
          onChange={(e) => { setTexte(e.target.value); setPieceFtusa(null) }}
          placeholder={EXEMPLE_DECLARATION}
          rows={5}
          className="mt-3 w-full rounded-md border border-line bg-creme p-3 text-sm focus:border-terracotta focus:outline-none"
        />
        {pieceFtusa && (
          <p className="mt-1.5 text-xs text-encre/50">
            📎 Constat importé — un devis chiffré sera requis avant le calcul de l'indemnité.
          </p>
        )}
        <div className="mt-3 flex gap-3">
          <label className="flex-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-encre/40">N° de police</span>
            <input value={police} onChange={(e) => setPolice(e.target.value)}
              className="mt-1 w-full rounded-md border border-line bg-creme p-2 font-mono text-sm" />
          </label>
          <label className="flex-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-encre/40">Montant devis joint (DT)</span>
            <input value={montant} onChange={(e) => { setMontant(e.target.value); setPieceFtusa(null) }} type="number"
              disabled={!!pieceFtusa}
              className="mt-1 w-full rounded-md border border-line bg-creme p-2 text-sm disabled:opacity-50" />
          </label>
        </div>
        {erreur && <p className="mt-2 text-sm text-bad">{erreur}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onFermer} className="rounded-md px-4 py-2 text-sm text-encre/60 hover:bg-surface-deep">
            Annuler
          </button>
          <button onClick={soumettre} disabled={!texte || !police || envoi}
            className="rounded-md bg-encre px-4 py-2 text-sm font-semibold text-creme hover:bg-encre/85 disabled:opacity-50">
            {envoi ? 'Création…' : 'Créer le dossier'}
          </button>
        </div>
      </div>
    </div>
  )
}
