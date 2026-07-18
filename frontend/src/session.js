// Session locale du superviseur, persistée entre les rafraîchissements.

const CLE = 'argus_session'

// Identité par défaut du superviseur.
export const COMPTE_SUPERVISEUR = {
  email: 'selma.gharbi@compagnie.tn',
  motDePasse: 'argus2026',
  nom: 'Selma Gharbi',
  role: 'superviseure',
}

function nomDepuisEmail(email) {
  const local = email.split('@')[0] || 'Invité'
  return local
    .split(/[.\-_]+/)
    .filter(Boolean)
    .map((mot) => mot.charAt(0).toUpperCase() + mot.slice(1))
    .join(' ') || 'Invité'
}

export function initiales(nom) {
  const mots = nom.trim().split(/\s+/)
  const premiere = mots[0]?.[0] ?? '?'
  const derniere = mots.length > 1 ? mots[mots.length - 1][0] : ''
  return (premiere + derniere).toUpperCase()
}

export function lireSession() {
  try {
    const brut = localStorage.getItem(CLE)
    if (!brut) return null
    const session = JSON.parse(brut)
    if (session.email === 'selma.gharbi@argus-demo.tn') {
      session.email = COMPTE_SUPERVISEUR.email
      localStorage.setItem(CLE, JSON.stringify(session))
    }
    return session
  } catch {
    return null
  }
}

export function connecter(email, motDePasse) {
  if (!email.trim() || !motDePasse.trim()) {
    throw new Error('Email et mot de passe requis.')
  }
  const estCompteSuperviseur = email.trim().toLowerCase() === COMPTE_SUPERVISEUR.email
  const session = estCompteSuperviseur
    ? { email: COMPTE_SUPERVISEUR.email, nom: COMPTE_SUPERVISEUR.nom, role: COMPTE_SUPERVISEUR.role }
    : { email: email.trim(), nom: nomDepuisEmail(email.trim()), role: 'superviseur' }
  localStorage.setItem(CLE, JSON.stringify(session))
  return session
}

export function deconnecter() {
  localStorage.removeItem(CLE)
}

// Chaîne d'attribution utilisée partout où l'ancienne constante VALIDATEUR
// était injectée (décisions humaines, en-tête) : "Nom (rôle)".
export function libelleValidateur(session) {
  return session ? `${session.nom} (${session.role})` : 'Invité'
}
