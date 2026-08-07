# templates_secteurs.py
# Modeles de retroplanning par secteur d'activite, proposes comme point de depart
# dans l'ecran de generation (boutons "Je pars d'un modele").
#
# Structure fixe : "Lancement du projet" en premiere etape, "Jour J" en derniere.
# Les etapes intermediaires sont entierement modifiables une fois le modele charge
# (renommer, deplacer, supprimer, en ajouter).

TEMPLATES_SECTEURS = {
    "mariage": {
        "label": "Mariage",
        "icone": "💍",
        "duree_recommandee_jours": 365,
        "description": "Sécurisez la réservation du lieu, le traiteur, les tenues et le plan de table jusqu'au jour J.",
        "etapes": [
            "Lancement du projet",
            "Réservation du lieu",
            "Traiteur & photographe",
            "Tenues",
            "Faire-part",
            "Plan de table",
            "Essayages finaux",
            "Jour J",
        ],
    },
    "salon_professionnel": {
        "label": "Salon professionnel / stand événementiel",
        "icone": "🎪",
        "duree_recommandee_jours": 90,
        "description": "Cadrez la réservation du stand, les objets publicitaires et la logistique transport jusqu'à l'ouverture.",
        "etapes": [
            "Lancement du projet",
            "Réservation du stand",
            "Design & objets publicitaires",
            "Communication invités",
            "Briefing équipe",
            "Logistique transport",
            "Jour J",
        ],
    },
    "lancement_produit": {
        "label": "Lancement de produit",
        "icone": "🚀",
        "duree_recommandee_jours": 60,
        "description": "Coordonnez supports de communication, presse, formation des équipes de vente et stock avant la sortie.",
        "etapes": [
            "Lancement du projet",
            "Production des supports",
            "Communication presse",
            "Formation équipe vente",
            "Teasing réseaux sociaux",
            "Stock & logistique",
            "Jour J",
        ],
    },
    "demenagement": {
        "label": "Déménagement",
        "icone": "📦",
        "duree_recommandee_jours": 60,
        "description": "N'oubliez ni les devis déménageurs, ni les résiliations, ni les cartons, ni les démarches administratives.",
        "etapes": [
            "Lancement du projet",
            "Devis déménageurs",
            "Résiliations & réexpédition courrier",
            "Cartons",
            "Démarches administratives",
            "Jour J",
        ],
    },
    "travaux_renovation": {
        "label": "Travaux / rénovation",
        "icone": "🔨",
        "duree_recommandee_jours": 90,
        "description": "Suivez les devis artisans, les permis, le choix des matériaux et le planning des intervenants.",
        "etapes": [
            "Lancement du projet",
            "Devis artisans",
            "Permis / déclarations",
            "Choix des matériaux",
            "Planning intervenants",
            "Jour J",
        ],
    },
    "recrutement": {
        "label": "Recrutement / onboarding",
        "icone": "🧑‍💼",
        "duree_recommandee_jours": 30,
        "description": "De la diffusion de l'offre à l'onboarding : entretiens, contrat et préparation du poste de travail.",
        "etapes": [
            "Lancement du projet",
            "Diffusion de l'offre",
            "Entretiens",
            "Contrat",
            "Préparation poste de travail",
            "Jour J",
        ],
    },
    "association": {
        "label": "Association / événement caritatif",
        "icone": "🤝",
        "duree_recommandee_jours": 90,
        "description": "Coordonnez la recherche de sponsors, la réservation du lieu, la communication et les bénévoles.",
        "etapes": [
            "Lancement du projet",
            "Recherche de sponsors",
            "Réservation du lieu",
            "Communication",
            "Bénévoles",
            "Jour J",
        ],
    },
    "these_memoire": {
        "label": "Soutenance de thèse / mémoire",
        "icone": "🎓",
        "duree_recommandee_jours": 90,
        "description": "Cadrez le plan, la rédaction, la relecture et la mise en forme avant la soutenance.",
        "etapes": [
            "Lancement du projet",
            "Plan",
            "Rédaction",
            "Relecture",
            "Mise en forme",
            "Jour J",
        ],
    },
}


def get_template(slug):
    """Retourne le modele correspondant au slug, ou None si inconnu."""
    return TEMPLATES_SECTEURS.get(slug)


def list_templates():
    """Retourne la liste des modeles pour affichage (boutons de selection)."""
    return [
        {"slug": slug, **data}
        for slug, data in TEMPLATES_SECTEURS.items()
    ]
