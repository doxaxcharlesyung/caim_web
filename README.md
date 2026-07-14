# CAIM Web

Flask migration of the CAIM website, targeting Python 3.12 and
`https://caim.doxaxsolutions.com`.

## Repository identity

This is the personal CAIM Web migration repository, separate from the other CAIM/Astro and
DX Sermon repositories:

- GitHub repository: `doxaxcharlesyung/caim_web`
- Remote: `https://github.com/doxaxcharlesyung/caim_web.git`
- Default branch: `main`
- Production site: `https://caim.doxaxsolutions.com`
- Production deployment: `.github/workflows/deploy-prod.yml`

Keep repository-specific deployment changes, content snapshots, and rollback tags here. Do not
assume that workflows, secrets, databases, or deployment paths from the other repositories apply
to this personal repository.

## Application structure

- `templates/layouts/` contains the shared HTML shell.
- `templates/components/` contains reusable site components.
- `templates/pages/` contains fixed website pages.
- `templates/articles/` contains database-ready article presentation templates.
- `app/routes.py` defines the public URL contract.
- `app/data.py` contains site-wide presentation settings and Traditional Chinese labels.
- `static/` contains migrated images, CSS, JavaScript, and the favicon.

The public application supports Traditional Chinese (`zh-Hant`), English (`en`), French (`fr`),
Spanish (`es`), and Simplified Chinese (`zh-Hans`). The shared header exposes the language
selector on every public page. The selected locale is retained in the session and can also be
specified with `?lang=<locale>`.

All five supported locales are enabled in the public site and Content Manager. Every public design
or content migration must include Traditional Chinese, English, French, Spanish, and Simplified
Chinese before it is considered complete.

### Francis v3 public-site authority

The Astro delivery at `D:\workspace\caim-website-francis-v3\src\pages` is the authoritative
source for public-page Traditional Chinese wording, page structure, assets, and page-specific
formatting. `scripts/extract_astro_styles.mjs` extracts its global, component, and page styles into
`static/css/v3`; rerun that script whenever the v3 Astro CSS changes instead of manually copying
individual rules. Flask templates preserve the v3 DOM and visual classes while replacing Astro's
static collections with approved, scheduled MySQL content.

Fixed public-page copy is translated through `app/i18n.py` and the checked-in UTF-8
`app/static_translations.json` catalog. Run `python scripts/build_static_translations.py` after
adding new Traditional Chinese template copy, then review prominent wording and run the complete
test suite. Database-managed articles, news, and courses remain subject to independent review and
approval per language; an unapproved translation deliberately falls back to the approved original.

All future public UI, navigation, accessibility labels, validation messages, and fixed-page copy
must ship in all five supported languages in the same change. A feature is not complete if it
introduces untranslated public text. Tests must cover UTF-8 rendering whenever Chinese copy is
added or changed. Templates and source files remain UTF-8, HTTP responses use UTF-8, and MySQL
connections/tables use `utf8mb4` so Traditional and Simplified Chinese are stored without loss.

## Local development

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

Open `http://127.0.0.1:8021/`.

## MySQL content migration

The site content imported from the Astro source is stored in MySQL. Local development expects
the following variables in `.env`:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=caimadmin
DB_PASSWORD=replace-with-the-database-password
DB_NAME=caimdb
TRANSLATION_API_URL=https://your-translation-service.example/translate
TRANSLATION_API_KEY=replace-with-the-service-key
```

`TRANSLATION_API_URL` must expose a LibreTranslate-compatible JSON endpoint for English, French,
and Spanish translation. The API key is optional when that service does not require one.
Traditional/Simplified Chinese conversion is performed locally with OpenCC and does not call the
external service.

After creating the database and user, import or refresh content from the Astro project with:

```powershell
.venv\Scripts\python scripts\import_astro_content.py --astro-root D:\workspace\caim-website-francis-v2
```

For a fresh production MySQL instance, run the idempotent bootstrap script with a MySQL
administrator account. The administrator password must be supplied only through the environment
or a protected env file; it is not the application database password:

```powershell
$env:MYSQL_ADMIN_HOST='127.0.0.1'
$env:MYSQL_ADMIN_USER='root'
$env:MYSQL_ADMIN_PASSWORD='your-mysql-admin-password'
.venv\Scripts\python scripts\create_prod_database.py
```

On Linux servers where the MySQL administrator is available only through a Unix socket, set
`MYSQL_ADMIN_SOCKET` instead of using `MYSQL_ADMIN_HOST` and `MYSQL_ADMIN_PORT`, for example
`/var/lib/mysql/mysql.sock`.

The script creates `caimdb`, creates/grants `caimadmin`, applies [schema.sql](D:/workspace/caim_web/scripts/schema.sql),
and seeds the initial hashed `admin` user. It is safe to run again on an existing database.

The import is repeatable. It creates the schema and updates courses, articles, page content,
navigation, news, services, leaders, testimonials, and DX Sermon tool collections. The public
course and article pages read these records at request time.

The committed [content_snapshot.json](D:/workspace/caim_web/scripts/content_snapshot.json) is
generated from the local development database and is imported into PROD by the GitHub Actions
deployment after schema migration. Refresh it before a content release with:

```powershell
.venv\Scripts\python scripts/export_content_snapshot.py --output scripts/content_snapshot.json
```

The snapshot contains content only; it excludes `admin_users` and all secrets.

Run the database-backed route tests with:

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

## Content Manager

The content-management application is separated from the public CAIM layout under `/content`.
Its authenticated entry point is `/content/content-manager`; successful login lands on
`/content/content-dashboard`. Administrator accounts and password hashes are stored in the
`admin_users` MySQL table. The initial migration seeds user `admin`; change its initial password
immediately through `/content/users`.

The dashboard provides navigation for three managed content groups:

- Articles: `/content/articles` and `/content/article-studio`
- Courses and workshop/events: `/content/courses` and `/content/course-studio`
- News and events: `/content/news` and `/content/news-studio`

Each library provides search, six tiles per page, pagination, Saved/Posted/Expired statuses,
scheduled posting, and soft deletion. Article Studio retains document extraction and Hero image
upload. Course Studio manages the existing public `/courses/` listing and detail pages, with
workshops classified as `event`. News Studio manages normalized records imported from the Astro
`src/data/news.ts`; posted news is shown on the CAIM home page.

Expired and Deleted records are hidden from public pages. Deleted records remain in MySQL for
manual review and physical deletion by a database administrator. Legacy `/article-dashboard/`
and `/article-studio/` GET URLs redirect to the new content manager.

### Multilingual content workflow

- Every article, course/workshop, and news/event record stores its `original_locale`.
- The content library marks the original language and shows the Saved, Review, or Posted state of
  each available translation.
- The original language must complete its own reviewer approval before the one-button translation
  action is enabled.
- One-button translation generates every missing supported language from the approved original in
  one operation. Each generated row enters Review in `content_translations`; it never overwrites
  the original record or an existing translation.
- Each language is submitted, reviewed, approved, scheduled, and posted independently. Approval
  of one language does not approve any other language.
- Reviewers use the language tabs in the library and studio to inspect and approve the selected
  language. Only Posted translations whose scheduled time has arrived are visible publicly.
- A missing or unapproved translation falls back to the approved original-language content. Once
  that requested language is separately approved and Posted, the public page automatically uses
  the translated version instead.
- Content snapshots include `original_locale` and `content_translations`, preserving multilingual
  content and publication state during production deployment.
- `scripts/approve_existing_original_content.py` is a guarded one-time migration for legacy base
  content. It marks the articles, courses, and news that existed at migration time as approved and
  Posted, while leaving Expired/Deleted records and every translated version unchanged. Its database
  marker prevents future drafts from being approved by later deployments.

For an existing installation, apply the dashboard migration once:

```powershell
.venv\Scripts\python scripts\migrate_article_dashboard.py
```

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
- HTTP redirects permanently to HTTPS; the HTTPS vhost proxies to `127.0.0.1:8021`, which serves the dedicated CAIM app from `/opt/caim_web`.
- `test.doxaxsolutions.com` remains separate and is served from `/opt/test.doxaxsolutions.com` on `127.0.0.1:18000`.
- The CAIM app itself serves a host-specific home page at `/`, and the current CAIM pages are self-contained.
- The SSL vhost expects a Let's Encrypt certificate at `/etc/letsencrypt/live/caim.doxaxsolutions.com/`.

## Deployment

- GitHub Actions deploys on pushes to `main` through [.github/workflows/deploy-prod.yml](.github/workflows/deploy-prod.yml).
- The deployment workflow is intended to run on a GitHub-hosted runner and connect to the external production host over SSH port `14322`.
- It installs the Flask package, Jinja templates, static assets, WSGI entry point, and requirements into `/opt/caim_web/`, creates or updates the Python 3.12 virtual environment, installs the Apache vhost files, installs `doxax-caim-web.service`, restarts the CAIM service, runs `apachectl configtest`, reloads `httpd`, and performs a local health check.
- The test site service and content remain separate under `/opt/test.doxaxsolutions.com`.
- The production runtime environment is represented by [deploy/prod.env.example](D:/workspace/caim_web/deploy/prod.env.example).
  The populated file belongs only on the production server at `/opt/caim_web/.env` and must have
  owner-only permissions.

## Production runtime

Apache terminates HTTPS and proxies to Gunicorn on `127.0.0.1:8021`. The systemd unit uses
the application-owned virtual environment at `/opt/caim_web/.venv` and starts `wsgi:app`.

## Content manager workflow

- `/content/content-manager` is the login entry point and `/content/content-dashboard` is the authenticated landing page.
- Authenticated `/content` pages include Logout. Sessions expire after 60 minutes without activity and are invalidated whenever the systemd application service restarts.
- `admin` is the initial administrator. `charles.yung` and `francis.lau` are seeded as active reviewers with the requested initial password. Change all seed passwords after first production login.
- `admin` is treated as a superuser account and is not offered as a content reviewer. With the two seeded content users, work created by `charles.yung` defaults to `francis.lau` as reviewer, and vice versa.
- Saving keeps content in `Saved`. Posting changes it to `Review`; it is not public at this stage.
- Article, course, and news studios let the creator select one or more active users as reviewers. The creator cannot select themselves, and every selected reviewer must approve.
- At least one reviewer is required. When the system has only two active users, the sole user other than the creator is selected automatically.
- If studio validation fails, submitted text, dates, selections, and reviewer choices are rendered back into the form. Browsers intentionally do not restore file-upload controls, so a file must be selected again.
- Studio saves distinguish New from Select/Edit. New content always uses an SQL insert and never an upsert; duplicate article/news slugs, course slugs, or course codes produce a validation error without changing the existing row. Select/Edit updates only the record identified by its original slug.
- After the last required approval, content becomes `Posted`. Public article, course, and news queries still hide it until its scheduled posting time. New studio forms default that time to Now.
- Course Studio accepts an uploaded image or an existing image path for both new and existing courses. Production uploads are retained under `/opt/caim_web/uploads` and linked into the static asset tree, so application deployments do not erase them.
- The homepage News & Events section renders all currently posted and scheduled-eligible database items in a single-row carousel. Desktop displays three cards, arrows appear when more than three items exist, and the carousel advances every five seconds before looping to the beginning. Hover, keyboard focus, reduced-motion preferences, and mobile swipe behavior are respected.

## GitHub Actions secrets

Create these repository secrets before pushing deployment changes to `main`. They are used only
for deployment access and application integrations:

- `PROD_SERVER`: `doxaxsolutions.com`
- `PROD_PORT`: `14322`
- `PROD_USER`: `cyung`
- `PROD_SECRET_KEY`: a long, random value used by Flask as the production `SECRET_KEY`
- `PROD_SSH_PRIVATE_KEY`: the private SSH key authorized for the `cyung` account on the production server
- `PROD_CRM_CONSULTATION_TOKEN`: the optional token matching dx-crm's `CONSULTATION_FORM_SECRET`

`PROD_SECRET_KEY` and `PROD_SSH_PRIVATE_KEY` are different secrets and must not be reused for
each other. Do not commit any populated `.env` file.

`PROD_SERVER`, `PROD_PORT`, `PROD_USER`, and `PROD_SSH_PRIVATE_KEY` remain deployment transport
secrets. They cannot be moved into the application `.env` because the workflow needs them before
it can connect to the server.

Database settings are stored on the production server, not in GitHub Actions secrets. Before the
first deployment, create `/opt/caim_web/.env` from [`deploy/prod.env.example`](deploy/prod.env.example)
and set `DB_HOST`, `DB_PASSWORD`, `MYSQL_ADMIN_USER`, `MYSQL_ADMIN_PASSWORD`, and optionally
`MYSQL_ADMIN_SOCKET`. The workflow validates and sources these values remotely, creates or
bootstraps `caimdb`, and imports `scripts/content_snapshot.json`. Keep the file mode `0600`.

The deployment writes the non-secret CRM endpoint to `/opt/caim_web/.env` as
`CRM_API_URL=https://dxcrm.doxaxsolutions.com/api/v1/public/consultation-intake`. The CAIM
contact form submits server-side to this dx-crm endpoint; the browser never receives the CRM
token. The submitted name, organization, email, phone, inquiry type, and message are mapped to a
dx-crm consultation request.

MySQL is required for the migrated content. Production must provide `DB_HOST`, `DB_PORT`,
`DB_USER`, `DB_PASSWORD`, and `DB_NAME` in `/opt/caim_web/.env`. Keep the production database
password in a dedicated GitHub Actions secret and never commit it. Run the schema/content import
against production before restarting the application; the Astro source directory must be
available to the importer for that operation.

The production server must already have Python 3.12, `sudo`, Apache, systemd, Gunicorn support
through the application virtual environment, and the Let's Encrypt certificate for
`caim.doxaxsolutions.com`. The `cyung` account must be allowed to authenticate with the SSH
private key and execute the required deployment commands through `sudo`. These are server
prerequisites, not GitHub Actions secrets.

## PROD rollback points

Verified production rollback points:

| Deployment date | Tag | Description |
| --- | --- | --- |
| 2026-07-14 | `prod-2026-07-14` | Multilingual content workflow and refined public site UI |
| 2026-07-13 | `prod-2026-07-13` | Force CAIM admin traffic to HTTPS (`0aafdbe`) |

The tag is an immutable rollback point for the application, Apache, systemd, and database
deployment scripts. The production database is not rolled back automatically; database changes
must be assessed separately before reverting application code.

To deploy this exact tagged version through GitHub Actions:

```powershell
git fetch origin --tags
gh workflow run deploy-prod.yml --ref prod-2026-07-14
```

Verify the workflow succeeds before directing traffic to the rollback version. To inspect the
tag locally without changing the current branch:

```powershell
git show --stat prod-2026-07-14
git diff main...prod-2026-07-14
```
