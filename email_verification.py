# email_verification.py
# Verification qu'une personne possede bien l'email qu'elle saisit, par code a
# usage unique (OTP) envoye par email. Utilise a deux endroits :
#   - app.py /checkout : avant d'accorder le bypass paiement a un email associe
#     a un abonnement actif (sinon n'importe qui connaissant cet email genere
#     gratuitement, cf. incident de securite).
#   - routes_billing.py /mon-compte : avant de donner acces au portail client
#     Stripe (factures, moyen de paiement, resiliation) pour un email donne.
#
# Variable d'environnement optionnelle :
#   RESEND_API_KEY   -> cle API Resend (resend.com) pour l'envoi reel des emails.
#                        Absente : le code est logge sur stdout au lieu d'etre
#                        envoye, pour ne jamais bloquer en dev/test/avant la
#                        creation du compte Resend.
#   VERIFICATION_EMAIL_FROM -> adresse d'expedition (defaut : voir plus bas).

import hashlib
import os
import secrets
from datetime import datetime, timedelta

import requests
from flask import current_app, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app import db
from models_billing import EmailVerification

CODE_TTL_MINUTES = 15
MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_FROM = os.environ.get("VERIFICATION_EMAIL_FROM", "Rétroplanning.eu <verification@retroplanning.eu>")

VERIFIED_EMAIL_COOKIE = "verified_email"
VERIFIED_EMAIL_COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 jours


# ---------------------------------------------------------------------------
# Generation / verification du code
# ---------------------------------------------------------------------------

def _hash_code(email, code):
    return hashlib.sha256(f"{email}:{code}".encode("utf-8")).hexdigest()


def _generate_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def can_request_new_code(email):
    """Anti-spam : au plus une demande de code par minute pour un meme email,
    pour eviter qu'un attaquant fasse spammer la boite d'un vrai abonne."""
    recent = (
        EmailVerification.query.filter_by(email=email)
        .order_by(EmailVerification.created_at.desc())
        .first()
    )
    if not recent:
        return True
    return datetime.utcnow() - recent.created_at > timedelta(seconds=RESEND_COOLDOWN_SECONDS)


def create_and_send_code(email):
    """Genere un nouveau code, l'enregistre (hache, jamais en clair en base) et
    l'envoie par email. Retourne "sent", "cooldown" (trop tot pour un nouveau
    code) ou "error" (l'envoi a echoue)."""
    email = email.strip().lower()
    if not can_request_new_code(email):
        return "cooldown"

    code = _generate_code()
    verification = EmailVerification(
        email=email,
        code_hash=_hash_code(email, code),
        expires_at=datetime.utcnow() + timedelta(minutes=CODE_TTL_MINUTES),
    )
    db.session.add(verification)
    db.session.commit()

    try:
        send_verification_email(email, code)
    except Exception:
        return "error"
    return "sent"


def verify_code(email, submitted_code):
    """Verifie un code saisi pour un email. Retourne (ok: bool, reason: str) ;
    reason vaut "ok", "no_pending_code", "expired", "too_many_attempts" ou
    "wrong_code"."""
    email = email.strip().lower()
    submitted_code = (submitted_code or "").strip()

    verification = (
        EmailVerification.query.filter_by(email=email, used_at=None)
        .order_by(EmailVerification.created_at.desc())
        .first()
    )
    if not verification:
        return False, "no_pending_code"

    if datetime.utcnow() > verification.expires_at:
        return False, "expired"

    if verification.attempts >= MAX_ATTEMPTS:
        return False, "too_many_attempts"

    verification.attempts += 1

    if verification.code_hash != _hash_code(email, submitted_code):
        db.session.commit()
        return False, "wrong_code"

    verification.used_at = datetime.utcnow()
    db.session.commit()
    return True, "ok"


def send_verification_email(email, code):
    if not RESEND_API_KEY:
        # Pas de cle configuree : on log le code au lieu d'echouer silencieusement,
        # utile en local/tests et le temps de creer le compte Resend.
        print(f"[email_verification] RESEND_API_KEY absente -- code pour {email} : {code}")
        return

    response = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={
            "from": EMAIL_FROM,
            "to": [email],
            "subject": f"Votre code de vérification : {code}",
            "html": (
                "<p>Voici votre code de vérification Rétroplanning.eu :</p>"
                f"<p style=\"font-size:28px;font-weight:bold;letter-spacing:4px;\">{code}</p>"
                f"<p>Ce code expire dans {CODE_TTL_MINUTES} minutes. "
                "Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.</p>"
            ),
        },
        timeout=10,
    )
    response.raise_for_status()


# ---------------------------------------------------------------------------
# Cookie "navigateur deja verifie" (30 jours)
# ---------------------------------------------------------------------------

def _serializer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="subscriber-email-verified")


def cookie_confirms_email(email):
    """True si ce navigateur a deja prouve, il y a moins de 30 jours, qu'il
    possede cet email (signature verifiee, donc infalsifiable sans secret_key)."""
    token = request.cookies.get(VERIFIED_EMAIL_COOKIE)
    if not token:
        return False
    try:
        cookie_email = _serializer().loads(token, max_age=VERIFIED_EMAIL_COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return False
    return cookie_email == email.strip().lower()


def set_verified_email_cookie(response, email):
    token = _serializer().dumps(email.strip().lower())
    response.set_cookie(
        VERIFIED_EMAIL_COOKIE,
        token,
        max_age=VERIFIED_EMAIL_COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="Lax",
    )
    return response
