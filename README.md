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

## Cycle automatique

Le vote mensuel s'ouvre et se clôt tout seul via une commande à lancer
quotidiennement par cron :

```bash
python manage.py cycle_tick
```

## Licence

GPL-3.0. Voir [LICENSE](LICENSE).
