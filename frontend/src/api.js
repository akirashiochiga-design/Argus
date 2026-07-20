// Unique point de contact avec le backend — tout le front passe par ici.
const BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8001' : '')

export const assetUrl = (chemin) => {
  if (!chemin) return ''
  if (/^https?:\/\//i.test(chemin)) return chemin
  return `${BASE_URL}/${chemin.replace(/^\/+/, '')}?v=photos-reelles-3`
}

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
  creerWorkflow: (corps) => post('/workflows', corps),
  modifierEtapesWorkflow: (id, agentIds) =>
    request(`/workflows/${id}/etapes`, {
      method: 'PATCH',
      body: JSON.stringify({ agent_ids: agentIds }),
    }),
  activerWorkflow: (id) => post(`/workflows/${id}/activer`),
  ajouterEtape: (workflowId, agentId) =>
    post(`/workflows/${workflowId}/ajouter-etape`, { agent_id: agentId }),
  // Studio — agent personnalisé depuis un prompt
  categoriesStudio: () => request('/studio/categories'),
  genererInstructions: (brief) => post('/studio/generer-instructions', { brief }),
  creerAgentPersonnalise: (corps) => post('/studio/agents-personnalises', corps),
  // Marketplace
  listerMarketplace: () => request('/marketplace/listings'),
  installerMarketplace: (id, corps) => post(`/marketplace/listings/${id}/installer`, corps),
  renouvelerInstallationMarketplace: (installationId, corps) =>
    post(`/marketplace/installations/${installationId}/renouveler`, corps),
  listerInstallationsMarketplace: () => request('/marketplace/installations'),
  soumettreMarketplace: (corps) => post('/marketplace/listings', corps),
  validerMarketplace: (id) => post(`/marketplace/listings/${id}/valider`),
  listerMarketplaceEditeur: (editeur) =>
    request(`/marketplace/editeurs/${encodeURIComponent(editeur)}/listings`),
  // Pipeline
  listerDossiers: () => request('/dossiers'),
  lireDossier: (id) => request(`/dossiers/${id}`),
  declarerSinistre: (corps) => post('/dossiers', corps),
  choisirTraitement: (id, workflowId) =>
    request(`/dossiers/${id}/traitement`, {
      method: 'PATCH',
      body: JSON.stringify({ workflow_id: workflowId }),
    }),
  executerEtape: (id) => post(`/dossiers/${id}/executer`),
  reculerEtape: (id) => post(`/dossiers/${id}/reculer`),
  rejouerDossier: (id) => post(`/dossiers/${id}/rejouer`),
  // Approbations
  listerTaches: (etat) => request(`/taches${etat ? `?etat=${etat}` : ''}`),
  deciderTache: (id, corps) => post(`/taches/${id}/decider`, corps),
  relancerTache: (id, validateur) => post(`/taches/${id}/relancer`, { validateur }),
  surveillerPieces: () => post('/integrations/connecteurs/sharepoint_demo/synchroniser'),
  // Audit & dashboard
  lireAudit: (params = {}) => request(`/audit?${new URLSearchParams(params)}`),
  lireKpi: () => request('/dashboard/kpi'),
  // Intégration base assurance
  statutBaseAssurance: () => request('/integrations/database/statut'),
  connecterBaseAssurance: () => post('/integrations/database/connecter'),
  testerBaseAssurance: () => post('/integrations/database/test'),
  apercuBaseAssurance: () => request('/integrations/database/apercu'),
  synchroniserBaseAssurance: () => post('/integrations/database/synchroniser'),
  inventaireBaseAssurance: () => request('/integrations/database/inventaire'),
  creerPoliceSource: (corps) => post('/integrations/database/polices', corps),
  creerSinistreSource: (corps) => post('/integrations/database/sinistres', corps),
  listerDocumentsSharePoint: () => request('/integrations/sharepoint/documents'),
  listerBibliothequeSharePoint: () => request('/integrations/sharepoint/bibliotheque'),
  ajouterDocumentSharePoint: (corps) => post('/integrations/sharepoint/documents', corps),
  deposerRetourSharePoint: (corps) => post('/integrations/sharepoint/retours', corps),
  listerConnecteurs: () => request('/integrations/connecteurs'),
  connecterConnecteur: (identifiant) => post(`/integrations/connecteurs/${identifiant}/connecter`),
  synchroniserConnecteur: (identifiant) => post(`/integrations/connecteurs/${identifiant}/synchroniser`),
  listerEcrituresErp: () => request('/integrations/erp/ecritures'),
  // Connexions MCP (style console Anthropic)
  listerPlateformesMcp: () => request('/studio/plateformes-mcp'),
  listerConnexionsAgent: (id) => request(`/agents/${id}/connexions`),
  connecterPlateformeAgent: (id, slug) => post(`/agents/${id}/connexions/${slug}/connecter`),
  deconnecterPlateformeAgent: (id, slug) =>
    request(`/agents/${id}/connexions/${slug}`, { method: 'DELETE' }),
  reseed: () => post('/admin/reseed'),
}
