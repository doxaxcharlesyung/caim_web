# caim_web
CAIM standalone website

## Operations

- Verified intranet SSH access to the Doxax Solutions PROD host at `192.168.2.43` as `cyung`.
- Verified remote `sudo -n pwd` returns `/home/cyung`.

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
- The workflow is written for a self-hosted runner labeled `prod` running inside the PROD intranet or on the PROD host itself.
- It installs the CAIM site files into `/opt/caim_web/`, installs the CAIM Apache vhost files into `/etc/httpd/conf.d/`, installs `doxax-caim-web.service`, restarts the CAIM service, runs `apachectl configtest`, and reloads `httpd`.
- The test site service and content remain separate under `/opt/test.doxaxsolutions.com`.

## CAIM Site

- `caim.doxaxsolutions.com` is deployed as a host-specific CAIM-owned site.
- The CAIM home page mirrors the source home page content from `D:\workspace\doxaxsolutions.com`, including the hero, Our Services, AI Opportunities, challenges, process, latest articles, and FAQ sections.
- The homepage is self-contained and uses CAIM-local content only.
- The current homepage keeps the `EN / 中文` language switch; the remaining CAIM tabs will be worked on later.
- Legacy CAIM routes now redirect back to the CAIM home page.
- CAIM routes are intentionally separate from the theology host and do not link to `www.doxaxsolutions.com`.

## Local Preview

- Open [`home.html`](home.html) directly in a browser on Windows 11.
- [`preview/caim-home-preview.html`](preview/caim-home-preview.html) redirects to the same page.
- Run `py -3.12 app.py` from the repo root to start a local Flask server on `http://127.0.0.1:8000/`.
