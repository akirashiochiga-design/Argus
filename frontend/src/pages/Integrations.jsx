import { useEffect, useState } from 'react'
import { api } from '../api'

const SYSTEMES_ASSURANCE = [
  { id: 'guidewire', nom: 'Guidewire ClaimCenter', couleur: 'bg-[#F59E0B]', initiales: 'GW' },
  { id: 'duck-creek', nom: 'Duck Creek Claims', couleur: 'bg-[#236192]', initiales: 'DC' },
  { id: 'sapiens', nom: 'Sapiens IDITSuite', couleur: 'bg-[#6D4C9F]', initiales: 'SP' },
  { id: 'interne', nom: 'SI assurance interne', couleur: 'bg-[#334155]', initiales: 'SI' },
]

const PIECES_SHAREPOINT = [
  { chemin: 'docs/samples/degats-3.jpg', libelle: 'Photo expertise' },
  { chemin: 'docs/samples/constat.jpg', libelle: 'Constat' },
  { chemin: 'docs/samples/facture.jpg', libelle: 'Facture' },
  { chemin: 'docs/samples/devis.jpg', libelle: 'Devis' },
]

const formule = (valeur) => (valeur === 'tous_risques' ? 'Tous risques' : 'Tiers')

const POLICE_DEMO = {
  assure_nom: 'Karim Mellouli',
  marque: 'Seat',
  modele: 'Leon',
  immatriculation: '246 TU 3310',
  formule: 'tous_risques',
  annee: 2022,
}

const SINISTRE_DEMO = {
  type_sinistre: 'collision',
  montant_estime: 2200,
  declaration:
    'Collision en sortie de parking le long du boulevard du 7 Novembre. ' +
    'Pare-chocs arrière et feu droit endommagés. Constat amiable joint.',
}

export default function Integrations() {
  const [statut, setStatut] = useState(null)
  const [apercu, setApercu] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [action, setAction] = useState(null)
  const [message, setMessage] = useState(null)
  const [connecteurs, setConnecteurs] = useState([])
  const [ecrituresErp, setEcrituresErp] = useState([])
  const [onglet, setOnglet] = useState('polices')
  const [panneau, setPanneau] = useState(null)

  const charger = async () => {
    try {
      const [etat, donnees, catalogue, ecritures] = await Promise.all([
        api.statutBaseAssurance(),
        api.apercuBaseAssurance(),
        api.listerConnecteurs(),
        api.listerEcrituresErp(),
      ])
      setStatut(etat)
      setApercu(donnees)
      setConnecteurs(catalogue)
      setEcrituresErp(ecritures)
    } catch (erreur) {
      setMessage({ ton: 'erreur', texte: erreur.message })
    } finally {
      setChargement(false)
    }
  }

  useEffect(() => {
    charger()
    const timer = setInterval(() => {
      api.statutBaseAssurance().then(setStatut).catch(() => {})
    }, 4000)
    return () => clearInterval(timer)
  }, [])

  const connecter = async () => {
    setAction('connexion')
    setMessage(null)
    try {
      await api.connecterBaseAssurance()
      const resultat = await api.synchroniserBaseAssurance()
      await charger()
      setMessage({
        ton: 'succes',
        texte: `Synchronisé — ${resultat.polices_creees + resultat.polices_mises_a_jour} police(s), ${resultat.sinistres_crees} nouveau(x) sinistre(s).`,
      })
    } catch (erreur) {
      await charger()
      setMessage({ ton: 'erreur', texte: erreur.message })
    } finally {
      setAction(null)
    }
  }

  const activerConnecteur = async (identifiant) => {
    setAction(identifiant)
    setMessage(null)
    try {
      await api.connecterConnecteur(identifiant)
      const resultat = await api.synchroniserConnecteur(identifiant)
      await charger()
      let texte
      if (identifiant === 'sharepoint_demo') {
        texte = resultat.dossiers_introuvables?.length
          ? `SharePoint prêt. ${resultat.dossiers_introuvables.length} dossier(s) encore absents d’Argus.`
          : `${resultat.documents_importes} document(s) importé(s), ${resultat.documents_ignores} déjà présent(s).`
      } else {
        texte = `${resultat.ecritures_envoyees} écriture(s) transmise(s) à l’ERP Finance.`
      }
      setMessage({ ton: 'succes', texte })
    } catch (erreur) {
      setMessage({ ton: 'erreur', texte: erreur.message })
    } finally {
      setAction(null)
    }
  }

  if (chargement) {
    return <p className="text-sm text-encre/50">Vérification de la source de données…</p>
  }

  const derniere = statut?.derniere_synchronisation
  const compteurs = statut?.compteurs ?? {}
  const connecte = statut?.statut === 'connecte'
  const sharepoint = connecteurs.find((item) => item.identifiant === 'sharepoint_demo')
  const erpInterne = connecteurs.find((item) => item.identifiant === 'erp_interne_demo')
  const polices = apercu?.apercu_polices ?? []
  const sinistres = apercu?.apercu_sinistres ?? []
  const erpAttente = ecrituresErp.filter((item) => item.statut === 'planifiee').length
  const erpEnvoyees = ecrituresErp.filter((item) => item.statut === 'envoyee').length

  return (
    <div className="mx-auto grid max-w-5xl gap-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Intégrations</h2>
          <p className="mt-1 max-w-xl text-sm leading-6 text-encre/50">
            Ouvrez le SI source, ajoutez un contrat ou un sinistre, puis synchronisez vers Argus.
          </p>
        </div>
        <button
          onClick={connecter}
          disabled={action !== null}
          className="rounded-md bg-encre px-4 py-2.5 text-sm font-semibold text-creme transition hover:bg-encre/85 disabled:opacity-50"
        >
          {action === 'connexion' ? 'Synchronisation…' : connecte ? 'Synchroniser Argus' : 'Connecter & synchroniser'}
        </button>
      </header>

      {message && (
        <div className={`flex items-start gap-3 rounded-lg px-4 py-3 text-sm ${
          message.ton === 'erreur' ? 'bg-bad-tint text-bad' : 'bg-ok-tint text-ok'
        }`}>
          <span className="mt-0.5 font-semibold">{message.ton === 'erreur' ? '!' : '✓'}</span>
          <span className="flex-1 leading-5">{message.texte}</span>
          <button type="button" onClick={() => setMessage(null)} className="opacity-50 hover:opacity-80">×</button>
        </div>
      )}

      <section className="overflow-hidden rounded-2xl border border-line bg-surface">
        <div className="flex flex-wrap items-center gap-4 border-b border-line px-6 py-5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-encre text-[11px] font-bold tracking-wide text-creme">
            CS
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-semibold">{statut?.source ?? 'CoreSinistre'}</h3>
              <StatutPoint actif={connecte} libelle={connecte ? 'Connecté' : 'Hors ligne'} />
            </div>
            <p className="mt-0.5 truncate text-sm text-encre/45">
              {statut?.organisation}
              {statut?.latence_ms != null ? ` · ${statut.latence_ms} ms` : ''}
            </p>
          </div>
          <button
            type="button"
            onClick={() => setPanneau('coresinistre')}
            className="rounded-md border border-line px-3 py-2 text-xs font-semibold text-encre/70 transition hover:bg-surface-deep"
          >
            Ouvrir le SI
          </button>
        </div>
        <div className="grid grid-cols-3 divide-x divide-line">
          {[
            ['Polices', compteurs.polices ?? 0],
            ['Sinistres', compteurs.sinistres ?? 0],
            ['Pièces', compteurs.pieces ?? 0],
          ].map(([libelle, valeur]) => (
            <div key={libelle} className="px-6 py-4">
              <div className="text-2xl font-semibold tabular-nums tracking-tight">{valeur}</div>
              <div className="mt-0.5 text-xs text-encre/40">{libelle}</div>
            </div>
          ))}
        </div>
        {derniere && (
          <p className="border-t border-line px-6 py-3 text-xs text-encre/40">
            Dernier import · {derniere.polices_creees + derniere.polices_mises_a_jour} polices ·{' '}
            {derniere.sinistres_crees} sinistres · {derniere.duree_ms} ms
          </p>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-center gap-1 border-b border-line">
          {[
            ['polices', 'Contrats', polices.length],
            ['sinistres', 'Sinistres', sinistres.length],
          ].map(([id, libelle, n]) => (
            <button
              key={id}
              type="button"
              onClick={() => setOnglet(id)}
              className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-medium transition ${
                onglet === id
                  ? 'border-terracotta text-encre'
                  : 'border-transparent text-encre/40 hover:text-encre/70'
              }`}
            >
              {libelle}
              <span className="ml-1.5 tabular-nums text-encre/30">{n}</span>
            </button>
          ))}
        </div>
        <div className="overflow-hidden rounded-xl border border-line bg-surface">
          {onglet === 'polices' ? (
            <TableApercu
              vide="Aucune police. Ouvrez CoreSinistre pour en ajouter une."
              colonnes={['Police', 'Assuré', 'Véhicule', 'Formule']}
              lignes={polices.map((p) => [p.numero, p.assure, p.vehicule, formule(p.formule)])}
            />
          ) : (
            <TableApercu
              vide="Aucun sinistre. Ouvrez CoreSinistre pour en déclarer un."
              colonnes={['Référence', 'Police', 'Type', 'Pièces']}
              lignes={sinistres.map((s) => [
                s.reference,
                s.police_numero,
                s.type_sinistre.replace('_', ' '),
                s.nombre_pieces,
              ])}
            />
          )}
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold text-encre/70">Flux connectés</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <LigneConnecteur
            initiales="SP"
            couleur="bg-[#038387]"
            titre="SharePoint Sinistres"
            detail={sharepoint ? `${sharepoint.documents_disponibles} document(s)` : 'Documents entrants'}
            connecte={sharepoint?.statut === 'connecte'}
            enCours={action === 'sharepoint_demo'}
            bloque={action !== null}
            onOuvrir={() => setPanneau('sharepoint')}
            onActiver={() => activerConnecteur('sharepoint_demo')}
          />
          <LigneConnecteur
            initiales="ERP"
            couleur="bg-[#334155]"
            titre="ERP Finance"
            detail={`${erpAttente} en attente · ${erpEnvoyees} envoyée(s)`}
            connecte={erpInterne?.statut === 'connecte'}
            enCours={action === 'erp_interne_demo'}
            bloque={action !== null}
            onOuvrir={() => setPanneau('erp')}
            onActiver={() => activerConnecteur('erp_interne_demo')}
          />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold text-encre/70">Autres cores disponibles</h3>
        <div className="flex flex-wrap gap-2">
          {SYSTEMES_ASSURANCE.map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-2.5 rounded-full border border-line bg-surface py-1.5 pl-1.5 pr-3.5"
            >
              <span className={`flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white ${item.couleur}`}>
                {item.initiales}
              </span>
              <span className="text-sm text-encre/75">{item.nom}</span>
            </div>
          ))}
        </div>
      </section>

      {panneau === 'coresinistre' && (
        <PanneauCoreSinistre
          onFermer={() => setPanneau(null)}
          onChange={async (texte) => {
            await charger()
            setMessage({ ton: 'succes', texte })
          }}
          onErreur={(texte) => setMessage({ ton: 'erreur', texte })}
          onSync={connecter}
          syncEnCours={action === 'connexion'}
        />
      )}
      {panneau === 'sharepoint' && (
        <PanneauSharePoint
          onFermer={() => setPanneau(null)}
          onChange={async (texte) => {
            await charger()
            setMessage({ ton: 'succes', texte })
          }}
          onErreur={(texte) => setMessage({ ton: 'erreur', texte })}
          onSync={() => activerConnecteur('sharepoint_demo')}
          syncEnCours={action === 'sharepoint_demo'}
          refsSinistres={sinistres.map((s) => s.reference)}
        />
      )}
      {panneau === 'erp' && (
        <PanneauErp
          onFermer={() => setPanneau(null)}
          ecritures={ecrituresErp}
          onSync={() => activerConnecteur('erp_interne_demo')}
          syncEnCours={action === 'erp_interne_demo'}
        />
      )}
    </div>
  )
}

function StatutPoint({ actif, libelle }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
      actif ? 'bg-ok-tint text-ok' : 'bg-surface-deep text-encre/45'
    }`}>
      <span className={`h-1.5 w-1.5 rounded-full ${actif ? 'bg-ok' : 'bg-encre/30'}`} />
      {libelle}
    </span>
  )
}

function TableApercu({ colonnes, lignes, vide }) {
  if (lignes.length === 0) {
    return <p className="px-5 py-10 text-center text-sm text-encre/40">{vide}</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-xs text-encre/40">
            {colonnes.map((c) => (
              <th key={c} className="px-5 py-3 font-medium">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lignes.map((ligne, i) => (
            <tr key={i} className="border-b border-line/70 last:border-0">
              {ligne.map((cellule, j) => (
                <td
                  key={j}
                  className={`px-5 py-3.5 ${j === 0 ? 'font-medium text-encre' : 'text-encre/65'} ${j === 2 ? 'capitalize' : ''}`}
                >
                  {cellule}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function LigneConnecteur({
  initiales,
  couleur,
  titre,
  detail,
  connecte,
  enCours,
  bloque,
  onOuvrir,
  onActiver,
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-line bg-surface px-4 py-3.5">
      <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[10px] font-bold text-white ${couleur}`}>
        {initiales}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-semibold">{titre}</span>
          <StatutPoint actif={connecte} libelle={connecte ? 'Actif' : 'Prêt'} />
        </div>
        <p className="mt-0.5 truncate text-xs text-encre/45">{detail}</p>
      </div>
      <button
        type="button"
        onClick={onOuvrir}
        className="shrink-0 rounded-md border border-line px-3 py-1.5 text-xs font-semibold text-encre/70 transition hover:bg-surface-deep"
      >
        Ouvrir
      </button>
      <button
        type="button"
        onClick={onActiver}
        disabled={bloque}
        className="shrink-0 rounded-md bg-encre px-3 py-1.5 text-xs font-semibold text-creme disabled:opacity-50"
      >
        {enCours ? '…' : connecte ? 'Sync' : 'Connecter'}
      </button>
    </div>
  )
}

function Overlay({ titre, sousTitre, onFermer, children, pied }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-encre/45 p-4" onClick={onFermer}>
      <div
        className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-surface shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-3 border-b border-line px-6 py-4">
          <div className="min-w-0 flex-1">
            <h3 className="text-lg font-semibold">{titre}</h3>
            {sousTitre && <p className="mt-0.5 text-sm text-encre/45">{sousTitre}</p>}
          </div>
          <button type="button" onClick={onFermer} className="rounded-md px-2 py-1 text-encre/40 hover:bg-surface-deep">
            ×
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {pied && <div className="border-t border-line px-6 py-4">{pied}</div>}
      </div>
    </div>
  )
}

function PanneauCoreSinistre({ onFermer, onChange, onErreur, onSync, syncEnCours }) {
  const [inventaire, setInventaire] = useState(null)
  const [mode, setMode] = useState('sinistre')
  const [envoi, setEnvoi] = useState(false)
  const [policeForm, setPoliceForm] = useState(POLICE_DEMO)
  const [sinistreForm, setSinistreForm] = useState(SINISTRE_DEMO)

  const charger = async () => {
    setInventaire(await api.inventaireBaseAssurance())
  }

  useEffect(() => {
    charger().catch((e) => onErreur(e.message))
  }, [])

  useEffect(() => {
    if (inventaire?.apercu_polices?.length && !sinistreForm.police_numero) {
      setSinistreForm((s) => ({
        ...s,
        police_numero: inventaire.apercu_polices[0].numero,
      }))
    }
  }, [inventaire])

  const soumettrePolice = async (e) => {
    e.preventDefault()
    setEnvoi(true)
    try {
      const cree = await api.creerPoliceSource(policeForm)
      await charger()
      setMode('sinistre')
      setSinistreForm((s) => ({ ...s, police_numero: cree.numero }))
      await onChange(`Contrat ${cree.numero} ajouté dans CoreSinistre. Synchronisez pour le voir dans Argus.`)
    } catch (erreur) {
      onErreur(erreur.message)
    } finally {
      setEnvoi(false)
    }
  }

  const soumettreSinistre = async (e) => {
    e.preventDefault()
    setEnvoi(true)
    try {
      const cree = await api.creerSinistreSource(sinistreForm)
      await charger()
      await onChange(`Sinistre ${cree.reference} déclaré dans CoreSinistre. Synchronisez pour l’importer dans Argus.`)
    } catch (erreur) {
      onErreur(erreur.message)
    } finally {
      setEnvoi(false)
    }
  }

  const polices = inventaire?.apercu_polices ?? []
  const sinistres = inventaire?.apercu_sinistres ?? []

  return (
    <Overlay
      titre="CoreSinistre"
      sousTitre="Système source — ajoutez ici, puis synchronisez vers Argus"
      onFermer={onFermer}
      pied={(
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onFermer} className="rounded-md px-4 py-2 text-sm text-encre/60">
            Fermer
          </button>
          <button
            type="button"
            onClick={onSync}
            disabled={syncEnCours}
            className="rounded-md bg-terracotta px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {syncEnCours ? 'Synchronisation…' : 'Synchroniser vers Argus'}
          </button>
        </div>
      )}
    >
      <div className="mb-5 flex gap-1 rounded-lg bg-surface-deep p-1">
        {[
          ['sinistre', 'Nouveau sinistre'],
          ['police', 'Nouveau contrat'],
          ['liste', 'Inventaire'],
        ].map(([id, libelle]) => (
          <button
            key={id}
            type="button"
            onClick={() => setMode(id)}
            className={`flex-1 rounded-md px-3 py-2 text-xs font-semibold ${
              mode === id ? 'bg-surface text-encre shadow-sm' : 'text-encre/45'
            }`}
          >
            {libelle}
          </button>
        ))}
      </div>

      {mode === 'police' && (
        <form className="grid gap-3 sm:grid-cols-2" onSubmit={soumettrePolice}>
          <Champ libelle="Assuré">
            <input className={inputClass} value={policeForm.assure_nom} onChange={(e) => setPoliceForm({ ...policeForm, assure_nom: e.target.value })} required />
          </Champ>
          <Champ libelle="Immatriculation">
            <input className={inputClass} value={policeForm.immatriculation} onChange={(e) => setPoliceForm({ ...policeForm, immatriculation: e.target.value })} required />
          </Champ>
          <Champ libelle="Marque">
            <input className={inputClass} value={policeForm.marque} onChange={(e) => setPoliceForm({ ...policeForm, marque: e.target.value })} required />
          </Champ>
          <Champ libelle="Modèle">
            <input className={inputClass} value={policeForm.modele} onChange={(e) => setPoliceForm({ ...policeForm, modele: e.target.value })} required />
          </Champ>
          <Champ libelle="Formule">
            <select className={inputClass} value={policeForm.formule} onChange={(e) => setPoliceForm({ ...policeForm, formule: e.target.value })}>
              <option value="tous_risques">Tous risques</option>
              <option value="tiers">Tiers</option>
            </select>
          </Champ>
          <Champ libelle="Année">
            <input type="number" className={inputClass} value={policeForm.annee} onChange={(e) => setPoliceForm({ ...policeForm, annee: Number(e.target.value) })} />
          </Champ>
          <button type="submit" disabled={envoi} className="sm:col-span-2 justify-self-end rounded-md bg-encre px-4 py-2 text-sm font-semibold text-creme disabled:opacity-50">
            {envoi ? 'Enregistrement…' : 'Ajouter le contrat dans CoreSinistre'}
          </button>
        </form>
      )}

      {mode === 'sinistre' && (
        <form className="grid gap-3" onSubmit={soumettreSinistre}>
          <Champ libelle="Police source">
            <select
              className={inputClass}
              value={sinistreForm.police_numero || ''}
              onChange={(e) => setSinistreForm({ ...sinistreForm, police_numero: e.target.value })}
              required
            >
              <option value="" disabled>Choisir une police</option>
              {polices.map((p) => (
                <option key={p.numero} value={p.numero}>
                  {p.numero} — {p.assure} ({p.vehicule})
                </option>
              ))}
            </select>
          </Champ>
          <div className="grid gap-3 sm:grid-cols-2">
            <Champ libelle="Type">
              <select className={inputClass} value={sinistreForm.type_sinistre} onChange={(e) => setSinistreForm({ ...sinistreForm, type_sinistre: e.target.value })}>
                <option value="collision">Collision</option>
                <option value="bris_glace">Bris de glace</option>
              </select>
            </Champ>
            <Champ libelle="Montant estimé (DT)">
              <input
                type="number"
                className={inputClass}
                value={sinistreForm.montant_estime ?? ''}
                onChange={(e) => setSinistreForm({ ...sinistreForm, montant_estime: e.target.value ? Number(e.target.value) : null })}
              />
            </Champ>
          </div>
          <Champ libelle="Déclaration">
            <textarea
              rows={4}
              className={textareaClass}
              value={sinistreForm.declaration}
              onChange={(e) => setSinistreForm({ ...sinistreForm, declaration: e.target.value })}
              required
            />
          </Champ>
          <button type="submit" disabled={envoi || !sinistreForm.police_numero} className="justify-self-end rounded-md bg-encre px-4 py-2 text-sm font-semibold text-creme disabled:opacity-50">
            {envoi ? 'Enregistrement…' : 'Déclarer dans CoreSinistre'}
          </button>
        </form>
      )}

      {mode === 'liste' && (
        <div className="grid gap-4">
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-encre/40">
              Contrats ({polices.length})
            </h4>
            <div className="overflow-hidden rounded-lg border border-line">
              <TableApercu
                vide="Aucun contrat"
                colonnes={['Police', 'Assuré', 'Véhicule', 'Formule']}
                lignes={polices.map((p) => [p.numero, p.assure, p.vehicule, formule(p.formule)])}
              />
            </div>
          </div>
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-encre/40">
              Sinistres ({sinistres.length})
            </h4>
            <div className="overflow-hidden rounded-lg border border-line">
              <TableApercu
                vide="Aucun sinistre"
                colonnes={['Réf.', 'Police', 'Type', 'Pièces']}
                lignes={sinistres.map((s) => [s.reference, s.police_numero, s.type_sinistre, s.nombre_pieces])}
              />
            </div>
          </div>
        </div>
      )}
    </Overlay>
  )
}

function PanneauSharePoint({ onFermer, onChange, onErreur, onSync, syncEnCours, refsSinistres }) {
  const [docs, setDocs] = useState([])
  const [envoi, setEnvoi] = useState(false)
  const [form, setForm] = useState({
    dossier_ref: refsSinistres[0] || 'EXT-SIN-2026-1002',
    type: 'photo_expertise',
    chemin: PIECES_SHAREPOINT[0].chemin,
  })

  useEffect(() => {
    api.listerDocumentsSharePoint()
      .then((d) => setDocs(d.documents || []))
      .catch((e) => onErreur(e.message))
  }, [])

  const soumettre = async (e) => {
    e.preventDefault()
    setEnvoi(true)
    try {
      const doc = await api.ajouterDocumentSharePoint(form)
      const maj = await api.listerDocumentsSharePoint()
      setDocs(maj.documents || [])
      await onChange(`Document « ${doc.nom_source} » déposé pour ${doc.dossier_ref}. Synchronisez pour l’attacher au dossier Argus.`)
    } catch (erreur) {
      onErreur(erreur.message)
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <Overlay
      titre="SharePoint Sinistres"
      sousTitre="Bibliothèque documentaire — déposez une pièce puis synchronisez"
      onFermer={onFermer}
      pied={(
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onFermer} className="rounded-md px-4 py-2 text-sm text-encre/60">Fermer</button>
          <button type="button" onClick={onSync} disabled={syncEnCours} className="rounded-md bg-terracotta px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {syncEnCours ? 'Synchronisation…' : 'Synchroniser vers Argus'}
          </button>
        </div>
      )}
    >
      <form className="mb-5 grid gap-3 sm:grid-cols-3" onSubmit={soumettre}>
        <Champ libelle="Dossier">
          <input className={inputClass} list="refs-sp" value={form.dossier_ref} onChange={(e) => setForm({ ...form, dossier_ref: e.target.value })} required />
          <datalist id="refs-sp">
            {refsSinistres.map((ref) => <option key={ref} value={ref} />)}
          </datalist>
        </Champ>
        <Champ libelle="Type">
          <select className={inputClass} value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
            <option value="photo_expertise">Photo expertise</option>
            <option value="constat">Constat</option>
            <option value="facture">Facture</option>
            <option value="devis">Devis</option>
          </select>
        </Champ>
        <Champ libelle="Fichier">
          <select className={inputClass} value={form.chemin} onChange={(e) => setForm({ ...form, chemin: e.target.value })}>
            {PIECES_SHAREPOINT.map((p) => (
              <option key={p.chemin} value={p.chemin}>{p.libelle}</option>
            ))}
          </select>
        </Champ>
        <button type="submit" disabled={envoi} className="sm:col-span-3 justify-self-end rounded-md bg-encre px-4 py-2 text-sm font-semibold text-creme disabled:opacity-50">
          {envoi ? 'Dépôt…' : 'Déposer dans SharePoint'}
        </button>
      </form>
      <div className="overflow-hidden rounded-lg border border-line">
        <TableApercu
          vide="Aucun document"
          colonnes={['Dossier', 'Type', 'Fichier']}
          lignes={docs.map((d) => [d.dossier_ref, d.type, d.nom_source])}
        />
      </div>
    </Overlay>
  )
}

function PanneauErp({ onFermer, ecritures, onSync, syncEnCours }) {
  return (
    <Overlay
      titre="ERP Finance"
      sousTitre="Écritures sortantes après validation humaine"
      onFermer={onFermer}
      pied={(
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onFermer} className="rounded-md px-4 py-2 text-sm text-encre/60">Fermer</button>
          <button type="button" onClick={onSync} disabled={syncEnCours} className="rounded-md bg-terracotta px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {syncEnCours ? 'Envoi…' : 'Envoyer les écritures planifiées'}
          </button>
        </div>
      )}
    >
      <p className="mb-4 text-sm text-encre/50">
        Les écritures apparaissent ici une fois le montant validé dans Approbations.
      </p>
      <div className="overflow-hidden rounded-lg border border-line">
        <TableApercu
          vide="Aucune écriture pour le moment"
          colonnes={['Dossier', 'Montant', 'Statut']}
          lignes={ecritures.map((e) => [
            e.dossier_ref || `#${e.dossier_id}`,
            `${e.montant} DT`,
            e.statut,
          ])}
        />
      </div>
    </Overlay>
  )
}

const inputClass = 'w-full rounded-md border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-terracotta'
const textareaClass = `${inputClass} resize-none`

function Champ({ libelle, children }) {
  return (
    <label className="grid gap-1 text-xs font-medium text-encre/55">
      {libelle}
      {children}
    </label>
  )
}
