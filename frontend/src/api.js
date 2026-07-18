// Unique point de contact avec le backend — tout le front passe par ici.
const BASE_URL = 'http://localhost:8000'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const corps = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = new Error(corps.detail || `${res.status} ${path}`)
    err.status = res.status
    throw err
  }
  return corps
}

const post = (path, body) =>
  request(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

export const api = {
  health: () => request('/health'),
  // Studio
  listerTemplates: () => request('/templates'),
  listerAgents: () => request('/agents'),
  creerAgent: (corps) => post('/agents', corps),
  publierAgent: (id) => post(`/agents/${id}/publier`),
  modifierAgent: (id, corps) =>
    request(`/agents/${id}`, { method: 'PATCH', body: JSON.stringify(corps) }),
  listerWorkflows: () => request('/workflows'),
  ajouterEtape: (workflowId, agentId) =>
    post(`/workflows/${workflowId}/ajouter-etape`, { agent_id: agentId }),
  // Studio — agent personnalisé depuis un prompt
  categoriesStudio: () => request('/studio/categories'),
  genererInstructions: (brief) => post('/studio/generer-instructions', { brief }),
  creerAgentPersonnalise: (corps) => post('/studio/agents-personnalises', corps),
  // Pipeline
  listerDossiers: () => request('/dossiers'),
  lireDossier: (id) => request(`/dossiers/${id}`),
  declarerSinistre: (corps) => post('/dossiers', corps),
  executerEtape: (id) => post(`/dossiers/${id}/executer`),
  reculerEtape: (id) => post(`/dossiers/${id}/reculer`),
  rejouerDossier: (id) => post(`/dossiers/${id}/rejouer`),
  // Approbations
  listerTaches: (etat) => request(`/taches${etat ? `?etat=${etat}` : ''}`),
  deciderTache: (id, corps) => post(`/taches/${id}/decider`, corps),
  // Audit & dashboard
  lireAudit: (params = {}) => request(`/audit?${new URLSearchParams(params)}`),
  lireKpi: () => request('/dashboard/kpi'),
  // Démo
  reseed: () => post('/admin/reseed'),
}
