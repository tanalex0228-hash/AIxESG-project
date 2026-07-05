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
- `app/docker-compose.yml`: Django web, Celery worker, Redis for `fin-app`.
- `app/.env.app.example`: Django production environment template.
- `web/docker-compose.yml`: Nginx for `fin-web`.
- `web/nginx.conf`: reverse proxy to `fin-app`.

Copy each example env file to its non-example name on the target host before running the matching `deploy_*.sh` script.
