# email_client.py
# Client minimal d'envoi d'emails transactionnels, partage par les differents
# usages (verification OTP dans email_verification.py, confirmation de
# commande dans notifications.py) pour eviter de dupliquer l'appel a l'API
# Resend.
#
# Variable d'environnement optionnelle :
#   RESEND_API_KEY -> cle API Resend (resend.com). Absente : le contenu de
#                      l'email est logge sur stdout au lieu d'etre envoye,
#                      pour ne jamais bloquer en dev/test/avant la creation
#                      du compte Resend.

import os

import requests

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
DEFAULT_EMAIL_FROM = os.environ.get("EMAIL_FROM", "Rétroplanning.eu <contact@retroplanning.eu>")


def send_email(to, subject, html, from_addr=None):
    """Envoie un email transactionnel via l'API Resend. Sans cle API
    configuree, log le contenu sur stdout au lieu d'echouer -- pour ne
    jamais bloquer en dev/test/avant creation du compte Resend."""
    from_addr = from_addr or DEFAULT_EMAIL_FROM
    if not RESEND_API_KEY:
        print(f"[email_client] RESEND_API_KEY absente -- email a {to} ({subject}) :\n{html}")
        return

    response = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={"from": from_addr, "to": [to], "subject": subject, "html": html},
        timeout=10,
    )
    response.raise_for_status()
