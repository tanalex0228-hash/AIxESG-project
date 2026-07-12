# AIxESG three-node deployment

This deployment splits AIxESG across the current servers:

- `fin-web` (`100.125.1.6`): public entrypoint, Nginx reverse proxy.
- `fin-app` (`100.72.157.21`): Django/Gunicorn, Celery worker, Redis.
- `fin-db` (`100.92.162.59`): PostgreSQL with pgvector.

Recommended directory layout on each host:

```text
/home/alex/aixesg/
  app/      # source checkout or compose files for that role
  data/     # bind mounts/backups if needed
  logs/     # service logs if not using docker logs
  secrets/  # local env files, never committed
```

Traffic flow:

```text
user -> fin-web:80 -> fin-app:8020 -> fin-db:5432
                         |
                         +-> Redis on fin-app docker network
```

## Files

- `db/docker-compose.yml`: PostgreSQL/pgvector for `fin-db`.
- `db/.env.db.example`: database secret template.
- `db/aixesg-db.service`: boot recovery service that waits for the Tailscale IP before recreating the DB container and port binding.
- `db/backup_postgres.sh`: PostgreSQL custom-format backup helper.
- `app/docker-compose.yml`: Django web, Celery worker, Redis for `fin-app`.
- `app/.env.app.example`: Django production environment template.
- `app/aixesg-app.service`: boot recovery service that waits for the Tailscale IP, starts app containers, reapplies firewall rules, and checks `/login/`.
- `app/backup_media.sh`: media volume backup helper.
- `web/docker-compose.yml`: Nginx for `fin-web`.
- `web/nginx.conf`: reverse proxy to `fin-app`.
- `web/aixesg-web.service`: boot recovery service that waits for the Tailscale IP, starts Nginx, checks `/login/`, and starts Funnel.

Copy each example env file to its non-example name on the target host before running the matching `deploy_*.sh` script.

## HTTPS and proxy headers

Tailscale Funnel terminates public HTTPS on `fin-web` and proxies to local Nginx over HTTP. Nginx forwards `X-Forwarded-Proto: https` to Django, and Django should run with:

```text
USE_X_FORWARDED_HOST=True
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## Backups

Run database backup on `fin-db`:

```bash
cd /home/alex/aixesg/db
./backup_postgres.sh
```

Run media backup on `fin-app`:

```bash
cd /home/alex/aixesg/app/source/deploy/three-node/app
./backup_media.sh
```

The scripts keep 14 days of backups by default. Set `RETENTION_DAYS` or `BACKUP_DIR` to override.

## Operational note

The shell scripts are the active deployment path on the current servers because Docker Compose was not installed when the deployment was performed. The compose files are retained as documentation and a future migration target; avoid mixing compose and shell deployments in the same maintenance operation.
