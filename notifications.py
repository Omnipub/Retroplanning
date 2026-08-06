# notifications.py
# Email de confirmation envoye apres generation reussie d'un retroplanning
# (paiement a l'acte confirme, ou generation abonne apres verification OTP).
# Distinct de email_verification.py, qui gere le code de verification OTP
# lui-meme.
#
# Variable d'environnement optionnelle :
#   ORDER_EMAIL_FROM -> adresse d'expedition (defaut : voir plus bas).
# Reutilise RESEND_API_KEY (email_client.py) : sans cle configuree, le
# contenu de l'email est simplement logge sur stdout au lieu d'etre envoye.

import os

from email_client import send_email

ORDER_EMAIL_FROM = os.environ.get("ORDER_EMAIL_FROM", "Rétroplanning.eu <contact@retroplanning.eu>")


def send_order_confirmation_email(email, download_url, invoice_url=None):
    """Envoie l'email de confirmation apres generation reussie d'un
    retroplanning : lien d'acces/telechargement + instructions. Le lien de
    facture Stripe est inclus s'il est disponible (paiement a l'acte -- les
    abonnes retrouvent leurs factures via /mon-compte). N'echoue jamais bruyamment :
    une erreur d'envoi ne doit pas empecher l'utilisateur d'acceder a son
    retroplanning deja genere."""
    email = (email or "").strip()
    if not email:
        return

    invoice_line = (
        f'<p>Votre facture est disponible ici : <a href="{invoice_url}">{invoice_url}</a></p>'
        if invoice_url else ""
    )

    html = (
        "<p>Merci pour votre commande sur Rétroplanning.eu !</p>"
        f'<p><a href="{download_url}" style="font-weight:bold;">Télécharger mon rétroplanning (PNG)</a></p>'
        "<p>Ce lien reste valable si vous souhaitez retélécharger votre visuel plus tard.</p>"
        f"{invoice_line}"
        "<p>Une question ? Répondez simplement à cet email, nous vous répondrons rapidement.</p>"
    )

    try:
        send_email(email, "Votre rétroplanning est prêt", html, from_addr=ORDER_EMAIL_FROM)
    except Exception as exc:  # noqa: BLE001 -- ne jamais bloquer l'acces deja acquis par erreur d'envoi
        print(f"[notifications] echec envoi email de confirmation a {email} : {exc!r}")
