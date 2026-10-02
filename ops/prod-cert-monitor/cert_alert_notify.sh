#!/usr/bin/env bash
set -euo pipefail

mail_api_url='http://127.0.0.1:18888/api/dxsendmail/send'
mail_env_file='/opt/dx-services/.env'
recipient='charles.yung@doxaxsolutions.com'
mode=${1:-}

case "$mode" in
  check)
    check_status=0
    check_output=$(/opt/dx-monitor/cert_monitor.sh 2>&1) || check_status=$?
    if (( check_status != 0 )) && ! grep -qE '^\[(WARN|ALERT)\]' <<<"$check_output"; then
      check_output="[ALERT] Certificate check failed unexpectedly (exit ${check_status})."$'\n'"${check_output}"
    fi
    if ! grep -qE '^\[(WARN|ALERT)\]' <<<"$check_output"; then
      printf '%s\n' "$check_output"
      exit 0
    fi
    subject="[PROD CERT ALERT] $(hostname -s) certificate check"
    message="Certificate monitoring found an issue on $(hostname -s) at $(date '+%Y-%m-%d %H:%M:%S %Z').

${check_output}"
    ;;
  renewal-failed)
    renew_result=$(systemctl show certbot-renew.service -p Result --value 2>/dev/null) || renew_result='unknown'
    subject="[PROD CERT ALERT] $(hostname -s) Certbot renewal failed"
    message="certbot-renew.service failed on $(hostname -s) at $(date '+%Y-%m-%d %H:%M:%S %Z') (result: ${renew_result}).

Inspect: journalctl -u certbot-renew.service -n 100 --no-pager"
    ;;
  test-mail)
    subject="[PROD CERT ALERT TEST] $(hostname -s)"
    message="This is a one-time test of the production certificate alert email route. No certificate failure is being reported."
    ;;
  *)
    printf 'Usage: %s {check|renewal-failed|test-mail}\n' "$0" >&2
    exit 2
    ;;
esac

mail_api_key=$(awk -F= '/^MAIL_API_KEY=/{print $2; exit}' "$mail_env_file")
if [[ -z "$mail_api_key" ]]; then
  printf '[ALERT] MAIL_API_KEY is missing; certificate email was not sent.\n' >&2
  exit 1
fi

payload=$(jq -n --arg to "$recipient" --arg subject "$subject" --arg msg "$message" '{to:$to, subject:$subject, msg:$msg}')
if ! response=$(curl -sS --max-time 30 -w '\n%{http_code}' -X POST "$mail_api_url" -H 'Content-Type: application/json' -H "X-API-Key: ${mail_api_key}" --data-binary "$payload"); then
  printf '[ALERT] DX sendmail request failed; certificate email was not sent.\n' >&2
  exit 1
fi

http_status=${response##*$'\n'}
response_body=${response%$'\n'*}
send_email_id=$(jq -r '.send_email_id // "none"' <<<"$response_body" 2>/dev/null) || send_email_id='none'
if [[ "$http_status" != '200' ]] || ! jq -e '.ok == true' <<<"$response_body" >/dev/null 2>&1; then
  printf '[ALERT] DX sendmail rejected certificate email (HTTP %s, id %s).\n' "$http_status" "$send_email_id" >&2
  exit 1
fi

printf '[OK] DX sendmail accepted certificate email (id %s).\n' "$send_email_id"
