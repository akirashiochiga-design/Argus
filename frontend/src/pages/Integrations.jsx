import { useEffect, useState } from 'react'
import { api } from '../api'

const SYSTEMES_ASSURANCE = [
  { id: 'guidewire', nom: 'Guidewire ClaimCenter', type: 'Sinistres', couleur: 'bg-[#F59E0B]', initiales: 'GW' },
  { id: 'duck-creek', nom: 'Duck Creek Claims', type: 'Core', couleur: 'bg-[#236192]', initiales: 'DC' },
  { id: 'sapiens', nom: 'Sapiens IDITSuite', type: 'Core', couleur: 'bg-[#6D4C9F]', initiales: 'SP' },
  { id: 'interne', nom: 'SI assurance interne', type: 'API · SQL · SFTP', couleur: 'bg-[#334155]', initiales: 'SI' },
]

const formule = (valeur) => (valeur === 'tous_risques' ? 'Tous risques' : 'Tiers')

export default function Integrations() {
  const [statut, setStatut] = useState(null)
  const [apercu, setApercu] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [action, setAction] = useState(null)
  const [message, setMessage] = useState(null)
  const [connecteurs, setConnecteurs] = useState([])
  const [ecrituresErp, setEcrituresErp] = useState([])
  const [onglet, setOnglet] = useState('polices')

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
        texte: `Connexion établie — ${resultat.polices_creees + resultat.polices_mises_a_jour} police(s) et ${resultat.sinistres_crees} sinistre(s) importés.`,
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
          ? `Bibliothèque connectée. Synchronisez d’abord CoreSinistre pour rattacher ${resultat.dossiers_introuvables.length} dossier(s) source.`
          : `${resultat.documents_importes} document(s) SharePoint importé(s), ${resultat.documents_ignores} déjà présent(s).`
      } else {
        texte = `${resultat.ecritures_envoyees} écriture(s) transmise(s) à l’ERP Finance interne.`
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
            Reliez Argus au SI assurance, aux documents et à la finance.
          </p>
        </div>
        <button
          onClick={connecter}
          disabled={action !== null}
          className="rounded-md bg-encre px-4 py-2.5 text-sm font-semibold text-creme transition hover:bg-encre/85 disabled:opacity-50"
        >
          {action === 'connexion'
            ? 'Synchronisation…'
            : connecte
              ? 'Actualiser'
              : 'Connecter CoreSinistre'}
        </button>
      </header>

      {message && (
        <div
          className={`flex items-start gap-3 rounded-lg px-4 py-3 text-sm ${
            message.ton === 'erreur' ? 'bg-bad-tint text-bad' : 'bg-ok-tint text-ok'
          }`}
        >
          <span className="mt-0.5 font-semibold">{message.ton === 'erreur' ? '!' : '✓'}</span>
          <span className="flex-1 leading-5">{message.texte}</span>
          <button type="button" onClick={() => setMessage(null)} className="opacity-50 hover:opacity-80">
            ×
          </button>
        </div>
      )}

      {/* Source principale */}
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
          {derniere && (
            <p className="text-xs text-encre/40">
              Dernier import · {derniere.polices_creees + derniere.polices_mises_a_jour} polices ·{' '}
              {derniere.sinistres_crees} sinistres · {derniere.duree_ms} ms
            </p>
          )}
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
      </section>

      {/* Aperçu données */}
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
              vide="Aucune police détectée."
              colonnes={['Police', 'Assuré', 'Véhicule', 'Formule']}
              lignes={polices.map((p) => [p.numero, p.assure, p.vehicule, formule(p.formule)])}
            />
          ) : (
            <TableApercu
              vide="Aucun sinistre disponible."
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

      {/* Flux annexes */}
      <section>
        <h3 className="mb-3 text-sm font-semibold text-encre/70">Flux connectés</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <LigneConnecteur
            initiales="SP"
            couleur="bg-[#038387]"
            titre="SharePoint Sinistres"
            detail={
              sharepoint
                ? `${sharepoint.documents_disponibles} document(s)`
                : 'Documents entrants'
            }
            connecte={sharepoint?.statut === 'connecte'}
            enCours={action === 'sharepoint_demo'}
            bloque={action !== null}
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
            onActiver={() => activerConnecteur('erp_interne_demo')}
          />
        </div>
      </section>

      {/* Catalogue discret */}
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
        onClick={onActiver}
        disabled={bloque}
        className="shrink-0 rounded-md border border-line px-3 py-1.5 text-xs font-semibold text-encre/70 transition hover:border-encre/20 hover:bg-surface-deep disabled:opacity-50"
      >
        {enCours ? '…' : connecte ? 'Sync' : 'Connecter'}
      </button>
    </div>
  )
}
