import { useEffect, useState } from 'react'
import { api } from '../api'

const ERP = [
  { id: 'sage', nom: 'Sage X3', type: 'ERP Finance', couleur: 'bg-[#00A376]', initiales: 'S' },
  { id: 'sap', nom: 'SAP S/4HANA', type: 'ERP & Comptabilité', couleur: 'bg-[#0A6ED1]', initiales: 'SAP' },
  { id: 'oracle', nom: 'Oracle Financials', type: 'Gestion financière', couleur: 'bg-[#C74634]', initiales: 'O' },
  { id: 'guidewire', nom: 'Guidewire ClaimCenter', type: 'Core assurance', couleur: 'bg-[#F59E0B]', initiales: 'GW' },
]

const formule = (valeur) => valeur === 'tous_risques' ? 'Tous risques' : 'Tiers'

export default function Integrations() {
  const [statut, setStatut] = useState(null)
  const [apercu, setApercu] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [action, setAction] = useState(null)
  const [message, setMessage] = useState(null)

  const charger = async () => {
    try {
      const [etat, donnees] = await Promise.all([
        api.statutBaseAssurance(),
        api.apercuBaseAssurance(),
      ])
      setStatut(etat)
      setApercu(donnees)
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

  if (chargement) return <p className="text-sm text-encre/50">Vérification de la source de données…</p>

  const derniere = statut?.derniere_synchronisation
  const compteurs = statut?.compteurs ?? {}
  const connecte = statut?.statut === 'connecte'

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

      <section>
        <h3 className="mb-3 font-semibold">Connecteurs ERP</h3>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {ERP.map((connecteur) => (
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
              <div className="mt-5 text-xs font-medium text-encre/40">Non connecté</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
