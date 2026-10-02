#!/usr/bin/env bash
set -u
set -o pipefail
shopt -s nullglob

warning_seconds=$((30 * 86400))
now_epoch=$(date -u +%s)
issues=0
checked=0

alert() {
  printf '[ALERT] %s\n' "$1"
  issues=$((issues + 1))
}

warn() {
  printf '[WARN] %s\n' "$1"
  issues=$((issues + 1))
}

if ! systemctl is-enabled --quiet certbot-renew.timer; then
  alert 'certbot-renew.timer is disabled.'
fi
if ! systemctl is-active --quiet certbot-renew.timer; then
  alert 'certbot-renew.timer is not active.'
fi

renew_result=$(systemctl show certbot-renew.service -p Result --value 2>/dev/null) || renew_result='unknown'
if [[ "$renew_result" != 'success' ]]; then
  alert "Last certbot-renew.service result is ${renew_result}."
fi

renewal_files=(/etc/letsencrypt/renewal/*.conf)
if (( ${#renewal_files[@]} == 0 )); then
  alert 'No Certbot renewal configurations were found.'
fi

for renewal_file in "${renewal_files[@]}"; do
  name=${renewal_file##*/}
  name=${name%.conf}
  cert_file="/etc/letsencrypt/live/${name}/fullchain.pem"

  if [[ ! -r "$cert_file" ]]; then
    alert "${name}: certificate file is missing or unreadable."
    continue
  fi

  expiry_line=$(openssl x509 -in "$cert_file" -noout -enddate 2>/dev/null) || {
    alert "${name}: certificate file cannot be parsed."
    continue
  }
  expiry_epoch=$(date -u -d "${expiry_line#notAfter=}" +%s 2>/dev/null) || {
    alert "${name}: certificate expiry cannot be parsed."
    continue
  }
  disk_fingerprint=$(openssl x509 -in "$cert_file" -noout -fingerprint -sha256 2>/dev/null) || {
    alert "${name}: certificate fingerprint cannot be read."
    continue
  }
  checked=$((checked + 1))

  if (( expiry_epoch <= now_epoch )); then
    alert "${name}: certificate expired at ${expiry_line#notAfter=}."
  elif (( expiry_epoch - now_epoch <= warning_seconds )); then
    days_left=$(( (expiry_epoch - now_epoch + 86399) / 86400 ))
    warn "${name}: certificate expires in ${days_left} day(s) at ${expiry_line#notAfter=}."
  fi

  served_fingerprint=$(timeout 10s openssl s_client -connect 127.0.0.1:443 -servername "$name" </dev/null 2>/dev/null | openssl x509 -noout -fingerprint -sha256 2>/dev/null) || {
    alert "${name}: Apache did not serve a readable certificate on port 443."
    continue
  }
  if [[ "$served_fingerprint" != "$disk_fingerprint" ]]; then
    alert "${name}: Apache serves a different certificate than Certbot's current file."
  fi
done

if (( issues == 0 )); then
  printf '[OK] Certbot timer and renewal status are healthy; %d managed certificates are valid and served by Apache.\n' "$checked"
  exit 0
fi

printf '[INFO] Checked %d managed certificates; found %d issue(s).\n' "$checked" "$issues"
exit 1
