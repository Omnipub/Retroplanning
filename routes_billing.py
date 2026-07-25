# routes_billing.py
# Routes Flask a enregistrer dans app.py (via app.register_blueprint).
# Complete la logique PayPal existante (coexistence temporaire, voir INTEGRATION.md).

from flask import Blueprint, request, redirect, jsonify, render_template

import stripe
from billing import (
    create_one_time_checkout,
    create_subscription_checkout,
    create_customer_portal_session,
    get_access_status,
    handle_webhook_event,
)
from models_billing import Customer

billing_bp = Blueprint("billing", __name__)

SITE_URL = "https://www.retroplanning.eu"  # deja defini dans app.py


# ---------------------------------------------------------------------------
# Page de choix d'offre
# ---------------------------------------------------------------------------

@billing_bp.route("/tarifs")
def tarifs():
    """Page presentant les 3 offres : 2EUR a l'acte / 9,90EUR (10 plannings) / 19,90EUR (illimite)."""
    return render_template("tarifs.html")


# ---------------------------------------------------------------------------
# Lancement des paiements
# ---------------------------------------------------------------------------

@billing_bp.route("/checkout/unique", methods=["POST"])
def checkout_unique():
    email = request.form.get("email")
    if not email:
        return jsonify({"error": "Email requis"}), 400

    checkout_session = create_one_time_checkout(
        email=email,
        success_url=SITE_URL + "/paiement/succes",
        cancel_url=SITE_URL + "/tarifs",
    )
    return redirect(checkout_session.url, code=303)


@billing_bp.route("/checkout/abonnement/<plan>", methods=["POST"])
def checkout_abonnement(plan):
    if plan not in ("starter_10", "illimite"):
        return jsonify({"error": "Plan inconnu"}), 400

    email = request.form.get("email")
    if not email:
        return jsonify({"error": "Email requis"}), 400

    checkout_session = create_subscription_checkout(
        email=email,
        plan=plan,
        success_url=SITE_URL + "/paiement/succes",
        cancel_url=SITE_URL + "/tarifs",
    )
    return redirect(checkout_session.url, code=303)


@billing_bp.route("/paiement/succes")
def paiement_succes():
    # Stripe redirige ici apres paiement reussi. Le webhook (asynchrone) est la source
    # de verite pour l'activation reelle -- cette page ne fait qu'afficher un message
    # de confirmation immediat a l'utilisateur.
    return render_template("paiement_succes.html")


# ---------------------------------------------------------------------------
# Portail client (gestion abonnement / resiliation en libre-service)
# ---------------------------------------------------------------------------

@billing_bp.route("/mon-compte", methods=["POST"])
def mon_compte():
    email = request.form.get("email")
    customer = Customer.query.filter_by(email=email).first()
    if not customer:
        return jsonify({"error": "Aucun compte trouve pour cet email"}), 404

    portal_session = create_customer_portal_session(
        stripe_customer_id=customer.stripe_customer_id,
        return_url=SITE_URL + "/",
    )
    return redirect(portal_session.url, code=303)


# ---------------------------------------------------------------------------
# Verification de quota avant generation (a appeler dans la route de generation existante)
# ---------------------------------------------------------------------------

def check_access_or_redirect(email):
    """A appeler en debut de la route de generation du retroplanning, pour les emails
    associes a un abonnement. Retourne None si acces autorise, sinon un dict d'erreur
    a renvoyer au front (redirection vers /tarifs avec message adapte)."""
    status = get_access_status(email)
    if status["allowed"]:
        return None
    if status["reason"] == "quota_exceeded":
        return {
            "error": "quota_depasse",
            "message": "Vous avez atteint vos 10 plannings ce mois-ci. "
                       "Passez a l'offre illimitee ou attendez le mois prochain.",
        }
    return {
        "error": "no_subscription",
        "message": "Aucun abonnement actif. Paiement a l'acte (2EUR) ou abonnement requis.",
    }


# ---------------------------------------------------------------------------
# Webhook Stripe
# ---------------------------------------------------------------------------

@billing_bp.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        handle_webhook_event(payload, sig_header)
    except stripe.error.SignatureVerificationError:
        return "Signature invalide", 400
    except Exception as exc:  # noqa: BLE001 -- on log largement pour diagnostiquer en prod
        print(f"[webhook stripe] erreur de traitement : {exc}")
        return "Erreur de traitement", 500

    return "", 200
