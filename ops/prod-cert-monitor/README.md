# PROD certificate safeguards

The files in this directory are deployed to `192.168.2.43`:

- `cert_monitor.sh` → `/opt/dx-monitor/cert_monitor.sh`
- `cert_alert_notify.sh` → `/opt/dx-monitor/cert_alert_notify.sh`
- `dx-cert-monitor.service` and `dx-cert-monitor.timer` → `/etc/systemd/system/`
- `dx-certbot-failure-alert.service` → `/etc/systemd/system/`
- `certbot-renew-alert.conf` → `/etc/systemd/system/certbot-renew.service.d/alert.conf`

The daily timer runs at 08:15 server time. It checks that Certbot's timer is enabled and active, that its last renewal run succeeded, that every managed certificate has more than 30 days remaining, and that Apache serves the matching certificate for each name. It emails only when it finds an issue. Certbot service failures trigger an immediate alert through `OnFailure`.

Both alert paths use DX sendmail at `127.0.0.1:18888`. The notifier reads `MAIL_API_KEY` from `/opt/dx-services/.env` and requires both HTTP 200 and `ok: true`. Failed notification attempts exit nonzero and are recorded in the systemd journal. The current DX sendmail SMTP credential is rejected by its upstream server; certificate detection works, but email delivery will remain unavailable until that credential is fixed.

After fixing the mail credential, run `/opt/dx-monitor/cert_alert_notify.sh test-mail` and confirm the message arrives at the configured recipient. Check `systemctl status dx-cert-monitor.timer` and `journalctl -u dx-cert-monitor.service -u dx-certbot-failure-alert.service` for subsequent results.
