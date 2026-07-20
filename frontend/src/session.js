// Sessions locales (assureur / éditeur), persistées entre les rafraîchissements.

const CLE = 'argus_session'
const CLE_EDITEUR = 'argus_session_editeur'

// Identité par défaut du superviseur.
export const COMPTE_SUPERVISEUR = {
  email: 'zak.chammam@compagnie.tn',
  motDePasse: 'argus2026',
  nom: 'Zak Chammam',
  role: 'responsable sinistres',
}

// Compte éditeur (portail /#editeur).
export const COMPTE_EDITEUR = {
  email: 'amine.benyoussef@independant.tn',
  motDePasse: 'argus2026',
  nom: 'Amine Ben Youssef',
  role: 'éditeur indépendant',
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
    if (
      session.email === 'selma.gharbi@argus-demo.tn'
      || session.email === 'selma.gharbi@compagnie.tn'
    ) {
      session.email = COMPTE_SUPERVISEUR.email
      session.nom = COMPTE_SUPERVISEUR.nom
    }
    if (session.role === 'superviseur' || session.role === 'superviseure') {
      session.role = 'responsable sinistres'
    }
    localStorage.setItem(CLE, JSON.stringify(session))
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
    : { email: email.trim(), nom: nomDepuisEmail(email.trim()), role: 'responsable sinistres' }
  localStorage.setItem(CLE, JSON.stringify(session))
  return session
}

export function deconnecter() {
  localStorage.removeItem(CLE)
}

export function lireSessionEditeur() {
  try {
    const brut = localStorage.getItem(CLE_EDITEUR)
    if (!brut) return null
    const session = JSON.parse(brut)
    if (!session?.email || !session?.nom) return null
    return session
  } catch {
    return null
  }
}

export function connecterEditeur(email, motDePasse) {
  if (!email.trim() || !motDePasse.trim()) {
    throw new Error('Email et mot de passe requis.')
  }
  const emailNorm = email.trim().toLowerCase()
  if (emailNorm !== COMPTE_EDITEUR.email) {
    throw new Error('Compte éditeur inconnu.')
  }
  if (motDePasse !== COMPTE_EDITEUR.motDePasse) {
    throw new Error('Mot de passe incorrect.')
  }
  const session = {
    email: COMPTE_EDITEUR.email,
    nom: COMPTE_EDITEUR.nom,
    role: COMPTE_EDITEUR.role,
  }
  localStorage.setItem(CLE_EDITEUR, JSON.stringify(session))
  return session
}

export function deconnecterEditeur() {
  localStorage.removeItem(CLE_EDITEUR)
}

// Chaîne d'attribution utilisée partout où l'ancienne constante VALIDATEUR
// était injectée (décisions humaines, en-tête) : "Nom (rôle)".
export function libelleValidateur(session) {
  return session ? `${session.nom} (${session.role})` : 'Invité'
}
