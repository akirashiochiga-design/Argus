"""File sortante locale représentant l'ERP financier interne d'un assureur."""
from sqlmodel import Session, select

from ..audit import tracer
from ..models import Dossier, EcritureERP


class ConnecteurERPDemo:
    identifiant = "erp_interne_demo"
    nom = "ERP Finance interne"
    direction = "sortant"
    protocole = "MCP"

    def tester(self) -> dict:
        from ..mcp import McpClient, serveur_erp

        client = McpClient(serveur_erp())
        ping = client.call_tool("ping", auditer=False)
        return {
            "identifiant": self.identifiant,
            "nom": self.nom,
            "direction": self.direction,
            "protocole": "MCP",
            "mcp_server": serveur_erp().name,
            "mcp_tools": [tool["name"] for tool in client.list_tools()],
            "mode": ping.get("mode", "écriture après validation humaine"),
            "latence_ms": ping.get("latence_ms", 12),
        }

    def synchroniser(self, session: Session) -> dict:
        from ..mcp import McpClient, serveur_erp

        client = McpClient(serveur_erp())
        return client.call_tool(
            "envoyer_ecritures_planifiees",
            session=session,
        )


def planifier_ecriture(
    session: Session,
    dossier: Dossier,
    validateur: str,
) -> EcritureERP | None:
    """Créer une seule écriture, uniquement si un humain a validé un montant."""
    if dossier.montant_valide is None:
        return None
    existante = session.exec(
        select(EcritureERP).where(EcritureERP.dossier_id == dossier.id)
    ).first()
    if existante:
        return existante
    ecriture = EcritureERP(
        dossier_id=dossier.id,
        montant=dossier.montant_valide,
        payload={
            "reference_sinistre": dossier.ref,
            "montant_valide": dossier.montant_valide,
            "devise": "TND",
            "valide_par": validateur,
            "protocole": "MCP",
        },
    )
    session.add(ecriture)
    session.flush()
    tracer(
        session,
        acteur=f"humain:{validateur}",
        acteur_type="humain",
        type="ecriture_erp_planifiee",
        objet=f"dossier:{dossier.ref}",
        apres={
            "ecriture_id": ecriture.id,
            "montant": ecriture.montant,
            "connecteur": ecriture.connecteur,
            "statut": ecriture.statut,
            "protocole": "MCP",
        },
        motif="Écriture préparée après validation explicite du gestionnaire",
    )
    session.commit()
    session.refresh(ecriture)
    return ecriture
