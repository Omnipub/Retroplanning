# Actions SEO/Perf à faire côté infra (hors code applicatif)

Ce fichier liste les correctifs identifiés lors de l'audit SEO/GEO/Perf (Limova.ai,
août 2026) qui ne se règlent pas dans ce dépôt — ce sont des réglages Cloudflare / DNS
OVH. À traiter par la personne ayant accès aux dashboards.

## 1. Chaîne de redirections sur le domaine apex

**Constat :** Google PageSpeed Insights (Mobile) chiffre à 1.11s la perte due à des
"redirections multiples de pages". Le robots.txt de l'audit a été récupéré sur
`http://retroplanning.eu/robots.txt` alors que le canonical du site est
`https://www.retroplanning.eu/`, ce qui indique une chaîne à 2 sauts :

```
http://retroplanning.eu → https://retroplanning.eu → https://www.retroplanning.eu
```

`app.py` ne contient aucune logique de redirection http→https ou apex→www (vérifié),
donc les deux sauts sont gérés par Cloudflare/le DNS, pas par Flask.

**Correctif à appliquer dans le dashboard Cloudflare :**
1. Activer **"Always Use HTTPS"** (SSL/TLS → Edge Certificates) pour que le saut
   http→https soit géré par Cloudflare en périphérie (rapide) et non par une réponse
   de l'origine.
2. Créer une **Redirect Rule** (Rules → Redirect Rules) qui envoie directement
   `retroplanning.eu/*` vers `https://www.retroplanning.eu/$1` en **un seul saut** —
   plutôt que de laisser une redirection http→https-apex suivie d'une seconde
   apex→www.
3. Vérifier après coup avec `curl -IL http://retroplanning.eu/` qu'il n'y a plus
   qu'un seul `301`/`308` avant le `200`.

## 2. Enregistrement DMARC absent

**Constat :** le SPF est en place (`v=spf1 include:mx.ovh.com -all`) mais aucun
enregistrement DMARC n'existe. Ça pèse sur la délivrabilité des emails transactionnels
(confirmations de paiement, codes de vérification) et laisse le domaine exposé à
l'usurpation.

**Correctif (zone DNS OVH) :** ajouter un enregistrement TXT sur
`_dmarc.retroplanning.eu`, par exemple pour démarrer en mode observation :

```
v=DMARC1; p=none; rua=mailto:contact@retroplanning.eu
```

Une fois les rapports analysés et la délivrabilité confirmée propre, passer
progressivement à `p=quarantine` puis `p=reject`.

## 3. Netlinking (priorité la plus élevée du rapport)

**Constat :** 0 backlink, 0 domaine référent, force de domaine = 0. C'est le plus gros
écart avec les sites leaders du secteur (audit noté F sur ce critère). Chantier
marketing continu, hors dépôt :
- Articles invités / partenariats avec des blogs événementiel, wedding planning,
  agences de com, gestion de projet.
- Inscription sur des annuaires métier et SaaS (Product Hunt, SaaSHub, annuaires
  French Tech).
- Créer une fiche Google Business Profile et la lier au site (impacte aussi le SEO
  local et les avis).
- Lier les réseaux sociaux de la marque (LinkedIn, Instagram, Facebook, X, YouTube)
  une fois créés.
