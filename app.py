from flask import Flask, render_template, request, send_file, redirect, session, url_for, abort
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from flask_sqlalchemy import SQLAlchemy
import os, uuid, json, re, unicodedata

app = Flask(__name__)

# --- CONFIGURATION ---
PAYPAL_EMAIL   = "commercial@omnipub.net"
CONTACT_EMAIL  = "contact@retroplanning.eu"
PRIX_TTC       = 2.00
PRIX_HT        = round(PRIX_TTC / 1.20, 2)
TVA            = round(PRIX_TTC - PRIX_HT, 2)
SITE_URL       = "https://www.retroplanning.eu"
ADMIN_PASSWORD = "Omnipub&2026"
app.secret_key = "retroplanning_secret_key_2026"
GA_ID          = "G-NW27CME5X7"

# --- BASE DE DONNEES ---
database_url = os.environ.get("DATABASE_URL", "sqlite:////tmp/retroplanning_blog.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

VENDEUR = {
    "nom":     "OMNIPUB",
    "adresse": "Parc Mermoz - 199 rue Helene Boucher",
    "cp":      "34170",
    "ville":   "Castelnau-le-Lez",
    "siret":   "432 764 785 00023",
    "tva":     "FR01432764785",
    "email":   "contact@retroplanning.eu",
    "tel":     "04 99 13 63 33",
}

ORDERS_FILE = "/tmp/orders.json"

HOME_FAQS = [
    {"question": "Comment faire un retroplanning evenementiel efficace ?",
     "answer": "Partez de la date de evenement et remontez le temps en definissant vos jalons cles."},
    {"question": "Qu est-ce qu un retroplanning ?",
     "answer": "Une methode de planification qui part de la date finale pour identifier toutes les etapes."},
    {"question": "A qui s adresse le generateur ?",
     "answer": "Aux agences de communication, organisateurs, imprimeurs et chefs de projet."},
    {"question": "Combien de jalons puis-je ajouter ?",
     "answer": "Jusqu a quatre etapes cles avant la date finale."},
    {"question": "Puis-je modifier les couleurs ?",
     "answer": "Oui, couleur principale et secondaire sont personnalisables."},
    {"question": "Puis-je l utiliser pour un autre projet ?",
     "answer": "Oui : production, impression, lancement, logistique."},
    {"question": "Le fichier est-il modifiable apres telechargement ?",
     "answer": "Non, le PNG est final. Modifiez les donnees avant l export."},
    {"question": "Vais-je recevoir une facture ?",
     "answer": "Oui, une facture PDF est generee apres paiement."},
]


# --- MODELE ARTICLE ---
class Article(db.Model):
    __tablename__ = "articles"
    id            = db.Column(db.Integer, primary_key=True)
    titre         = db.Column(db.String(220), nullable=False)
    slug          = db.Column(db.String(240), nullable=False, unique=True, index=True)
    categorie     = db.Column(db.String(80),  nullable=False, default="Guides")
    extrait       = db.Column(db.Text, nullable=False)
    resume        = db.Column(db.Text, default="")
    contenu       = db.Column(db.Text, nullable=False)
    points_cles   = db.Column(db.Text, default="")
    image_url     = db.Column(db.String(1000), default="")
    image_alt     = db.Column(db.String(300),  default="")
    meta_title    = db.Column(db.String(70),   default="")
    meta_desc     = db.Column(db.String(170),  default="")
    faq_json      = db.Column(db.Text, default="[]")
    statut        = db.Column(db.String(20), nullable=False, default="brouillon")
    published_at  = db.Column(db.DateTime, nullable=True)
    created_at    = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, nullable=False, default=datetime.utcnow,
                              onupdate=datetime.utcnow)

    @property
    def faqs(self):
        try:
            return json.loads(self.faq_json or "[]")
        except Exception:
            return []

    @property
    def category_slug(self):
        return _slugify(self.categorie)

    @property
    def reading_minutes(self):
        return max(1, round(len((self.contenu or "").split()) / 220))


# --- HELPERS ---
@app.context_processor
def inject_globals():
    return dict(ga_id=GA_ID, contact_email=CONTACT_EMAIL, site_url=SITE_URL)


@app.template_filter("content_blocks")
def content_blocks(content):
    blocks, para = [], []

    def flush():
        if para:
            blocks.append(("p", " ".join(para)))
            para.clear()

    for line in (content or "").splitlines():
        line = line.strip()
        if not line:
            flush()
        elif line.startswith("### "):
            flush(); blocks.append(("h3", line[4:]))
        elif line.startswith("## "):
            flush(); blocks.append(("h2", line[3:]))
        elif line.startswith("- "):
            flush(); blocks.append(("li", line[2:]))
        else:
            para.append(line)
    flush()
    return blocks


def _slugify(value):
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-") or "article"


def _unique_slug(title, article_id=None):
    base = _slugify(title)
    candidate = base
    n = 2
    while True:
        existing = Article.query.filter_by(slug=candidate).first()
        if not existing or existing.id == article_id:
            return candidate
        candidate = base + "-" + str(n)
        n += 1


def _is_admin():
    return bool(session.get("admin"))


def load_orders():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_order(token, data):
    orders = load_orders()
    orders[token] = data
    with open(ORDERS_FILE, "w") as f:
        json.dump(orders, f)


def get_order(token):
    return load_orders().get(token)


def next_invoice_number():
    count = sum(1 for o in load_orders().values() if o.get("paid")) + 1
    return "FAC-" + str(datetime.now().year) + "-" + str(count).zfill(4)


def generate_png(nom_client, nom_evenement, steps, phone, email,
                 web, footer_societe, c_main="#3F8078", c_alt="#75A097"):
    fig = plt.figure(figsize=(16, 8))
    ax  = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 16); ax.set_ylim(0, 8); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 6.5), 16, 1.5, color=c_main))
    ax.text(8, 7.5, "RETROPLANNING DE PRODUCTION",
            ha="center", va="center", fontsize=20, color="#FFFFFF", fontweight="bold")
    ax.text(8, 7.0, nom_evenement + " | " + nom_client,
            ha="center", va="center", fontsize=14, color="#FFFFFF")
    start_date = steps[0]["date"]
    end_date   = steps[-1]["date"]
    total_days = max((end_date - start_date).days, 1)

    def get_x(d):
        return 1 + 14 * ((d - start_date).days / total_days)

    ax.add_patch(FancyBboxPatch((1, 3.8), 14, 0.4,
                 boxstyle="round,pad=0.1", color=c_main, alpha=0.2))
    for i in range(len(steps) - 1):
        x0 = get_x(steps[i]["date"])
        x1 = get_x(steps[i + 1]["date"])
        fc = c_main if i % 2 == 0 else c_alt
        ax.add_patch(plt.Rectangle((x0, 3.8), x1 - x0, 0.4,
                     linewidth=0, facecolor=fc, zorder=3))
    for i, step in enumerate(steps):
        x   = get_x(step["date"])
        top = i % 2 == 0
        y   = 5.2 if top else 2.8
        ax.scatter(x, 4, s=200, color=c_main, zorder=5)
        ax.plot([x, x], [4, y], color=c_main, linestyle="--", alpha=0.5)
        ax.text(x, y + (0.2 if top else -0.2), step["label"],
                ha="center", va="bottom" if top else "top",
                fontsize=10, fontweight="bold", color="#1A1A1A")
        ax.text(x, y + (0.6 if top else -0.6),
                step["date"].strftime("%d/%m/%Y"),
                ha="center", va="center", color="#FFFFFF", fontweight="bold",
                bbox=dict(boxstyle="round,pad=.3", facecolor=c_main, edgecolor="none"))
    parts  = [p for p in [footer_societe, phone, email, web] if p]
    footer = "  |  ".join(parts) if parts else nom_client
    ax.text(8, 0.5, footer, ha="center", va="center",
            fontsize=11, color="#1A1A1A", fontweight="bold")
    filename = "retroplanning_" + nom_client.replace(" ", "_") + "_" + uuid.uuid4().hex[:6] + ".png"
    filepath = os.path.join("/tmp", filename)
    plt.savefig(filepath, dpi=200, bbox_inches="tight")
    plt.close()
    return filepath


def get_steps_from_form(form):
    steps = []
    for i in range(1, 5):
        label    = form.get("label" + str(i), "").strip()
        date_str = form.get("date"  + str(i), "").strip()
        if label and date_str:
            try:
                steps.append({"label": label,
                               "date": datetime.strptime(date_str, "%Y-%m-%d")})
            except ValueError:
                pass
    date_event = form.get("date_event", "").strip()
    if date_event:
        try:
            steps.append({"label": "EVENEMENT",
                           "date": datetime.strptime(date_event, "%Y-%m-%d")})
        except ValueError:
            pass
    return sorted(steps, key=lambda x: x["date"])


def generate_facture(order, client_info, num_facture):
    filepath = os.path.join("/tmp", "facture_" + num_facture + ".pdf")
    doc   = SimpleDocTemplate(filepath, pagesize=A4,
                              rightMargin=2*cm, leftMargin=2*cm,
                              topMargin=2*cm, bottomMargin=2*cm)
    story = []
    green = colors.HexColor("#3F8078")
    sv    = ParagraphStyle("sv", fontSize=10, leading=14)
    nom   = VENDEUR["nom"]
    story += [
        Paragraph("<b>" + nom + "</b>",
                  ParagraphStyle("v", fontSize=14, textColor=green, spaceAfter=4)),
        Paragraph(VENDEUR["adresse"], sv),
        Paragraph(VENDEUR["cp"] + " " + VENDEUR["ville"], sv),
        Paragraph("SIRET : " + VENDEUR["siret"], sv),
        Paragraph("N TVA : " + VENDEUR["tva"], sv),
        Paragraph("Email : " + VENDEUR["email"] + " | Tel : " + VENDEUR["tel"], sv),
        Spacer(1, 0.8*cm),
        Paragraph("<b>FACTURE N " + num_facture + "</b>",
                  ParagraphStyle("t", fontSize=16, textColor=green,
                                 alignment=TA_CENTER, spaceAfter=4)),
        Paragraph("Date : " + datetime.now().strftime("%d/%m/%Y"),
                  ParagraphStyle("d", fontSize=10, alignment=TA_CENTER, spaceAfter=12)),
        Spacer(1, 0.5*cm),
        Paragraph("<b>Facture a :</b>",
                  ParagraphStyle("h", fontSize=11, textColor=green, spaceAfter=4)),
        Paragraph("<b>" + client_info.get("raison_sociale", "") + "</b>", sv),
        Paragraph(client_info.get("adresse", ""), sv),
        Paragraph(client_info.get("cp", "") + " " + client_info.get("ville", ""), sv),
        Spacer(1, 0.8*cm),
    ]
    data = [
        ["Designation", "Qte", "Prix HT", "TVA", "Total TTC"],
        ["Retroplanning de production (PNG HD)", "1",
         str(round(PRIX_HT, 2)) + " EUR",
         "20% (" + str(round(TVA, 2)) + " EUR)",
         str(round(PRIX_TTC, 2)) + " EUR"],
    ]
    t = Table(data, colWidths=[8*cm, 1.5*cm, 2.5*cm, 3*cm, 2.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), green),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [
        t, Spacer(1, 0.5*cm),
        Paragraph("<b>Total HT : " + str(round(PRIX_HT, 2)) + " EUR</b>",
                  ParagraphStyle("r1", fontSize=10, alignment=TA_RIGHT)),
        Paragraph("TVA 20% : " + str(round(TVA, 2)) + " EUR",
                  ParagraphStyle("r2", fontSize=10, alignment=TA_RIGHT)),
        Paragraph("<b>Total TTC : " + str(round(PRIX_TTC, 2)) + " EUR</b>",
                  ParagraphStyle("r3", fontSize=12, textColor=green,
                                 alignment=TA_RIGHT, spaceBefore=4)),
        Spacer(1, 1*cm),
        Paragraph("Reglement effectue par PayPal. Merci pour votre confiance.",
                  ParagraphStyle("f", fontSize=9, textColor=colors.grey,
                                 alignment=TA_CENTER)),
    ]
    doc.build(story)
    return filepath


# ─── ROUTES PUBLIQUES ────────────────────────────────────────────────────────

@app.route("/")
def landing():
    return render_template("landing.html", faqs=HOME_FAQS, contact_email=CONTACT_EMAIL)

@app.route("/formulaire")
def index():
    return render_template("index.html", prix=str(PRIX_TTC), contact_email=CONTACT_EMAIL)

@app.route("/checkout", methods=["POST"])
def checkout():
    token     = uuid.uuid4().hex
    steps_raw = []
    for i in range(1, 5):
        label    = request.form.get("label" + str(i), "").strip()
        date_str = request.form.get("date"  + str(i), "").strip()
        if label and date_str:
            steps_raw.append((label, date_str))
    data = {
        "token":          token,
        "paid":           False,
        "nom_client":     request.form.get("client", ""),
        "nom_evenement":  request.form.get("evenement", ""),
        "phone":          request.form.get("phone", ""),
        "email":          request.form.get("email", ""),
        "web":            request.form.get("web", ""),
        "footer_societe": request.form.get("footer_societe", ""),
        "c_main":         request.form.get("c_main", "#3F8078"),
        "c_alt":          request.form.get("c_alt", "#75A097"),
        "steps_raw":      steps_raw,
        "date_event":     request.form.get("date_event", ""),
    }
    save_order(token, data)
    import urllib.parse
    params = urllib.parse.urlencode({
        "cmd":           "_xclick",
        "business":      PAYPAL_EMAIL,
        "item_name":     "Retroplanning - " + data["nom_evenement"] + " - " + data["nom_client"],
        "amount":        str(PRIX_TTC),
        "currency_code": "EUR",
        "return":        SITE_URL + "/success?token=" + token,
        "cancel_return": SITE_URL + "/cancel",
        "no_shipping":   "1",
        "no_note":       "1",
    })
    return redirect("https://www.paypal.com/cgi-bin/webscr?" + params)

@app.route("/success", methods=["GET", "POST"])
def success():
    token = request.args.get("token", "")
    order = get_order(token)
    if not order:
        return "Commande introuvable.", 404
    if not order.get("paid"):
        order["paid"] = True
        save_order(token, order)
    steps = []
    for label, date_str in order.get("steps_raw", []):
        try:
            steps.append({"label": label,
                           "date": datetime.strptime(date_str, "%Y-%m-%d")})
        except ValueError:
            pass
    if order.get("date_event"):
        try:
            steps.append({"label": "EVENEMENT",
                           "date": datetime.strptime(order["date_event"], "%Y-%m-%d")})
        except ValueError:
            pass
    steps.sort(key=lambda x: x["date"])
    order["png_path"] = generate_png(
        order["nom_client"], order["nom_evenement"], steps,
        order.get("phone", ""), order.get("email", ""),
        order.get("web", ""), order.get("footer_societe", ""),
        order.get("c_main", "#3F8078"), order.get("c_alt", "#75A097")
    )
    save_order(token, order)
    return render_template("success.html", token=token, order=order,
                           contact_email=CONTACT_EMAIL)

@app.route("/download/png/<token>")
def download_png(token):
    order = get_order(token)
    if not order or not order.get("paid"):
        return "Acces non autorise.", 403
    return send_file(order["png_path"], as_attachment=True,
                     download_name="retroplanning_" + order["nom_client"].replace(" ", "_") + ".png")

@app.route("/facture/<token>", methods=["GET", "POST"])
def facture(token):
    order = get_order(token)
    if not order or not order.get("paid"):
        return "Acces non autorise.", 403
    if request.method == "POST":
        info = {k: request.form.get(k, "")
                for k in ["raison_sociale", "adresse", "cp", "ville", "siret", "tva_intra"]}
        num = next_invoice_number()
        return send_file(generate_facture(order, info, num), as_attachment=True,
                         download_name="facture_" + num + ".pdf")
    return render_template("facture.html", token=token, order=order,
                           contact_email=CONTACT_EMAIL)

@app.route("/cancel")
def cancel():
    return render_template("cancel.html", contact_email=CONTACT_EMAIL)


# ─── BLOG PUBLIC ─────────────────────────────────────────────────────────────

@app.route("/blog")
def blog_index():
    articles = Article.query.filter_by(statut="publie").order_by(
        Article.published_at.desc()).all()
    return render_template("blog_index.html", articles=articles, current_category=None)

@app.route("/blog/categorie/<cat_slug>")
def blog_category(cat_slug):
    all_arts = Article.query.filter_by(statut="publie").order_by(
        Article.published_at.desc()).all()
    articles = [a for a in all_arts if a.category_slug == cat_slug]
    if not articles:
        abort(404)
    return render_template("blog_index.html", articles=articles,
                           current_category=articles[0].categorie)

@app.route("/blog/<slug>")
def blog_article(slug):
    article = Article.query.filter_by(slug=slug, statut="publie").first_or_404()
    related = Article.query.filter(
        Article.statut == "publie",
        Article.categorie == article.categorie,
        Article.id != article.id
    ).order_by(Article.published_at.desc()).limit(3).all()
    return render_template("blog_article.html", article=article, related=related)


# ─── ADMINISTRATION ──────────────────────────────────────────────────────────

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
    if not _is_admin():
        return redirect(url_for("admin_login"))
    return render_template("admin_dashboard.html")

@app.route("/admin/generate", methods=["GET", "POST"])
def admin_generate():
    if not _is_admin():
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        steps = get_steps_from_form(request.form)
        if len(steps) < 2:
            return "Il faut au moins 1 etape + la date evenement.", 400
        filepath = generate_png(
            request.form.get("client", "CLIENT"),
            request.form.get("evenement", "EVENEMENT"),
            steps,
            request.form.get("phone", ""),
            request.form.get("email", ""),
            request.form.get("web", ""),
            request.form.get("footer_societe", ""),
            request.form.get("c_main", "#3F8078"),
            request.form.get("c_alt", "#75A097")
        )
        return send_file(filepath, as_attachment=True)
    return render_template("admin_generate.html")

@app.route("/admin/blog")
def admin_blog():
    if not _is_admin():
        return redirect(url_for("admin_login"))
    articles = Article.query.order_by(Article.updated_at.desc()).all()
    return render_template("admin_blog_list.html", articles=articles)

def _fill_article(article):
    article.titre       = request.form.get("titre", "").strip()
    article.slug        = _unique_slug(
        request.form.get("slug", "").strip() or article.titre, article.id)
    article.categorie   = request.form.get("categorie", "").strip() or "Guides"
    article.extrait     = request.form.get("extrait", "").strip()
    article.resume      = request.form.get("resume", "").strip()
    article.contenu     = request.form.get("contenu", "").strip()
    article.points_cles = request.form.get("points_cles", "").strip()
    article.image_url   = request.form.get("image_url", "").strip()
    article.image_alt   = request.form.get("image_alt", "").strip()
    article.meta_title  = request.form.get("meta_title", "").strip() or article.titre
    article.meta_desc   = request.form.get("meta_description", "").strip() or article.extrait
    faqs = []
    for i in range(1, 4):
        q = request.form.get("faq_q" + str(i), "").strip()
        a = request.form.get("faq_a" + str(i), "").strip()
        if q and a:
            faqs.append({"question": q, "answer": a})
    article.faq_json = json.dumps(faqs, ensure_ascii=False)
    article.statut   = "publie" if request.form.get("statut") == "publie" else "brouillon"
    if article.statut == "publie" and not article.published_at:
        article.published_at = datetime.utcnow()
    if article.statut == "brouillon":
        article.published_at = None

@app.route("/admin/blog/nouveau", methods=["GET", "POST"])
def admin_blog_new():
    if not _is_admin():
        return redirect(url_for("admin_login"))
    article = Article()
    if request.method == "POST":
        _fill_article(article)
        if not article.titre or not article.extrait or not article.contenu:
            return render_template("admin_blog_form.html", article=article,
                                   error="Titre, extrait et contenu sont obligatoires.")
        db.session.add(article)
        db.session.commit()
        return redirect(url_for("admin_blog"))
    return render_template("admin_blog_form.html", article=article, error=None)

@app.route("/admin/blog/<int:article_id>/modifier", methods=["GET", "POST"])
def admin_blog_edit(article_id):
    if not _is_admin():
        return redirect(url_for("admin_login"))
    article = Article.query.get_or_404(article_id)
    if request.method == "POST":
        _fill_article(article)
        if not article.titre or not article.extrait or not article.contenu:
            return render_template("admin_blog_form.html", article=article,
                                   error="Titre, extrait et contenu sont obligatoires.")
        db.session.commit()
        return redirect(url_for("admin_blog"))
    return render_template("admin_blog_form.html", article=article, error=None)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/")


# ─── SEO ─────────────────────────────────────────────────────────────────────

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
        "",
        "Sitemap: " + SITE_URL + "/sitemap.xml",
        "",
    ]
    return app.response_class("\n".join(lines), mimetype="text/plain")

@app.route("/sitemap.xml")
def sitemap():
    urls = [
        (SITE_URL + "/",           "weekly",  "1.0"),
        (SITE_URL + "/formulaire", "monthly", "0.8"),
        (SITE_URL + "/blog",       "weekly",  "0.9"),
    ]
    for art in Article.query.filter_by(statut="publie").all():
        urls.append((SITE_URL + "/blog/" + art.slug, "monthly", "0.8"))
    entries = ""
    for loc, freq, priority in urls:
        entries += "<url>"
        entries += "<loc>" + loc + "</loc>"
        entries += "<lastmod>" + datetime.utcnow().date().isoformat() + "</lastmod>"
        entries += "<changefreq>" + freq + "</changefreq>"
        entries += "<priority>" + priority + "</priority>"
        entries += "</url>"
    xml = '<?xml version="1.0" encoding="UTF-8"?>'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    xml += entries + "</urlset>"
    return app.response_class(xml, mimetype="application/xml")


# ─── INIT ─────────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
