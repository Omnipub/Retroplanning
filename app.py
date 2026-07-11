from flask import Flask, render_template, request, send_file, redirect  
import matplotlib  
matplotlib.use('Agg')  
import matplotlib.pyplot as plt  
from matplotlib.patches import FancyBboxPatch, Polygon  
from datetime import datetime  
import os

app = Flask(__name__)

# --- CONFIGURATION ---  
PAYPAL_EMAIL = "commercial@omnipub.net"   
PRIX_TTC = "5.00"  
SITE_URL = "https://www.retroplanning.eu"

@app.route('/')  
def index():  
    return render_template('index.html', prix=PRIX_TTC, paypal_email=PAYPAL_EMAIL)

@app.route('/generate', methods=['POST'])  
def generate():  
    nom_client = request.form.get('client', 'CLIENT')  
    nom_evenement = request.form.get('evenement', 'EVENEMENT')  
      
    # Récupération des 4 étapes  
    steps = []  
    for i in range(1, 5):  
        label = request.form.get(f'label{i}')  
        date_str = request.form.get(f'date{i}')  
        if label and date_str:  
            steps.append({'label': label, 'date': datetime.strptime(date_str, '%Y-%m-%d')})  
      
    date_evenement = datetime.strptime(request.form.get('date_event'), '%Y-%m-%d')  
    steps.append({'label': 'ÉVÉNEMENT', 'date': date_evenement})  
      
    # Tri par date  
    steps.sort(key=lambda x: x['date'])  
      
    # Couleurs Omnipub  
    C_MAIN = "#3F8078"  
    C_ALT = "#75A097"  
    C_DARK = "#1A1A1A"  
    C_WHITE = "#FFFFFF"

    fig = plt.figure(figsize=(16, 8))  
    ax = fig.add_axes([0, 0, 1, 1])  
    ax.set_xlim(0, 16)  
    ax.set_ylim(0, 8)  
    ax.axis('off')

    # Header  
    ax.add_patch(plt.Rectangle((0, 6.5), 16, 1.5, color=C_MAIN))  
    ax.text(8, 7.5, "RETROPLANNING DE PRODUCTION", ha='center', va='center', fontsize=20, color=C_WHITE, fontweight='bold')  
    ax.text(8, 7.0, f"{nom_evenement} | {nom_client}", ha='center', va='center', fontsize=14, color=C_WHITE)

    # Timeline logic  
    start_date = steps[0]['date']  
    end_date = steps[-1]['date']  
    total_days = (end_date - start_date).days if (end_date - start_date).days > 0 else 1  
      
    def get_x(date):  
        return 1 + 14 * ((date - start_date).days / total_days)

    # Dessin de la barre  
    ax.add_patch(FancyBboxPatch((1, 3.8), 14, 0.4, boxstyle="round,pad=0.1", color=C_MAIN, alpha=0.3))

    # Jalons avec correction d'espacement  
    for i, step in enumerate(steps):  
        x = get_x(step['date'])  
        side = "top" if i % 2 == 0 else "bottom"  
          
        # Point sur la ligne  
        ax.scatter(x, 4, s=200, color=C_MAIN, zorder=5)  
          
        # Ligne et texte  
        y_text = 5.2 if side == "top" else 2.8  
        ax.plot([x, x], [4, y_text], color=C_MAIN, linestyle='--', alpha=0.5)  
          
        ax.text(x, y_text + (0.2 if side == "top" else -0.2), step['label'],   
                ha='center', va='bottom' if side == "top" else 'top',   
                fontsize=10, fontweight='bold', color=C_DARK)  
          
        ax.text(x, y_text + (0.6 if side == "top" else -0.6), step['date'].strftime('%d/%m/%Y'),  
                ha='center', va='center', color=C_WHITE, fontweight='bold',  
                bbox=dict(boxstyle="round,pad=0.3", facecolor=C_MAIN, edgecolor='none'))

    # Footer  
    ax.text(8, 0.5, f"{nom_client} | {request.form.get('phone', '')} | {request.form.get('email', '')}",   
            ha='center', va='center', fontsize=12, color=C_DARK, fontweight='bold')

    filename = f"retroplanning_{nom_client}.png"  
    filepath = os.path.join('/tmp', filename)  
    plt.savefig(filepath, dpi=200, bbox_inches='tight')  
    plt.close()  
      
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':  
    app.run(debug=True)  
