# retroplanning.eu — Version 2

## Nouveautés v2
- Prix : 1€ TTC
- Couleurs personnalisables (2 codes hex)
- Choix de 5 symboles (losange, hexagone, cercle, étoile, flèche)
- Filigrane sur la prévisualisation
- Génération automatique de facture PDF
- Compte admin avec accès gratuit (mot de passe : voir app.py)

## Configuration dans app.py
PAYPAL_EMAIL    = "votre_email@paypal.com"
SITE_URL        = "https://www.retroplanning.eu"
ADMIN_PASSWORD  = "omnipub"

## Déploiement
1. Uploader sur GitHub (repo : retroplanning)
2. Render.com → Build: pip install -r requirements.txt
3. Render.com → Start: gunicorn app:app
