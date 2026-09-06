#!/usr/bin/env bash
# ODII backend -> https://odii.intelsof.com
#
# REVISED for the real state of server1.intelsof.com:
#   - nginx is ALREADY running on 80/443 serving other sites. We ADD a vhost.
#     We do not install, reconfigure, or remove anything that already exists.
#   - A second, unrelated gunicorn owns 127.0.0.1:8000. We never touch it.
#   - ODII gunicorn is on 0.0.0.0:8001 (publicly exposed, plain http).
#     We move it to 127.0.0.1:8001 so nginx is the only front door.
#   - Redis is already up on 127.0.0.1:6379. We use it for Channels.
#
# Run as root, from inside this deploy/ directory.
set -euo pipefail

DOMAIN="odii.intelsof.com"
EMAIL="samsupreme0@gmail.com"
APP_DIR="/root/odii_backend/ODI-App-Backend"
VENV="$APP_DIR/venv"
UNIT="/etc/systemd/system/odii_backend.service"
STAMP="$(date +%Y%m%d-%H%M%S)"

echo "==> 0. DNS must already point here or certbot will fail"
RESOLVED=$(getent hosts "$DOMAIN" | awk '{print $1}' | head -1 || true)
MYIP=$(curl -s https://api.ipify.org || true)
echo "    $DOMAIN -> ${RESOLVED:-<nothing>}   this box -> ${MYIP:-?}"
if [ "$RESOLVED" != "$MYIP" ]; then
  echo "    !! Add an A record in the intelsof.com zone:  odii -> $MYIP  (TTL 300)"
  exit 1
fi

echo "==> 1. certbot (nginx itself is already installed - leaving it alone)"
if ! command -v certbot >/dev/null; then
  apt-get update -qq
  apt-get install -y certbot python3-certbot-nginx
fi

echo "==> 2. Add the ODII vhost (existing sites untouched)"
if [ -e /etc/nginx/sites-enabled/odii.intelsof.com ]; then
  cp /etc/nginx/sites-available/odii.intelsof.com \
     "/etc/nginx/sites-available/odii.intelsof.com.bak-$STAMP"
fi
cp odii.intelsof.com.nginx.conf /etc/nginx/sites-available/odii.intelsof.com
ln -sf /etc/nginx/sites-available/odii.intelsof.com \
       /etc/nginx/sites-enabled/odii.intelsof.com
mkdir -p /var/www/html
nginx -t
systemctl reload nginx        # reload, NOT restart - other sites stay up

echo "==> 3. Certificate for $DOMAIN only"
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect
systemctl enable --now certbot.timer

echo "==> 4. Python deps: daphne (websockets) + channels_redis (shared layer)"
"$VENV/bin/pip" install -q daphne channels_redis

echo "==> 5. Rebind ODII gunicorn to loopback"
cp "$UNIT" "$UNIT.bak-$STAMP"
sed -i 's|--bind 0\.0\.0\.0:8001|--bind 127.0.0.1:8001|' "$UNIT"
grep -q -- '--bind 127.0.0.1:8001' "$UNIT" || { echo "!! sed failed, edit $UNIT by hand"; exit 1; }

echo "==> 6. Install the daphne unit"
cp odii_daphne.service /etc/systemd/system/odii_daphne.service
systemctl daemon-reload

echo "==> 7. Collect static (WhiteNoise serves them; nginx cannot read /root)"
cd "$APP_DIR"
"$VENV/bin/python" manage.py collectstatic --noinput
"$VENV/bin/python" manage.py check --deploy || true

echo "==> 8. Restart ODII services (the :8000 app is not touched)"
systemctl restart odii_backend
systemctl enable --now odii_daphne
sleep 3
systemctl --no-pager --lines=5 status odii_backend || true
systemctl --no-pager --lines=5 status odii_daphne  || true

echo "==> 9. Close the old public port"
ufw delete allow 8001 2>/dev/null || true
ufw status 2>/dev/null || true

echo
echo "==> VERIFY"
echo "  ss -ltnp | grep 8001      # must now read 127.0.0.1:8001"
echo "  curl -I https://$DOMAIN/api/"
echo "  curl -I http://$MYIP:8001/api/   # must now FAIL / time out"
echo "  openssl s_client -connect $DOMAIN:443 -servername $DOMAIN </dev/null 2>/dev/null | grep -E 'Protocol|Cipher'"
