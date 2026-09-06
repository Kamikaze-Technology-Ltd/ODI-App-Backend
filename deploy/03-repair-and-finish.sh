#!/usr/bin/env bash
# Repairs the two problems from the 01-install.sh run, then finishes the job.
#
# PROBLEM 1 (serious): certbot's nginx installer picked the WRONG vhost.
#   "Successfully deployed certificate for odii.intelsof.com
#    to /etc/nginx/sites-enabled/invest-frontend"
#   invest-frontend matched because of its *.intelsof.com wildcard, and our
#   stage-1 file had no 443 block for certbot to prefer. If certbot rewrote
#   invest-frontend's ssl_certificate to the odii-only cert, then
#   intelsof.com and www.intelsof.com are serving a mismatched certificate.
#
# PROBLEM 2 (cosmetic): 'http2 on;' needs nginx >= 1.25.1. Fixed in the
#   stage-2 config by using 'listen 443 ssl http2;'.
#
# Run as root from inside this deploy/ directory, AFTER 02-URGENT-diagnose.sh.
set -euo pipefail

DOMAIN="odii.intelsof.com"
APP_DIR="/root/odii_backend/ODI-App-Backend"
VENV="$APP_DIR/venv"
UNIT="/etc/systemd/system/odii_backend.service"
IF_CONF="/etc/nginx/sites-available/invest-frontend"
AVAIL="/etc/nginx/sites-available/odii.intelsof.com"
STAMP="$(date +%Y%m%d-%H%M%S)"

########################################################################
# STEP 1 - put invest-frontend back on a cert that actually covers it
########################################################################
echo "==> 1. Checking invest-frontend's certificate"
cp "$IF_CONF" "$IF_CONF.bak-$STAMP"

if grep -q "live/$DOMAIN/" "$IF_CONF"; then
  echo "    !! CONFIRMED: invest-frontend is pointing at the odii-only cert."
  echo "    !! intelsof.com and www.intelsof.com are serving a mismatched cert."
  echo "    Restoring it to the wildcard (intelsof.com-0001)."

  # intelsof.com-0001 covers intelsof.com + *.intelsof.com, which is what
  # this vhost's server_name actually needs.
  sed -i "s#/etc/letsencrypt/live/$DOMAIN/#/etc/letsencrypt/live/intelsof.com-0001/#g" "$IF_CONF"

  grep -n 'ssl_certificate' "$IF_CONF" | sed 's/^/       /'
else
  echo "    OK: invest-frontend does not reference the odii cert. No change."
  rm -f "$IF_CONF.bak-$STAMP"
fi

########################################################################
# STEP 2 - install the corrected odii vhost
########################################################################
echo "==> 2. Installing the fixed stage-2 vhost (http2 syntax corrected)"
cp "$AVAIL" "$AVAIL.prev-$STAMP"
cp odii.stage2-final.conf "$AVAIL"

if ! nginx -t; then
  echo "!! Validation failed. Rolling BOTH files back."
  cp "$AVAIL.prev-$STAMP" "$AVAIL"
  [ -f "$IF_CONF.bak-$STAMP" ] && cp "$IF_CONF.bak-$STAMP" "$IF_CONF"
  nginx -t && systemctl reload nginx
  exit 1
fi
systemctl reload nginx
echo "    nginx reloaded."

########################################################################
# STEP 3 - stop certbot from hijacking invest-frontend on renewal
########################################################################
echo "==> 3. Pinning the odii renewal to certonly (no nginx installer)"
# Without this, a future 'certbot renew' can re-run the nginx installer and
# repeat the same misplacement. The cert files update in place; our vhost
# already points at them directly.
RC="/etc/letsencrypt/renewal/$DOMAIN.conf"
if [ -f "$RC" ]; then
  cp "$RC" "$RC.bak-$STAMP"
  sed -i 's/^installer = nginx/installer = None/' "$RC"
  grep -nE '^(installer|authenticator)' "$RC" | sed 's/^/       /'
fi
# Reload nginx after any renewal so the new cert is picked up.
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'HOOK'
#!/usr/bin/env bash
systemctl reload nginx
HOOK
chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

########################################################################
# STEP 4 - finish the original install (steps 7-11 of 01-install.sh)
########################################################################
echo "==> 4. channels_redis (daphne 4.2.1 already installed)"
"$VENV/bin/pip" install -q channels_redis

echo "==> 5. Rebind gunicorn to loopback - closes the public plain-HTTP port"
# ufw is inactive, so this is the ONLY thing that closes 0.0.0.0:8001.
if grep -q -- '--bind 0.0.0.0:8001' "$UNIT"; then
  cp "$UNIT" "$UNIT.bak-$STAMP"
  sed -i 's|--bind 0\.0\.0\.0:8001|--bind 127.0.0.1:8001|' "$UNIT"
fi
grep -q -- '--bind 127.0.0.1:8001' "$UNIT" || { echo "!! edit $UNIT manually"; exit 1; }

echo "==> 6. Install the daphne unit"
cp odii_daphne.service /etc/systemd/system/odii_daphne.service
systemctl daemon-reload

echo "==> 7. collectstatic"
cd "$APP_DIR"
"$VENV/bin/python" manage.py collectstatic --noinput

echo "==> 8. Restart ODII services only"
systemctl restart odii_backend
systemctl enable --now odii_daphne
sleep 3
systemctl --no-pager --lines=5 status odii_backend || true
systemctl --no-pager --lines=5 status odii_daphne  || true

########################################################################
# VERIFY
########################################################################
MYIP=$(curl -s https://api.ipify.org || true)
echo
echo "================= VERIFY ================="
echo "1. Ports (8001 and 8002 must both be 127.0.0.1):"
ss -ltnp | grep -E ':8001|:8002' | sed 's/^/   /' || true

echo
echo "2. Correct cert per hostname:"
for H in odii.intelsof.com intelsof.com www.intelsof.com api.intelsof.com; do
  printf '   %-22s ' "$H"
  echo | openssl s_client -connect 127.0.0.1:443 -servername "$H" 2>/dev/null \
    | openssl x509 -noout -subject 2>/dev/null | sed 's/subject=//'
done

echo
echo "3. Endpoints:"
curl -s -o /dev/null -w '   https://odii.intelsof.com/api/ -> %{http_code}\n' "https://$DOMAIN/api/" || true
curl -s -o /dev/null -w '   https://api.intelsof.com/      -> %{http_code}\n' https://api.intelsof.com/ || true
curl -s -o /dev/null -w '   https://intelsof.com/          -> %{http_code}\n' https://intelsof.com/ || true

echo
echo "4. Old open port must now FAIL:"
curl -s -o /dev/null -m 8 -w '   plain :8001 -> %{http_code}\n' "http://$MYIP:8001/api/" \
  || echo "   no response - CORRECT"

echo
echo "5. TLS version (must be 1.2 or 1.3 for iOS):"
openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" </dev/null 2>/dev/null \
  | grep -E 'Protocol|Cipher' | sed 's/^/   /' || true
echo "========================================="
