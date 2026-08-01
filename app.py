from flask import Flask, render_template, request, send_file, redirect, session, url_for, abort
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from flask_sqlalchemy import SQLAlchemy
import os
import uuid
import json
import re
import unicodedata
import urllib.parse

app = Flask(__name__)

PAYPAL_EMAIL = "commercial@omnipub.net"
CONTACT_EMAIL = "contact@retroplanning.eu"
PRIX_HT = 2.00
PRIX_TTC = round(PRIX_HT * 1.20, 2)
TVA = round(PRIX_TTC - PRIX_HT, 2)
SITE_URL = "https://www.retroplanning.eu"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("La variable d'environnement ADMIN_PASSWORD doit etre definie")

app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("La variable d'environnement FLASK_SECRET_KEY doit etre definie")
GA_ID = "G-NW27CME5X7"

database_url = os.environ.get("DATABASE_URL", "sqlite:////tmp/retroplanning_blog.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --- Modeles sectoriels de retroplanning : voir retroplanning-templates/INTEGRATION.md ---
from templates_secteurs import get_template  # noqa: E402
from routes_templates import templates_bp  # noqa: E402
app.register_blueprint(templates_bp)
# --- Stripe billing (facturation) : voir retroplanning-stripe/INTEGRATION.md ---
# db est deja defini juste au-dessus : on importe les modeles ici (pour db.create_all())
# et on enregistre le blueprint des routes de facturation Stripe.
from models_billing import Customer, Subscription, UsageRecord, OneTimePayment  # noqa: E402,F401
from routes_billing import billing_bp  # noqa: E402
app.register_blueprint(billing_bp)
# Acces direct au generateur pour un email d'abonne actif (bypass paiement) :
# voir routes_billing.check_access_or_redirect / billing.get_access_status / billing.record_usage
from routes_billing import check_access_or_redirect # noqa: E402
from billing import record_usage, create_one_time_checkout # noqa: E402
from routes_billing import SITE_URL as BILLING_SITE_URL # noqa: E402
# --- Simulateur de TJM : voir cahier des charges "simulateur_tjm_v1" ---
from models_tjm import SimulationTJM  # noqa: E402,F401
from routes_tjm import tjm_bp  # noqa: E402
app.register_blueprint(tjm_bp)

ORDERS_FILE = "/tmp/orders.json"

VENDEUR = {
    "nom": "OMNIPUB",
    "adresse": "Parc Mermoz - 199 rue Helene Boucher",
    "cp": "34170",
    "ville": "Castelnau-le-Lez",
    "siret": "432 764 785 00023",
    "tva": "FR01432764785",
    "email": "contact@retroplanning.eu",
    "tel": "04 99 13 63 33",
}

HOME_FAQS = [
    {
        "question": "Comment faire un rétroplanning événementiel efficace ?",
        "answer": "Un bon rétroplanning part de la date de l'événement et remonte le temps. Définissez les jalons clés afin de visualiser les dates limites."
    },
    {
        "question": "Qu'est-ce qu'un rétroplanning ?",
        "answer": "Un rétroplanning est une méthode de planification qui part de la date finale du projet pour identifier les étapes nécessaires."
    },
    {
        "question": "À qui s'adresse le générateur de rétroplanning ?",
        "answer": "Il est conçu pour les agences, organisateurs d'événements, imprimeurs et chefs de projet."
    },
    {
        "question": "Combien de jalons puis-je ajouter ?",
        "answer": "Le générateur permet de renseigner jusqu'à six étapes clés avant la date finale."
    },
    {
        "question": "Puis-je modifier les couleurs du graphique ?",
        "answer": "Oui. Vous choisissez une couleur principale et une couleur secondaire."
    },
    {
        "question": "Puis-je utiliser le rétroplanning pour un autre projet ?",
        "answer": "Oui. Il convient aussi aux projets de production, impression, lancement et logistique."
    },
    {
        "question": "Le fichier est-il modifiable après téléchargement ?",
        "answer": "Le téléchargement est un PNG HD prêt à intégrer dans vos documents. Les données sont modifiables avant export."
    },
    {
        "question": "Vais-je recevoir une facture ?",
        "answer": "Oui. Après paiement, vous pouvez générer une facture PDF pour votre entreprise."
    },
    {
        "question": "Quelles sont les formules disponibles ?",
        "answer": "Paiement à l'acte à 2€ HT, abonnement Starter à 9,90€ HT/mois (10 rétroplannings), ou abonnement Illimité à 19,90€ HT/mois. Des modèles préétablis par secteur d'activité sont aussi disponibles pour démarrer plus vite."
    }
]


class Article(db.Model):
    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(220), nullable=False)
    slug = db.Column(db.String(240), nullable=False, unique=True, index=True)
    categorie = db.Column(db.String(80), nullable=False, default="Guides")
    extrait = db.Column(db.Text, nullable=False)
    resume = db.Column(db.Text, default="")
    contenu = db.Column(db.Text, nullable=False)
    points_cles = db.Column(db.Text, default="")
    image_url = db.Column(db.String(1000), default="")
    image_alt = db.Column(db.String(300), default="")
    meta_title = db.Column(db.String(70), default="")
    meta_description = db.Column(db.String(170), default="")
    faq_json = db.Column(db.Text, default="[]")
    statut = db.Column(db.String(20), nullable=False, default="brouillon")
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    @property
    def faqs(self):
        try:
            return json.loads(self.faq_json or "[]")
        except json.JSONDecodeError:
            return []

    @property
    def category_slug(self):
        return slugify(self.categorie)

    @property
    def reading_minutes(self):
        return max(1, round(len((self.contenu or "").split()) / 220))


@app.context_processor
def inject_globals():
    return {
        "ga_id": GA_ID,
        "contact_email": CONTACT_EMAIL,
        "site_url": SITE_URL
    }


@app.template_filter("content_blocks")
def content_blocks(content):
    blocks = []
    paragraph = []

    def flush():
        nonlocal paragraph
        if paragraph:
            blocks.append(("p", " ".join(paragraph)))
            paragraph = []

    for line in (content or "").splitlines():
        line = line.strip()
        if not line:
            flush()
        elif line.startswith("### "):
            flush()
            blocks.append(("h3", line[4:]))
        elif line.startswith("## "):
            flush()
            blocks.append(("h2", line[3:]))
        elif line.startswith("- "):
            flush()
            blocks.append(("li", line[2:]))
        else:
            paragraph.append(line)

    flush()
    return blocks


def slugify(value):
    text = unicodedata.normalize("NFKD", value or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "article"


def unique_slug(title, article_id=None):
    base = slugify(title)
    candidate = base
    number = 2

    while True:
        existing = Article.query.filter_by(slug=candidate).first()
        if not existing or existing.id == article_id:
            return candidate
        candidate = f"{base}-{number}"
        number += 1


def is_admin():
    return bool(session.get("admin"))


def load_orders():
    if not os.path.exists(ORDERS_FILE):
        return {}
    with open(ORDERS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_order(token, data):
    orders = load_orders()
    orders[token] = data
    with open(ORDERS_FILE, "w", encoding="utf-8") as file:
        json.dump(orders, file)


def get_order(token):
    return load_orders().get(token)


def next_invoice_number():
    count = sum(1 for order in load_orders().values() if order.get("paid")) + 1
    return f"FAC-{datetime.now().year}-{count:04d}"


def get_steps_from_form(form):
    steps = []
    for index in range(1, 5):
        label = form.get(f"label{index}", "").strip()
        date_value = form.get(f"date{index}", "").strip()
        if label and date_value:
            try:
                steps.append({
                    "label": label,
                    "date": datetime.strptime(date_value, "%Y-%m-%d")
                })
            except ValueError:
                pass

    event_date = form.get("date_event", "").strip()
    if event_date:
        try:
            steps.append({
                "label": "ÉVÉNEMENT",
                "date": datetime.strptime(event_date, "%Y-%m-%d")
            })
        except ValueError:
            pass

    return sorted(steps, key=lambda item: item["date"])


def generate_png(nom_client, nom_evenement, steps, phone, email, web, footer_societe, c_main="#3F8078", c_alt="#75A097"):
    fig = plt.figure(figsize=(16, 8))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 8)
    ax.axis("off")

    ax.add_patch(plt.Rectangle((0, 6.5), 16, 1.5, color=c_main))
    ax.text(8, 7.5, "RETROPLANNING DE PRODUCTION", ha="center", va="center", fontsize=20, color="white", fontweight="bold")
    ax.text(8, 7.0, f"{nom_evenement} | {nom_client}", ha="center", va="center", fontsize=14, color="white")

    start_date = steps[0]["date"]
    end_date = steps[-1]["date"]
    total_days = max((end_date - start_date).days, 1)

    def get_x(date_value):
        return 1 + 14 * ((date_value - start_date).days / total_days)

    ax.add_patch(FancyBboxPatch((1, 3.8), 14, 0.4, boxstyle="round,pad=0.1", color=c_main, alpha=0.2))

    for index in range(len(steps) - 1):
        x0 = get_x(steps[index]["date"])
        x1 = get_x(steps[index + 1]["date"])
        color = c_main if index % 2 == 0 else c_alt
        ax.add_patch(plt.Rectangle((x0, 3.8), x1 - x0, 0.4, linewidth=0, facecolor=color, zorder=3))

    for index, step in enumerate(steps):
        x = get_x(step["date"])
        top = index % 2 == 0
        y = 5.2 if top else 2.8
        ax.scatter(x, 4, s=200, color=c_main, zorder=5)
        ax.plot([x, x], [4, y], color=c_main, linestyle="--", alpha=0.5)
        ax.text(x, y + (0.2 if top else -0.2), step["label"], ha="center", va="bottom" if top else "top", fontsize=10, fontweight="bold", color="#1A1A1A")
        ax.text(
            x, y + (0.6 if top else -0.6),
            step["date"].strftime("%d/%m/%Y"),
            ha="center", va="center", color="white", fontweight="bold",
            bbox={"boxstyle": "round,pad=0.3", "facecolor": c_main, "edgecolor": "none"}
        )

    footer = " | ".join(item for item in [footer_societe, phone, email, web] if item) or nom_client
    ax.text(8, 0.5, footer, ha="center", va="center", fontsize=11, color="#1A1A1A", fontweight="bold")

    filename = f"retroplanning_{nom_client.replace(' ', '_')}_{uuid.uuid4().hex[:6]}.png"
    filepath = os.path.join("/tmp", filename)
    plt.savefig(filepath, dpi=200, bbox_inches="tight")
    plt.close()
    return filepath


def generate_facture(order, client_info, num_facture):
    filepath = os.path.join("/tmp", f"facture_{num_facture}.pdf")
    doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
    green = colors.HexColor("#3F8078")
    style = ParagraphStyle("base", fontSize=10, leading=14)

    story = [
        Paragraph("<b>OMNIPUB</b>", ParagraphStyle("vendor", fontSize=14, textColor=green)),
        Paragraph(VENDEUR["adresse"], style),
        Paragraph(f"{VENDEUR['cp']} {VENDEUR['ville']}", style),
        Paragraph(f"SIRET : {VENDEUR['siret']}", style),
        Paragraph(f"TVA : {VENDEUR['tva']}", style),
        Spacer(1, 0.8 * cm),
        Paragraph(f"<b>FACTURE N {num_facture}</b>", ParagraphStyle("invoice", fontSize=16, textColor=green, alignment=TA_CENTER)),
        Spacer(1, 0.5 * cm),
        Paragraph("<b>Facture a :</b>", ParagraphStyle("heading", fontSize=11, textColor=green)),
        Paragraph(f"<b>{client_info.get('raison_sociale', '')}</b>", style),
        Paragraph(client_info.get("adresse", ""), style),
        Paragraph(f"{client_info.get('cp', '')} {client_info.get('ville', '')}", style),
        Spacer(1, 0.8 * cm),
    ]

    data = [
        ["Designation", "Qte", "Prix HT", "TVA", "Total TTC"],
        ["Retroplanning de production PNG HD", "1", f"{PRIX_HT:.2f} EUR", f"20 percent ({TVA:.2f} EUR)", f"{PRIX_TTC:.2f} EUR"],
    ]

    table = Table(data, colWidths=[8 * cm, 1.5 * cm, 2.5 * cm, 3 * cm, 2.5 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), green),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story += [
        table,
        Spacer(1, 0.5 * cm),
        Paragraph(f"<b>Total TTC : {PRIX_TTC:.2f} EUR</b>", ParagraphStyle("total", fontSize=12, textColor=green, alignment=TA_RIGHT)),
    ]
    doc.build(story)
    return filepath


@app.route("/")
def landing():
    return render_template("landing.html", faqs=HOME_FAQS, contact_email=CONTACT_EMAIL)


@app.route("/formulaire")
def index():
    modele_slug = request.args.get("modele")
    etapes_initiales = None
    if modele_slug:
        modele = get_template(modele_slug)
        if modele:
            # Le formulaire gere jusqu'a 6 etapes intermediaires + date evenement.
            # On exclut "Lancement du projet" (1ere etape) et "Jour J" (derniere etape),
            # deja couverts par les champs client/evenement/date_event. 6 est le nombre
            # maximum d'etapes intermediaires parmi les 8 modeles (mariage en compte 6).
            etapes_initiales = modele["etapes"][1:-1][:6]
    return render_template(
        "index.html",
        prix=f"{PRIX_TTC:.2f}",
        contact_email=CONTACT_EMAIL,
        etapes_initiales=etapes_initiales,
    )


@app.route("/checkout", methods=["POST"])
def checkout():
    token = uuid.uuid4().hex
    steps_raw = []

    for index in range(1, 7):
        label = request.form.get(f"label{index}", "").strip()
        date_value = request.form.get(f"date{index}", "").strip()
        if label and date_value:
            steps_raw.append((label, date_value))

    order = {
        "token": token,
        "paid": False,
        "nom_client": request.form.get("client", ""),
        "nom_evenement": request.form.get("evenement", ""),
        "phone": request.form.get("phone", ""),
        "email": request.form.get("email", ""),
        "web": request.form.get("web", ""),
        "footer_societe": request.form.get("footer_societe", ""),
        "c_main": request.form.get("c_main", "#3F8078"),
        "c_alt": request.form.get("c_alt", "#75A097"),
        "steps_raw": steps_raw,
        "date_event": request.form.get("date_event", ""),
    }
    save_order(token, order)

    # --- Stripe billing : un email d'abonne actif genere directement, sans repasser par un paiement ---
    email = order.get("email", "").strip()
    if email and check_access_or_redirect(email) is None:
        return redirect(url_for("success", token=token, abonne="1"))

    session = create_one_time_checkout(
        email=email,
        success_url=BILLING_SITE_URL + f"/success?token={token}",
        cancel_url=BILLING_SITE_URL + "/cancel",
    )
    return redirect(session.url, code=303)


@app.route("/success")
def success():
    token = request.args.get("token", "")
    order = get_order(token)
    if not order:
        return "Commande introuvable.", 404

    order["paid"] = True
    steps = []

    for label, date_value in order.get("steps_raw", []):
        try:
            steps.append({"label": label, "date": datetime.strptime(date_value, "%Y-%m-%d")})
        except ValueError:
            pass

    if order.get("date_event"):
        try:
            steps.append({"label": "ÉVÉNEMENT", "date": datetime.strptime(order["date_event"], "%Y-%m-%d")})
        except ValueError:
            pass

    steps.sort(key=lambda item: item["date"])
    order["png_path"] = generate_png(
        order["nom_client"], order["nom_evenement"], steps,
        order.get("phone", ""), order.get("email", ""),
        order.get("web", ""), order.get("footer_societe", ""),
        order.get("c_main", "#3F8078"), order.get("c_alt", "#75A097")
    )
    save_order(token, order)

    # --- Stripe billing : decompte le quota mensuel si la generation vient d'un abonnement ---
    if request.args.get("abonne") == "1" and order.get("email"):
        record_usage(order["email"])

    return render_template("success.html", token=token, order=order, contact_email=CONTACT_EMAIL)


@app.route("/download/png/<token>")
def download_png(token):
    order = get_order(token)
    if not order or not order.get("paid"):
        return "Acces non autorise.", 403
    return send_file(order["png_path"], as_attachment=True, download_name=f"retroplanning_{order['nom_client'].replace(' ', '_')}.png")


@app.route("/facture/<token>", methods=["GET", "POST"])
def facture(token):
    order = get_order(token)
    if not order or not order.get("paid"):
        return "Acces non autorise.", 403

    if request.method == "POST":
        client_info = {
            key: request.form.get(key, "")
            for key in ["raison_sociale", "adresse", "cp", "ville", "siret", "tva_intra"]
        }
        number = next_invoice_number()
        pdf_path = generate_facture(order, client_info, number)
        return send_file(pdf_path, as_attachment=True, download_name=f"facture_{number}.pdf")

    return render_template("facture.html", token=token, order=order, contact_email=CONTACT_EMAIL)


@app.route("/cancel")
def cancel():
    return render_template("cancel.html", contact_email=CONTACT_EMAIL)


@app.route("/blog")
def blog_index():
    articles = Article.query.filter_by(statut="publie").order_by(Article.published_at.desc()).all()
    return render_template("blog_index.html", articles=articles, current_category=None)


@app.route("/blog/categorie/<category_slug>")
def blog_category(category_slug):
    articles = [
        article for article in Article.query.filter_by(statut="publie").order_by(Article.published_at.desc()).all()
        if article.category_slug == category_slug
    ]
    if not articles:
        abort(404)
    return render_template("blog_index.html", articles=articles, current_category=articles[0].categorie)


@app.route("/blog/<slug>")
def blog_article(slug):
    article = Article.query.filter_by(slug=slug, statut="publie").first_or_404()
    related = Article.query.filter(
        Article.statut == "publie",
        Article.categorie == article.categorie,
        Article.id != article.id
    ).order_by(Article.published_at.desc()).limit(3).all()
    return render_template("blog_article.html", article=article, related=related)


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if request.form.get("password", "") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Mot de passe incorrect."
    return render_template("admin_login.html", error=error)


@app.route("/admin/dashboard")
def admin_dashboard():
    if not is_admin():
        return redirect(url_for("admin_login"))
    return render_template("admin_dashboard.html")


@app.route("/admin/generate", methods=["GET", "POST"])
def admin_generate():
    if not is_admin():
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        steps = get_steps_from_form(request.form)
        if len(steps) < 2:
            return "Il faut au moins une étape et la date événement.", 400
        file_path = generate_png(
            request.form.get("client", "CLIENT"),
            request.form.get("evenement", "ÉVÉNEMENT"),
            steps,
            request.form.get("phone", ""),
            request.form.get("email", ""),
            request.form.get("web", ""),
            request.form.get("footer_societe", ""),
            request.form.get("c_main", "#3F8078"),
            request.form.get("c_alt", "#75A097")
        )
        return send_file(file_path, as_attachment=True)

    return render_template("admin_generate.html")


@app.route("/admin/blog")
def admin_blog():
    if not is_admin():
        return redirect(url_for("admin_login"))
    articles = Article.query.order_by(Article.updated_at.desc()).all()
    return render_template("admin_blog_list.html", articles=articles)


def save_article_from_form(article):
    article.titre = request.form.get("titre", "").strip()
    article.slug = unique_slug(request.form.get("slug", "").strip() or article.titre, article.id)
    article.categorie = request.form.get("categorie", "").strip() or "Guides"
    article.extrait = request.form.get("extrait", "").strip()
    article.resume = request.form.get("resume", "").strip()
    article.contenu = request.form.get("contenu", "").strip()
    article.points_cles = request.form.get("points_cles", "").strip()
    article.image_url = request.form.get("image_url", "").strip()
    article.image_alt = request.form.get("image_alt", "").strip()
    article.meta_title = request.form.get("meta_title", "").strip() or article.titre
    article.meta_description = request.form.get("meta_description", "").strip() or article.extrait

    faqs = []
    for index in range(1, 4):
        question = request.form.get(f"faq_q{index}", "").strip()
        answer = request.form.get(f"faq_a{index}", "").strip()
        if question and answer:
            faqs.append({"question": question, "answer": answer})

    article.faq_json = json.dumps(faqs, ensure_ascii=False)
    article.statut = "publie" if request.form.get("statut") == "publie" else "brouillon"

    if article.statut == "publie" and not article.published_at:
        article.published_at = datetime.utcnow()
    if article.statut == "brouillon":
        article.published_at = None


@app.route("/admin/blog/nouveau", methods=["GET", "POST"])
def admin_blog_new():
    if not is_admin():
        return redirect(url_for("admin_login"))

    article = Article()
    if request.method == "POST":
        save_article_from_form(article)
        if not article.titre or not article.extrait or not article.contenu:
            return render_template(
                "admin_blog_form.html",
                article=article,
                error="Titre, extrait et contenu sont obligatoires."
            )
        db.session.add(article)
        db.session.commit()
        return redirect(url_for("admin_blog"))

    return render_template("admin_blog_form.html", article=article, error=None)


@app.route("/admin/blog/<int:article_id>/modifier", methods=["GET", "POST"])
def admin_blog_edit(article_id):
    if not is_admin():
        return redirect(url_for("admin_login"))

    article = Article.query.get_or_404(article_id)
    if request.method == "POST":
        save_article_from_form(article)
        if not article.titre or not article.extrait or not article.contenu:
            return render_template(
                "admin_blog_form.html",
                article=article,
                error="Titre, extrait et contenu sont obligatoires."
            )
        db.session.commit()
        return redirect(url_for("admin_blog"))

    return render_template("admin_blog_form.html", article=article, error=None)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/")


@app.route("/robots.txt")
def robots():
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin",
        "Disallow: /checkout",
        "Disallow: /success",
        "Disallow: /facture",
        "Disallow: /download",
        "Disallow: /tjm/calculer",
        "Disallow: /tjm/resultats",
        "Disallow: /tjm/rapport",
        "",
        "Sitemap: " + SITE_URL + "/sitemap.xml",
        "",
    ]
    return app.response_class("\n".join(lines), mimetype="text/plain")


_sitemap_cache = {"content": None, "ts": 0}
SITEMAP_CACHE_TTL = 600


@app.route("/sitemap.xml")
def sitemap():
    import time
    now = time.time()
    if _sitemap_cache["content"] and (now - _sitemap_cache["ts"] < SITEMAP_CACHE_TTL):
        return app.response_class(_sitemap_cache["content"], mimetype="application/xml")

    urls = [
        (SITE_URL + "/", "weekly", "1.0"),
        (SITE_URL + "/formulaire", "monthly", "0.8"),
        (SITE_URL + "/blog", "weekly", "0.9"),
        (SITE_URL + "/tjm", "monthly", "0.8"),
    ]

    try:
        for article in Article.query.filter_by(statut="publie").all():
            urls.append((SITE_URL + "/blog/" + article.slug, "monthly", "0.8"))
    except Exception:
        # Base de donnees indisponible ou lente : on sert quand meme les pages statiques
        pass

    entries = []
    today = datetime.utcnow().date().isoformat()
    for location, frequency, priority in urls:
        entries.append(
            "<url>"
            + "<loc>" + location + "</loc>"
            + "<lastmod>" + today + "</lastmod>"
            + "<changefreq>" + frequency + "</changefreq>"
            + "<priority>" + priority + "</priority>"
            + "</url>"
        )

    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(entries)
        + "</urlset>"
    )
    _sitemap_cache["content"] = content
    _sitemap_cache["ts"] = now

    return app.response_class(content, mimetype="application/xml")


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
