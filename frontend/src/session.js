// Authentification factice (CLAUDE.md §3 : "un login factice + un rôle
// superviseur suffisent" — pas de vrai backend RBAC dans ce périmètre).
// Persistée en localStorage pour survivre à un rafraîchissement pendant la démo.

const CLE = 'argus_session'

// Le compte de démo affiché sur l'écran de connexion. N'importe quel autre
// email/mot de passe est accepté aussi (stub) — le nom affiché en haut à
// droite est alors dérivé de l'email saisi, pour que "qui se connecte" et
// "qui est affiché" restent toujours cohérents.
export const COMPTE_DEMO = {
  email: 'selma.gharbi@argus-demo.tn',
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
    return brut ? JSON.parse(brut) : null
  } catch {
    return null
  }
}

// Stub volontaire : accepte tout email/mot de passe non vides. Le compte
// de démo renvoie une identité soignée ; tout autre email dérive un nom
// plausible — mais c'est toujours CE qui a été saisi qui détermine l'affichage.
export function connecter(email, motDePasse) {
  if (!email.trim() || !motDePasse.trim()) {
    throw new Error('Email et mot de passe requis.')
  }
  const estCompteDemo = email.trim().toLowerCase() === COMPTE_DEMO.email
  const session = estCompteDemo
    ? { email: COMPTE_DEMO.email, nom: COMPTE_DEMO.nom, role: COMPTE_DEMO.role }
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
