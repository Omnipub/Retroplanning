# tests/test_stripe_billing.py
# Suite pytest couvrant la logique metier de l'integration Stripe (voir billing.py,
# routes_billing.py, models_billing.py) sur la branche feature/stripe-integration.
#
# Portee : ces tests utilisent une base SQLite temporaire et ne font AUCUN appel reseau
# reel a Stripe (stripe.Webhook.construct_event est mocke pour le scenario webhook ;
# les autres scenarios n'appellent jamais l'API Stripe, ils testent uniquement la
# logique d'acces/quota interne a l'application). Ils ne remplacent donc pas un test
# reel de bout en bout en mode Stripe test (voir le protocole manuel fourni a part pour
# la verification du webhook reel sur le déploiement Render).
#
# Execution locale : pip install pytest && pytest tests/ -v
# Execution automatique : voir .github/workflows/tests.yml (declenche a chaque push).

import sys
import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest


TEST_ENV = {
    "ADMIN_PASSWORD": "test-admin-password",
    "FLASK_SECRET_KEY": "test-secret-key",
    "STRIPE_SECRET_KEY": "sk_test_dummy",
    "STRIPE_WEBHOOK_SECRET": "whsec_test_dummy",
    "STRIPE_PRICE_ID_ONE_TIME": "price_test_onetime",
    "STRIPE_PRICE_ID_STARTER10": "price_test_starter10",
    "STRIPE_PRICE_ID_UNLIMITED": "price_test_unlimited",
}

APP_MODULES = ["app", "billing", "routes_billing", "models_billing"]


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    """Importe l'application Flask avec un environnement isole : base SQLite
    temporaire et cles Stripe factices, pour ne jamais toucher a une vraie base
    ni a un vrai compte Stripe pendant les tests."""
    db_path = tmp_path / f"test_{uuid.uuid4().hex}.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    for key, value in TEST_ENV.items():
        monkeypatch.setenv(key, value)

    for mod in APP_MODULES:
        sys.modules.pop(mod, None)

    import app as imported_app

    imported_app.app.config["TESTING"] = True
    yield imported_app

    for mod in APP_MODULES:
        sys.modules.pop(mod, None)


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


def _make_active_subscriber(app_module, email, plan="starter_10"):
    """Insere directement un client + abonnement actif en base : represente l'etat
    obtenu apres un paiement Stripe reussi, sans dependre d'un appel reseau reel."""
    from models_billing import Customer, Subscription

    with app_module.app.app_context():
        customer = Customer(
            email=email,
            stripe_customer_id=f"cus_test_{uuid.uuid4().hex[:8]}",
        )
        app_module.db.session.add(customer)
        app_module.db.session.commit()

        subscription = Subscription(
            customer_id=customer.id,
            stripe_subscription_id=f"sub_test_{uuid.uuid4().hex[:8]}",
            plan=plan,
            status="active",
        )
        app_module.db.session.add(subscription)
        app_module.db.session.commit()


def _checkout_payload(email):
    return {
        "client": "Client Test",
        "evenement": "Evenement Test",
        "email": email,
        "label1": "Etape 1",
        "date1": "2026-08-01",
        "date_event": "2026-08-15",
    }


class TestWebhookCreatesSubscription:
    """Scenario 1 : un evenement webhook Stripe checkout.session.completed
    (mode=subscription, plan=starter_10) doit creer un abonnement actif en base,
    sans qu'aucun appel reseau reel a Stripe ne soit necessaire (construct_event
    est mocke, seule la logique de traitement applicative est testee ici)."""

    def test_webhook_creates_active_starter10_subscription(self, app_module, client):
        from models_billing import Customer

        email = "abonne.test@example.com"
        fake_event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer_email": email,
                    "customer": "cus_test_webhook123",
                    "mode": "subscription",
                    "metadata": {"plan": "starter_10"},
                    "subscription": "sub_test_webhook123",
                }
            },
        }

        with patch("billing.stripe.Webhook.construct_event", return_value=fake_event):
            response = client.post(
                "/webhook/stripe",
                data=b"{}",
                headers={"Stripe-Signature": "t=1,v1=fake_signature_for_test"},
                content_type="application/json",
            )

        assert response.status_code == 200

        with app_module.app.app_context():
            customer = Customer.query.filter_by(email=email).first()
            assert customer is not None
            assert customer.subscription is not None
            assert customer.subscription.plan == "starter_10"
            assert customer.subscription.status == "active"


class TestCheckoutBypassForActiveSubscriber:
    """Scenario 2 : le meme email, actif sur /checkout, genere directement
    (redirection vers /success avec abonne=1) sans repasser par PayPal ni Stripe
    a l'acte."""

    def test_active_subscriber_bypasses_paypal(self, app_module, client):
        email = "abonne.actif@example.com"
        _make_active_subscriber(app_module, email, plan="starter_10")

        response = client.post(
            "/checkout", data=_checkout_payload(email), follow_redirects=False
        )

        assert response.status_code in (301, 302, 303)
        location = response.headers["Location"]
        assert "paypal.com" not in location
        assert "/success" in location
        assert "abonne=1" in location


class TestQuotaBlocksEleventhGeneration:
    """Scenario 3 : apres 10 generations comptabilisees dans le mois, la 11e n'est
    plus autorisee en acces direct (quota du plan starter_10 atteint) et /checkout
    repasse alors par un paiement Stripe a l'acte, exactement comme un compte non
    abonne. On mocke stripe.checkout.Session.create pour ne jamais appeler l'API
    Stripe reelle."""

    def test_tenth_allowed_eleventh_blocked_by_quota(self, app_module, client):
        from billing import get_access_status, record_usage

        email = "quota.test@example.com"
        _make_active_subscriber(app_module, email, plan="starter_10")

        with app_module.app.app_context():
            for _ in range(10):
                status = get_access_status(email)
                assert status["allowed"] is True
                record_usage(email)

            status_after_ten = get_access_status(email)
            assert status_after_ten["allowed"] is False
            assert status_after_ten["reason"] == "quota_exceeded"

        fake_session = SimpleNamespace(url="https://checkout.stripe.com/test-session-quota")
        with patch("billing.stripe.checkout.Session.create", return_value=fake_session) as mock_create:
            response = client.post(
                "/checkout", data=_checkout_payload(email), follow_redirects=False
            )

        mock_create.assert_called_once()
        location = response.headers["Location"]
        assert location == fake_session.url
        assert "abonne=1" not in location


class TestNonSubscriberChargedViaStripe:
    """Scenario 4 : un email qui n'a jamais souscrit d'abonnement est redirige vers
    un paiement Stripe a l'acte (mode=payment), sans regression introduite par la
    logique d'acces aux abonnements. On mocke stripe.checkout.Session.create pour
    ne jamais appeler l'API Stripe reelle."""

    def test_non_subscriber_redirected_to_stripe_checkout(self, client):
        email = "jamais.abonne@example.com"

        fake_session = SimpleNamespace(url="https://checkout.stripe.com/test-session-onetime")
        with patch("billing.stripe.checkout.Session.create", return_value=fake_session) as mock_create:
            response = client.post(
                "/checkout", data=_checkout_payload(email), follow_redirects=False
            )

        mock_create.assert_called_once()
        assert response.status_code in (301, 302, 303)
        location = response.headers["Location"]
        assert location == fake_session.url
        assert "abonne=1" not in location

        # Regression : /checkout construit success_url avec un ?token=... deja
        # present ; create_one_time_checkout ne doit pas y accoler un second '?'
        # (sinon Flask lit tout apres le premier '?' comme la valeur du token,
        # cf. bug "Commande introuvable" en prod).
        called_success_url = mock_create.call_args.kwargs["success_url"]
        assert called_success_url.count("?") == 1
        assert "&session_id={CHECKOUT_SESSION_ID}" in called_success_url
