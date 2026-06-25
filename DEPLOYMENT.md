# Deployment

This project is prepared for a Django production deploy on Render-style Python
hosting.

## Render blueprint

1. Push this repository to GitHub.
2. In Render, create a new Blueprint from this repo.
3. Render will read `render.yaml`, create a web service and Postgres database,
   run `./build.sh`, run migrations, then start:

```bash
python3 -m gunicorn monprojet.wsgi:application --log-file -
```

## Manual web service settings

If you do not use `render.yaml`, use:

```bash
Build Command: ./build.sh
Pre-Deploy Command: python3 manage.py migrate
Start Command: python3 -m gunicorn monprojet.wsgi:application --log-file -
```

Required environment variables:

```bash
DEBUG=False
SECRET_KEY=<generate a secure value>
DATABASE_URL=<hosted Postgres URL>
```

For custom domains, also set:

```bash
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

## Media uploads

Static files are handled by WhiteNoise after `collectstatic`.

User-uploaded files under `media/` need persistent storage in production. Use a
host persistent disk mounted at `media/`, or move uploads to object storage such
as S3-compatible storage before relying on this for real candidate documents.

For local testing with the existing virtualenv:

```bash
PYTHON_BIN=.venv/bin/python ./build.sh
```
