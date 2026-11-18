# Analyse de Letterboxd et inventaire des fonctions

Analyse faite le 18 novembre 2026 sur letterboxd.com : pages publiques (accueil, fiche film, listes, membres, Pro) puis compte connecté, en lecture seule (activité, profil, diary, watchlist, listes, réseau, réglages). Aucun log, like ni modification n'a été fait. Les fenêtres « Review or log » et « Add to lists » n'ont pas été ouvertes (elles écrivent des données) : leurs champs exacts restent à confirmer.

Objectif : s'inspirer de Letterboxd pour un outil de club de lecture privé, sans le copier.

## 1. Ce que fait Letterboxd

| Fonction Letterboxd | Équivalent club de lecture |
|---|---|
| **Log** d'un film vu, avec date (diary) | Journal de lecture : lu, en cours, abandonné, avec dates |
| **Note sur 5 étoiles, demi-points** | Même échelle |
| **Reviews** avec likes, commentaires | Avis, qui justifient une note |
| **Watchlist** (à voir) | « À lire » |
| **Listes** (description, likes, commentaires), onglets « Your lists » et « Shared with you » | Listes thématiques, y compris listes du club |
| **Showdowns** (votes communautaires) | Vote du prochain livre du club |
| **Fiche film** : casting, détails, distribution des notes, listes qui contiennent le film | Fiche livre : auteur, détails, répartition des notes du club, listes |
| **Membres** : profils, suivi, flux d'activité | Profils des membres du club, flux du club |
| **HQs**, journal, actus | Hors périmètre (privé) |
| **Pro** (21 €/an), Year in Review | Stats et bilan de lecture |
| Données TMDB, JustWatch | Open Library, éventuellement BnF |

### Ce qui est transposable

- Une **base de référence partagée** : chaque livre a une fiche unique, et tout (avis, notes, listes) s'y rattache. C'est l'étape la plus délicate.
- Un **geste de base minuscule** (je l'ai lu, je mets une note) sur lequel le social se construit.
- Un **panneau d'actions** de quelques boutons sur chaque fiche : Lu, J'aime, À lire, Noter, Écrire un avis…, Ajouter à une liste….
- Des **compteurs** (likes, nombre de lectures) qui donnent de la vie.

### Fonctions confirmées côté membre connecté

- **Diary** : vue chronologique par mois et par jour ; colonnes film, année, note, like, rewatch, review ; filtres par date, genre, décennie, année, note.
- **Profil** : onglets Activity, Films, Diary, Reviews, Watchlist, Lists, Likes, Tags, Network ; recherche dans ses propres avis et listes.
- **Watchlist** : tri, filtres, import (jusqu'à 1 900 titres), export, passage en privé, vidage.
- **Réseau** : Following, Followers, Blocked.
- **Réglages** : profil, 2FA, notifications fines (nouveaux followers, commentaires de fils suivis, activité des seuls membres suivis), export des données.
- **Pro** : stats annuelles et globales, notes moyennes des amis, clonage de listes, gestion des tags.

### Ce que le club doit ajouter

- Un **cycle de club** : proposition, vote, livre du mois, calendrier de lecture.
- Le **masquage des spoilers** (plus important pour un livre).
- Une **progression de lecture** (page ou %) : reportée en P3.

## 2. Voix et copy (observés sur Letterboxd, adaptés au club)

Règles :

1. **Triptyque de verbes** à l'accueil : trois phrases courtes, un verbe d'action chacune.
2. **Verbes simples, sans jargon** : on note, on like ; jamais « soumettre ».
3. **Points de suspension** sur les actions qui ouvrent une fenêtre (« Écrire un avis… »).
4. **Empty states en deux temps** : constat bref, puis invitation à démarrer.
5. **Première personne** : « ce que tu veux lire », pas « la liste de l'utilisateur ».

Décision : **français, tutoiement** partout. Textes d'interface externalisés (gettext).

| Élément | Copy proposé (à passer au tutoiement) |
|---|---|
| Accroche d'accueil | Note ce que tu lis. Garde ce que tu veux lire. Dis ce qui vaut le coup. |
| CTA principal | Rejoindre le club |
| Chemins d'inscription | Créer mon club · Rejoindre un club |
| Actions sur un livre | Lu · J'aime · À lire · Noter · Écrire un avis… · Ajouter à une liste… |
| Empty state : liste | Aucune liste pour l'instant. Crée la première ? |
| Empty state : à lire | Ta pile est vide. Ajoute un livre depuis sa fiche. |
| Empty state : avis | Pas encore d'avis. Sois le premier à dire ce que tu en as pensé. |
| Vote du mois | Quel sera le prochain livre du club ? Vote avant le [date]. |
| Spoiler | Cet avis révèle l'intrigue. Afficher quand même |
| Suppression d'une liste | Supprimer cette liste ? Les 12 livres resteront dans ta bibliothèque. · Supprimer la liste / Garder |
| Erreur d'import | Import impossible. Le fichier n'est pas au format attendu. Télécharge notre modèle CSV et réessaie. |
| Notification (réglage) | Préviens-moi seulement pour les réponses à mes commentaires |

Notes : le français est 20 à 30 % plus long que l'anglais (prévoir de la marge sur les boutons) ; libeller les notes en toutes lettres pour l'accessibilité (« 3,5 sur 5 ») ; « Watchlist » devient « À lire » ou « Ma pile ».

## 3. Inventaire final et priorités

P1 = MVP, P2 = v2, P3 = plus tard. Priorités arbitrées par MC le 18 novembre 2026. La colonne « Lot » renvoie à `PLAN.md`.

### P1 — MVP

| # | Élément | Lot |
|---|---|---|
| 1 | Catalogue de livres (Open Library, copie locale des fiches utilisées) | L2 |
| 3 | Fiche livre (auteur, détails, répartition des notes du club, listes) | L2 |
| 4 | Recherche (livres, membres du club) | L2 |
| 6 | Inscription, connexion, mot de passe oublié | L1 |
| 8 | Profil (bio, avatar, onglets) | L1 |
| 9 | Réglages : confidentialité, notifications, suppression de compte | L1 |
| 11 | Statuts : à lire, en cours, lu, abandonné | L5 |
| 12 | Journal de lecture daté, avec relecture | L5 |
| 13 | Note sur 5 étoiles avec demi-points | L5 |
| 17 | Filtres et tris (genre, période, note) | L5 |
| 18 | Avis avec commentaires et réponses | L4 |
| 19 | Masquage des spoilers | L4 |
| 21 | Flux d'activité du club | L4 |
| 22 | Notifications de base | L4 |
| 25 | Listes (titre, description) | L5 |
| 29 | Club : création, rôles animateur/membre, liste des membres | L1 |
| 30 | Cycle du club : propositions, vote, livre du mois, calendrier | L3 |
| 37 | Stats et bilan de lecture | L6 |
| 43 | Guide de copy en français | L6 |
| 44 | Accessibilité et responsive | L6 |
| 45 | Modération par l'animateur (exclusion, signalement) | L1 |
| 46 | RGPD léger, CGU, mentions légales | L1 |
| 47 | Licence, README, configuration par variables d'environnement, aucun secret dans le dépôt public | L0 |
| 48 | Rejoindre un club par lien d'invitation | L1 |

### P2

| # | Élément |
|---|---|
| 2 | Regroupement des éditions d'une œuvre |
| 7 | Double authentification |
| 22 | Notifications granulaires |
| 26 | Listes collaboratives |
| 38 | Import CSV (Goodreads) |
| 39 | Export des données |
| 49 | Interface multi-clubs (sélecteur de club) |
| 50 | BnF comme source complémentaire pour les livres français |

### P3

| # | Élément |
|---|---|
| 5 | Liens d'emprunt / d'achat |
| 14 | Progression (page ou %) |
| 15 | « J'aime » sur livres, listes, avis |
| 16 | Tags personnels |
| 28 | Cloner une liste |
| 31 | Fils de discussion par chapitre |
| 32 | Rencontres / événements |
| 33 | Duels de livres |

### Écartés ou remplacés

| # | Élément | Raison |
|---|---|---|
| 10 | Visibilité public/privé par objet | remplacée par la règle des clubs communs |
| 20 | Suivre / être suivi | inutile à l'échelle d'un club ; seule l'exclusion par l'animateur est gardée (45) |
| 23, 24, 27, 34, 35, 36 | Populaire cette semaine, partage externe et RSS, listes mises en avant, annuaire, journal éditorial, comptes éditeurs | hors périmètre (privé) |
| 41 | Application mobile | écartée : site web uniquement, habillage optimisé mobile plus tard |
| 42 | Offre premium | écartée : pas de diffusion publique |

### À discuter

| # | Élément |
|---|---|
| 40 | API publique |

## 4. Arbitrages de MC (rappel)

1. L'outil sert à **animer un club de lecture privé** ; le code est public sur GitHub, l'application n'est pas diffusée.
2. **Catalogue** : Open Library (plus de 40 millions d'éditions, API sans clé, dumps JSON mensuels, qualité inégale car base éditable par la communauté) ; la BnF (Licence Ouverte depuis 2014, SRU / Z39.50 en UNIMARC, dépôt légal français) en source complémentaire. La BnF change de format et de modèle de catalogage en juin 2026 : état non vérifié.
3. **Un seul club** (quelques dizaines de lecteurs) au départ ; « créer mon groupe » ou « rejoindre un groupe » est central à l'inscription ; un utilisateur pourra appartenir à plusieurs groupes ; le profil est visible de tous les groupes de l'utilisateur.
4. **Discussion** par commentaires avec réponses ; **adhésion** par lien ; **langue** : français (tutoiement), internationalisation possible plus tard.
5. **Avis** : il justifie une note et n'existe pas sans elle.
6. **Hébergement** : serveur personnel ; **licence** : GPL ; **mobile** : web uniquement.
