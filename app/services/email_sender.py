"""Envoi transactionnel du CSV par HTTPS avec Resend."""
import base64
from urllib.parse import urlsplit

import httpx

from app.config import email_config
from app.models.analysis import Analysis


class EmailConfigurationError(Exception):
    pass


class EmailDeliveryError(Exception):
    pass


def ensure_email_configured() -> tuple[str, str, str]:
    key, sender, url = email_config()
    parsed = urlsplit(url)
    if not key or not sender or parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise EmailConfigurationError("Le service d’e-mail n’est pas encore configuré.")
    return key, sender, url


def send_corrected_csv(analysis: Analysis, recipient: str) -> None:
    """Envoyer au propriétaire ; aucune adresse n’est acceptée depuis le navigateur."""
    key, sender, url = ensure_email_configured()
    # Un nom fixe évite de propager les chemins ou caractères spéciaux du nom importé.
    payload = {
        "from": sender,
        "to": [recipient],
        "subject": f"CSV Check — votre fichier sans doublons (rapport #{analysis.id})",
        "text": (
            "Bonjour,\n\n"
            "Voici votre CSV après suppression des doublons exacts.\n"
            f"Lignes analysées : {analysis.row_count}\n"
            f"Doublons supprimés : {analysis.duplicate_count}\n"
            f"Cellules vides détectées dans le fichier initial : {analysis.empty_cell_count}\n\n"
            "Les cellules vides restent vides : aucune valeur n’a été inventée. "
            "L’ordre, les valeurs et le séparateur sont conservés. "
            "Les lignes vierges sont ignorées et le fichier est réexporté en UTF-8.\n\n"
            f"Retrouvez votre historique privé : {url}/#history\n\n"
            f"CSV Check vous a été utile ? Partagez le lien de l’outil : {url}/\n"
            "Vos rapports restent privés.\n"
        ),
        "attachments": [{
            "filename": f"analyse-{analysis.id}-sans-doublons.csv",
            "content": base64.b64encode(analysis.corrected_csv).decode("ascii"),
        }],
    }
    try:
        response = httpx.post(
            "https://api.resend.com/emails", json=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Idempotency-Key": f"csv-check-{analysis.correction_key}",
            },
            timeout=15,
        )
        if not response.is_success:
            raise EmailDeliveryError("Le service d’e-mail a refusé l’envoi. Vérifiez sa configuration.")
        result = response.json()
        if not isinstance(result, dict) or not result.get("id"):
            raise EmailDeliveryError("L’envoi n’a pas pu être confirmé.")
    except (httpx.HTTPError, ValueError) as error:
        raise EmailDeliveryError(
            "L’envoi n’a pas pu être confirmé. Vérifiez votre messagerie avant de réessayer."
        ) from error
