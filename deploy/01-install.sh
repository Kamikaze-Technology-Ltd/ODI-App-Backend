#!/usr/bin/env bash
# ODII backend -> https://odii.intelsof.com
#
# Written against the ACTUAL state of server1.intelsof.com as measured by
# 00-PREFLIGHT.sh:
#
#   - nginx already runs 80/443 with TWO enabled sites:
#       api.intelsof.com   (exact name, its own cert, 75 days)
#       invest-frontend    (server_name intelsof.com www.intelsof.com *.intelsof.com)
#     Neither is modified. The wildcard on invest-frontend currently answers
#     for odii.intelsof.com; our EXACT server_name outranks it in nginx, so
#     no edit to invest-frontend is required.
#   - ODII gunicorn is on 0.0.0.0:8001 => publicly exposed plain HTTP. ufw is
#     INACTIVE, so nothing is filtering it. We rebind to 127.0.0.1.
#   - A second, unrelated gunicorn owns 127.0.0.1:8000. Never touched.
#   - Redis is up on 127.0.0.1:6379 -> used for the Channels layer.
#   - daphne 4.2.1 is already installed in the venv.
#   - DNS for odii.intelsof.com already resolves here. Good.
#
# TWO-STAGE nginx, deliberately: nginx will not load a `listen 443 ssl` block
# with no ssl_certificate, and the cert does not exist yet. Stage 1 is HTTP
# only, certbot builds the TLS block, stage 2 swaps in the hardened config.
#
# Run as root from inside this deploy/ directory.
set -euo pipefail

DOMAIN="odii.intelsof.com"

# Sets the Let's Encrypt account contact. Currently 'none' on this box, which
# is why the wildcard silently drifted to 17 days. Applies to ALL certs here.
EMAIL=""                      # <-- PUT A REAL MONITORED ADDRESS HERE

APP_DIR="/root/odii_backend/ODI-App-Backend"
VENV="$APP_DIR/venv"
UNIT="/etc/systemd/system/odii_backend.service"
AVAIL="/etc/nginx/sites-available/odii.intelsof.com"
ENABLED="/etc/nginx/sites-enabled/odii.intelsof.com"
STAMP="$(date +%Y%m%d-%H%M%S)"

if [ -z "$EMAIL" ]; then
  echo "!! Set EMAIL at the top of this script first."
  echo "!! Your ACME account has no contact address, so you currently get zero"
  echo "!! warning when a certificate fails to renew. Use something like"
  echo "!! devops@intelsof.com that more than one person reads."
  exit 1
fi

echo "==> 0. Confirm DNS (preflight already showed this resolving correctly)"
RESOLVED=$(getent hosts "$DOMAIN" | awk '{print $1}' | head -1 || true)
MYIP=$(curl -s https://api.ipify.org || true)
[ "$RESOLVED" = "$MYIP" ] || { echo "!! $DOMAIN -> $RESOLVED but box is $MYIP"; exit 1; }
echo "    $DOMAIN -> $RESOLVED  OK"

echo "==> 1. certbot present?"
command -v certbot >/dev/null || { apt-get update -qq; apt-get install -y certbot python3-certbot-nginx; }

echo "==> 2. Set the ACME account contact address"
certbot update_account --email "$EMAIL" --no-eff-email --non-interactive

echo "==> 3. STAGE 1: install the HTTP-only vhost"
[ -f "$AVAIL" ] && cp "$AVAIL" "$AVAIL.bak-$STAMP"
cp odii.stage1-http.conf "$AVAIL"
ln -sf "$AVAIL" "$ENABLED"
mkdir -p /var/www/html
nginx -t
systemctl reload nginx     # reload, never restart: api.intelsof.com and
                           # invest-frontend keep serving throughout

echo "==> 4. Issue a DEDICATED cert for $DOMAIN"
# NOT reusing the *.intelsof.com wildcard: it expires 2026-09-24 (17 days) and
# is not auto-renewing, because a wildcard needs DNS-01 and --nginx uses
# HTTP-01. Tying the mobile app to it would take the app down when it lapses.
# -d is mandatory so certbot never offers to touch the other two vhosts.
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --redirect
systemctl enable --now certbot.timer

[ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ] || {
  echo "!! Certificate missing. Stopping before stage 2."; exit 1; }

echo "==> 5. STAGE 2: swap in the hardened vhost (adds /ws/, upload limits, HSTS)"
cp "$AVAIL" "$AVAIL.certbot-$STAMP"
cp odii.stage2-final.conf "$AVAIL"
if ! nginx -t; then
  echo "!! Stage 2 failed validation. Reverting to certbot's working version."
  cp "$AVAIL.certbot-$STAMP" "$AVAIL"
  nginx -t && systemctl reload nginx
  exit 1
fi
systemctl reload nginx

echo "==> 6. Verify renewal works for the new cert"
certbot renew --cert-name "$DOMAIN" --dry-run

echo "==> 7. channels_redis (daphne 4.2.1 already present)"
"$VENV/bin/pip" install -q channels_redis

echo "==> 8. Close the public plain-HTTP port: rebind gunicorn to loopback"
# ufw is inactive, so this rebind is the ONLY thing that closes 8001.
cp "$UNIT" "$UNIT.bak-$STAMP"
sed -i 's|--bind 0\.0\.0\.0:8001|--bind 127.0.0.1:8001|' "$UNIT"
grep -q -- '--bind 127.0.0.1:8001' "$UNIT" || { echo "!! sed failed; edit $UNIT manually"; exit 1; }

echo "==> 9. Install the daphne unit for websockets"
cp odii_daphne.service /etc/systemd/system/odii_daphne.service
systemctl daemon-reload

echo "==> 10. collectstatic (WhiteNoise serves these; nginx cannot read /root)"
cd "$APP_DIR"
"$VENV/bin/python" manage.py collectstatic --noinput

echo "==> 11. Restart ODII only"
systemctl restart odii_backend
systemctl enable --now odii_daphne
sleep 3
systemctl --no-pager --lines=5 status odii_backend || true
systemctl --no-pager --lines=5 status odii_daphne  || true

echo
echo "================= VERIFY ================="
echo "1. gunicorn is now loopback-only:"
ss -ltnp | grep -E ':8001|:8002' || true
echo
echo "2. HTTPS works:"
curl -s -o /dev/null -w '   https://%{host} -> HTTP %{http_code}\n' "https://$DOMAIN/api/" || true
echo
echo "3. The old open port is CLOSED (this must fail / time out):"
curl -s -o /dev/null -m 8 -w '   plain :8001 -> HTTP %{http_code}\n' \
  "http://$MYIP:8001/api/" || echo "   no response - correct"
echo
echo "4. TLS version must be 1.2 or 1.3 or iOS still blocks:"
openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" </dev/null 2>/dev/null \
  | grep -E 'Protocol|Cipher' || true
echo
echo "5. Other sites unaffected:"
curl -s -o /dev/null -w '   api.intelsof.com -> HTTP %{http_code}\n' https://api.intelsof.com/ || true
echo "========================================="
