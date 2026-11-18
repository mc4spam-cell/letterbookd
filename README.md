# letterbookd

Outil de club de lecture privé. Voir [CLAUDE.md](CLAUDE.md), [docs/PLAN.md](docs/PLAN.md), [docs/ANALYSE.md](docs/ANALYSE.md).

## Démarrage local

```bash
cp .env.example .env
docker compose up --build
```

L'application est servie sur <http://localhost/> via Caddy.

## Développement

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python manage.py migrate
python manage.py runserver
```

Tests :

```bash
pytest
ruff check .
```

## Sauvegardes

Sauvegarde nocturne chiffrée de PostgreSQL (à lancer par cron sur l'hôte) :

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gpg --symmetric --cipher-algo AES256 \
  > "backup-$(date +%F).sql.gpg"
```

Restauration (à tester une fois avant mise en service) :

```bash
gpg --decrypt backup-YYYY-MM-DD.sql.gpg \
  | docker compose exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB"
```

## Cycle automatique

Le vote mensuel s'ouvre et se clôt tout seul via une commande à lancer
quotidiennement par cron :

```bash
python manage.py cycle_tick
```

## Licence

GPL-3.0. Voir [LICENSE](LICENSE).
