# tests/test_tjm_routes.py
# Tests d'integration du parcours du simulateur de TJM (routes_tjm.py, models_tjm.py),
# sur le meme modele que tests/test_stripe_billing.py : base SQLite temporaire, aucun
# appel reseau reel.
#
# Execution : pytest tests/ -v

import sys
import uuid

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

APP_MODULES = ["app", "billing", "routes_billing", "models_billing", "models_tjm", "routes_tjm", "calculs_tjm"]

DONNEES_VALIDES = {
    "revenu_net_mensuel": "3000",
    "mois_remuneres": "11",
    "charges_mensuelles": "400",
    "statut_juridique": "micro",
    "temps_facturable": "60",
    "jours_par_semaine": "5",
    "semaines_conges": "5",
}


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
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


def test_accueil_repond_200(client):
    assert client.get("/tjm/").status_code == 200


def test_questionnaire_repond_200(client):
    assert client.get("/tjm/questionnaire").status_code == 200


def test_calcul_valide_redirige_vers_resultats(client):
    reponse = client.post("/tjm/calculer", data=DONNEES_VALIDES)
    assert reponse.status_code == 302
    assert "/tjm/resultats/" in reponse.headers["Location"]


def test_calcul_valide_puis_page_resultats_affiche_le_tjm(client):
    reponse = client.post("/tjm/calculer", data=DONNEES_VALIDES)
    page_resultats = client.get(reponse.headers["Location"])
    assert page_resultats.status_code == 200
    assert b"TJM conseill" in page_resultats.data
    assert b"TJM minimum" in page_resultats.data


def test_calcul_enregistre_une_simulation_en_base(client, app_module):
    reponse = client.post("/tjm/calculer", data=DONNEES_VALIDES)
    token = reponse.headers["Location"].rsplit("/", 1)[-1]

    with app_module.app.app_context():
        simulation = app_module.SimulationTJM.query.filter_by(token=token).first()
        assert simulation is not None
        assert simulation.email is None
        assert simulation.consentement_marketing is False
        assert simulation.tjm_conseille > simulation.tjm_minimum


def test_champ_manquant_renvoie_400_et_ne_cree_pas_de_simulation(client, app_module):
    donnees = dict(DONNEES_VALIDES)
    donnees["revenu_net_mensuel"] = ""
    reponse = client.post("/tjm/calculer", data=donnees)
    assert reponse.status_code == 400

    with app_module.app.app_context():
        assert app_module.SimulationTJM.query.count() == 0


def test_temps_facturable_nul_renvoie_400_avec_message_explicite(client):
    donnees = dict(DONNEES_VALIDES)
    donnees["temps_facturable"] = "0"
    reponse = client.post("/tjm/calculer", data=donnees)
    assert reponse.status_code == 400
    assert "facturable".encode() in reponse.data


def test_resultats_pour_token_inconnu_renvoie_404(client):
    assert client.get("/tjm/resultats/token-inexistant").status_code == 404


def test_rapport_sans_email_ne_capture_pas_de_prospect(client, app_module):
    reponse = client.post("/tjm/calculer", data=DONNEES_VALIDES)
    token = reponse.headers["Location"].rsplit("/", 1)[-1]

    rapport = client.post(f"/tjm/rapport/{token}", data={})
    assert rapport.status_code == 200
    assert rapport.content_type == "application/pdf"

    with app_module.app.app_context():
        simulation = app_module.SimulationTJM.query.filter_by(token=token).first()
        assert simulation.email is None


def test_rapport_avec_email_et_consentement_met_a_jour_la_simulation(client, app_module):
    reponse = client.post("/tjm/calculer", data=DONNEES_VALIDES)
    token = reponse.headers["Location"].rsplit("/", 1)[-1]

    rapport = client.post(
        f"/tjm/rapport/{token}",
        data={"email": "prospect@example.com", "consentement_marketing": "on"},
    )
    assert rapport.status_code == 200

    with app_module.app.app_context():
        simulation = app_module.SimulationTJM.query.filter_by(token=token).first()
        assert simulation.email == "prospect@example.com"
        assert simulation.consentement_marketing is True


def test_consentement_marketing_decoche_par_defaut(client, app_module):
    reponse = client.post("/tjm/calculer", data=DONNEES_VALIDES)
    token = reponse.headers["Location"].rsplit("/", 1)[-1]

    # Case non cochee (absente du POST, comme un navigateur le ferait) : le consentement
    # doit rester False meme si un email est fourni.
    client.post(f"/tjm/rapport/{token}", data={"email": "prospect2@example.com"})

    with app_module.app.app_context():
        simulation = app_module.SimulationTJM.query.filter_by(token=token).first()
        assert simulation.consentement_marketing is False
