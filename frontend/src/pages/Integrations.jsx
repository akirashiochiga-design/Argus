import { useEffect, useState } from 'react'
import { api } from '../api'

const SYSTEMES_ASSURANCE = [
  { id: 'guidewire', nom: 'Guidewire ClaimCenter', type: 'Gestion des sinistres', couleur: 'bg-[#F59E0B]', initiales: 'GW' },
  { id: 'duck-creek', nom: 'Duck Creek Claims', type: 'Core sinistres', couleur: 'bg-[#236192]', initiales: 'DC' },
  { id: 'sapiens', nom: 'Sapiens IDITSuite', type: 'Core assurance', couleur: 'bg-[#6D4C9F]', initiales: 'SP' },
  { id: 'interne', nom: 'SI assurance interne', type: 'API · SQL · SFTP', couleur: 'bg-[#334155]', initiales: 'SI' },
]

const formule = (valeur) => valeur === 'tous_risques' ? 'Tous risques' : 'Tiers'

export default function Integrations() {
  const [statut, setStatut] = useState(null)
  const [apercu, setApercu] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [action, setAction] = useState(null)
  const [message, setMessage] = useState(null)
  const [connecteurs, setConnecteurs] = useState([])
  const [ecrituresErp, setEcrituresErp] = useState([])

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
          ? `Bibliothèque connectée. Synchronisez d’abord AssurCore pour rattacher ${resultat.dossiers_introuvables.length} dossier(s) source.`
          : `${resultat.documents_importes} document(s) SharePoint importé(s), ${resultat.documents_ignores} déjà présent(s).`
      } else {
        texte = `${resultat.ecritures_envoyees} écriture(s) transmise(s) à l’ERP interne de démonstration.`
      }
      setMessage({ ton: 'succes', texte })
    } catch (erreur) {
      setMessage({ ton: 'erreur', texte: erreur.message })
    } finally {
      setAction(null)
    }
  }

  if (chargement) return <p className="text-sm text-encre/50">Vérification de la source de données…</p>

  const derniere = statut?.derniere_synchronisation
  const compteurs = statut?.compteurs ?? {}
  const connecte = statut?.statut === 'connecte'
  const sharepoint = connecteurs.find((item) => item.identifiant === 'sharepoint_demo')
  const erpInterne = connecteurs.find((item) => item.identifiant === 'erp_interne_demo')

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <h2 className="text-lg font-semibold">Intégrations</h2>
          <p className="mt-1 text-sm text-encre/50">
            Connectez Argus aux contrats, véhicules et sinistres du système d&apos;information assurance.
          </p>
        </div>
        <button
          onClick={connecter}
          disabled={action !== null}
          className="ml-auto rounded-md bg-encre px-4 py-2 text-sm font-semibold text-creme transition hover:bg-encre/85 disabled:opacity-50"
        >
          {action === 'connexion'
            ? 'Connexion et import…'
            : statut?.statut === 'connecte'
              ? 'Actualiser les données'
              : 'Se connecter'}
        </button>
      </div>

      {message && (
        <div className={`flex items-center gap-2 rounded-lg border px-4 py-3 text-sm ${
          message.ton === 'erreur'
            ? 'border-bad/30 bg-bad-tint text-bad'
            : 'border-ok/30 bg-ok-tint text-ok'
        }`}>
          <span>{message.ton === 'erreur' ? '!' : '✓'}</span>
          <span>{message.texte}</span>
          <button onClick={() => setMessage(null)} className="ml-auto opacity-60">×</button>
        </div>
      )}

      <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
        <div className="flex flex-wrap items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#334155] text-xs font-bold text-white">
            DB
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold">{statut?.source ?? 'Base assurance'}</h3>
              <span className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
                connecte ? 'bg-ok-tint text-ok' : 'bg-bad-tint text-bad'
              }`}>
                <span className={`h-2 w-2 rounded-full ${connecte ? 'bg-ok' : 'bg-bad'}`} />
                {connecte ? 'Connectée' : 'Indisponible'}
              </span>
            </div>
            <p className="mt-1 text-sm text-encre/50">
              {statut?.organisation} · {statut?.fichier} · schéma v{statut?.schema_version}
            </p>
            <p className="mt-1 text-xs text-encre/40">
              {connecte
                ? 'Accès en lecture seule, synchronisation contrôlée vers Argus.'
                : 'Base source disponible, non reliée à la plateforme.'}
            </p>
          </div>
          <div className="ml-auto text-right text-xs text-encre/45">
            <div>Dernier test : {statut?.latence_ms ?? 0} ms</div>
            <div>{statut?.tables?.length ?? 0} tables validées</div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          {[
            ['Polices actives', compteurs.polices ?? 0],
            ['Sinistres disponibles', compteurs.sinistres ?? 0],
            ['Pièces rattachées', compteurs.pieces ?? 0],
          ].map(([libelle, valeur]) => (
            <div key={libelle} className="rounded-lg bg-surface-deep p-3">
              <div className="text-2xl font-semibold">{valeur}</div>
              <div className="text-xs text-encre/45">{libelle}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <div className="overflow-hidden rounded-xl border border-line bg-surface">
          <div className="border-b border-line px-5 py-4">
            <h3 className="font-semibold">Contrats détectés</h3>
            <p className="text-xs text-encre/45">Aperçu anonymisé lu directement dans le SI source</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-deep text-encre/45">
                <tr>
                  <th className="px-4 py-2 font-medium">Police</th>
                  <th className="px-4 py-2 font-medium">Assuré</th>
                  <th className="px-4 py-2 font-medium">Véhicule</th>
                  <th className="px-4 py-2 font-medium">Formule</th>
                </tr>
              </thead>
              <tbody>
                {(apercu?.apercu_polices ?? []).map((police) => (
                  <tr key={police.numero} className="border-t border-line">
                    <td className="px-4 py-3 font-semibold">{police.numero}</td>
                    <td className="px-4 py-3">{police.assure}</td>
                    <td className="px-4 py-3">{police.vehicule}</td>
                    <td className="px-4 py-3">{formule(police.formule)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-line bg-surface">
          <div className="border-b border-line px-5 py-4">
            <h3 className="font-semibold">Sinistres disponibles</h3>
            <p className="text-xs text-encre/45">Dossiers prêts à être intégrés au parcours de traitement</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-deep text-encre/45">
                <tr>
                  <th className="px-4 py-2 font-medium">Référence</th>
                  <th className="px-4 py-2 font-medium">Police</th>
                  <th className="px-4 py-2 font-medium">Type</th>
                  <th className="px-4 py-2 font-medium">Pièces</th>
                </tr>
              </thead>
              <tbody>
                {(apercu?.apercu_sinistres ?? []).map((sinistre) => (
                  <tr key={sinistre.reference} className="border-t border-line">
                    <td className="px-4 py-3 font-semibold">{sinistre.reference}</td>
                    <td className="px-4 py-3">{sinistre.police_numero}</td>
                    <td className="px-4 py-3 capitalize">{sinistre.type_sinistre.replace('_', ' ')}</td>
                    <td className="px-4 py-3">{sinistre.nombre_pieces}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-line bg-surface p-5">
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <h3 className="font-semibold">Dernière synchronisation</h3>
            <p className="mt-0.5 text-sm text-encre/50">
              Import idempotent : une même police ou un même sinistre ne sont jamais dupliqués.
            </p>
          </div>
          <span className={`ml-auto rounded-full px-3 py-1 text-xs font-semibold ${
            derniere ? 'bg-ok-tint text-ok' : 'bg-surface-deep text-encre/45'
          }`}>
            {derniere ? 'Synchronisé' : 'Aucun import'}
          </span>
        </div>
        {derniere && (
          <div className="mt-4 grid gap-3 sm:grid-cols-4">
            {[
              ['Polices créées', derniere.polices_creees],
              ['Polices mises à jour', derniere.polices_mises_a_jour],
              ['Sinistres créés', derniere.sinistres_crees],
              ['Durée', `${derniere.duree_ms} ms`],
            ].map(([libelle, valeur]) => (
              <div key={libelle} className="rounded-lg bg-surface-deep p-3">
                <div className="font-semibold">{valeur}</div>
                <div className="text-xs text-encre/45">{libelle}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-xl border border-terracotta/25 bg-terracotta-tint/40 p-5">
        <div className="flex flex-wrap items-start gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-terracotta-deep">
              Connexion rapide
            </div>
            <h3 className="mt-1 font-semibold">Un adaptateur, pas une réécriture du SI</h3>
            <p className="mt-1 max-w-2xl text-sm text-encre/55">
              Les données sont traduites vers le modèle Argus par un Relay déployé chez
              l’assureur. Les agents ne reçoivent ni identifiants ERP ni accès réseau libre.
            </p>
          </div>
          <span className="ml-auto rounded-full bg-surface px-3 py-1 text-xs font-semibold text-encre/60">
            REST · SQL lecture seule · SFTP · Graph
          </span>
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-4">
          {[
            ['1', 'Choisir', 'Pack ERP ou connecteur universel'],
            ['2', 'Tester', 'Schéma et droits minimaux'],
            ['3', 'Mapper', 'Champs vers Police, Dossier, Pièce'],
            ['4', 'Activer', 'Dry-run, audit et reprise sur erreur'],
          ].map(([numero, titre, detail]) => (
            <div key={numero} className="rounded-lg bg-surface p-3">
              <div className="text-xs font-bold text-terracotta">{numero} · {titre}</div>
              <div className="mt-1 text-xs leading-5 text-encre/50">{detail}</div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="mb-3">
          <h3 className="font-semibold">Adaptateurs actifs</h3>
          <p className="text-xs text-encre/45">
            Preuves locales du même contrat d’intégration utilisé par AssurCore.
          </p>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <CarteConnecteur
            connecteur={sharepoint}
            titre="SharePoint Sinistres"
            sousTitre="Documents entrants · Microsoft Graph en production"
            initiales="SP"
            couleur="bg-[#038387]"
            action={action}
            onActiver={() => activerConnecteur('sharepoint_demo')}
            detail={sharepoint
              ? `${sharepoint.documents_disponibles} document(s) disponibles · environnement démo`
              : 'Bibliothèque documentaire locale de démonstration'}
          />
          <CarteConnecteur
            connecteur={erpInterne}
            titre="ERP Finance interne"
            sousTitre="Écritures sortantes vers le SI de l’assureur"
            initiales="SI"
            couleur="bg-[#334155]"
            action={action}
            onActiver={() => activerConnecteur('erp_interne_demo')}
            detail={`${ecrituresErp.filter((item) => item.statut === 'planifiee').length} en attente · ${ecrituresErp.filter((item) => item.statut === 'envoyee').length} envoyée(s)`}
          />
        </div>
      </section>

      <section>
        <h3 className="mb-3 font-semibold">Cores assurance et systèmes internes prêts à configurer</h3>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {SYSTEMES_ASSURANCE.map((connecteur) => (
            <div key={connecteur.id} className="rounded-xl border border-line bg-surface p-5">
              <div className="flex items-start gap-3">
                <div className={`flex h-10 w-10 items-center justify-center rounded-lg text-xs font-bold text-white ${connecteur.couleur}`}>
                  {connecteur.initiales}
                </div>
                <div>
                  <div className="font-semibold">{connecteur.nom}</div>
                  <div className="text-xs text-encre/45">{connecteur.type}</div>
                </div>
              </div>
              <div className="mt-5 text-xs font-medium text-encre/40">Pack disponible</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function CarteConnecteur({
  connecteur,
  titre,
  sousTitre,
  initiales,
  couleur,
  detail,
  action,
  onActiver,
}) {
  const connecte = connecteur?.statut === 'connecte'
  const enCours = action === connecteur?.identifiant
  return (
    <article className="rounded-xl border border-line bg-surface p-5 shadow-sm">
      <div className="flex items-start gap-3">
        <div className={`flex h-11 w-11 items-center justify-center rounded-lg text-xs font-bold text-white ${couleur}`}>
          {initiales}
        </div>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-semibold">{titre}</h4>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
              connecte ? 'bg-ok-tint text-ok' : 'bg-surface-deep text-encre/45'
            }`}>
              {connecte ? 'Connecté' : 'Prêt à connecter'}
            </span>
          </div>
          <p className="text-xs text-encre/45">{sousTitre}</p>
        </div>
      </div>
      <p className="mt-4 text-sm text-encre/55">{detail}</p>
      <div className="mt-4 flex items-center gap-2 border-t border-line pt-4">
        <span className="text-[10px] font-medium uppercase tracking-wide text-encre/35">
          Simulation locale auditée
        </span>
        <button
          onClick={onActiver}
          disabled={action !== null || !connecteur}
          className="ml-auto rounded-md bg-encre px-3 py-2 text-xs font-semibold text-creme disabled:opacity-50"
        >
          {enCours ? 'Synchronisation…' : connecte ? 'Synchroniser' : 'Tester et connecter'}
        </button>
      </div>
    </article>
  )
}
