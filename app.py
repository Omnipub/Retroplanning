from flask import Flask, render_template, request, send_file, redirect, session
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

PAYPAL_EMAIL   = "commercial@omnipub.net"
PRIX_TTC       = 2.00
PRIX_HT        = round(PRIX_TTC / 1.20, 2)
TVA            = round(PRIX_TTC - PRIX_HT, 2)
SITE_URL       = "https://www.retroplanning.eu"
ADMIN_PASSWORD = "Omnipub&2026"
app.secret_key = "retroplanning_secret_key_2026"

VENDEUR = {
    "nom":     "OMNIPUB",
    "adresse": "Parc Mermoz - 199 rue Hélène Boucher",
    "cp":      "34170",
    "ville":   "Castelnau-le-Lez",
    "siret":   "432 764 785 00023",
    "tva":     "FR01432764785",
    "email":   "commercial@omnipub.net",
    "tel":     "04 99 13 63 33",
    "web":     "www.omnipub.net",
}

ORDERS_FILE = '/tmp/orders.json'

def load_orders():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_order(token, data):
    orders = load_orders()
    orders[token] = data
    with open(ORDERS_FILE, 'w') as f:
        json.dump(orders, f)

def get_order(token):
    return load_orders().get(token)

def next_invoice_number():
    orders = load_orders()
    year = datetime.now().year
    count = sum(1 for o in orders.values() if o.get('paid')) + 1
    return f"FAC-{year}-{count:04d}"

def generate_png(nom_client, nom_evenement, steps,
                 phone='', email='', footer_societe='', website='',
                 color1='#3F8078', color2='#75A097'):

    C_MAIN  = color1
    C_ALT   = color2
    C_DARK  = "#1A1A1A"
    C_WHITE = "#FFFFFF"

    fig = plt.figure(figsize=(16, 8))
    ax  = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 8)
    ax.axis('off')

    # Header
    ax.add_patch(plt.Rectangle((0, 6.5), 16, 1.5, color=C_MAIN))
    ax.text(8, 7.5, "RETROPLANNING DE PRODUCTION",
            ha='center', va='center', fontsize=20, color=C_WHITE, fontweight='bold')
    ax.text(8, 7.0, f"{nom_evenement} | {nom_client}",
            ha='center', va='center', fontsize=14, color=C_WHITE)

    # Timeline
    start_date = steps[0]['date']
    end_date   = steps[-1]['date']
    total_days = max((end_date - start_date).days, 1)

    def get_x(date):
        return 1 + 14 * ((date - start_date).days / total_days)

    # Barre de fond
    ax.add_patch(FancyBboxPatch((1, 3.75), 14, 0.5,
                 boxstyle="round,pad=0.1", color=C_MAIN, alpha=0.2))

    # Segments colorés alternés
    for i in range(len(steps) - 1):
        x0 = get_x(steps[i]['date'])
        x1 = get_x(steps[i+1]['date'])
        col = C_MAIN if i % 2 == 0 else C_ALT
        ax.add_patch(plt.Rectangle((x0, 3.75), x1 - x0, 0.5, color=col, zorder=2))

    # Jalons
    for i, step in enumerate(steps):
        x    = get_x(step['date'])
        side = "top" if i % 2 == 0 else "bottom"
        ax.scatter(x, 4.0, s=250, color=C_WHITE, edgecolors=C_MAIN, linewidths=2.5, zorder=5)
        ax.scatter(x, 4.0, s=100, color=C_MAIN, zorder=6)
        y_text = 5.4 if side == "top" else 2.6
        ax.plot([x, x], [4.25 if side=="top" else 3.75, y_text],
                color=C_MAIN, linestyle='--', alpha=0.5, linewidth=1.2)
        ax.text(x, y_text + (0.15 if side == "top" else -0.15),
                step['label'], ha='center',
                va='bottom' if side == "top" else 'top',
                fontsize=9, fontweight='bold', color=C_DARK)
        ax.text(x, y_text + (0.55 if side == "top" else -0.55),
                step['date'].strftime('%d/%m/%Y'),
                ha='center', va='center', color=C_WHITE, fontweight='bold', fontsize=10,
                bbox=dict(boxstyle="round,pad=0.3", facecolor=C_MAIN, edgecolor='none'))

    # Footer dynamique
    parts = [p for p in [footer_societe, phone, email, website] if p.strip()]
    footer = "  |  ".join(parts) if parts else nom_client
    ax.plot([0.5, 15.5], [0.8, 0.8], color='#CCCCCC', linewidth=0.8)
    ax.text(8, 0.45, footer, ha='center', va='center',
            fontsize=11, color=C_DARK, fontweight='bold')

    filename = f"retroplanning_{nom_client.replace(' ', '_')}_{uuid.uuid4().hex[:6]}.png"
    filepath = os.path.join('/tmp', filename)
    plt.savefig(filepath, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    return filepath


def generate_facture(order, client_info, num_facture):
    filename = f"facture_{num_facture}.pdf"
    filepath = os.path.join('/tmp', filename)
    doc  = SimpleDocTemplate(filepath, pagesize=A4,
                             rightMargin=2*cm, leftMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    story = []
    green = colors.HexColor('#3F8078')
    sv = ParagraphStyle('sv', fontSize=10, leading=14)

    story.append(Paragraph(f"<b>{VENDEUR['nom']}</b>", ParagraphStyle('v', fontSize=14, textColor=green, spaceAfter=4)))
    story.append(Paragraph(VENDEUR['adresse'], sv))
    story.append(Paragraph(f"{VENDEUR['cp']} {VENDEUR['ville']}", sv))
    story.append(Paragraph(f"SIRET : {VENDEUR['siret']}", sv))
    story.append(Paragraph(f"N° TVA : {VENDEUR['tva']}", sv))
    story.append(Paragraph(f"Email : {VENDEUR['email']} | Tél : {VENDEUR['tel']}", sv))
    story.append(Spacer(1, 0.8*cm))

    story.append(Paragraph(f"<b>FACTURE N° {num_facture}</b>",
                            ParagraphStyle('t', fontSize=16, textColor=green, alignment=TA_CENTER, spaceAfter=4)))
    story.append(Paragraph(f"Date : {datetime.now().strftime('%d/%m/%Y')}",
                            ParagraphStyle('d', fontSize=10, alignment=TA_CENTER, spaceAfter=12)))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("<b>Facturé à :</b>", ParagraphStyle('h', fontSize=11, textColor=green, spaceAfter=4)))
    story.append(Paragraph(f"<b>{client_info.get('raison_sociale','')}</b>", sv))
    story.append(Paragraph(client_info.get('adresse',''), sv))
    story.append(Paragraph(f"{client_info.get('cp','')} {client_info.get('ville','')}", sv))
    if client_info.get('siret'): story.append(Paragraph(f"SIRET : {client_info['siret']}", sv))
    if client_info.get('tva_intra'): story.append(Paragraph(f"N° TVA : {client_info['tva_intra']}", sv))
    story.append(Spacer(1, 0.8*cm))

    data = [
        ['Désignation', 'Qté', 'Prix HT', 'TVA', 'Total TTC'],
        ['Rétroplanning de production (PNG HD)', '1',
         f"{PRIX_HT:.2f} €", f"20% ({TVA:.2f} €)", f"{PRIX_TTC:.2f} €"],
    ]
    table = Table(data, colWidths=[8*cm, 1.5*cm, 2.5*cm, 3*cm, 2.5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),green), ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'), ('FONTSIZE',(0,0),(-1,-1),9),
        ('ALIGN',(1,0),(-1,-1),'CENTER'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F0F7F6')]),
        ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#CCCCCC')),
        ('TOPPADDING',(0,0),(-1,-1),6), ('BOTTOMPADDING',(0,0),(-1,-1),6),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"<b>Total HT : {PRIX_HT:.2f} €</b>", ParagraphStyle('t1', fontSize=10, alignment=TA_RIGHT)))
    story.append(Paragraph(f"TVA 20% : {TVA:.2f} €", ParagraphStyle('t2', fontSize=10, alignment=TA_RIGHT)))
    story.append(Paragraph(f"<b>Total TTC : {PRIX_TTC:.2f} €</b>",
                            ParagraphStyle('t3', fontSize=12, textColor=green, alignment=TA_RIGHT, spaceBefore=4)))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Règlement effectué par PayPal. Merci pour votre confiance.",
                            ParagraphStyle('f', fontSize=9, textColor=colors.grey, alignment=TA_CENTER)))
    doc.build(story)
    return filepath


def get_steps_from_form(form):
    steps = []
    for i in range(1, 5):
        label    = form.get(f'label{i}')
        date_str = form.get(f'date{i}')
        if label and date_str:
            steps.append({'label': label, 'date': datetime.strptime(date_str, '%Y-%m-%d')})
    date_event_str = form.get('date_event')
    if date_event_str:
        steps.append({'label': 'EVENEMENT', 'date': datetime.strptime(date_event_str, '%Y-%m-%d')})
    steps.sort(key=lambda x: x['date'])
    return steps


@app.route('/')
def index():
    return render_template('index.html', prix=f"{PRIX_TTC:.2f}", paypal_email=PAYPAL_EMAIL)


@app.route('/checkout', methods=['POST'])
def checkout():
    token = uuid.uuid4().hex
    order_data = {
        'token':          token,
        'paid':           False,
        'nom_client':     request.form.get('client', ''),
        'nom_evenement':  request.form.get('evenement', ''),
        'phone':          request.form.get('phone', ''),
        'email':          request.form.get('email', ''),
        'footer_societe': request.form.get('footer_societe', ''),
        'website':        request.form.get('website', ''),
        'color1':         request.form.get('color1', '#3F8078'),
        'color2':         request.form.get('color2', '#75A097'),
        'steps_raw':      [(request.form.get(f'label{i}'), request.form.get(f'date{i}')) for i in range(1, 5)],
        'date_event':     request.form.get('date_event', ''),
    }
    save_order(token, order_data)

    import urllib.parse
    params = urllib.parse.urlencode({
        'cmd':           '_xclick',
        'business':      PAYPAL_EMAIL,
        'item_name':     f"Rétroplanning - {order_data['nom_evenement']} - {order_data['nom_client']}",
        'amount':        f"{PRIX_TTC:.2f}",
        'currency_code': 'EUR',
        'return':        f"{SITE_URL}/success?token={token}",
        'cancel_return': f"{SITE_URL}/cancel",
        'no_shipping':   '1',
        'no_note':       '1',
    })
    return redirect(f"https://www.paypal.com/cgi-bin/webscr?{params}")


@app.route('/success', methods=['GET', 'POST'])
def success():
    token = request.args.get('token', '')
    order = get_order(token)
    if not order:
        return "Commande introuvable.", 404
    if not order.get('paid'):
        order['paid'] = True
        save_order(token, order)

    steps = []
    for label, date_str in order.get('steps_raw', []):
        if label and date_str:
            steps.append({'label': label, 'date': datetime.strptime(date_str, '%Y-%m-%d')})
    if order.get('date_event'):
        steps.append({'label': 'EVENEMENT', 'date': datetime.strptime(order['date_event'], '%Y-%m-%d')})
    steps.sort(key=lambda x: x['date'])

    png_path = generate_png(
        order['nom_client'], order['nom_evenement'], steps,
        order.get('phone',''), order.get('email',''),
        order.get('footer_societe',''), order.get('website',''),
        order.get('color1','#3F8078'), order.get('color2','#75A097')
    )
    order['png_path'] = png_path
    save_order(token, order)
    return render_template('success.html', token=token, order=order)


@app.route('/download/png/<token>')
def download_png(token):
    order = get_order(token)
    if not order or not order.get('paid'):
        return "Accès non autorisé.", 403
    return send_file(order['png_path'], as_attachment=True,
                     download_name=f"retroplanning_{order['nom_client'].replace(' ','_')}.png")


@app.route('/facture/<token>', methods=['GET', 'POST'])
def facture(token):
    order = get_order(token)
    if not order or not order.get('paid'):
        return "Accès non autorisé.", 403
    if request.method == 'POST':
        client_info = {
            'raison_sociale': request.form.get('raison_sociale',''),
            'adresse':        request.form.get('adresse',''),
            'cp':             request.form.get('cp',''),
            'ville':          request.form.get('ville',''),
            'siret':          request.form.get('siret',''),
            'tva_intra':      request.form.get('tva_intra',''),
        }
        num = next_invoice_number()
        pdf_path = generate_facture(order, client_info, num)
        return send_file(pdf_path, as_attachment=True, download_name=f"facture_{num}.pdf")
    return render_template('facture.html', token=token, order=order)


@app.route('/cancel')
def cancel():
    return render_template('cancel.html')


@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form.get('password','') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin/generate')
        error = "Mot de passe incorrect."
    return render_template('admin_login.html', error=error)


@app.route('/admin/generate', methods=['GET', 'POST'])
def admin_generate():
    if not session.get('admin'):
        return redirect('/admin')
    if request.method == 'POST':
        steps = get_steps_from_form(request.form)
        filepath = generate_png(
            request.form.get('client','CLIENT'),
            request.form.get('evenement','EVENEMENT'),
            steps,
            request.form.get('phone',''),
            request.form.get('email',''),
            request.form.get('footer_societe',''),
            request.form.get('website',''),
            request.form.get('color1','#3F8078'),
            request.form.get('color2','#75A097'),
        )
        return send_file(filepath, as_attachment=True)
    return render_template('admin_generate.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
