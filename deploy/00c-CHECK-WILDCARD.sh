#!/usr/bin/env bash
# READ-ONLY diagnostic. Changes nothing. Safe to run any time.
#
# QUESTION: will intelsof.com-0001 (intelsof.com + *.intelsof.com,
# expiring 2026-09-24) renew by itself, or will it lapse?
#
# WHY IT MATTERS MORE NOW: 03-repair-and-finish.sh points the invest-frontend
# vhost back at this certificate. If it cannot renew, intelsof.com and
# www.intelsof.com start showing certificate errors on 24 September.
#
# THE TELL: a wildcard name (*.intelsof.com) cannot be validated over HTTP-01.
# Let's Encrypt only issues wildcards via DNS-01. The --nginx plugin does
# HTTP-01 exclusively. So if authenticator is nginx or webroot, unattended
# renewal is impossible. If it is manual, certbot refuses to renew
# unattended unless a validation hook is configured.

RC="/etc/letsencrypt/renewal/intelsof.com-0001.conf"

echo "===== 1. Renewal config for the wildcard ====="
if [ -f "$RC" ]; then
  grep -vE '^\s*#' "$RC" | grep -vE '^\s*$'
else
  echo "    !! $RC not found"
fi

echo
echo "===== 2. The decisive lines ====="
AUTH=$(grep -E '^\s*authenticator' "$RC" 2>/dev/null | awk -F'=' '{gsub(/ /,"",$2); print $2}')
echo "    authenticator = ${AUTH:-<unset>}"
grep -E '^\s*(installer|manual_auth_hook|dns_|credentials|renew_hook)' "$RC" 2>/dev/null | sed 's/^/    /'

case "$AUTH" in
  nginx|webroot|standalone|apache)
    echo
    echo "    VERDICT: CANNOT auto-renew."
    echo "    '$AUTH' uses HTTP-01, which Let's Encrypt does not accept for a"
    echo "    wildcard. This is why it sits at ~18 days while your other two"
    echo "    certs are at 75. It has almost certainly been failing silently"
    echo "    for weeks, unnoticed because the ACME account had no email."
    ;;
  manual)
    echo
    echo "    VERDICT: will NOT renew unattended unless manual_auth_hook is set"
    echo "    above. certbot refuses non-interactive manual renewals otherwise."
    ;;
  dns-*|*dns*)
    echo
    echo "    VERDICT: DNS-01 plugin in use - renewal is possible. Confirm the"
    echo "    dry-run in section 6 actually succeeds."
    ;;
  *)
    echo "    VERDICT: unrecognised or unset - see the dry-run in section 6."
    ;;
esac

echo
echo "===== 3. Compare against a cert that IS renewing fine ====="
# api.intelsof.com sits at 75 days, so whatever it does works.
grep -E '^\s*(authenticator|installer)' \
  /etc/letsencrypt/renewal/api.intelsof.com.conf 2>/dev/null | sed 's/^/    api.intelsof.com: /'
grep -E '^\s*(authenticator|installer)' \
  /etc/letsencrypt/renewal/intelsof.com.conf 2>/dev/null | sed 's/^/    intelsof.com:     /'

echo
echo "===== 4. Is the renewal timer even running? ====="
systemctl is-active certbot.timer 2>/dev/null | sed 's/^/    certbot.timer: /'
systemctl list-timers certbot.timer --no-pager 2>/dev/null | sed 's/^/    /'

echo
echo "===== 5. Recent renewal failures in the log ====="
grep -iE 'intelsof\.com-0001|wildcard|\*\.intelsof' /var/log/letsencrypt/letsencrypt.log 2>/dev/null \
  | grep -iE 'error|fail|problem|refus|unauthor' | tail -20 | sed 's/^/    /' \
  || echo "    (nothing matched in the current log file)"

echo
echo "===== 6. Does the wildcard actually still NEED to exist? ====="
# This is the escape hatch. Every subdomain you really serve now has its own
# vhost and its own auto-renewing cert (api.intelsof.com, odii.intelsof.com).
# If nothing depends on the wildcard, point invest-frontend at the healthy
# 'intelsof.com' cert and delete intelsof.com-0001 - no DNS-01 needed.
echo "    Files referencing the wildcard cert:"
grep -rl 'intelsof.com-0001' /etc/nginx/ 2>/dev/null | sed 's/^/      /' \
  || echo "      (none)"
echo
echo "    Every server_name configured on this box:"
nginx -T 2>/dev/null | grep -E '^\s*server_name' | sort -u | sed 's/^/      /'
echo
echo "    Hostnames covered by the healthy 'intelsof.com' cert:"
openssl x509 -in /etc/letsencrypt/live/intelsof.com/fullchain.pem \
  -noout -ext subjectAltName 2>/dev/null | sed 's/^/      /'

echo
echo "===== 7. Staging dry-run (no rate-limit cost, changes nothing) ====="
certbot renew --cert-name intelsof.com-0001 --dry-run 2>&1 | tail -25 | sed 's/^/    /'

echo
echo "===== DONE ====="
echo "If section 2 says CANNOT auto-renew, look at section 6. If the only"
echo "server_names on the box are intelsof.com, www.intelsof.com,"
echo "api.intelsof.com and odii.intelsof.com, then no real hostname needs a"
echo "wildcard and you can retire intelsof.com-0001 entirely."
