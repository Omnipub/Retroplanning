# models_billing.py
# A ajouter au fichier models existant (ou a importer dans app.py) aux cotes du modele Article.
# Utilise la meme instance SQLAlchemy db que le reste de l'application.
#
# NOTE D'INTEGRATION : dans ce projet, l'instance SQLAlchemy `db` est definie directement
# dans app.py (il n'existe pas de module db.py separe). On importe donc `db` depuis `app`.

from datetime import datetime
from app import db


class Customer(db.Model):
    """Un client identifie par son email + son Customer ID Stripe."""
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    stripe_customer_id = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subscription = db.relationship(
        "Subscription", backref="customer", uselist=False, cascade="all, delete-orphan"
    )
    usage_records = db.relationship(
        "UsageRecord", backref="customer", cascade="all, delete-orphan"
    )


class Subscription(db.Model):
    """Abonnement actif (ou passe) d'un client. Un seul abonnement actif par client a la fois."""
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    stripe_subscription_id = db.Column(db.String(64), unique=True, nullable=False)
    plan = db.Column(db.String(32), nullable=False)  # "starter_10" ou "illimite"
    status = db.Column(db.String(32), nullable=False, default="active")
    # valeurs possibles (miroir des statuts Stripe) :
    # active, trialing, past_due, canceled, unpaid, incomplete, incomplete_expired
    current_period_end = db.Column(db.DateTime, nullable=True)
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def is_active(self):
        return self.status in ("active", "trialing")


class UsageRecord(db.Model):
    """
    Compteur d'utilisation mensuel, pour le palier 'starter_10' (10 plannings max/mois).
    Une ligne par (client, mois) ; incrementee a chaque generation reussie.
    """
    __tablename__ = "usage_records"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    period = db.Column(db.String(7), nullable=False)  # format "YYYY-MM"
    count = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("customer_id", "period", name="uq_customer_period"),
    )


class OneTimePayment(db.Model):
    """Trace des paiements a l'acte (2 euros), pour la generation de facture et l'historique."""
    __tablename__ = "one_time_payments"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    stripe_checkout_session_id = db.Column(db.String(64), unique=True, nullable=False)
    stripe_payment_intent_id = db.Column(db.String(64), nullable=True)
    amount_ttc = db.Column(db.Numeric(10, 2), nullable=False)
    invoice_url = db.Column(db.String(512), nullable=True)  # lien facture Stripe (hosted_invoice_url ou receipt)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
