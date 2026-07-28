# routes_templates.py
# Route Flask a brancher sur app.py pour proposer les modeles sectoriels
# avant la generation du retroplanning.
#
# NOTE D'INTEGRATION : dans ce projet, il n'existe pas de route/template "/generer"
# ni "generer.html" (contrairement au schema suppose ci-dessous a titre d'exemple).
# La route de generation existante est "/formulaire" (fonction index() dans app.py,
# template templates/index.html). La lecture du parametre ?modele=<slug> a donc ete
# ajoutee DIRECTEMENT dans la route existante "/formulaire" (voir app.py), plutot que
# dupliquee ici sous forme de nouvelle route "/generer". Seule la route "/modeles"
# (l'ecran de selection) est definie dans ce blueprint.

from flask import Blueprint, render_template

from templates_secteurs import list_templates

templates_bp = Blueprint("templates_secteurs", __name__)


@templates_bp.route("/modeles")
def choix_modele():
    """Ecran de selection : une grille de boutons, un par secteur, plus
    un bouton 'Je pars de zero'. Chaque bouton mene vers /formulaire?modele=<slug>."""
    return render_template("choix_modele.html", modeles=list_templates())
