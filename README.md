# CSV Check

Application web qui analyse un fichier CSV pour repérer les cellules vides et les lignes en double, puis conserve un rapport dans PostgreSQL.

Ce MVP est développé avec l’aide de l’IA dans le cadre d’un projet à réaliser en une journée.

## Fonctionnalités

- Sélection d’un fichier CSV ou ajout par glisser-déposer.
- Choix du séparateur : virgule ou point-virgule.
- Détection des cellules vides et des lignes entièrement identiques.
- Affichage des compteurs et des anomalies avec leurs numéros de ligne.
- Enregistrement du rapport en base de données.
- Interface adaptée aux petits écrans et page de référence du design system.

## Technologies

| Partie | Technologies |
| --- | --- |
| API | Python 3.12, FastAPI, Uvicorn |
| Base de données | PostgreSQL, SQLAlchemy, Psycopg |
| Interface | HTML, CSS, JavaScript |
| Environnement de développement | GitHub Codespaces, Dev Containers |
| Hébergement | Render |

## Démarrer dans GitHub Codespaces

1. Ouvrir le dépôt dans un Codespace.
2. Appliquer la configuration `.devcontainer` avec **Codespaces: Rebuild Container** si nécessaire. Elle prépare Python, PostgreSQL et la variable `DATABASE_URL`.
3. Depuis la racine du dépôt, installer les dépendances et initialiser la table :

   ```bash
   .venv/bin/python -m pip install -r requirements.txt
   .venv/bin/python -m app.init_db
   ```

4. Démarrer l’application :

   ```bash
   .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Ouvrir le port **8000** depuis l’onglet **Ports** de Codespaces. La racine `/` affiche le formulaire d’analyse.

La commande `app.init_db` crée les tables absentes. Elle ne met pas à jour la structure d’une table déjà existante.

## Utilisation

1. Choisir un CSV encodé en UTF-8, de **1 Mio maximum**.
2. Sélectionner le séparateur utilisé dans le fichier.
3. Cliquer sur **Analyser le CSV**.
4. Consulter le rapport : lignes analysées, doublons, cellules vides et détail des points à vérifier.

Un fichier d’exemple est téléchargeable depuis l’interface. Il contient **3 lignes de données, 1 doublon et 1 cellule vide**.

### Règles d’analyse

- La première ligne doit contenir un nom non vide et unique pour chaque colonne.
- Les lignes de données doivent avoir le même nombre de colonnes que l’en-tête.
- Une cellule est vide si elle ne contient aucune valeur ou uniquement des espaces.
- Un doublon est une répétition d’une ligne dont toutes les valeurs sont identiques. La première occurrence n’est pas comptée comme un doublon.
- Les valeurs ne sont pas normalisées pour comparer les doublons : la casse et les espaces sont conservés.
- L’en-tête et les lignes complètement vierges sont exclus du nombre de lignes analysées.
- Les numéros affichés correspondent aux lignes du CSV, en comptant l’en-tête. Pour un enregistrement sur plusieurs lignes, le numéro indique sa première ligne.

Une cellule vide ou un doublon représente un **point à vérifier**, pas nécessairement une erreur métier.

## Principales routes

| Méthode | Route | Rôle |
| --- | --- | --- |
| `GET` | `/` | Interface d’analyse |
| `POST` | `/analyses` | Analyser un CSV et enregistrer son rapport |
| `GET` | `/health` | Vérifier que l’application répond |
| `GET` | `/docs` | Documentation interactive de l’API |
| `GET` | `/design-system` | Page de référence des composants visuels |

`POST /analyses` reçoit un fichier dans le champ multipart `file`. Le paramètre de requête `delimiter` vaut `,` par défaut ou `;` pour un point-virgule.

Une analyse réussie renvoie le statut **201**, avec l’identifiant du rapport, son nom de fichier, sa date, les compteurs et la liste des anomalies.

Les pages HTML `/` et `/design-system` sont volontairement masquées dans `/docs`. La route `/health` vérifie la réponse de l’application, sans interroger PostgreSQL.

## Organisation du projet

| Emplacement | Rôle |
| --- | --- |
| `app/main.py` | Création de l’application, routes et fichiers statiques |
| `app/database.py` | Configuration de la connexion à PostgreSQL |
| `app/init_db.py` | Initialisation des tables |
| `app/models/` | Modèle de données du rapport |
| `app/routers/` | Routes de l’API et page du design system |
| `app/services/` | Logique d’analyse des CSV |
| `app/templates/` | Pages HTML |
| `app/static/` | CSS, JavaScript et fichier d’exemple |
| `docs/` | Documentation du projet |
| `.devcontainer/` | Environnement de développement Codespaces |
| `scripts/start.sh` | Initialisation et démarrage sur Render |
| `render.yaml` | Configuration du déploiement Render |

## Base de données

Une seule table, `analyses`, contient les rapports :

| Champ | Contenu |
| --- | --- |
| `id` | Identifiant du rapport |
| `filename` | Nom du fichier analysé |
| `created_at` | Date de l’analyse |
| `row_count` | Nombre de lignes de données analysées |
| `duplicate_count` | Nombre de lignes en double |
| `empty_cell_count` | Nombre de cellules vides |
| `anomalies` | Liste des points détectés, au format JSON |

Les fichiers importés ne sont pas stockés durablement par l’application. Les résultats sont conservés en base. La connexion est définie par la variable d’environnement `DATABASE_URL`.

## Déploiement sur Render

1. Pousser le code et `render.yaml` sur GitHub.
2. Dans Render, sélectionner **New → Blueprint**, puis connecter le dépôt et choisir la branche `main`.
3. Vérifier les ressources proposées, puis lancer le déploiement.

La configuration crée l’API et PostgreSQL dans la même région et transmet automatiquement `DATABASE_URL` à l’application. Le script `scripts/start.sh` initialise les tables avant de lancer Uvicorn.

Les nouveaux commits poussés sur `main` déclenchent un déploiement automatique. L’URL de l’application est disponible dans le tableau de bord Render.

La base Render est indépendante de celle du Codespace. Sur les offres Free, la base expire après 30 jours et le service web se met en veille après 15 minutes d’inactivité.

## Vérifications manuelles

- `/health` renvoie `{"status":"ok"}`.
- Le fichier d’exemple produit 3 lignes analysées, 1 doublon et 1 cellule vide, avec un identifiant de rapport.
- Un fichier séparé par des points-virgules est analysé avec le séparateur correspondant.
- Un CSV mal formé, un fichier vide ou un fichier trop volumineux affiche un message compréhensible.
- La réinitialisation permet de sélectionner et d’analyser un autre fichier.
- `/docs` et `/design-system` restent accessibles.

Effectuer ces vérifications dans Codespaces, puis sur l’URL Render après déploiement.

## Périmètre du MVP

Le projet contrôle uniquement les cellules vides et les doublons exacts. Il ne valide pas les règles métier, les adresses e-mail ou les types de données.

L’interface affiche au maximum les **200 premiers points détectés** ; les compteurs et le rapport enregistré restent complets. Un fichier contenant uniquement des en-têtes est signalé comme ne contenant aucune ligne de données.

Les rapports sont enregistrés, mais leur consultation dans un historique reste à développer. Un rechargement de la page efface le résultat affiché, sans supprimer le rapport en base. Le MVP ne comporte pas d’authentification.

## Documentation et conventions

- [Design system](docs/design-system.md)

La documentation et l’interface sont rédigées en français. Les noms de fichiers, variables, classes, champs de l’API et identifiants techniques restent en anglais lorsque c’est logique. Les commandes et les noms officiels des outils sont conservés.
