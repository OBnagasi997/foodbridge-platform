# Projet 1 : pipeline CI/CD

**Ce que ça prouve** : du `git push` à une image testée, scannée et publiée, sans intervention manuelle,
avec une chaîne d'approvisionnement que l'on sait défendre.

## Stack

| Rôle | Outil |
|---|---|
| Application | FastAPI + React (deux images) |
| CI/CD | GitHub Actions (`.github/workflows/ci.yml`) |
| Registre | GitHub Container Registry (GHCR) |
| Lint / types | Ruff (backend), `tsc` (frontend) |
| Tests | pytest sur **PostgreSQL réel** (service du runner), Vitest |
| Sécurité | Trivy (échec sur CRITICAL), contrôle non-root, Dependabot |

## Ce que fait le pipeline

```
push / pull request
 ├─ backend  : Ruff → alembic upgrade → alembic check (dérive) → pytest (Postgres réel)
 ├─ frontend : npm ci → tsc → Vitest → build
 └─ images (×2, après backend + frontend)
      build (tag = SHA) → taille < limite → non-root → Trivy (CRITICAL = échec) → rapport en artefact
      └─ push sur main / tag v*.*.* seulement
           └─ publish : charge l'image scannée → docker push GHCR  (seul job avec packages: write)
 └─ ci-passed : un seul contrôle à rendre obligatoire
```

Points de conception :

- **Ce qui est publié est ce qui a été scanné.** L'image est transmise d'un job à l'autre sous forme d'archive,
  jamais reconstruite.
- **Moindre privilège.** Permissions par défaut : lecture seule. Seul `publish` peut écrire sur GHCR, et il
  n'exécute aucune action tierce. Le job qui exécute Trivy ne peut rien publier.
- **Aucun mot de passe stocké.** GHCR est atteint avec le `GITHUB_TOKEN` éphémère du workflow.
- **`alembic check` en CI** : échoue si un modèle a changé sans migration.
- **Un seul contrôle obligatoire** (`CI passed`) : les noms de jobs en matrice changent, celui-ci reste stable.
- **Tags** : `<sha>` toujours ; `latest` sur `main` ; `1.2.3` quand on pousse le tag `v1.2.3`.

## Sécurité de la chaîne d'approvisionnement (à savoir raconter en entretien)

Le **19 mars 2026**, un attaquant disposant d'identifiants volés a redirigé **76 des 77 tags** de
`aquasecurity/trivy-action` vers du code qui exfiltrait les secrets des pipelines. L'outil de sécurité du PDF a
donc été retourné contre ses utilisateurs. Seul le tag `0.35.0` est resté sain (release immuable). Sources :
l'avis `GHSA-69fq-xp46-6x23` d'Aqua Security et les analyses de StepSecurity et Snyk.

Ce que le pipeline en retient :

| Mesure | Où |
|---|---|
| Action tierce épinglée par **SHA de commit** (un tag est modifiable, un SHA non) | `ci.yml`, étape Trivy |
| Une seule action tierce ; build et push Docker en simples commandes | `ci.yml` |
| Permissions minimales ; l'action tierce n'a jamais `packages: write` | `permissions:` |
| Mises à jour d'actions proposées par Dependabot, **relues** avant fusion | `dependabot.yml` |

Versions d'actions vérifiées le 11 novembre 2026 (`checkout`, `setup-python`, `setup-node`, `upload-artifact`
en v7, `download-artifact` en v8). Les actions officielles `actions/*` sont référencées par tag majeur ;
vérifier les nouvelles majeures sur la page de chaque action.

## Mise en route (une seule fois)

1. Créer le dépôt GitHub et pousser le code (`git push -u origin main`).
2. Onglet **Actions** : le premier run démarre. Lire chaque job, noter les durées.
3. **Settings → Branches → Add rule** sur `main` : exiger une pull request et le contrôle **`CI passed`**.
4. **Settings → Actions → General → Workflow permissions** : « Read repository contents ».
5. Après le premier push sur `main`, GHCR contient deux paquets privés (`foodbridge-backend`, `foodbridge-frontend`).
   Pour les tirer depuis Kubernetes au projet 3, les rendre publics ou créer un `imagePullSecret`.
6. Tester les tags sémantiques : `git tag v0.1.0 && git push origin v0.1.0`.
7. Ajouter le badge en tête du README (remplacer `OWNER/REPO`) :
   `![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)`

### Mesurer les images avant de pousser

```bash
docker build -t fb-backend ./backend && docker build -t fb-frontend ./frontend
docker images | grep fb-
docker image inspect fb-backend --format '{{.Config.User}}'    # doit afficher "app"
```

Les limites (backend 200 Mo, frontend 100 Mo) sont dans la matrice de `ci.yml`. **Le backend est une estimation
à ~185 Mo non confirmée** : si la CI échoue sur la taille, mesurer et soit optimiser, soit ajuster la limite en
le documentant.

## Comment surveiller

- Onglet **Actions** : durée de chaque job et étape en échec. Une durée qui grimpe signale souvent un cache perdu.
- **Résumé du run** : taille et utilisateur de chaque image, rapport Trivy.
- **Artefacts** : `trivy-backend` et `trivy-frontend` (30 jours).
- Notifications d'échec : e-mail GitHub par défaut ; Slack ou Discord via webhook en option.
- Dependabot : onglet **Pull requests**, une fois par semaine.

## Ce qui va casser et comment le réparer

| Symptôme | Cause probable | Réparation |
|---|---|---|
| Les tests passent en local, échouent en CI | Dépendance absente de `requirements.txt`, ou variable d'environnement manquante | Reproduire dans un venv vierge (`pip install -r requirements-dev.txt`) |
| `alembic check` échoue | Un modèle a changé sans migration | `make revision m="..."`, relire la migration, committer |
| `denied: permission_denied` au push GHCR | `packages: write` absent du job `publish`, ou dépôt/paquet restreint | Vérifier le bloc `permissions` et les réglages du paquet |
| Trivy échoue sur une CRITICAL | Image de base ou dépendance obsolète | Mettre à jour l'image de base ou la dépendance, reconstruire |
| Trivy : `TOOMANYREQUESTS` au téléchargement de la base | Limite de débit du registre GHCR | Miroir déjà configuré (`TRIVY_DB_REPOSITORY`) ; relancer le job |
| `Image trop lourde` | Dépendance volumineuse (ex. `phonenumbers` : 46 Mo, d'où `phonenumberslite`) | `du -sm` sur le venv, retirer ou remplacer le paquet |
| `L'image tourne en root` | `USER` absent du Dockerfile | Ajouter l'utilisateur dédié et `USER` |
| Le conteneur démarre mais l'API est injoignable | Écoute sur `127.0.0.1` | `uvicorn --host 0.0.0.0` (déjà fait) |
| `ci-passed` rouge alors que tout semble vert | Un job a été ignoré (`skipped`) car un amont a échoué | Corriger le job amont |
| Un secret apparaît dans les logs | `echo` d'une variable, secret passé en argument | GitHub Secrets (masqués), révoquer le secret exposé |

## Limites assumées

- **Le build Docker, Trivy et le push GHCR n'ont pas pu être exécutés lors de la conception** (pas de Docker dans
  l'environnement de développement). Le workflow a été validé par `actionlint`, et ses jobs backend et frontend
  rejoués à l'identique en environnement vierge. Le premier run réel sur GitHub est la vraie validation.
- La version de Trivy utilisée est celle embarquée par l'action épinglée ; à réviser quand Dependabot propose une mise à jour.
- Pas de cache de couches Docker : chaque build repart de zéro (simple et reproductible, un peu plus lent).
- Pas encore de déploiement : il arrive avec les projets 2 (Terraform) et 3 (Kubernetes).

## Checklist de fin

- [ ] Un push sur `main` produit deux images taguées par SHA sur GHCR
- [ ] Une pull request avec un test cassé est bloquée (protection de branche + `CI passed`)
- [ ] Le pipeline échoue quand je casse volontairement une règle (test, lint, migration manquante)
- [ ] Les images tournent en non-root et respectent les limites de taille
- [ ] Le rapport Trivy est disponible en artefact
- [ ] Le badge du pipeline est vert dans le README
- [ ] Au moins une panne rencontrée et réparée est documentée dans `docs/troubleshooting.md`
- [ ] Je sais expliquer l'incident Trivy de mars 2026 et ce que le pipeline en tire
