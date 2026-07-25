# billing.py
# Logique Stripe : creation des sessions de paiement/abonnement, verification de quota,
# traitement des webhooks. A appeler depuis les routes Flask (voir routes_billing.py).
#
# Variables d'environnement requises (a definir sur Render, jamais en dur dans le code) :
#   STRIPE_SECRET_KEY            -> cle secrete Stripe (sk_live_... ou sk_test_...)
#   STRIPE_WEBHOOK_SECRET        -> secret de signature du endpoint webhook (whsec_...)
#   STRIPE_PRICE_ID_STARTER10    -> Price ID Stripe du plan "9,90EUR HT / 10 plannings"
#   STRIPE_PRICE_ID_UNLIMITED    -> Price ID Stripe du plan "19,90EUR HT / illimite"
#   STRIPE_PRICE_ID_ONE_TIME     -> Price ID Stripe du paiement a l'acte (2EUR TTC)
#   SITE_URL                     -> deja existant dans app.py (https://www.retroplanning.eu)
#
# NOTE D'INTEGRATION : `db` est importe depuis `app` (pas de module db.py separe dans ce projet).

import os
from datetime import datetime, timezone

import stripe
from app import db
from models_billing import Customer, Subscription, UsageRecord, OneTimePayment

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

PRICE_ONE_TIME = os.environ.get("STRIPE_PRICE_ID_ONE_TIME")
PRICE_STARTER10 = os.environ.get("STRIPE_PRICE_ID_STARTER10")
PRICE_UNLIMITED = os.environ.get("STRIPE_PRICE_ID_UNLIMITED")

PLAN_QUOTAS = {
    "starter_10": 10,
    "illimite": None,  # None = pas de limite
}


# ---------------------------------------------------------------------------
# Creation des sessions Stripe Checkout
# ---------------------------------------------------------------------------

def create_one_time_checkout(email, success_url, cancel_url):
    """Paiement a l'acte, 2EUR TTC. Pas de compte necessaire au sens strict :
    Stripe cree/retrouve un Customer via l'email, mais aucun mot de passe n'est demande."""
    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=email,
        line_items=[{"price": PRICE_ONE_TIME, "quantity": 1}],
        invoice_creation={"enabled": True},  # genere automatiquement une facture PDF
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"type": "one_time"},
    )
    return session


def create_subscription_checkout(email, plan, success_url, cancel_url):
    """Abonnement mensuel resiliable. plan = 'starter_10' ou 'illimite'."""
    price_id = PRICE_STARTER10 if plan == "starter_10" else PRICE_UNLIMITED
    if not price_id:
        raise ValueError(f"Price ID Stripe manquant pour le plan '{plan}'")

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=email,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"type": "subscription", "plan": plan},
        subscription_data={"metadata": {"plan": plan}},
    )
    return session


def create_customer_portal_session(stripe_customer_id, return_url):
    """Lien vers le portail Stripe (facturation, resiliation en libre-service, sans compte
    a creer sur le site : gere entierement par Stripe)."""
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=return_url,
    )
    return session


# ---------------------------------------------------------------------------
# Verification de quota (palier "starter_10")
# ---------------------------------------------------------------------------

def current_period_key(now=None):
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def get_access_status(email):
    """
    Retourne un dict decrivant les droits d'un email pour generer un retroplanning :
      {"allowed": bool, "reason": str, "plan": str|None, "remaining": int|None}

    Logique :
      - Pas de client / pas d'abonnement actif -> paiement a l'acte requis (gere ailleurs)
      - Abonnement 'illimite' actif -> toujours autorise
      - Abonnement 'starter_10' actif -> autorise si compteur du mois < 10
    """
    customer = Customer.query.filter_by(email=email).first()
    if not customer or not customer.subscription or not customer.subscription.is_active():
        return {"allowed": False, "reason": "no_active_subscription", "plan": None, "remaining": None}

    sub = customer.subscription
    if sub.plan == "illimite":
        return {"allowed": True, "reason": "unlimited_plan", "plan": "illimite", "remaining": None}

    if sub.plan == "starter_10":
        period = current_period_key()
        usage = UsageRecord.query.filter_by(customer_id=customer.id, period=period).first()
        used = usage.count if usage else 0
        remaining = max(0, 10 - used)
        return {
            "allowed": remaining > 0,
            "reason": "quota_ok" if remaining > 0 else "quota_exceeded",
            "plan": "starter_10",
            "remaining": remaining,
        }

    return {"allowed": False, "reason": "unknown_plan", "plan": sub.plan, "remaining": None}


def record_usage(email):
    """A appeler juste apres une generation reussie de retroplanning, uniquement pour
    les comptes en abonnement (le paiement a l'acte n'a pas besoin de compteur)."""
    customer = Customer.query.filter_by(email=email).first()
    if not customer or not customer.subscription:
        return
    period = current_period_key()
    usage = UsageRecord.query.filter_by(customer_id=customer.id, period=period).first()
    if not usage:
        usage = UsageRecord(customer_id=customer.id, period=period, count=0)
        db.session.add(usage)
    usage.count += 1
    db.session.commit()


# ---------------------------------------------------------------------------
# Traitement des webhooks Stripe
# ---------------------------------------------------------------------------

def handle_webhook_event(payload, sig_header):
    """A appeler depuis la route /webhook/stripe. Verifie la signature puis dispatch
    l'evenement vers le bon handler. Leve stripe.error.SignatureVerificationError si
    la signature est invalide (la route doit repondre 400 dans ce cas)."""
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)

    handlers = {
        "checkout.session.completed": on_checkout_completed,
        "customer.subscription.updated": on_subscription_updated,
        "customer.subscription.deleted": on_subscription_deleted,
        "invoice.paid": on_invoice_paid,
    }
    handler = handlers.get(event["type"])
    if handler:
        handler(event["data"]["object"])

    return event


def get_or_create_customer(email, stripe_customer_id):
    customer = Customer.query.filter_by(email=email).first()
    if not customer:
        customer = Customer(email=email, stripe_customer_id=stripe_customer_id)
        db.session.add(customer)
        db.session.commit()
    return customer


def on_checkout_completed(session_obj):
    email = session_obj.get("customer_email") or session_obj.get("customer_details", {}).get("email")
    stripe_customer_id = session_obj.get("customer")
    mode = session_obj.get("mode")

    if mode == "payment":
        # Paiement a l'acte : on trace le paiement, la facture est generee automatiquement
        # par Stripe (invoice_creation active dans create_one_time_checkout).
        payment = OneTimePayment(
            email=email,
            stripe_checkout_session_id=session_obj["id"],
            stripe_payment_intent_id=session_obj.get("payment_intent"),
            amount_ttc=(session_obj.get("amount_total") or 0) / 100,
        )
        db.session.add(payment)
        db.session.commit()

    elif mode == "subscription":
        plan = (session_obj.get("metadata") or {}).get("plan", "starter_10")
        customer = get_or_create_customer(email, stripe_customer_id)
        stripe_subscription_id = session_obj.get("subscription")

        sub = Subscription.query.filter_by(stripe_subscription_id=stripe_subscription_id).first()
        if not sub:
            sub = Subscription(
                customer_id=customer.id,
                stripe_subscription_id=stripe_subscription_id,
                plan=plan,
                status="active",
            )
            db.session.add(sub)
        else:
            sub.plan = plan
            sub.status = "active"
        db.session.commit()


def on_subscription_updated(sub_obj):
    sub = Subscription.query.filter_by(stripe_subscription_id=sub_obj["id"]).first()
    if not sub:
        return
    sub.status = sub_obj.get("status", sub.status)
    sub.cancel_at_period_end = sub_obj.get("cancel_at_period_end", False)
    period_end = sub_obj.get("current_period_end")
    if period_end:
        sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)
    db.session.commit()


def on_subscription_deleted(sub_obj):
    sub = Subscription.query.filter_by(stripe_subscription_id=sub_obj["id"]).first()
    if sub:
        sub.status = "canceled"
        db.session.commit()


def on_invoice_paid(invoice_obj):
    # Utile si vous voulez tracer chaque facture d'abonnement recurrente (historique complet).
    # Optionnel pour le MVP : Stripe envoie deja la facture par email automatiquement.
    pass
