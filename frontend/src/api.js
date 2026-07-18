// Unique point de contact avec le backend — tout le front passe par ici.
const BASE_URL = 'http://localhost:8000'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`${res.status} ${path} — ${detail}`)
  }
  return res.json()
}

export const api = {
  health: () => request('/health'),
  // Studio
  listerTemplates: () => request('/templates'),
  listerAgents: () => request('/agents'),
  // Pipeline
  listerDossiers: () => request('/dossiers'),
  lireDossier: (id) => request(`/dossiers/${id}`),
  // À venir (étapes 2-3 du plan) :
  // executerEtape: (id) => request(`/dossiers/${id}/executer`, { method: 'POST' }),
  // listerTaches: () => request('/taches?etat=en_attente'),
  // deciderTache: (id, corps) => request(`/taches/${id}/decider`, { method: 'POST', body: JSON.stringify(corps) }),
  // lireAudit: (params) => request(`/audit?${new URLSearchParams(params)}`),
  // lireKpi: () => request('/dashboard/kpi'),
}
