# Fiche Google Business Profile — contenu prêt à l'emploi

L'audit Limova.ai pointe : *« Aucun profil Google Business n'a été identifié qui renvoie à ce
site Web »*. C'est l'action à plus fort ratio impact/effort du rapport après le netlinking
(gratuit, rapide, améliore le SEO local ET permet de collecter des avis).

Je ne peux pas créer la fiche moi-même : ça se fait depuis un compte Google que vous contrôlez
(nécessaire pour la vérification et la propriété du profil). Voici tout le contenu prêt à
copier-coller, cohérent avec les coordonnées déjà présentes dans le schema `LocalBusiness` du
site (`app.py` → `ENTREPRISE`), pour que Google ne voie aucune divergence NAP
(Nom/Adresse/Téléphone) entre le site et la fiche.

## Avant de commencer : un point important sur l'adresse

Rétroplanning.eu est un outil 100% en ligne : personne ne se déplace à l'adresse d'Omnipub
pour l'utiliser. Google distingue les fiches "établissement visitable" des fiches
**"zone de service"** (Service Area Business). Pour ce cas, il faut créer la fiche en mode
**zone de service** et **masquer l'adresse physique** (elle reste utilisée pour la
vérification par Google, mais n'apparaît pas publiquement sur la fiche). Cocher la mauvaise
option ferait apparaître l'adresse d'Omnipub comme un lieu que des clients pourraient visiter,
ce qui ne correspond pas à l'usage réel.

## 1. Créer le profil

1. Aller sur https://business.google.com et se connecter avec un compte Google qui doit rester
   sous le contrôle de l'entreprise (éviter un compte personnel — utiliser une adresse liée à
   Omnipub si un Google Workspace existe, sinon `contact@retroplanning.eu` si un vrai compte
   Google y est rattaché).
2. Nom de l'établissement : **Rétroplanning.eu**
   *(le nom du produit, pas "Omnipub" — c'est ce que les gens recherchent ; Omnipub est
   mentionné comme éditeur dans la description).*
3. Catégorie principale : **Éditeur de logiciels**
   Catégorie(s) secondaire(s) si proposées par Google : *Fournisseur de services informatiques*,
   *Service de conception graphique* (pertinent pour l'export personnalisé aux couleurs client).
4. « Avez-vous un local que les clients peuvent visiter ? » → **Non**. Google propose alors le
   mode zone de service.
5. Zone de service : **France** (le site est en français, la clientèle visée est
   francophone/France — ne pas cocher un rayon autour de Castelnau-le-Lez, ça n'a pas de sens
   pour un outil en ligne).
6. Adresse (demandée pour la vérification, à masquer ensuite dans les paramètres de visibilité) :
   ```
   Omnipub
   Parc Mermoz - 199 rue Hélène Boucher
   34170 Castelnau-le-Lez
   France
   ```

## 2. Coordonnées

- **Téléphone :** 04 99 13 63 33
- **Site web :** https://www.retroplanning.eu
- **Email :** contact@retroplanning.eu (si Google Business Profile demande un email de contact
  visible — sinon laisser vide, l'email n'est pas un champ public standard sur GBP)

## 3. Horaires

Le générateur est accessible 24h/24 (site automatisé). Deux options :

- **Simple :** cocher « Ouvert 24h/24, 7j/7 ».
- **Plus honnête si le support par email n'est traité qu'en semaine :** indiquer les horaires
  réels de traitement du support (ex. Lun-Ven 9h-18h) et laisser le site lui-même accessible en
  continu — Google n'exige pas que les horaires GBP correspondent à la disponibilité technique
  du service, seulement à la disponibilité du contact humain.

## 4. Description (750 caractères max — celle-ci en fait ~480)

```
Rétroplanning.eu est un générateur en ligne de rétroplannings événementiels et de
production. Renseignez vos jalons clés et une date d'échéance : l'outil calcule et génère
une frise chronologique visuelle, personnalisable aux couleurs de votre charte graphique et
exportable en PNG haute définition. Conçu pour les agences de communication, organisateurs
d'événements, chefs de projet et particuliers (mariage, salon professionnel, lancement de
produit, déménagement, travaux, recrutement, événement associatif, soutenance de thèse).
Édité par Omnipub (Castelnau-le-Lez, Occitanie).
```

## 5. Bouton d'action et liens

- Bouton principal : **Site web** → https://www.retroplanning.eu
- Si Google propose un bouton "Réserver"/"Commander en ligne" (parfois disponible même pour du
  SaaS) : pointer vers https://www.retroplanning.eu/modeles (l'écran de choix de modèle, plus
  actionnable qu'une simple page d'accueil).

## 6. Produits (section "Produits" de la fiche)

Ajouter les 3 formules comme fiches produit, avec lien vers `/tarifs` :

| Nom | Prix | Description courte |
|---|---|---|
| À l'acte | 2,40 € TTC | 1 rétroplanning, export PNG HD immédiat |
| Starter 10 | 11,88 € TTC/mois | 10 rétroplannings par mois, résiliable à tout moment |
| Illimité | 23,88 € TTC/mois | Rétroplannings illimités, résiliable à tout moment |

## 7. Photos

- Logo (déjà disponible : `static/img/icon-512.png`)
- 1-2 captures d'écran du produit (la landing page ou un export de rétroplanning généré)
- Éviter une photo de bureau/local si l'adresse est masquée — resterait incohérent avec le
  choix "zone de service".

## 8. Vérification

Google propose généralement, selon l'éligibilité du compte : **téléphone**, **email**, ou
**courrier postal** (carte avec code, sous 5 à 14 jours, envoyée à l'adresse d'Omnipub même si
elle est masquée publiquement). Vérifier régulièrement le courrier de l'entreprise pendant
cette période.

## 9. Après validation : lier la fiche au site et collecter des avis

1. Une fois la fiche validée, ajouter le lien de la fiche (`g.page/r/...` ou URL Maps) dans le
   footer du site et/ou dans les emails de confirmation de commande, avec une invitation à
   laisser un avis — l'audit note aussi l'absence totale d'avis Google.
2. Vérifier que Google affiche bien le site retroplanning.eu comme site officiel associé à la
   fiche (corrige directement le point d'audit *« Aucun profil commercial Google identifié qui
   renvoie à ce site »*).

Aucune modification de code n'est nécessaire pour cette étape : les coordonnées ci-dessus sont
déjà strictement identiques à celles du schema `LocalBusiness` embarqué sur `/` et `/a-propos`
(`ENTREPRISE` dans `app.py`), donc pas de risque d'incohérence NAP entre le site et la fiche.
