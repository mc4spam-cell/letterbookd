# CLAUDE.md — outil de club de lecture privé

Point de départ du projet. Lis ce fichier en entier, puis `docs/PLAN.md` (plan de développement) et `docs/ANALYSE.md` (analyse de Letterboxd et inventaire des fonctions).

## En une phrase

Une application web pour animer **un club de lecture privé** (quelques dizaines de lecteurs) : choisir le livre du mois, noter, écrire des avis, en discuter. Inspirée de Letterboxd, pas une copie.

## Règles produit (valent contrat pour tout le code)

1. **Tout est privé.** Rien n'est lisible sans compte, ni en dehors d'un club.
2. **Visibilité par clubs communs.** Un membre voit le profil, les lectures, les avis et les listes d'un autre membre si et seulement s'ils partagent au moins un club. Une seule fonction centrale (« partage-t-il un club avec moi ? ») filtre toutes les requêtes de données, jamais seulement les écrans. Elle est testée avant tout le reste.
3. **Un club au départ, plusieurs possibles.** Le modèle autorise plusieurs adhésions par utilisateur dès le début. L'interface multi-clubs vient en P2.
4. **Adhésion par lien.** L'animateur partage un lien d'invitation ; le suivre suffit. Le lien est renouvelable (l'ancien cesse de fonctionner). L'animateur peut exclure un membre.
5. **Un avis justifie une note.** La note vit sur la *lecture* ; l'avis s'y rattache et n'existe pas sans elle. Une note peut exister sans avis.
6. **Discussion par commentaires** sur les avis, avec réponses imbriquées. Pas de fils par chapitre.

L'inscription propose d'emblée deux chemins : **créer mon club** ou **rejoindre un club** (avec un lien).

## Stack (validée)

- Python, **Django**, rendu côté serveur ; gabarits Django + **HTMX** + **Tailwind CSS**
- **PostgreSQL**
- **django-allauth** (e-mail + mot de passe)
- Catalogue : API **Open Library** (sans clé) avec **copie locale** des seules fiches utilisées
- E-mail : SMTP configurable
- Tests : **pytest-django** ; CI : **GitHub Actions** ; style : **ruff**
- Déploiement : **Docker Compose** (application, PostgreSQL, Caddy) sur un serveur personnel sous Linux ; sauvegarde nocturne chiffrée de PostgreSQL vers un stockage externe
- Interface en **français uniquement, tutoiement**, mais **tous les textes sont externalisés** (gettext) pour une traduction possible plus tard
- Licence : **GPL** ; dépôt public sur GitHub (le code est public, l'appli n'est pas diffusée)

## Périmètre

- **Hors périmètre** : pages publiques, découverte ouverte, partage externe, flux RSS, annuaire public, comptes d'éditeurs, journal éditorial, offre premium, application mobile native.
- **Mobile** : site web uniquement ; un habillage optimisé mobile viendra plus tard.
- **À discuter plus tard** : API publique (point 40).

## Par où commencer

Travaille **lot par lot** dans l'ordre de `docs/PLAN.md`. Commence par le **lot 0** : dépôt, licence GPL, README, CI, Docker Compose, squelette Django, textes externalisés. Critère de fin : `docker compose up` lance l'appli et la CI est verte.

Deux portes à ne pas franchir sans validation de MC :
- **Porte 1** (après le lot 1) : deux clubs sont étanches, prouvé par des tests.
- **Porte 2** (après le lot 4) : mise en service pilote.

## Règles de travail

- **Aucun secret ni donnée de membre dans Git.** Configuration par variables d'environnement ; fichier d'exemple sans valeur réelle ; contrôle de secrets en CI.
- Écris les **tests d'isolation entre clubs avant** les fonctions qui lisent des données.
- Pas d'appel réseau réel en test (réponses Open Library simulées).
- Une correction manuelle d'une fiche livre n'est jamais écrasée par une actualisation.
- Ajoute une dépendance seulement si elle apporte nettement plus qu'elle ne coûte, et dis-le.
- Propose un plan court avant tout changement qui touche au modèle de données ou à la règle de visibilité.
- Les textes d'interface suivent le ton de `docs/ANALYSE.md` (verbes simples, tutoiement, confirmations qui nomment ce qui est perdu et ce qui est gardé).

## Conventions proposées (à confirmer par MC)

- Identifiants, noms de modèles et commentaires de code en anglais ; textes d'interface en français via gettext.
- Un fichier `docs/DECISIONS.md` tenu à jour pour toute décision d'architecture.

## Points encore ouverts

- Accès à Internet du serveur personnel : tunnel (par exemple Cloudflare Tunnel) ou ouverture de port, à définir.
- Conditions d'usage d'Open Library (identification de l'application, limites de requêtes) à vérifier avant le lot 2.
- BnF comme source complémentaire (P2) : changement de format en juin 2026 non vérifié.
