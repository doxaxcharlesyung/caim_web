# CAIM Web

Flask migration of the CAIM website, targeting Python 3.12 and
`https://caim.doxaxsolutions.com`.

## Application structure

- `templates/layouts/` contains the shared HTML shell.
- `templates/components/` contains reusable site components.
- `templates/pages/` contains fixed website pages.
- `templates/articles/` contains database-ready article presentation templates.
- `app/routes.py` defines the public URL contract.
- `app/data.py` contains site-wide presentation settings and Traditional Chinese labels.
- `static/` contains migrated images, CSS, JavaScript, and the favicon.

This migration renders Traditional Chinese (`zh-Hant`) only. Locale selection is centralized
so approved translations can be introduced later without duplicating layouts or components.
Article templates are separate from fixed pages so MySQL can supply article records in a later
phase without storing fixed page content in the database.

## Local development

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

Open `http://127.0.0.1:8000/`.

## Production Operations

The externally accessible production server is:

- Host: `doxaxsolutions.com`
- SSH port: `14322`
- SSH user: `cyung`
- Application directory: `/opt/caim_web`

The production deployment connects to this host over SSH. It does not use the development or
intranet address `192.168.2.43`.

## Apache Virtual Hosts

- `theology.doxaxsolutions.com` is configured as a normal name-based Apache vhost on the same `*:80` and `*:443` listeners used by `www.doxaxsolutions.com`.
- The separation is by `ServerName` plus HTTPS SNI, not by separate ports.
- The `theology` vhost proxies both HTTP and HTTPS traffic to the local app on `127.0.0.1:18002`.
- HTTP on `theology.doxaxsolutions.com` redirects to HTTPS, and the SSL vhost uses its own Let's Encrypt certificate at `/etc/letsencrypt/live/theology.doxaxsolutions.com/`.

## CAIM Virtual Host

- Apache vhost templates for `caim.doxaxsolutions.com` live in [`deploy/apache/`](deploy/apache/).
- The CAIM vhost uses the same name-based vhost pattern as `theology.doxaxsolutions.com`.
- Both HTTP and HTTPS proxy to `127.0.0.1:18003`, which serves the dedicated CAIM app from `/opt/caim_web`.
- `test.doxaxsolutions.com` remains separate and is served from `/opt/test.doxaxsolutions.com` on `127.0.0.1:18000`.
- The CAIM app itself serves a host-specific home page at `/`, and the current CAIM pages are self-contained.
- The SSL vhost expects a Let's Encrypt certificate at `/etc/letsencrypt/live/caim.doxaxsolutions.com/`.

## Deployment

- GitHub Actions deploys on pushes to `main` through [.github/workflows/deploy-prod.yml](.github/workflows/deploy-prod.yml).
- The deployment workflow is intended to run on a GitHub-hosted runner and connect to the external production host over SSH port `14322`.
- It installs the Flask package, Jinja templates, static assets, WSGI entry point, and requirements into `/opt/caim_web/`, creates or updates the Python 3.12 virtual environment, installs the Apache vhost files, installs `doxax-caim-web.service`, restarts the CAIM service, runs `apachectl configtest`, reloads `httpd`, and performs a local health check.
- The test site service and content remain separate under `/opt/test.doxaxsolutions.com`.

## Production runtime

Apache terminates HTTPS and proxies to Gunicorn on `127.0.0.1:18003`. The systemd unit uses
the application-owned virtual environment at `/opt/caim_web/.venv` and starts `wsgi:app`.

## GitHub Actions secrets

Create these repository secrets before pushing deployment changes to `main`:

- `PROD_SERVER`: `doxaxsolutions.com`
- `PROD_PORT`: `14322`
- `PROD_USER`: `cyung`
- `PROD_SECRET_KEY`: a long, random value used by Flask as the production `SECRET_KEY`
- `PROD_SSH_PRIVATE_KEY`: the private SSH key authorized for the `cyung` account on the production server

`PROD_SECRET_KEY` and `PROD_SSH_PRIVATE_KEY` are different secrets and must not be reused for
each other. The workflow writes `PROD_SECRET_KEY` to `/opt/caim_web/.env` with owner-only
permissions. Do not commit any secret value to the repository or place it in this file.

No MySQL secret is required by the current migration because article database integration has
not been implemented yet. When MySQL is added, create a separate secret such as
`CAIM_DATABASE_URL` and inject it into the production environment rather than committing it.

The production server must already have Python 3.12, `sudo`, Apache, systemd, Gunicorn support
through the application virtual environment, and the Let's Encrypt certificate for
`caim.doxaxsolutions.com`. The `cyung` account must be allowed to authenticate with the SSH
private key and execute the required deployment commands through `sudo`. These are server
prerequisites, not GitHub Actions secrets.
