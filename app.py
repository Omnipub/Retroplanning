from flask import Flask, render_template, request, send_file, redirect, url_for, session, jsonify
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, RegularPolygon
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
import numpy as np
from datetime import datetime
import io, os, urllib.parse, uuid
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'retroplanning-secret-2026')

# ============================================================
# CONFIGURATION
# ============================================================
PAYPAL_EMAIL    = "votre_email@paypal.com"
SITE_URL        = "https://www.retroplanning.eu"
PRIX_TTC        = "1.00"
PRIX_HT         = "0.83"
TVA             = "0.17"
EMAIL_RECEPTION = "commercial@omnipub.net"
ADMIN_PASSWORD  = "omnipub"

# Email SMTP (optionnel — à configurer pour envoi auto)
SMTP_HOST       = "smtp.gmail.com"
SMTP_PORT       = 587
SMTP_USER       = ""
SMTP_PASS       = ""
# ============================================================

SYMBOLES = {
    'losange':    'diamond',
    'hexagone':   'hexagon',
    'cercle':     'circle',
    'etoile':     'star',
    'fleche':     'arrow',
}

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4))

def draw_symbol(ax, symbole, x, y, color, size=0.06):
    """Dessine le symbole choisi centré en (x,y) dans les coordonnées axes."""
    if symbole == 'cercle':
        circle = plt.Circle((x, y), size*0.8, color=color, transform=ax.transAxes, zorder=5)
        ax.add_patch(circle)
    elif symbole == 'etoile':
        star = RegularPolygon((x, y), numVertices=5, radius=size,
                               orientation=np.pi/2, color=color,
                               transform=ax.transAxes, zorder=5)
        # Étoile via path
        theta = np.linspace(0, 2*np.pi, 11)
        r = np.array([size if i%2==0 else size*0.4 for i in range(11)])
        xs = x + r * np.sin(theta)
        ys = y + r * np.cos(theta)
        ax.fill(xs, ys, color=color, transform=ax.transAxes, zorder=5)
    elif symbole == 'hexagone':
        hex_patch = RegularPolygon((x, y), numVertices=6, radius=size,
                                    orientation=0, color=color,
                                    transform=ax.transAxes, zorder=5)
        ax.add_patch(hex_patch)
    elif symbole == 'fleche':
        ax.annotate('', xy=(x+size, y), xytext=(x-size, y),
                    xycoords='axes fraction', textcoords='axes fraction',
                    arrowprops=dict(arrowstyle='->', color=color, lw=3), zorder=5)
    else:  # losange (défaut)
        diamond = plt.Polygon([[x, y+size], [x+size*0.7, y],
                                [x, y-size], [x-size*0.7, y]],
                               color=color, transform=ax.transAxes, zorder=5)
        ax.add_patch(diamond)


def generate_retroplanning(data, watermark=True):
    from matplotlib.patches import FancyBboxPatch, Polygon
    from datetime import datetime, timedelta

    MOIS_FR = {
        'Jan':'Jan','Feb':'Fev','Mar':'Mar','Apr':'Avr',
        'May':'Mai','Jun':'Juin','Jul':'Juil','Aug':'Aout',
        'Sep':'Sep','Oct':'Oct','Nov':'Nov','Dec':'Dec'
    }
    def format_date_fr(d):
        s = d.strftime('%d %b %Y')
        for en, fr in MOIS_FR.items():
            s = s.replace(en, fr)
        return s

    def parse_date(s):
        if not s:
            return None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
            try:
                return datetime.strptime(s, fmt)
            except:
                pass
        return None

    nom_client    = data.get('societe', 'Client')
    nom_evenement = data.get('evenement', 'Evenement')
    couleur1      = data.get('couleur1', '#3F8078').strip()
    couleur2      = data.get('couleur2', '#75A097').strip()
    if not couleur1.startswith('#'): couleur1 = '#' + couleur1
    if not couleur2.startswith('#'): couleur2 = '#' + couleur2
    symbole       = data.get('symbole', 'losange')

    C_MAIN  = couleur1
    C_ALT   = couleur2
    C_WHITE = "#FFFFFF"
    C_DARK  = "#1A1A1A"

    d1 = parse_date(data.get('etape1_date', ''))
    d2 = parse_date(data.get('etape2_date', ''))
    d3 = parse_date(data.get('etape3_date', ''))
    d4 = parse_date(data.get('etape4_date', ''))
    d5 = parse_date(data.get('etape5_date', ''))

    label1 = data.get('etape1_label', 'Etape 1').upper()
    label2 = data.get('etape2_label', 'Etape 2').upper()
    label3 = data.get('etape3_label', 'Etape 3').upper()
    label4 = data.get('etape4_label', 'Etape 4').upper()
    label5 = data.get('etape5_label', 'Etape 5').upper()

    if not d1: d1 = datetime(2026, 1, 1)
    if not d5: d5 = d1 + timedelta(days=60)
    if not d2: d2 = d1 + timedelta(days=15)
    if not d3: d3 = d1 + timedelta(days=30)
    if not d4: d4 = d1 + timedelta(days=45)

    total_days = max((d5 - d1).days, 1)
    def date_to_x(d): return (d - d1).days / total_days

    FIG_W, FIG_H = 16.0, 6.8
    fig = plt.figure(figsize=(FIG_W, FIG_H))
    fig.patch.set_facecolor('none')
    fig.patch.set_alpha(0)

    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_facecolor('none')
    ax.set_xlim(0, FIG_W)
    ax.set_ylim(0, FIG_H)
    ax.set_aspect('equal')
    ax.axis('off')

    def rx(r): return r * FIG_W
    def ry(r): return r * FIG_H
    def x_pos(d): return rx(0.03 + 0.94 * date_to_x(d))

    Y_HEADER_BOT = ry(0.76)
    Y_HEADER_TOP = ry(1.00)
    Y_TRACK_CY   = ry(0.44)
    TRACK_H      = ry(0.13)
    TRACK_X0     = rx(0.03)
    TRACK_X1     = rx(0.97)

    # HEADER
    ax.add_patch(FancyBboxPatch((rx(0.0), Y_HEADER_BOT), rx(1.0),
        Y_HEADER_TOP - Y_HEADER_BOT,
        boxstyle="square,pad=0", linewidth=0, facecolor=C_MAIN, zorder=1))
    ax.add_patch(FancyBboxPatch((rx(0.0), Y_HEADER_BOT), rx(0.006),
        Y_HEADER_TOP - Y_HEADER_BOT,
        boxstyle="square,pad=0", linewidth=0, facecolor="#2A5550", zorder=2))
    ax.plot([rx(0.0), rx(1.0)], [Y_HEADER_BOT]*2, color="#2A5550", linewidth=2, zorder=3)
    ax.text(rx(0.5), ry(0.955), "RETROPLANNING DE PRODUCTION",
        ha='center', va='center', fontsize=18, fontweight='bold', color=C_WHITE, zorder=4)
    ax.text(rx(0.5), ry(0.885),
        "Ce retroplanning est fourni a titre indicatif. Les dates ne sont pas contractuelles.",
        ha='center', va='center', fontsize=11, style='italic', color=C_WHITE, zorder=4)
    ax.text(rx(0.5), ry(0.815), f"{nom_evenement}   |   {nom_client}",
        ha='center', va='center', fontsize=12, fontweight='bold', color=C_WHITE, zorder=4)

    # TIMELINE
    segments = [
        (d1, d2, C_MAIN), (d2, d3, C_ALT),
        (d3, d4, C_MAIN), (d4, d5, C_ALT),
    ]
    ax.add_patch(FancyBboxPatch(
        (TRACK_X0, Y_TRACK_CY - TRACK_H/2), TRACK_X1 - TRACK_X0, TRACK_H,
        boxstyle="round,pad=0", linewidth=0, facecolor=C_MAIN, zorder=2))
    for ds, de, col in segments:
        x0 = x_pos(ds); x1 = x_pos(de)
        ax.add_patch(plt.Rectangle(
            (x0, Y_TRACK_CY - TRACK_H/2), x1 - x0, TRACK_H,
            linewidth=0, facecolor=col, zorder=3))
    ax.add_patch(FancyBboxPatch(
        (TRACK_X0, Y_TRACK_CY - TRACK_H/2), TRACK_X1 - TRACK_X0, TRACK_H,
        boxstyle="round,pad=0", linewidth=1.5, edgecolor=C_WHITE,
        facecolor="none", zorder=5))

    # JALONS
    DW = ry(0.072); DH = ry(0.042)
    milestones = [
        (d1, label1, "bottom"), (d2, label2, "top"),
        (d3, label3, "bottom"), (d4, label4, "top"),
        (d5, label5, "bottom"),
    ]
    GAP_LINE  = ry(0.008); LINE_LEN  = ry(0.065)
    GAP_LABEL = ry(0.012); GAP_DATE  = ry(0.010)

    for date, label, side in milestones:
        x = x_pos(date); cy = Y_TRACK_CY

        if symbole == 'cercle':
            ax.add_patch(plt.Circle((x, cy), DW*0.9, color=C_WHITE, ec=C_MAIN, linewidth=2.5, zorder=6))
            ax.add_patch(plt.Circle((x, cy), DW*0.5, color=C_MAIN, zorder=7))
        elif symbole == 'hexagone':
            from matplotlib.patches import RegularPolygon
            ax.add_patch(RegularPolygon((x, cy), numVertices=6, radius=DW*0.9,
                facecolor=C_WHITE, edgecolor=C_MAIN, linewidth=2.5, zorder=6))
            ax.add_patch(RegularPolygon((x, cy), numVertices=6, radius=DW*0.5,
                facecolor=C_MAIN, edgecolor="none", zorder=7))
        elif symbole == 'etoile':
            import numpy as np
            theta = np.linspace(0, 2*np.pi, 11)
            r_o = np.array([DW*0.9 if i%2==0 else DW*0.4 for i in range(11)])
            r_i = np.array([DW*0.5 if i%2==0 else DW*0.22 for i in range(11)])
            ax.fill(x + r_o*np.sin(theta), cy + r_o*np.cos(theta), color=C_WHITE, zorder=6)
            ax.fill(x + r_i*np.sin(theta), cy + r_i*np.cos(theta), color=C_MAIN, zorder=7)
        elif symbole == 'fleche':
            ax.annotate('', xy=(x+DW, cy), xytext=(x-DW, cy),
                arrowprops=dict(arrowstyle='->', color=C_WHITE, lw=3), zorder=6)
        else:  # losange
            ax.add_patch(Polygon(
                [[x-DW, cy], [x, cy+DH], [x+DW, cy], [x, cy-DH]],
                closed=True, facecolor=C_WHITE, edgecolor=C_MAIN, linewidth=2.5, zorder=6))
            ax.add_patch(Polygon(
                [[x-DW*0.55, cy], [x, cy+DH*0.55], [x+DW*0.55, cy], [x, cy-DH*0.55]],
                closed=True, facecolor=C_MAIN, edgecolor="none", zorder=7))

        if side == "top":
            y0 = cy+DH+GAP_LINE; y1 = y0+LINE_LEN
            yl = y1+GAP_LABEL;   yd = yl+ry(0.075)+GAP_DATE
            vl = 'bottom';       vd = 'bottom'
        else:
            y0 = cy-DH-GAP_LINE; y1 = y0-LINE_LEN
            yl = y1-GAP_LABEL;   yd = yl-ry(0.075)-GAP_DATE
            vl = 'top';          vd = 'top'

        ax.plot([x, x], [y0, y1], color=C_MAIN, linewidth=1.6, linestyle='--', zorder=5, alpha=0.55)
        ax.text(x, yl, label, ha='center', va=vl, fontsize=9, fontweight='bold',
            color=C_DARK, multialignment='center', zorder=8)
        ax.text(x, yd, format_date_fr(date), ha='center', va=vd,
            fontsize=11, color=C_WHITE, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.35", facecolor=C_MAIN, edgecolor="none"),
            zorder=8)

    # FILIGRANE
    if watermark:
        for wx in [0.25, 0.5, 0.75]:
            ax.text(rx(wx), ry(0.44), 'APERCU\nretroplanning.eu',
                fontsize=18, color='#333333', alpha=0.12,
                ha='center', va='center', rotation=25, fontweight='bold', zorder=10)

    # FOOTER
    parts = [p for p in [nom_client, data.get('contact',''),
                          data.get('telephone',''), data.get('email_client','')] if p]
    ax.plot([rx(0.0), rx(1.0)], [ry(0.09), ry(0.09)], color="#C0B8A8", linewidth=1, zorder=1)
    ax.text(rx(0.5), ry(0.055), '   |   '.join(parts),
        ha='center', va='center', fontsize=11, color=C_DARK, fontweight='bold')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=200,
                transparent=True, facecolor='none', bbox_inches=None, pad_inches=0)
    buf.seek(0)
    plt.close(fig)
    return buf


def generate_facture_pdf(data, num_facture):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # En-tête
    title_style = ParagraphStyle('title', fontSize=22, fontName='Helvetica-Bold',
                                  textColor=colors.HexColor('#1a1a2e'), spaceAfter=6)
    story.append(Paragraph("FACTURE", title_style))
    story.append(Spacer(1, 0.3*cm))

    # Infos facture
    info_style = ParagraphStyle('info', fontSize=10, fontName='Helvetica',
                                 textColor=colors.grey)
    now = datetime.now().strftime('%d/%m/%Y')
    story.append(Paragraph(f"N° {num_facture}  —  Date : {now}", info_style))
    story.append(Spacer(1, 0.8*cm))

    # Vendeur / Acheteur
    two_col = [
        [Paragraph("<b>VENDEUR</b><br/>retroplanning.eu<br/>commercial@omnipub.net", styles['Normal']),
         Paragraph(f"<b>CLIENT</b><br/>{data.get('societe','')}<br/>{data.get('contact','')}<br/>{data.get('email_client','')}<br/>{data.get('telephone','')}", styles['Normal'])]
    ]
    t = Table(two_col, colWidths=[8.5*cm, 8.5*cm])
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.8*cm))

    # Tableau produit
    data_table = [
        ['Description', 'Qté', 'Prix HT', 'TVA (20%)', 'Total TTC'],
        [f"Rétroplanning — {data.get('evenement','')}", '1', f"{PRIX_HT} €", f"{TVA} €", f"{PRIX_TTC} €"],
    ]
    prod_table = Table(data_table, colWidths=[8*cm, 1.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
    prod_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(prod_table)
    story.append(Spacer(1, 0.5*cm))

    # Total
    total_style = ParagraphStyle('total', fontSize=12, fontName='Helvetica-Bold',
                                  alignment=TA_RIGHT,
                                  textColor=colors.HexColor('#1a1a2e'))
    story.append(Paragraph(f"TOTAL TTC : {PRIX_TTC} €", total_style))
    story.append(Spacer(1, 1.5*cm))

    # Pied de page
    footer_style = ParagraphStyle('footer', fontSize=8, fontName='Helvetica',
                                   textColor=colors.grey, alignment=TA_CENTER)
    story.append(Paragraph("retroplanning.eu — commercial@omnipub.net", footer_style))
    story.append(Paragraph("TVA non applicable selon article 293 B du CGI si micro-entreprise — ou TVA 20% selon régime fiscal", footer_style))

    doc.build(story)
    buf.seek(0)
    return buf


# ============================================================
# ROUTES
# ============================================================

@app.route('/', methods=['GET'])
def index():
    admin = session.get('admin', False)
    return render_template('index.html', prix=PRIX_TTC, admin=admin)


@app.route('/admin-login', methods=['POST'])
def admin_login():
    pwd = request.form.get('password', '')
    if pwd == ADMIN_PASSWORD:
        session['admin'] = True
    return redirect('/')


@app.route('/admin-logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/')


@app.route('/preview', methods=['POST'])
def preview():
    data = request.form.to_dict()
    buf = generate_retroplanning(data, watermark=True)
    return send_file(buf, mimetype='image/png')


@app.route('/download-free', methods=['POST'])
def download_free():
    """Téléchargement gratuit pour l'admin."""
    if not session.get('admin'):
        return redirect('/')
    data = request.form.to_dict()
    buf = generate_retroplanning(data, watermark=False)
    return send_file(buf, mimetype='image/png',
                     as_attachment=True,
                     download_name='retroplanning.png')


@app.route('/pay', methods=['POST'])
def pay():
    data = request.form.to_dict()
    # Stocker les données en session pour récupération après paiement
    session['rp_data'] = data
    params = urllib.parse.urlencode(data)
    return_url  = f"{SITE_URL}/success?{params}"
    cancel_url  = f"{SITE_URL}/cancel"

    paypal_url = (
        "https://www.paypal.com/cgi-bin/webscr"
        f"?cmd=_xclick"
        f"&business={urllib.parse.quote(PAYPAL_EMAIL)}"
        f"&item_name={urllib.parse.quote('Rétroplanning - ' + data.get('evenement',''))}"
        f"&amount={PRIX_TTC}"
        f"&currency_code=EUR"
        f"&return={urllib.parse.quote(return_url)}"
        f"&cancel_return={urllib.parse.quote(cancel_url)}"
        f"&no_shipping=1"
        f"&lc=FR"
    )
    return redirect(paypal_url)


@app.route('/success', methods=['GET'])
def success():
    data = request.args.to_dict()
    if not data:
        data = session.get('rp_data', {})

    num_facture = f"RP-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

    # Générer le PNG (sans filigrane)
    png_buf = generate_retroplanning(data, watermark=False)
    png_bytes = png_buf.read()

    # Générer la facture PDF
    pdf_buf = generate_facture_pdf(data, num_facture)
    pdf_bytes = pdf_buf.read()

    # Stocker temporairement en session (base64)
    import base64
    session['png_b64'] = base64.b64encode(png_bytes).decode()
    session['pdf_b64'] = base64.b64encode(pdf_bytes).decode()
    session['num_facture'] = num_facture

    return render_template('success.html', num_facture=num_facture,
                            evenement=data.get('evenement',''))


@app.route('/download/png')
def download_png():
    import base64
    b64 = session.get('png_b64')
    if not b64:
        return redirect('/')
    buf = io.BytesIO(base64.b64decode(b64))
    return send_file(buf, mimetype='image/png',
                     as_attachment=True,
                     download_name='retroplanning.png')


@app.route('/download/pdf')
def download_pdf():
    import base64
    b64 = session.get('pdf_b64')
    if not b64:
        return redirect('/')
    buf = io.BytesIO(base64.b64decode(b64))
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True,
                     download_name='facture_retroplanning.pdf')


@app.route('/cancel')
def cancel():
    return render_template('cancel.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
