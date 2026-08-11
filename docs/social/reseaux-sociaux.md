# Réseaux sociaux — contenu prêt à l'emploi

Répond au point d'audit *"Créez et liez [profil]"* pour Facebook, X, Instagram, YouTube,
LinkedIn (tous en priorité faible individuellement, mais l'absence totale de présence sociale
pèse aussi sur les signaux d'autorité GEO — *"Signaux d'autorité et de confiance limités"*).

Ordre de priorité pour une cible BtoB agences de communication / événementiel : **LinkedIn et
Instagram d'abord** (les plus consultés par ce public avant de faire confiance à un outil),
Facebook et X ensuite, YouTube seulement si du contenu vidéo est prévu un jour.

Logo à utiliser comme photo de profil sur toutes les plateformes : `static/img/icon-512.png`
(déjà généré, cohérent avec le favicon du site).

---

## 1. LinkedIn (priorité haute)

- **Type de page** : Page entreprise (pas profil personnel)
- **Nom** : Rétroplanning.eu
- **URL suggérée** : `linkedin.com/company/retroplanning-eu`
- **Secteur** : Logiciels
- **Taille** : 1-10 employés (ou la taille réelle d'Omnipub)
- **Site web** : https://www.retroplanning.eu
- **Slogan** (120 caractères max) :
  ```
  Générez un rétroplanning événementiel ou de production professionnel en 2 minutes.
  ```
- **À propos** (2 600 caractères max — celle-ci en fait ~520) :
  ```
  Rétroplanning.eu est un générateur en ligne de rétroplannings événementiels et de
  production. Renseignez vos jalons clés et une date d'échéance : l'outil calcule et
  génère une frise chronologique visuelle, personnalisable aux couleurs de votre charte
  graphique et exportable en PNG haute définition.

  Conçu pour les agences de communication, organisateurs d'événements, chefs de projet
  et toute personne devant visualiser les étapes clés menant à une date de livraison :
  mariage, salon professionnel, lancement de produit, déménagement, travaux, recrutement,
  événement associatif, soutenance de thèse.

  Paiement à l'usage ou abonnement, sans engagement, résiliation en libre-service.

  Édité par Omnipub (Castelnau-le-Lez, Occitanie).
  ```
- **Premier post suggéré** : reprendre l'accroche de la landing ("Le rétroplanning de
  production simple et pro.") + lien vers `/modeles`, avec un visuel d'export PNG en exemple.

---

## 2. Instagram (priorité haute)

- **Nom d'utilisateur suggéré** : `@retroplanning.eu` (ou `@retroplanning_eu` si pris)
- **Nom affiché** : Rétroplanning.eu
- **Catégorie** : Logiciel / Application
- **Bio** (150 caractères max) :
  ```
  📅 Rétroplannings événementiels & production en 2 min
  🎨 Aux couleurs de votre agence
  📥 Export PNG HD
  👇 Essayez gratuitement
  ```
- **Lien en bio** : https://www.retroplanning.eu/modeles
- **Contenu suggéré pour démarrer** : captures d'écran des 8 modèles sectoriels (mariage,
  salon pro, etc. — visuellement adapté au format carré/story), avant/après d'un
  rétroplanning généré.

---

## 3. Facebook (priorité moyenne)

- **Type** : Page entreprise (catégorie "Logiciel" ou "Service de planification d'événements")
- **Nom** : Rétroplanning.eu
- **URL suggérée** : `facebook.com/retroplanning.eu`
- **À propos court** :
  ```
  Générateur en ligne de rétroplannings événementiels et de production. Créez votre
  frise chronologique en 2 minutes, personnalisable aux couleurs de votre agence.
  ```
- **Site web** : https://www.retroplanning.eu
- Le site utilise déjà les balises **Facebook Open Graph** (vérifié ✅ dans l'audit), donc
  tout partage d'un lien retroplanning.eu affichera automatiquement titre/description/image
  correctement sur Facebook — pas d'action supplémentaire nécessaire côté site pour ça.

---

## 4. X / anciennement Twitter (priorité moyenne)

- **Handle suggéré** : `@retroplanningeu` (15 caractères, dans la limite)
- **Nom affiché** : Rétroplanning.eu
- **Bio** (160 caractères max) :
  ```
  Générateur en ligne de rétroplannings événementiels & de production. 2 min chrono,
  export PNG HD. 👉 retroplanning.eu
  ```
- Le site utilise déjà les **cartes X (Twitter Cards)** (vérifié ✅ dans l'audit) — même
  remarque que Facebook, aucune action site nécessaire pour l'aperçu des liens partagés.

---

## 5. YouTube (priorité faible, à différer si pas de contenu vidéo prévu)

- **Nom de chaîne** : Rétroplanning.eu
- **Handle suggéré** : `@retroplanningeu`
- **Description de chaîne** :
  ```
  Rétroplanning.eu — générateur en ligne de rétroplannings événementiels et de
  production. Découvrez comment créer votre frise chronologique en 2 minutes.
  ```
- Pas de priorité immédiate : n'a de sens qu'avec du contenu (ex. une courte démo de
  l'outil, 60-90s). À revisiter une fois les autres profils en place.

---

## Une fois les profils créés

Envoyez-moi les URL de chaque profil créé, et je m'occupe de :

1. **Les lier depuis le footer du site** (nouvelle rangée d'icônes, cohérente avec le
   design actuel).
2. **Les ajouter au schema `Organization`/`LocalBusiness`** en JSON-LD via la propriété
   `sameAs` — c'est ce qui compte le plus pour Google/les moteurs génératifs : ça confirme
   à l'algorithme que ces profils et le site représentent la même entité, renforçant
   directement le point d'audit *"Signaux d'autorité et de confiance"* (GEO) au-delà du
   simple lien visuel.

Inutile d'attendre d'avoir créé les 5 — envoyez-les au fur et à mesure, j'intègre par lots.
