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
- Both HTTP and HTTPS proxy to `127.0.0.1:18000`, which matches the mirrored CAIM snapshot service on the host.
- The CAIM app itself serves a host-specific test home page at `/`, while `/caim-2/` remains available as the mirrored snapshot page.
- The SSL vhost expects a Let's Encrypt certificate at `/etc/letsencrypt/live/caim.doxaxsolutions.com/`.

## Deployment

- GitHub Actions deploys on pushes to `main` through [.github/workflows/deploy-prod.yml](.github/workflows/deploy-prod.yml).
- The workflow is written for a self-hosted runner labeled `prod` running inside the PROD intranet or on the PROD host itself.
- It installs the CAIM Apache vhost files into `/etc/httpd/conf.d/`, runs `apachectl configtest`, and reloads `httpd`.

## CAIM Test Home

- `caim.doxaxsolutions.com` is deployed as a host-specific test landing page on the mirrored CAIM backend.
- The root page is intentionally separate from the theology host and links into the mirrored CAIM snapshot content.
