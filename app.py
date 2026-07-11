from flask import Flask, render_template, request, send_file, redirect, session  
import matplotlib  
matplotlib.use('Agg')  
import matplotlib.pyplot as plt  
from matplotlib.patches import FancyBboxPatch, Polygon  
from datetime import datetime  
import os

app = Flask(__name__)

# --- CONFIGURATION ---  
PAYPAL_EMAIL    = "commercial@omnipub.net"  
PRIX_TTC        = "5.00"  
SITE_URL        = "https://www.retroplanning.eu"  
ADMIN_PASSWORD  = "omnipub2026"   # ← Changez ce mot de passe !  
app.secret_key  = "retroplanning_secret_key_2026"

# ─────────────────────────────────────────────
# GÉNÉRATION DU PNG
# ─────────────────────────────────────────────  
def generate_png(nom_client, nom_evenement, steps, phone, email):  
    C_MAIN  = "#3F8078"  
    C_ALT   = "#75A097"  
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
    start_date  = steps[0]['date']  
    end_date    = steps[-1]['date']  
    total_days  = max((end_date - start_date).days, 1)

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

    # Footer  
    footer = f"{nom_client}"  
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
# ROUTES PUBLIQUES
# ─────────────────────────────────────────────  
@app.route('/')  
def index():  
    return render_template('index.html', prix=PRIX_TTC, paypal_email=PAYPAL_EMAIL)

@app.route('/generate', methods=['POST'])  
def generate():  
    nom_client    = request.form.get('client', 'CLIENT')  
    nom_evenement = request.form.get('evenement', 'EVENEMENT')  
    phone         = request.form.get('phone', '')  
    email         = request.form.get('email', '')

    steps = []  
    for i in range(1, 5):  
        label    = request.form.get(f'label{i}')  
        date_str = request.form.get(f'date{i}')  
        if label and date_str:  
            steps.append({'label': label,  
                          'date': datetime.strptime(date_str, '%Y-%m-%d')})

    date_event_str = request.form.get('date_event')  
    if date_event_str:  
        steps.append({'label': 'ÉVÉNEMENT',  
                      'date': datetime.strptime(date_event_str, '%Y-%m-%d')})

    steps.sort(key=lambda x: x['date'])  
    filepath = generate_png(nom_client, nom_evenement, steps, phone, email)  
    return send_file(filepath, as_attachment=True)

# ─────────────────────────────────────────────
# ROUTES ADMIN
# ─────────────────────────────────────────────  
@app.route('/admin', methods=['GET', 'POST'])  
def admin_login():  
    error = None  
    if request.method == 'POST':  
        if request.form.get('password') == ADMIN_PASSWORD:  
            session['admin'] = True  
            return redirect('/admin/generate')  
        else:  
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

        steps = []  
        for i in range(1, 5):  
            label    = request.form.get(f'label{i}')  
            date_str = request.form.get(f'date{i}')  
            if label and date_str:  
                steps.append({'label': label,  
                              'date': datetime.strptime(date_str, '%Y-%m-%d')})

        date_event_str = request.form.get('date_event')  
        if date_event_str:  
            steps.append({'label': 'ÉVÉNEMENT',  
                          'date': datetime.strptime(date_event_str, '%Y-%m-%d')})

        steps.sort(key=lambda x: x['date'])  
        filepath = generate_png(nom_client, nom_evenement, steps, phone, email)  
        return send_file(filepath, as_attachment=True)

    return render_template('admin_generate.html')

@app.route('/admin/logout')  
def admin_logout():  
    session.pop('admin', None)  
    return redirect('/')

if __name__ == '__main__':  
    app.run(debug=True)  
