import { useState } from 'react'

const CONNECTEURS = [
  { id: 'sage', nom: 'Sage X3', type: 'ERP Finance', couleur: 'bg-[#00A376]', initiales: 'S' },
  { id: 'sap', nom: 'SAP S/4HANA', type: 'ERP & Comptabilité', couleur: 'bg-[#0A6ED1]', initiales: 'SAP' },
  { id: 'oracle', nom: 'Oracle Financials', type: 'Gestion financière', couleur: 'bg-[#C74634]', initiales: 'O' },
  { id: 'guidewire', nom: 'Guidewire ClaimCenter', type: 'Core assurance', couleur: 'bg-[#F59E0B]', initiales: 'GW' },
  { id: 'database', nom: 'Base de données', type: 'SQL Server · PostgreSQL', couleur: 'bg-[#334155]', initiales: 'DB' },
]

export default function Integrations() {
  const [configures, setConfigures] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('argus_integrations') || '["sage"]')
    } catch {
      return ['sage']
    }
  })
  const [selection, setSelection] = useState(null)
  const [enregistrement, setEnregistrement] = useState(false)
  const [message, setMessage] = useState(null)

  const enregistrer = () => {
    setEnregistrement(true)
    setTimeout(() => {
      const suivants = [...new Set([...configures, selection.id])]
      setConfigures(suivants)
      localStorage.setItem('argus_integrations', JSON.stringify(suivants))
      setEnregistrement(false)
      setSelection(null)
      setMessage(`${selection.nom} est prêt à échanger des données avec Argus.`)
    }, 700)
  }

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <h2 className="text-lg font-semibold">Intégrations</h2>
          <p className="mt-1 text-sm text-encre/50">
            Centralisez les dossiers, règlements et écritures comptables avec vos systèmes métier.
          </p>
        </div>
        <button
          onClick={() => setSelection(CONNECTEURS.find((connecteur) => connecteur.id === 'database'))}
          className="ml-auto rounded-md bg-encre px-4 py-2 text-sm font-semibold text-creme transition hover:bg-encre/85"
        >
          + Connecter une base de données
        </button>
      </div>

      {message && (
        <div className="flex items-center gap-2 rounded-lg border border-ok/30 bg-ok-tint px-4 py-3 text-sm text-ok">
          <span>✓</span>
          <span>{message}</span>
          <button onClick={() => setMessage(null)} className="ml-auto text-ok/60">×</button>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {CONNECTEURS.map((connecteur) => {
          const configure = configures.includes(connecteur.id)
          return (
            <div key={connecteur.id} className="rounded-xl border border-line bg-surface p-5 shadow-sm">
              <div className="flex items-start gap-3">
                <div className={`flex h-11 w-11 items-center justify-center rounded-lg text-xs font-bold text-white ${connecteur.couleur}`}>
                  {connecteur.initiales}
                </div>
                <div>
                  <div className="font-semibold">{connecteur.nom}</div>
                  <div className="text-xs text-encre/45">{connecteur.type}</div>
                </div>
              </div>
              <div className="mt-5 flex items-center justify-between">
                <span className={`flex items-center gap-1.5 text-xs font-medium ${configure ? 'text-ok' : 'text-encre/40'}`}>
                  <span className={`h-2 w-2 rounded-full ${configure ? 'bg-ok' : 'bg-encre/20'}`} />
                  {configure ? 'Configuré' : 'Disponible'}
                </span>
                <button
                  onClick={() => setSelection(connecteur)}
                  className="rounded-md border border-line px-3 py-1.5 text-xs font-semibold text-encre/70 transition hover:border-terracotta/40 hover:bg-terracotta-tint"
                >
                  {configure ? 'Modifier' : connecteur.id === 'database' ? 'Connecter' : 'Configurer'}
                </button>
              </div>
            </div>
          )
        })}
      </div>

      <div className="rounded-xl border border-line bg-surface p-5">
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <h3 className="font-semibold">Flux de synchronisation</h3>
            <p className="mt-0.5 text-sm text-encre/50">Échanges préparés pour les systèmes configurés.</p>
          </div>
          <span className="ml-auto rounded-full bg-ok-tint px-3 py-1 text-xs font-semibold text-ok">
            {configures.length} intégration{configures.length > 1 ? 's' : ''} active{configures.length > 1 ? 's' : ''}
          </span>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {[
            ['Dossiers sinistres', 'Import des références et pièces'],
            ['Règlements validés', 'Transmission après approbation'],
            ['Écritures comptables', 'Rapprochement et suivi financier'],
          ].map(([titre, detail]) => (
            <div key={titre} className="rounded-lg bg-surface-deep p-3">
              <div className="text-sm font-semibold">{titre}</div>
              <div className="mt-0.5 text-xs text-encre/45">{detail}</div>
            </div>
          ))}
        </div>
      </div>

      {selection && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-encre/55 p-4" onClick={() => setSelection(null)}>
          <div className="w-full max-w-lg rounded-xl bg-surface p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg text-xs font-bold text-white ${selection.couleur}`}>
                {selection.initiales}
              </div>
              <div>
                <h3 className="font-semibold">Configurer {selection.nom}</h3>
                <p className="text-xs text-encre/45">Connexion sécurisée au système métier</p>
              </div>
            </div>
            <div className="mt-5 grid gap-3">
              <label className="text-sm">
                <span className="text-xs uppercase tracking-wide text-encre/40">Adresse du serveur</span>
                <input defaultValue={selection.id === 'database' ? 'sqlserver.compagnie.tn:1433' : `https://${selection.id}.compagnie.tn/api`}
                  className="mt-1 w-full rounded-md border border-line bg-creme p-2.5 text-sm focus:border-terracotta focus:outline-none" />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="text-sm">
                  <span className="text-xs uppercase tracking-wide text-encre/40">
                    {selection.id === 'database' ? "Nom d'utilisateur" : 'Identifiant client'}
                  </span>
                  <input placeholder={selection.id === 'database' ? 'argus_service' : 'ARGUS_PROD'}
                    className="mt-1 w-full rounded-md border border-line bg-creme p-2.5 text-sm" />
                </label>
                <label className="text-sm">
                  <span className="text-xs uppercase tracking-wide text-encre/40">Clé d'accès</span>
                  <input type="password" placeholder="••••••••••••" className="mt-1 w-full rounded-md border border-line bg-creme p-2.5 text-sm" />
                </label>
              </div>
              <label className="flex items-center gap-2 rounded-md bg-surface-deep px-3 py-2 text-sm text-encre/70">
                <input type="checkbox" defaultChecked className="accent-terracotta" />
                Synchroniser automatiquement les règlements validés
              </label>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setSelection(null)} className="rounded-md px-4 py-2 text-sm text-encre/55 hover:bg-surface-deep">
                Annuler
              </button>
              <button onClick={enregistrer} disabled={enregistrement}
                className="rounded-md bg-terracotta px-4 py-2 text-sm font-semibold text-white hover:bg-terracotta-deep disabled:opacity-50">
                {enregistrement ? 'Vérification…' : 'Enregistrer la connexion'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
