# routes_tjm.py
# Routes Flask du simulateur de TJM (Taux Journalier Moyen), a enregistrer dans app.py
# via app.register_blueprint (meme pattern que routes_templates.py et routes_billing.py).
#
# Parcours (cahier des charges section 5) :
#   GET  /tjm                      -> page d'accueil (5.1)
#   GET  /tjm/questionnaire        -> questionnaire multi-etapes (5.2)
#   POST /tjm/calculer             -> valide + calcule + enregistre la simulation, redirige
#   GET  /tjm/resultats/<token>    -> page de resultats (5.3)
#   POST /tjm/rapport/<token>      -> capture email/consentement + telechargement PDF (6)

import os
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, send_file, abort
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from app import db
from calculs_tjm import DEFAUTS, DISCLAIMER, ResultatImpossible, ValeurInvalide, calculer_tjm, valider_entrees
from models_tjm import SimulationTJM

tjm_bp = Blueprint("tjm", __name__, url_prefix="/tjm")

CHAMPS_FORMULAIRE = [
    "revenu_net_mensuel",
    "mois_remuneres",
    "charges_mensuelles",
    "statut_juridique",
    "temps_facturable",
    "jours_par_semaine",
    "semaines_conges",
]


def _simulation_ou_404(token):
    simulation = SimulationTJM.query.filter_by(token=token).first()
    if not simulation:
        abort(404)
    return simulation


@tjm_bp.route("/")
def accueil():
    return render_template("tjm_accueil.html")


@tjm_bp.route("/questionnaire")
def questionnaire():
    return render_template("tjm_questionnaire.html", defauts=DEFAUTS, erreur=None, valeurs=DEFAUTS)


@tjm_bp.route("/calculer", methods=["POST"])
def calculer():
    valeurs_soumises = {champ: request.form.get(champ, "") for champ in CHAMPS_FORMULAIRE}

    try:
        entrees = valider_entrees(valeurs_soumises)
        resultat = calculer_tjm(entrees)
    except (ValeurInvalide, ResultatImpossible) as exc:
        return render_template(
            "tjm_questionnaire.html",
            defauts=DEFAUTS,
            erreur=str(exc),
            valeurs=valeurs_soumises,
        ), 400

    simulation = SimulationTJM(
        token=uuid.uuid4().hex,
        source=request.args.get("source", "simulateur_tjm"),
        jours_facturables_an=resultat.jours_facturables_an,
        ca_cible_annuel=resultat.ca_cible_annuel,
        tjm_minimum=resultat.tjm_minimum,
        tjm_conseille=resultat.tjm_conseille,
        **entrees.as_dict(),
    )
    db.session.add(simulation)
    db.session.commit()

    return redirect(url_for("tjm.resultats", token=simulation.token))


@tjm_bp.route("/resultats/<token>")
def resultats(token):
    simulation = _simulation_ou_404(token)
    entrees = valider_entrees(simulation.entrees_dict())
    resultat = calculer_tjm(entrees)
    return render_template(
        "tjm_resultats.html",
        simulation=simulation,
        resultat=resultat,
        disclaimer=DISCLAIMER,
    )


@tjm_bp.route("/rapport/<token>", methods=["POST"])
def rapport(token):
    simulation = _simulation_ou_404(token)
    entrees = valider_entrees(simulation.entrees_dict())
    resultat = calculer_tjm(entrees)

    email = request.form.get("email", "").strip()
    if email:
        simulation.email = email
        simulation.consentement_marketing = request.form.get("consentement_marketing") == "on"
        db.session.commit()

    pdf_path = _generer_rapport_pdf(simulation, resultat)
    return send_file(pdf_path, as_attachment=True, download_name=f"rapport-tjm-{token[:8]}.pdf")


def _generer_rapport_pdf(simulation, resultat):
    filepath = os.path.join("/tmp", f"rapport_tjm_{simulation.token}.pdf")
    doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
    teal = colors.HexColor("#3F8078")
    style = ParagraphStyle("base", fontSize=10, leading=14)

    story = [
        Paragraph("<b>OMNIPUB — Simulateur de TJM</b>", ParagraphStyle("titre", fontSize=16, textColor=teal)),
        Paragraph("Rapport de simulation de Taux Journalier Moyen", style),
        Spacer(1, 0.8 * cm),
        Paragraph(f"<b>TJM conseille : {resultat.tjm_conseille:.2f} € / jour</b>", ParagraphStyle("resultat", fontSize=14, textColor=teal)),
        Paragraph(f"TJM minimum : {resultat.tjm_minimum:.2f} € / jour", style),
        Spacer(1, 0.5 * cm),
    ]

    donnees = [
        ["Indicateur", "Valeur"],
        ["Chiffre d'affaires cible annuel", f"{resultat.ca_cible_annuel:.2f} €"],
        ["Chiffre d'affaires cible mensuel", f"{resultat.ca_cible_mensuel:.2f} €"],
        ["Jours facturables estimes par an", f"{resultat.jours_facturables_an:.1f}"],
        ["Revenu net mensuel souhaite", f"{simulation.revenu_net_mensuel:.2f} €"],
        ["Charges professionnelles mensuelles", f"{simulation.charges_mensuelles:.2f} €"],
        ["Statut juridique", simulation.statut_juridique],
    ]
    table = Table(donnees, colWidths=[10 * cm, 6 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), teal),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(DISCLAIMER, ParagraphStyle("mentions", fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))

    doc.build(story)
    return filepath
