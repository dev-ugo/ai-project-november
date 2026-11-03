# CSV Check

Application web qui analyse un CSV, repère ses cellules vides et ses doublons, puis conserve un rapport privé. L’utilisateur peut demander par e-mail une version sans doublons.

Projet réalisé avec l’aide de l’IA dans le cadre d’un exercice de développement rapide.

## Fonctionnalités

- Inscription, connexion et déconnexion par adresse e-mail et mot de passe.
- Analyse de CSV UTF-8 de **1 Mio maximum**, séparés par une virgule ou un point-virgule.
- Compteurs et détail des cellules vides et des doublons exacts.
- Historique privé des **50 dernières analyses**, avec réouverture des rapports.
- Envoi, sur demande, du CSV sans doublons à l’adresse du compte connecté.
- Interface responsive, en français, et page de référence du design system.

## Technologies

| Partie | Technologies |
| --- | --- |
| API | Python 3.12, FastAPI, Uvicorn |
| Données | PostgreSQL, SQLAlchemy, Psycopg |
| Authentification | Argon2 via pwdlib, sessions opaques en cookie HttpOnly |
| Interface | HTML, CSS, JavaScript sans framework |
| E-mail | API HTTPS Resend |
| Développement et hébergement | GitHub Codespaces, Render |

## Démarrer dans Codespaces

L’environnement `.devcontainer` fournit Python, PostgreSQL et `DATABASE_URL`.
Depuis la racine du dépôt :

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
cp -n .env.example .env
.venv/bin/python -m app.init_db
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Ouvrir l’URL **HTTPS** du port 8000, créer un compte et importer le CSV d’exemple.
Sur un accès local en HTTP uniquement, définir `COOKIE_SECURE=false` dans `.env`.
Les variables déjà définies dans l’environnement ont priorité sur `.env`.

`app.init_db` crée les tables absentes et applique l’évolution additive de l’historique privé.
La commande peut être rejouée. Elle ne supprime aucune analyse et n’est pas un système général de migrations.

## Utilisation et règles

1. Créer un compte ou se connecter (mot de passe de 12 à 128 caractères).
2. Choisir le fichier et son séparateur, puis lancer l’analyse.
3. Lire les compteurs et les points à vérifier.
4. Facultativement, demander **Recevoir le CSV corrigé par e-mail**.
5. Retrouver le rapport dans **Mon historique**, y compris après rechargement.

Le fichier d’exemple contient 3 lignes de données, 1 doublon et 1 cellule vide.

Les en-têtes doivent être non vides et uniques. Chaque enregistrement doit avoir le bon nombre de colonnes. Une cellule vide contient une valeur absente ou uniquement des espaces. Un doublon est une répétition exacte de toutes les valeurs d’une ligne ; la première occurrence est conservée. La casse et les espaces ne sont pas normalisés.

Les lignes complètement vierges et l’en-tête sont exclus du nombre de lignes analysées. Les numéros affichés correspondent aux lignes physiques du CSV, en comptant l’en-tête ; un enregistrement multiligne est repéré par sa première ligne.

La **correction supprime seulement les doublons exacts** et ignore les lignes vierges. Elle conserve les valeurs restantes, les cellules vides, l’ordre des lignes et le séparateur. Le CSV est réexporté en UTF-8 avec BOM et fins de ligne CRLF ; sa mise en forme peut donc changer. Aucune donnée manquante n’est inventée. Le rapport décrit toujours le fichier initial.

## API

| Méthode | Route | Accès et rôle |
| --- | --- | --- |
| `GET` | `/` | Interface publique, espace de travail après connexion |
| `POST` | `/auth/register` | Inscription et ouverture de session |
| `POST` | `/auth/login` | Connexion |
| `GET` | `/auth/me` | Identité du compte connecté |
| `POST` | `/auth/logout` | Révocation de la session |
| `POST` | `/analyses` | Analyser un CSV pour le compte connecté |
| `GET` | `/analyses` | 50 derniers rapports du compte connecté |
| `GET` | `/analyses/{id}` | Détail d’un rapport appartenant au compte |
| `POST` | `/analyses/{id}/email` | Envoi de sa correction à l’adresse du compte |
| `GET` | `/health` | Disponibilité de l’application, sans contrôle de la base |
| `GET` | `/docs` | Documentation interactive de l’API |
| `GET` | `/design-system` | Référence des composants, sans appels API |

Les routes `POST` exigent l’en-tête `X-CSRF-Protection: 1`. L’interface l’ajoute automatiquement. Dans `/docs`, saisir `1` dans ce champ. La connexion effectuée depuis la page `/` vaut aussi dans `/docs` sur la même origine. Aucune origine CORS externe n’est autorisée : ne pas ajouter une autorisation générale avec cookies.

`POST /analyses` reçoit le champ multipart `file` et le paramètre de requête `delimiter` (`,` ou `;`). Il répond `201`. Sans session, les routes d’analyse répondent `401` ; un rapport absent ou appartenant à un autre compte répond `404`. Le destinataire d’un e-mail vient toujours du compte, jamais d’un paramètre de la requête.

## Base de données

| Table | Contenu |
| --- | --- |
| `users` | Adresse unique normalisée en minuscules, mot de passe haché, date, compteur d’envois |
| `user_sessions` | Empreinte du jeton de session, propriétaire et expiration |
| `analyses` | Propriétaire, nom de fichier, date, compteurs, anomalies JSON, CSV corrigé et date de transmission par e-mail |

Les sessions durent sept jours et sont révoquées lors de la déconnexion. Seule une empreinte du jeton aléatoire est stockée en base. Les réponses privées portent `Cache-Control: no-store`.

Les anciens rapports restent en base avec `user_id=NULL` : aucun utilisateur ne peut les consulter. Ils ne sont pas attribués automatiquement au premier inscrit. Les anciennes données originales n’existent pas en base ; réimporter un CSV permet de créer un nouveau rapport privé et sa correction.

Le fichier original n’est pas conservé. **Sa version corrigée est conservée dans PostgreSQL**, avec le rapport, sans purge automatique. L’envoi demandé transmet cette version et l’adresse du compte à Resend. Les administrateurs de la base conservent naturellement l’accès aux données stockées.

## Configuration des e-mails et déploiement

Voir le [guide d’intégration](docs/auth-history-email.md) pour les étapes complètes et le commit unique.

| Variable | Valeur attendue |
| --- | --- |
| `DATABASE_URL` | Connexion PostgreSQL, déjà fournie par Codespaces/Render |
| `COOKIE_SECURE` | `true` en HTTPS ; `false` uniquement en HTTP local |
| `RESEND_API_KEY` | Clé privée Resend, uniquement côté serveur |
| `EMAIL_FROM` | Expéditeur autorisé chez Resend |
| `APP_URL` | URL publique de CSV Check, utilisée dans l’e-mail |

Sans configuration e-mail, les comptes et analyses fonctionnent ; une demande d’envoi répond `503` avec un message explicite. Une transmission acceptée par Resend ne garantit pas la réception finale : vérifier les indésirables ou le tableau de bord du prestataire.

Un seul envoi confirmé est autorisé par analyse, et cinq tentatives par compte sur une fenêtre d’une heure. Une clé d’idempotence stable limite les doublons en cas de nouvelle tentative après un incident (garantie Resend limitée à 24 heures). L’envoi est synchrone, sans file de tâches ni relance automatique.

Sur Render, conserver `pip install -r requirements.txt` comme commande de build et `bash scripts/start.sh` comme commande de démarrage. Le script prépare la base avant Uvicorn. Ajouter les variables e-mail dans **Environment**, puis déployer le commit. Le Blueprint transmet déjà `DATABASE_URL` et définit le cookie sécurisé.

Le premier déploiement peut prendre plus de temps pour installer Argon2. La base Render est distincte de celle du Codespace. Les limitations de l’offre gratuite restent applicables, notamment l’expiration de PostgreSQL après 30 jours.

## Organisation

| Emplacement | Rôle |
| --- | --- |
| `app/main.py` | Application, routes, fichiers statiques et en-têtes de réponse |
| `app/config.py`, `app/database.py` | Configuration et connexion PostgreSQL |
| `app/init_db.py` | Initialisation et évolution additive du schéma |
| `app/auth.py` | Sessions, hachage, protection CSRF et limitation des tentatives |
| `app/models/` | Modèles des comptes, sessions et analyses |
| `app/routers/` | Routes de compte, d’analyse et pages de référence |
| `app/services/` | Analyse, correction du CSV et envoi d’e-mail |
| `app/templates/`, `app/static/` | Interface et design system |
| `tests/` | Tests isolés de l’API et de la correction |
| `docs/` | Documentation française |
| `.devcontainer/`, `render.yaml`, `scripts/` | Codespaces et déploiement |

## Tests

```bash
.venv/bin/python -m pytest -q
```

Les tests utilisent une base SQLite temporaire et des réponses e-mail simulées : aucune donnée réelle n’est modifiée, aucun message n’est envoyé. Ils couvrent les sessions, la protection CSRF, les deux comptes distincts, les rapports sans propriétaire, les règles CSV, les pièces jointes et les échecs d’envoi. Ils ne reproduisent pas les verrous concurrents PostgreSQL ni la délivrabilité réelle.

Tester aussi dans Codespaces puis sur Render : inscription, analyse de l’exemple, historique après rechargement, déconnexion, second compte sans accès au premier rapport, puis réception d’un e-mail réel après configuration. `/health`, `/docs` et `/design-system` doivent rester accessibles.

## Limites du projet pédagogique

Le projet vérifie uniquement les cellules vides et doublons exacts, sans validation métier. L’interface affiche les 200 premières anomalies, les compteurs et le rapport restent complets.

Cette version ne comprend pas encore la confirmation de propriété de l’adresse e-mail, la récupération du mot de passe, la suppression de compte ou la purge des fichiers. Les protections contre les tentatives de connexion répétées sont locales au processus, réinitialisées au redémarrage, et adaptées au lancement Uvicorn avec un seul processus. Ce n’est pas un service prêt pour une ouverture publique à grande échelle.

## Documentation et conventions

- [Design system](docs/design-system.md)
- [Comptes, historique privé et e-mails](docs/auth-history-email.md)

Interface et documentation en français ; identifiants techniques et messages de commit en anglais lorsque c’est logique.
