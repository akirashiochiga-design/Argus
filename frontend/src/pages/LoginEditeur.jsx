import { useState } from 'react'
import { COMPTE_EDITEUR, connecterEditeur } from '../session'
import { Logo, Wordmark } from '../ui'

export default function LoginEditeur({ onConnecte }) {
  const [email, setEmail] = useState(COMPTE_EDITEUR.email)
  const [motDePasse, setMotDePasse] = useState(COMPTE_EDITEUR.motDePasse)
  const [erreur, setErreur] = useState(null)
  const [envoi, setEnvoi] = useState(false)

  const soumettre = (e) => {
    e.preventDefault()
    setErreur(null)
    setEnvoi(true)
    try {
      const session = connecterEditeur(email, motDePasse)
      onConnecte(session)
    } catch (err) {
      setErreur(err.message)
      setEnvoi(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-encre px-4 text-creme">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <Logo size={56} className="text-creme" />
          <Wordmark className="text-4xl text-creme" />
          <p className="text-sm text-creme/50">Portail éditeurs · Norix for Creators</p>
        </div>

        <form onSubmit={soumettre} className="rounded-xl border border-creme/15 bg-creme/[0.04] p-6">
          <h1 className="mb-1 text-lg font-semibold">Connexion éditeur</h1>
          <p className="mb-5 text-sm text-creme/50">
            Publiez vos agents sans accéder aux données assureur.
          </p>

          <label className="block text-sm">
            <span className="text-xs uppercase tracking-wide text-creme/40">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="prenom.nom@independant.tn"
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
        </form>

        <p className="mt-6 text-center text-xs text-creme/40">
          Vous êtes assureur ?{' '}
          <a href="/" className="font-semibold text-creme/70 underline-offset-2 hover:underline">
            Connexion plateforme
          </a>
        </p>
      </div>
    </div>
  )
}
