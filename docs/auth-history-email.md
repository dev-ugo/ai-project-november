# Intégrer les comptes, l’historique privé et les e-mails

Cette évolution remplace l’historique public par un espace personnel et ajoute l’envoi du CSV sans doublons. Un seul commit regroupe le code, les tests et la documentation.

## 1. Installer les fichiers dans le Codespace

L’archive est préparée à partir du commit `3c174ee` (`add: display history`). Elle contient uniquement les fichiers ajoutés ou modifiés, avec les chemins du dépôt. Elle ne contient ni secret, ni base de données, ni environnement virtuel.

Depuis la racine du dépôt, vérifier `git status --short`. Si des modifications personnelles sont présentes, les examiner avant d’extraire : l’archive remplace les fichiers portant le même nom. Glisser l’archive téléchargée dans l’explorateur du Codespace, à la racine, puis :

```bash
unzip -o csv-check-accounts.zip
.venv/bin/python -m pip install -r requirements-dev.txt
cp -n .env.example .env
```

Ne pas ajouter `.env` au suivi Git. Il est déjà ignoré. `cp -n` conserve un éventuel fichier `.env` existant.

## 2. Préparer la base existante

Arrêter Uvicorn avec `Ctrl+C` dans son terminal, puis :

```bash
.venv/bin/python -m app.init_db
```

La commande crée `users` et `user_sessions`, puis ajoute à `analyses` le propriétaire, le CSV corrigé, une clé d’envoi et sa date. Une transaction et un verrou PostgreSQL protègent l’exécution. La commande est rejouable et le script de démarrage Render l’exécutera également.

Les rapports antérieurs sont conservés sans propriétaire et ne figurent dans aucun historique. Aucun rapport n’est partagé ni attribué à un compte lors de l’inscription. Une nouvelle importation est nécessaire pour obtenir sa version corrigée.

## 3. Configurer Resend

Render Free bloque les ports SMTP habituels : l’application appelle l’API HTTPS de Resend.

1. Créer un compte sur [Resend](https://resend.com/).
2. Dans **API Keys**, créer une clé disposant du droit d’envoi. La garder côté serveur.
3. Pour une démonstration sans domaine, utiliser `CSV Check <onboarding@resend.dev>` comme expéditeur. Le destinataire doit alors être **l’adresse du compte Resend** : créer le compte CSV Check avec cette même adresse.
4. Pour envoyer aux adresses d’autres utilisateurs, ajouter un domaine dans **Domains**, publier les enregistrements DNS demandés et attendre sa validation. Utiliser ensuite une adresse de ce domaine comme expéditeur. Le domaine `onrender.com` ne vous appartient pas et ne peut pas servir à cette validation.
5. Renseigner `.env` dans Codespaces, sans coller la clé dans Git ni dans le navigateur :

```dotenv
COOKIE_SECURE=true
RESEND_API_KEY=re_VOTRE_CLE_PRIVEE
EMAIL_FROM=CSV Check <onboarding@resend.dev>
APP_URL=https://VOTRE-URL-CODESPACES
```

Remplacer les exemples par les valeurs réelles. Pour un domaine validé, changer aussi `EMAIL_FROM`.
`APP_URL` est l’origine de l’application, sans `/docs` ni `/analyses`. Aucun secret de signature de session n’est nécessaire : les sessions utilisent des jetons aléatoires stockés sous forme d’empreintes en base.

On peut laisser la configuration e-mail vide et tester les comptes et l’analyse d’abord. Le bouton d’envoi indiquera alors que le service n’est pas configuré.

## 4. Lancer et vérifier

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Ouvrir le port 8000 via son URL HTTPS, et vérifier dans cet ordre :

1. Créer un compte A ; un mot de passe doit contenir 12 à 128 caractères.
2. Analyser le CSV d’exemple : **3 lignes, 1 doublon, 1 cellule vide**.
3. Recharger la page : la session et l’historique sont retrouvés. Ouvrir le rapport.
4. Cliquer sur le bouton d’envoi. Le CSV reçu contient **2 lignes de données et la cellule vide conservée**. Le bouton devient indisponible une fois l’envoi accepté. Vérifier les indésirables si nécessaire.
5. Se déconnecter et créer un compte B (une autre adresse). Son historique doit être vide.
6. Depuis `/docs`, connecté au compte B, appeler `GET /analyses/{id}` avec l’identifiant du rapport A : réponse **404**. Pour `POST /analyses/{id}/email`, saisir `1` dans `x-csrf-protection` : réponse **404** également.
7. Sans connexion, `GET /analyses` doit répondre **401**.
8. Vérifier `/health`, `/docs`, `/design-system` et l’affichage sur une fenêtre étroite.

L’e-mail est envoyé uniquement à l’adresse du compte, sur clic explicite. Il contient le fichier en pièce jointe, un résumé et un lien vers l’outil que l’utilisateur peut partager. Il ne rend pas le rapport public.

Le contrôle d’accès côté API est couvert par les tests, indépendamment du masquage de l’interface.

## 5. Créer le seul commit

Quand les tests et la vérification locale sont terminés :

```bash
git diff --check
git add app tests docs README.md requirements.txt requirements-dev.txt render.yaml .env.example
git diff --cached --stat
git diff --cached --check
git commit -m "feat: add accounts private history and corrected CSV emails"
git push
```

Ne pas créer de commit intermédiaire. Les archives ZIP et `.env` restent ignorés.

## 6. Configurer et vérifier Render

Dans le service web existant, ouvrir **Environment** et ajouter :

| Variable | Valeur |
| --- | --- |
| `COOKIE_SECURE` | `true` |
| `RESEND_API_KEY` | La clé privée Resend |
| `EMAIL_FROM` | L’expéditeur autorisé |
| `APP_URL` | L’URL HTTPS Render de l’application |

Conserver `DATABASE_URL` déjà configurée. Ces variables sont des paramètres du service, pas du code à committer. Enregistrer puis redéployer si nécessaire. Le push déclenche aussi le déploiement automatique habituel.

Conserver la commande de build `pip install -r requirements.txt` et le démarrage `bash scripts/start.sh`. Vérifier dans les logs le message **Base prête. Tables :** puis le démarrage Uvicorn. Si la migration échoue, le script s’arrête : corriger l’erreur au lieu de supprimer les tables.

Créer de nouveau les comptes de test sur Render : la base est indépendante de Codespaces. Refaire les vérifications du point 4 sur cette URL. L’envoi réel ne peut être validé qu’avec vos paramètres Resend et votre messagerie.

## Choix et limites

- Cookie HttpOnly, Secure en HTTPS, SameSite strict ; sessions de sept jours révocables.
- Mots de passe hachés avec Argon2 ; aucun mot de passe brut en base.
- En-tête `X-CSRF-Protection: 1` exigé pour les mutations et aucune origine CORS externe autorisée.
- Liste, détail et envoi filtrés par propriétaire. Les utilisateurs ne voient pas les rapports d’autres comptes ; l’administrateur de la base garde accès aux données.
- Historique limité aux 50 dernières analyses, sans pagination dans cette version.
- Version corrigée conservée en PostgreSQL ; fichier original non conservé. Pas encore de purge automatique.
- Une correction supprime les doublons exacts et les lignes vierges. Les autres valeurs, y compris les cellules vides, sont conservées. Réexport UTF-8 avec BOM et CRLF.
- Un envoi accepté par analyse ; cinq tentatives par heure et par compte. Le serveur utilise des verrous PostgreSQL pour sérialiser les envois d’un compte.
- Clé d’idempotence stable côté Resend, valable 24 h. Après un délai réseau ambigu, regarder la messagerie avant de retenter. Sans file de tâches durable, une interruption de processus ou une relance après 24 h peut encore créer un doublon.
- La mention « transmis au service d’e-mail » ne garantit pas une réception en boîte de réception.
- Pas encore de vérification de propriété d’adresse e-mail, de mot de passe oublié ou de suppression de compte. Pour la démonstration, utiliser vos propres adresses.
- Limitation des essais de connexion en mémoire, prévue pour un seul processus ; réinitialisée au redémarrage. Ne pas ajouter de multiples workers sans la remplacer par une limitation partagée.

## Vérifications effectuées lors de la préparation

- 17 tests Python/API réussis sur SQLite isolée, sans envoi réel.
- Parcours JavaScript vérifié avec un DOM et des réponses simulées : compte, historique, rapport, double clic, envoi, expiration, déconnexion et erreurs.
- SQL d’initialisation et d’évolution exécuté sur PostgreSQL embarqué (PGlite) : base neuve, ancien schéma avec rapport conservé, seconde exécution et contrainte de propriétaire.
- Le fonctionnement de l’hébergement Render, les verrous entre plusieurs connexions PostgreSQL et la réception réelle d’un e-mail restent à valider dans votre environnement.

## Références

- [Limitations de Render Free](https://render.com/docs/free)
- [Envoi et pièces jointes avec Resend](https://resend.com/docs/api-reference/emails/send-email)
- [Limite du domaine de test resend.dev](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain)
- [Clés d’idempotence Resend](https://resend.com/docs/dashboard/emails/idempotency-keys)
- [Hachage des mots de passe dans FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
