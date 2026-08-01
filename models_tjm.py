# models_tjm.py
# Modele de base de donnees du simulateur de TJM : une ligne par simulation realisee,
# incluant les eventuelles coordonnees de prospect (section 3 et 6 du cahier des charges).
# Utilise la meme instance SQLAlchemy `db` que le reste de l'application (definie dans app.py).

from datetime import datetime

from app import db


class SimulationTJM(db.Model):
    __tablename__ = "simulations_tjm"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # --- Entrees saisies par l'utilisateur (section 3) ---
    revenu_net_mensuel = db.Column(db.Float, nullable=False)
    mois_remuneres = db.Column(db.Float, nullable=False)
    charges_mensuelles = db.Column(db.Float, nullable=False)
    statut_juridique = db.Column(db.String(20), nullable=False)
    temps_facturable = db.Column(db.Float, nullable=False)
    jours_par_semaine = db.Column(db.Float, nullable=False)
    semaines_conges = db.Column(db.Float, nullable=False)

    # --- Resultats calcules au moment de la simulation (calculs_tjm.calculer_tjm) ---
    jours_facturables_an = db.Column(db.Float, nullable=False)
    ca_cible_annuel = db.Column(db.Float, nullable=False)
    tjm_minimum = db.Column(db.Float, nullable=False)
    tjm_conseille = db.Column(db.Float, nullable=False)

    # --- Capture de prospect (section 6), toujours facultative ---
    email = db.Column(db.String(255), nullable=True, index=True)
    consentement_marketing = db.Column(db.Boolean, nullable=False, default=False)
    source = db.Column(db.String(80), nullable=True, default="simulateur_tjm")

    def entrees_dict(self):
        """Reconstruit les entrees saisies, pour recalculer un ResultatTJM complet
        (avec repartition et messages) via calculs_tjm.calculer_tjm sans les stocker
        deux fois en base."""
        return {
            "revenu_net_mensuel": self.revenu_net_mensuel,
            "mois_remuneres": self.mois_remuneres,
            "charges_mensuelles": self.charges_mensuelles,
            "statut_juridique": self.statut_juridique,
            "temps_facturable": self.temps_facturable,
            "jours_par_semaine": self.jours_par_semaine,
            "semaines_conges": self.semaines_conges,
        }
