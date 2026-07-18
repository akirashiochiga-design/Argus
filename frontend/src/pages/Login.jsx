import { useState } from 'react'
import { COMPTE_DEMO, connecter } from '../session'
import { Logo, Wordmark } from '../ui'

export default function Login({ onConnecte }) {
  const [email, setEmail] = useState('')
  const [motDePasse, setMotDePasse] = useState('')
  const [erreur, setErreur] = useState(null)
  const [envoi, setEnvoi] = useState(false)

  const soumettre = (e) => {
    e.preventDefault()
    setErreur(null)
    setEnvoi(true)
    try {
      const session = connecter(email, motDePasse)
      onConnecte(session)
    } catch (err) {
      setErreur(err.message)
      setEnvoi(false)
    }
  }

  const remplirCompteDemo = () => {
    setEmail(COMPTE_DEMO.email)
    setMotDePasse(COMPTE_DEMO.motDePasse)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-encre px-4 text-creme">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <Logo size={56} className="text-creme" />
          <Wordmark className="text-4xl text-creme" />
          <p className="text-sm text-creme/50">l'usine à agents pour l'assurance</p>
        </div>

        <form onSubmit={soumettre} className="rounded-xl border border-creme/15 bg-creme/[0.04] p-6">
          <h1 className="mb-1 text-lg font-semibold">Connexion</h1>
          <p className="mb-5 text-sm text-creme/50">Accédez à la plateforme de gestion des sinistres.</p>

          <label className="block text-sm">
            <span className="text-xs uppercase tracking-wide text-creme/40">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="prenom.nom@compagnie.tn"
              autoFocus
              className="mt-1 w-full rounded-md border border-creme/20 bg-creme/5 p-2.5 text-sm text-creme placeholder:text-creme/30 focus:border-terracotta focus:outline-none"
            />
          </label>
          <label className="mt-3 block text-sm">
            <span className="text-xs uppercase tracking-wide text-creme/40">Mot de passe</span>
            <input
              type="password"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              placeholder="••••••••"
              className="mt-1 w-full rounded-md border border-creme/20 bg-creme/5 p-2.5 text-sm text-creme placeholder:text-creme/30 focus:border-terracotta focus:outline-none"
            />
          </label>

          {erreur && <p className="mt-3 text-sm text-terracotta">{erreur}</p>}

          <button
            type="submit"
            disabled={envoi}
            className="mt-5 w-full rounded-md bg-terracotta py-2.5 text-sm font-semibold text-white transition hover:bg-terracotta-deep disabled:opacity-50"
          >
            Se connecter
          </button>

          <div className="mt-5 rounded-md border border-creme/15 bg-creme/[0.03] p-3 text-xs text-creme/60">
            <div className="mb-1.5 font-semibold uppercase tracking-wide text-creme/40">Compte de démonstration</div>
            <div>{COMPTE_DEMO.email}</div>
            <div>{COMPTE_DEMO.motDePasse}</div>
            <button
              type="button"
              onClick={remplirCompteDemo}
              className="mt-2 rounded border border-creme/20 px-2.5 py-1 text-[11px] font-medium text-creme/80 hover:bg-creme/10"
            >
              Remplir automatiquement
            </button>
          </div>
        </form>

        <p className="mt-4 text-center text-[11px] text-creme/30">
          Authentification de démonstration — n'importe quel email/mot de passe fonctionne ;
          l'identité affichée dans l'application correspond à ce que vous saisissez ici.
        </p>
      </div>
    </div>
  )
}
