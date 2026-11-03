# Analyse immédiate, correction et compte par e-mail

## Le parcours

1. Le visiteur importe un CSV sans compte.
2. Il voit immédiatement ses doublons et cellules vides.
3. Il saisit son adresse sous **Recevoir une version corrigée**.
4. L’e-mail contient la pièce jointe et un lien d’accès personnel.
5. Il ouvre le lien puis confirme l’adresse affichée. C’est seulement à cette confirmation que le compte est créé, ou retrouvé s’il existe. Les rapports invités envoyés à cette adresse sont rattachés au compte.
6. Pour revenir plus tard, **Se connecter** envoie un nouveau lien. Aucun mot de passe n’est demandé dans l’interface.

La « version corrigée » supprime les doublons exacts. Les cellules vides sont conservées : aucune valeur n’est inventée. L’e-mail est transactionnel et n’inscrit à aucune liste marketing.

## Installer l’évolution

L’archive est basée sur le commit `aad245a`. Elle remplace les fichiers correspondants : examiner les modifications personnelles avec `git status --short` avant extraction.

À la racine du Codespace, après avoir déposé le ZIP :

```bash
unzip -o csv-check-email-onboarding.zip
.venv/bin/python -m app.init_db
.venv/bin/python -m pytest -q
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Arrêter Uvicorn avant l’initialisation si nécessaire. Les dépendances restent celles du projet existant. Si les outils de test ne sont pas installés : `.venv/bin/python -m pip install -r requirements-dev.txt`.

La migration additive crée `magic_links` et ajoute `guest_hash`, `claim_email` aux analyses ainsi que `verified_at` aux comptes. Elle conserve les données et peut être rejouée. Render l’exécutera au démarrage via `scripts/start.sh`.

## Configuration Resend et Render

Conserver les variables existantes :

| Variable | Valeur |
| --- | --- |
| `DATABASE_URL` | Connexion PostgreSQL fournie par Codespaces ou Render |
| `COOKIE_SECURE` | `true` pour les URL HTTPS |
| `RESEND_API_KEY` | Clé d’envoi privée, côté serveur |
| `EMAIL_FROM` | Expéditeur autorisé chez Resend |
| `APP_URL` | URL publique HTTPS de l’application, sans chemin ni fragment |

`APP_URL` doit correspondre à l’environnement testé : URL Codespaces dans `.env`, URL Render dans les variables du service. Le lien de connexion est construit à partir de cette variable, jamais depuis l’en-tête Host d’une requête.

Avec `onboarding@resend.dev`, le destinataire doit être l’adresse de votre compte Resend. Pour ouvrir la démonstration au professeur ou à d’autres utilisateurs, un domaine d’envoi validé est nécessaire. Le domaine `onrender.com` ne vous appartient pas. Désactiver le suivi des clics sur le domaine transactionnel pour conserver les liens personnels tels quels.

Sans configuration Resend, l’analyse invitée fonctionne ; les demandes d’e-mail signalent une indisponibilité. Le bouton de partage copie l’adresse publique de l’outil, sans rapport ni lien personnel.

## Vérifications avant le commit

- En navigation privée, la page d’arrivée affiche l’import de fichier, sans connexion.
- Le CSV d’exemple produit 3 lignes analysées, 1 doublon, 1 cellule vide.
- Saisir son adresse et demander la correction. Vérifier la pièce jointe : 2 lignes de données, cellule vide conservée.
- Avant de confirmer, l’historique demande une connexion. Aucun compte n’est créé simplement par la saisie de l’adresse.
- Ouvrir le lien reçu : l’adresse apparaît avec un bouton de confirmation. Confirmer ouvre une session et le rapport est retrouvé dans l’historique.
- Le même lien ne fonctionne plus après usage. Un lien non utilisé expire après quinze minutes. Le menu de connexion permet d’en recevoir un nouveau.
- Dans un autre navigateur, connaître `/#report/ID` ne permet pas d’ouvrir le rapport. Une confirmation e-mail peut cependant être effectuée sur un autre appareil, qui devient alors connecté.
- Après rattachement au compte, le cookie invité du navigateur initial ne suffit plus à ouvrir le rapport.
- « Partager CSV Check » copie uniquement l’origine publique, sans `#report` ni `#verify`.
- Une erreur d’envoi reste visible dans le résultat. Le visiteur peut réessayer ; un renvoi invité est limité à un par minute et invalide les précédents liens de ce rapport. Il peut corriger son adresse à cette occasion.
- Vérifier aussi les anciens comptes et rapports après migration.

## Commit unique

Lorsque l’initialisation, les tests et le parcours réel sont validés :

```bash
git diff --check
git add app tests docs README.md
git diff --cached --check
git diff --cached --stat
git commit -m "feat: add guest analysis and passwordless email onboarding"
git push
```

Après le déploiement Render, recharger la page avec `Ctrl+Shift+R` et refaire le parcours. Vérifier les logs d’initialisation de la base en cas d’échec.

## Fonctionnement et limites

- Les résultats invités sont protégés par un cookie aléatoire HttpOnly/Secure/SameSite strict. Seule son empreinte est en base. Un identifiant de rapport n’est jamais une autorisation.
- Les rapports historiques sans propriétaire et sans cookie invité restent inaccessibles.
- Les nouvelles importations connectées sont directement liées au compte.
- Un lien personnel contient un jeton aléatoire, stocké uniquement sous forme d’empreinte, valable quinze minutes. Le fragment est retiré de la barre d’adresse dès son ouverture. Les aperçus n’ouvrent aucune session : seule la confirmation POST consomme le lien.
- La confirmation invalide les autres liens de cette adresse. Plusieurs rapports invités déjà envoyés à cette adresse sont rattachés ensemble.
- Les anciens comptes sont retrouvés par leur adresse normalisée. À leur première confirmation par e-mail, les anciens mots de passe et sessions sont révoqués pour éviter un accès par quelqu’un qui aurait créé un compte avec une adresse non vérifiée. Les anciennes routes de mot de passe restent temporairement compatibles pour les comptes non encore migrés.
- Les envois des rapports déjà liés au compte gardent leur règle : destinataire du compte, un envoi confirmé par rapport et cinq tentatives par heure.
- Protection des mutations par `X-CSRF-Protection: 1`, sans origine CORS externe autorisée.
- Les imports invités sont limités à vingt par heure et IP ; les demandes de liens à vingt par heure et IP et cinq par adresse. Ces protections sont locales au processus, réinitialisées au redémarrage et prévues pour un seul processus Uvicorn. Selon le proxy, plusieurs visiteurs peuvent partager une limite IP. Avant une ouverture large, utiliser une limitation partagée et configurer explicitement les proxies de confiance.
- Les fichiers corrigés sont conservés dans PostgreSQL, sans purge automatique. Les invités qui ne confirment pas restent sans propriétaire de compte ; une politique de suppression reste à ajouter.
- Une réponse d’envoi perdue peut malgré tout correspondre à un e-mail reçu. Vérifier la messagerie avant de renvoyer. Chaque nouveau lien est une demande distincte ; pas de garantie d’envoi unique entre deux demandes distinctes.
- Les liens personnels et pièces jointes ne doivent pas être transférés pour promouvoir le produit : le partage utilise le lien public dédié.

## Validation de cette livraison

La syntaxe Python et JavaScript ainsi que le parcours DOM avec réponses simulées ont été vérifiés. Les tests Python couvrant les nouveaux accès invités et liens e-mail ont été ajoutés, mais n’ont pas pu être exécutés dans l’environnement de préparation, l’installation des dépendances étant bloquée par le réseau. Les exécuter dans Codespaces avant le commit. La migration PostgreSQL et la réception réelle des e-mails doivent également y être vérifiées.

## Références

- [Jetons à usage unique et expiration — OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)
- [API d’envoi Resend](https://resend.com/docs/api-reference/emails/send-email)
- [Limite du domaine resend.dev](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain)
