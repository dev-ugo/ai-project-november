# Design system de CSV Check

Version 0.1. Une base visuelle légère, sans framework CSS, pour le MVP CSV Check.

## Direction visuelle

L’interface utilise un fond clair, des cartes blanches, un texte sombre et une couleur bleue pour les actions principales. Elle accompagne l’utilisateur dans l’ajout d’un CSV et la lecture de son rapport.

L’interface et la documentation sont en français. Les noms de fichiers, variables, classes CSS et identifiants techniques restent en anglais lorsque c’est logique. La police est fournie par le système d’exploitation.

## Fondations

### Couleurs

Les couleurs sont centralisées dans des variables CSS pour conserver une apparence cohérente.

| Variable CSS | Valeur | Utilisation |
| --- | --- | --- |
| `--cc-bg` | `#F6F8FB` | Fond de page |
| `--cc-surface` | `#FFFFFF` | Cartes et champs de formulaire |
| `--cc-text` | `#182230` | Texte principal |
| `--cc-muted` | `#596579` | Texte secondaire |
| `--cc-border` | `#E4E7EC` | Bordures décoratives des cartes |
| `--cc-control-border` | `#7C879A` | Bordures des champs et boutons secondaires |
| `--cc-primary` | `#1D4ED8` | Actions principales, liens et indicateurs de focus |
| `--cc-primary-hover` | `#1E40AF` | Survol des boutons principaux |
| `--cc-primary-soft` | `#EFF6FF` | Fonds bleus discrets |
| `--cc-success` / `--cc-success-soft` | `#166534` / `#ECFDF3` | Confirmation d’une opération réussie |
| `--cc-warning` / `--cc-warning-soft` | `#92400E` / `#FFFAEB` | Points à vérifier |
| `--cc-danger` / `--cc-danger-soft` | `#B42318` / `#FEF3F2` | Erreurs empêchant l’envoi ou l’analyse |

### Typographie et mise en page

- Police sans empattement du système. Une police à chasse fixe est réservée aux noms de colonnes et aux valeurs techniques.
- Titre principal : 32 à 44 px selon l’espace disponible. Titre de section : 24 px. Titre de composant : 18 px.
- Texte courant : 16 px, avec un interligne de 1,6. Libellés : 14 px. Métadonnées : 12 px.
- Graisse : 400 pour le texte courant, 600 à 700 pour la hiérarchie.
- Espacements : 4, 8, 12, 16, 24, 32 et 48 px.
- Arrondis : 8 px pour les champs et boutons, 12 px pour les cartes, 16 px pour les grandes surfaces.
- Hauteur des champs et boutons : au moins 44 px.
- Sur la page de référence, sous 700 px, les colonnes et statistiques s’empilent et la navigation défile horizontalement.
- Les tableaux denses défilent dans leur propre cadre pour préserver la largeur de la page et la lisibilité des libellés.

## Composants

| Composant | Classes | États ou variantes |
| --- | --- | --- |
| Bouton | `cc-btn`, `cc-btn--primary`, `cc-btn--secondary`, `cc-btn--quiet` | Normal, survol, focus clavier, désactivé, chargement |
| Champ de saisie | `cc-input`, `cc-label`, `cc-help`, `cc-error` | Normal, focus, invalide, lecture seule |
| Liste de sélection | `cc-select` | Virgule ou point-virgule |
| Zone de dépôt | `cc-dropzone` | Attente, survol, focus clavier, glisser-déposer, fichier sélectionné, invalide |
| Badge | `cc-badge` et variantes `cc-badge--*` | `neutral`, `info`, `success`, `warning`, `danger` |
| Message | `cc-alert` et variantes `cc-alert--*` | `info`, `success`, `warning`, `danger` |
| Carte | `cc-card`, `cc-card__head`, `cc-card__body` | Contenu et rapports |
| Statistique | `cc-stat`, `cc-stat__label`, `cc-stat__value`, `cc-stat__hint` | Compteurs de lignes, doublons et cellules vides |
| Tableau de détail | `cc-table-scroll`, `cc-table` | En-têtes accessibles et défilement horizontal |
| État vide | `cc-empty` | Explication et action pour commencer |

Un écran privilégie une action principale. Les actions secondaires utilisent un style plus discret.

## Règles de statut

- L’enregistrement d’un rapport est une opération réussie, même si des points à vérifier ont été détectés.
- Les cellules vides et les doublons sont des **points à vérifier**, pas nécessairement des erreurs métier.
- Le rouge indique que l’opération n’a pas pu aboutir : format, taille ou encodage invalide, CSV mal formé ou requête en échec.
- L’absence de points détectés signifie seulement qu’aucune cellule vide ni aucun doublon exact n’a été trouvé. Elle ne garantit pas que toutes les données sont correctes.
- Chaque statut comporte un texte explicite ; une icône peut compléter la couleur.
- Les compteurs correspondent directement à `row_count`, `duplicate_count` et `empty_cell_count`.
- La page de référence présente un exemple de 3 lignes de données : une cellule vide à la ligne 3 et un doublon à la ligne 4 du CSV. Ces valeurs sont illustratives.

## Accessibilité et interactions

- Utiliser des boutons HTML, des libellés associés aux champs, un seul titre `h1` et une hiérarchie de titres ordonnée.
- Maintenir un focus clavier visible. Le champ natif de sélection de fichier reste accessible au clavier, même s’il est masqué visuellement.
- Annoncer les changements d’état de l’envoi dans une zone de statut.
- Associer les champs invalides à leur message explicatif. Les erreurs inattendues doivent être annoncées comme des alertes.
- Conserver des bordures de champs et des indicateurs de focus visibles sur leur fond.
- Donner un attribut `scope` aux en-têtes du tableau, un titre au tableau et un cadre de défilement accessible au clavier.
- Respecter `prefers-reduced-motion` pour réduire les animations.
- Transmettre les informations importantes par un texte, en complément des icônes, des couleurs et des effets de survol.

## Fichiers du design system

| Fichier | Rôle |
| --- | --- |
| `app/static/css/design-system.css` | Variables CSS, mises en page et styles des composants |
| `app/static/js/design-system.js` | Interactions locales de la page de référence |
| `app/templates/design-system.html` | Page de référence utilisant les styles partagés |
| `app/routers/design_system.py` | Route FastAPI `/design-system` |
| `docs/design-system.md` | Principes visuels, composants et utilisation |

La page `/design-system` **n’appelle pas l’API**. Sa zone de dépôt vérifie uniquement l’extension et la taille du fichier pour la démonstration. Le bouton de chargement simule une requête et ne crée aucun rapport.

L’interface réelle utilise `app/templates/index.html`, `app/static/css/app.css` et `app/static/js/app.js`. Elle réutilise les composants partagés et envoie les fichiers à `POST /analyses`.

## Intégration dans FastAPI

Les fichiers statiques sont exposés sous `/static` et la page de référence est enregistrée dans `app/main.py`.

Imports nécessaires :

```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from app.routers import design_system
```

Après la création de `app = FastAPI(...)` :

```python
APP_DIR = Path(__file__).resolve().parent

app.mount(
    "/static",
    StaticFiles(directory=APP_DIR / "static"),
    name="static",
)

app.include_router(design_system.router)
```

Ce montage et cet enregistrement ne doivent être ajoutés qu’une fois. Les autres routes de l’application sont conservées.

La route `/design-system` utilise `include_in_schema=False` : elle reste accessible directement, mais n’apparaît pas dans la documentation interactive `/docs`.

## Vérification de la page de référence

Démarrer l’application depuis la racine du dépôt :

```bash
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Ouvrir `/design-system` sur le port transféré, puis vérifier :

- l’affichage des couleurs, des textes et des composants ;
- le chargement simulé et la réinitialisation ;
- la sélection d’un fichier et le message affiché pour une extension invalide ;
- la navigation au clavier et les indicateurs de focus ;
- la mise en page sur une fenêtre étroite ;
- le fonctionnement de `/health` et `/docs`.

Après un déploiement Render réussi, `/design-system` est également disponible sur l’URL hébergée.

## Réutilisation dans l’interface

Charger le fichier CSS partagé, puis utiliser les classes des composants :

```html
<link rel="stylesheet" href="/static/css/design-system.css">

<button class="cc-btn cc-btn--primary" type="submit">
  Analyser le fichier
</button>

<span class="cc-badge cc-badge--warning">Points à vérifier</span>

<div class="cc-card cc-card__body">
  <h2>Résultat de l’analyse</h2>
</div>
```

Les envois réels utilisent `POST /analyses`, avec le fichier dans le champ multipart `file` et le séparateur choisi dans le paramètre de requête `delimiter`.

Le JavaScript de démonstration reste limité à la page de référence. L’écran d’analyse gère ses propres requêtes, le chargement, les erreurs et l’affichage du rapport.

## Parcours de l’interface

L’application affiche un seul écran principal à la fois :

| Écran | Action principale | Informations secondaires |
| --- | --- | --- |
| Connexion ou inscription | Se connecter / créer son compte | Lien pour changer de mode, sans deux boutons de soumission concurrents |
| Analyse | Choisir un CSV puis l’analyser | Séparateur compact et lien vers un exemple |
| Résultat | Recevoir la version sans doublons par e-mail | Compteurs, détail des anomalies repliable, nouvelle analyse |
| Historique | Ouvrir un rapport | Date, nombre de lignes et résumé des points à vérifier |

La navigation principale se limite à **Analyser** et **Historique**. Le menu **Compte** contient l’adresse connectée et la déconnexion. Les liens vers le design system et la documentation API sont dans le pied de page.

Le résultat remplace le formulaire après une analyse réussie. L’historique est chargé uniquement lorsqu’il est ouvert ou actualisé. Les liens `#analysis`, `#history` et `#report/ID` permettent le retour arrière et la réouverture d’un rapport après rechargement, sous réserve d’une session autorisée.

Sur mobile, les lignes de l’historique deviennent des cartes compactes ; le bouton « Ouvrir » reste visible sans déplacement horizontal. Le tableau détaillé des anomalies conserve son propre défilement horizontal.

## États et accessibilité du parcours

- Un seul titre `h1`, mis à jour avec l’écran actif. Le focus rejoint le titre lors d’un changement d’écran pour annoncer le nouveau contexte.
- Les écrans inactifs utilisent `hidden` et ne restent pas dans le parcours clavier.
- La navigation active utilise `aria-current`. Le menu du compte et le détail des anomalies utilisent des éléments HTML `details`/`summary` accessibles au clavier.
- Le menu du compte se ferme au clic extérieur ou avec Échap. Dans ce dernier cas, le focus revient à son bouton.
- Les messages de connexion, d’historique et d’e-mail sont des régions de statut. Les erreurs d’analyse sont des alertes.
- Les contrôles sont désactivés pendant une requête pour éviter les doubles actions. Une session expirée efface les listes affichées et revient à la connexion.
- Les noms de fichiers et de colonnes sont insérés comme texte, jamais comme HTML.

Le bouton **Recevoir par e-mail** précise son destinataire et la règle de correction : retirer les doublons exacts, conserver les cellules vides. Aucun envoi n’est déclenché automatiquement. La confirmation indique la transmission au prestataire sans promettre la réception finale.
