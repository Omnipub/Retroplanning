from flask import Flask, render_template, request, send_file, redirect, session, url_for
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
import os, uuid, json

app = Flask(__name__)

# --- CONFIGURATION ---
PAYPAL_EMAIL   = "commercial@omnipub.net"
PRIX_HT        = 1.67
TVA_TAUX       = 0.20
PRIX_TTC       = round(PRIX_HT * (1 + TVA_TAUX), 2)  # 2.00€
SITE_URL       = "https://www.retroplanning.eu"
ADMIN_PASSWORD = "Omnipub&2026"
app.secret_key = "retroplanning_secret_key_2026"

# Infos vendeur
VENDEUR = {
    "nom":     "OMNIPUB",
    "adresse": "Parc Mermoz - 199 rue Hélène Boucher",
    "cp_ville":"34170 Castelnau-le-Lez",
    "siret":   "432 764 785 00023",
    "tva":     "FR01432764785",
    "rcs":     "RCS Montpellier 432 764 785",
    "email":   "commercial@omnipub.net",
    "web":     "www.omnipub.net",
}

# ─────────────────────────────────────────────
# GÉNÉRATION DU PNG
# ─────────────────────────────────────────────
def generate_png(nom_client, nom_evenement, steps, phone, email):
    C_MAIN  = "#3F8078"
    C_DARK  = "#1A1A1A"
    C_WHITE = "#FFFFFF"

    fig = plt.figure(figsize=(16, 8))
    ax  = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 8)
    ax.axis('off')

    ax.add_patch(plt.Rectangle((0, 6.5), 16, 1.5, color=C_MAIN))
    ax.text(8, 7.5, "RETROPLANNING DE PRODUCTION",
            ha='center', va='center', fontsize=20, color=C_WHITE, fontweight='bold')
    ax.text(8, 7.0, f"{nom_evenement} | {nom_client}",
            ha='center', va='center', fontsize=14, color=C_WHITE)

    start_date = steps[0]['date']
    end_date   = steps[-1]['date']
    total_days = max((end_date - start_date).days, 1)

    def get_x(date):
        return 1 + 14 * ((date - start_date).days / total_days)

    ax.add_patch(FancyBboxPatch((1, 3.8), 14, 0.4,
                 boxstyle="round,pad=0.1", color=C_MAIN, alpha=0.3))

    for i, step in enumerate(steps):
        x    = get_x(step['date'])
        side = "top" if i % 2 == 0 else "bottom"
        ax.scatter(x, 4, s=200, color=C_MAIN, zorder=5)
        y_text = 5.2 if side == "top" else 2.8
        ax.plot([x, x], [4, y_text], color=C_MAIN, linestyle='--', alpha=0.5)
        ax.text(x, y_text + (0.2 if side == "top" else -0.2),
                step['label'], ha='center',
                va='bottom' if side == "top" else 'top',
                fontsize=10, fontweight='bold', color=C_DARK)
        ax.text(x, y_text + (0.6 if side == "top" else -0.6),
                step['date'].strftime('%d/%m/%Y'),
                ha='center', va='center', color=C_WHITE, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor=C_MAIN, edgecolor='none'))

    footer = nom_client
    if phone: footer += f" | {phone}"
    if email: footer += f" | {email}"
    ax.text(8, 0.5, footer, ha='center', va='center',
            fontsize=12, color=C_DARK, fontweight='bold')

    filename = f"retroplanning_{nom_client.replace(' ', '_')}.png"
    filepath = os.path.join('/tmp', filename)
    plt.savefig(filepath, dpi=200, bbox_inches='tight')
    plt.close()
    return filepath


# ─────────────────────────────────────────────
# GÉNÉRATION DE LA FACTURE PDF
# ─────────────────────────────────────────────
def generate_facture(num_facture, date_facture, client_info):
    filepath = f"/tmp/facture_{num_facture}.pdf"
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    # Couleur principale
    VERT = colors.HexColor("#3F8078")

    # Style titre
    style_titre = ParagraphStyle('titre', fontSize=22, textColor=VERT,
                                  fontName='Helvetica-Bold', spaceAfter=6)
    style_normal = ParagraphStyle('normal', fontSize=10, fontName='Helvetica',
                                   leading=14)
    style_bold   = ParagraphStyle('bold', fontSize=10, fontName='Helvetica-Bold',
                                   leading=14)
    style_right  = ParagraphStyle('right', fontSize=10, fontName='Helvetica',
                                   alignment=TA_RIGHT)
    style_center = ParagraphStyle('center', fontSize=10, fontName='Helvetica',
                                   alignment=TA_CENTER)

    # En-tête
    header_data = [
        [Paragraph(f"<b>{VENDEUR['nom']}</b>", style_titre),
         Paragraph(f"<b>FACTURE N° {num_facture}</b>", ParagraphStyle('fac',
                   fontSize=16, fontName='Helvetica-Bold',
                   alignment=TA_RIGHT, textColor=VERT))],
        [Paragraph(VENDEUR['adresse'], style_normal),
         Paragraph(f"Date : {date_facture}", style_right)],
        [Paragraph(VENDEUR['cp_ville'], style_normal), ""],
        [Paragraph(f"SIRET : {VENDEUR['siret']}", style_normal), ""],
        [Paragraph(f"TVA : {VENDEUR['tva']}", style_normal), ""],
        [Paragraph(f"{VENDEUR['rcs']}", style_normal), ""],
        [Paragraph(VENDEUR['email'], style_normal), ""],
    ]
    header_table = Table(header_data, colWidths=[9*cm, 8*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5*cm))

    # Ligne séparatrice
    sep = Table([[""]], colWidths=[17*cm], rowHeights=[3])
    sep.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), VERT)]))
    story.append(sep)
    story.append(Spacer(1, 0.5*cm))

    # Bloc client
    story.append(Paragraph("<b>FACTURÉ À :</b>", style_bold))
    story.append(Spacer(1, 0.2*cm))
    client_data = [
        [Paragraph(f"<b>{client_info.get('raison_sociale','')}</b>", style_bold)],
        [Paragraph(client_info.get('adresse',''), style_normal)],
        [Paragraph(f"{client_info.get('cp','')} {client_info.get('ville','')}", style_normal)],
        [Paragraph(f"SIRET : {client_info.get('siret','')}", style_normal)],
        [Paragraph(f"N° TVA : {client_info.get('tva_client','')}", style_normal)],
    ]
    client_table = Table(client_data, colWidths=[17*cm])
    client_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#D1D5DB")),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(client_table)
    story.append(Spacer(1, 0.8*cm))

    # Tableau des prestations
    prix_ht  = PRIX_HT
    tva_mnt  = round(prix_ht * TVA_TAUX, 2)
    prix_ttc = PRIX_TTC

    data = [
        ["Description", "Qté", "Prix HT", "TVA", "Total TTC"],
        ["Génération de rétroplanning de production\n(fichier PNG haute résolution)", "1",
         f"{prix_ht:.2f} €", f"{TVA_TAUX*100:.0f}%", f"{prix_ttc:.2f} €"],
    ]
    t = Table(data, colWidths=[8*cm, 1.5*cm, 2.5*cm, 2*cm, 3*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), VERT),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F0F9F8")]),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#D1D5DB")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # Totaux
    totaux = [
        ["", "Sous-total HT :", f"{prix_ht:.2f} €"],
        ["", f"TVA ({TVA_TAUX*100:.0f}%) :", f"{tva_mnt:.2f} €"],
        ["", "TOTAL TTC :", f"{prix_ttc:.2f} €"],
    ]
    t2 = Table(totaux, colWidths=[9*cm, 5*cm, 3*cm])
    t2.setStyle(TableStyle([
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,2), (-1,2), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BACKGROUND', (0,2), (-1,2), VERT),
        ('TEXTCOLOR', (0,2), (-1,2), colors.white),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (2,0), (2,-1), 8),
    ]))
    story.append(t2)
    story.append(Spacer(1, 1*cm))

    # Mentions légales
    story.append(sep)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "Paiement effectué par PayPal. Pas d'escompte pour paiement anticipé. "
        "En cas de retard de paiement, une pénalité de 3 fois le taux d'intérêt légal sera appliquée, "
        "ainsi qu'une indemnité forfaitaire de 40€ pour frais de recouvrement.",
        ParagraphStyle('mention', fontSize=8, textColor=colors.grey, leading=11)))

    doc.build(story)
    return filepath


def get_steps_from_form(form):
    steps = []
    for i in range(1, 5):
        label    = form.get(f'label{i}')
        date_str = form.get(f'date{i}')
        if label and date_str:
            steps.append({'label': label,
                          'date': datetime.strptime(date_str, '%Y-%m-%d')})
    date_event_str = form.get('date_event')
    if date_event_str:
        steps.append({'label': 'EVENEMENT',
                      'date': datetime.strptime(date_event_str, '%Y-%m-%d')})
    steps.sort(key=lambda x: x['date'])
    return steps


def get_next_facture_num():
    counter_file = '/tmp/facture_counter.txt'
    try:
        with open(counter_file, 'r') as f:
            n = int(f.read().strip()) + 1
    except:
        n = 1
    with open(counter_file, 'w') as f:
        f.write(str(n))
    return f"FAC-2026-{n:04d}"


# ─────────────────────────────────────────────
# ROUTES PUBLIQUES
# ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html', prix=f"{PRIX_TTC:.2f}", paypal_email=PAYPAL_EMAIL)


@app.route('/checkout', methods=['POST'])
def checkout():
    token = str(uuid.uuid4()).replace('-', '')[:20]
    data  = {
        'nom_client':    request.form.get('client', ''),
        'nom_evenement': request.form.get('evenement', ''),
        'phone':         request.form.get('phone', ''),
        'email':         request.form.get('email', ''),
        'steps': [
            {'label': request.form.get(f'label{i}'),
             'date':  request.form.get(f'date{i}')}
            for i in range(1, 5)
            if request.form.get(f'label{i}') and request.form.get(f'date{i}')
        ],
        'date_event': request.form.get('date_event'),
    }
    with open(f'/tmp/order_{token}.json', 'w') as f:
        json.dump(data, f)

    import urllib.parse
    params = urllib.parse.urlencode({
        'cmd':           '_xclick',
        'business':      PAYPAL_EMAIL,
        'item_name':     f"Retroplanning {data['nom_evenement']} - {data['nom_client']}",
        'amount':        f"{PRIX_TTC:.2f}",
        'currency_code': 'EUR',
        'return':        f"{SITE_URL}/success?token={token}",
        'cancel_return': f"{SITE_URL}/cancel",
        'no_shipping':   '1',
        'rm':            '2',
    })
    paypal_url = f"https://www.paypal.com/cgi-bin/webscr?{params}"
    return redirect(paypal_url)


@app.route('/success')
def success():
    token = request.args.get('token', '')
    return render_template('success.html', token=token)


@app.route('/download/<token>')
def download_png(token):
    try:
        with open(f'/tmp/order_{token}.json', 'r') as f:
            data = json.load(f)
        steps = []
        for s in data['steps']:
            steps.append({'label': s['label'],
                          'date':  datetime.strptime(s['date'], '%Y-%m-%d')})
        if data.get('date_event'):
            steps.append({'label': 'EVENEMENT',
                          'date':  datetime.strptime(data['date_event'], '%Y-%m-%d')})
        steps.sort(key=lambda x: x['date'])
        filepath = generate_png(data['nom_client'], data['nom_evenement'],
                                steps, data['phone'], data['email'])
        return send_file(filepath, as_attachment=True,
                         download_name=f"retroplanning_{data['nom_client']}.png")
    except Exception as e:
        return f"Erreur : {str(e)}", 400


@app.route('/facture/<token>', methods=['GET', 'POST'])
def facture(token):
    if request.method == 'POST':
        client_info = {
            'raison_sociale': request.form.get('raison_sociale', ''),
            'adresse':        request.form.get('adresse', ''),
            'cp':             request.form.get('cp', ''),
            'ville':          request.form.get('ville', ''),
            'siret':          request.form.get('siret', ''),
            'tva_client':     request.form.get('tva_client', ''),
        }
        num_facture  = get_next_facture_num()
        date_facture = datetime.now().strftime('%d/%m/%Y')
        filepath     = generate_facture(num_facture, date_facture, client_info)
        return send_file(filepath, as_attachment=True,
                         download_name=f"facture_{num_facture}.pdf")
    return render_template('facture.html', token=token)


@app.route('/cancel')
def cancel():
    return render_template('cancel.html')


# ─────────────────────────────────────────────
# ROUTES ADMIN
# ─────────────────────────────────────────────
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form.get('password', '') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin/generate')
        error = "Mot de passe incorrect."
    return render_template('admin_login.html', error=error)


@app.route('/admin/generate', methods=['GET', 'POST'])
def admin_generate():
    if not session.get('admin'):
        return redirect('/admin')
    if request.method == 'POST':
        nom_client    = request.form.get('client', 'CLIENT')
        nom_evenement = request.form.get('evenement', 'EVENEMENT')
        phone         = request.form.get('phone', '')
        email         = request.form.get('email', '')
        steps         = get_steps_from_form(request.form)
        filepath      = generate_png(nom_client, nom_evenement, steps, phone, email)
        return send_file(filepath, as_attachment=True)
    return render_template('admin_generate.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
