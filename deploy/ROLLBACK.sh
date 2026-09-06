#!/usr/bin/env bash
# Undo 01-install.sh. Other intelsof.com sites are never touched by this.
set -euo pipefail

echo "==> Removing the ODII vhost"
rm -f /etc/nginx/sites-enabled/odii.intelsof.com
nginx -t && systemctl reload nginx

echo "==> Stopping daphne"
systemctl disable --now odii_daphne 2>/dev/null || true
rm -f /etc/systemd/system/odii_daphne.service

echo "==> Restoring the previous gunicorn unit"
LATEST=$(ls -t /etc/systemd/system/odii_backend.service.bak-* 2>/dev/null | head -1 || true)
if [ -n "$LATEST" ]; then
  cp "$LATEST" /etc/systemd/system/odii_backend.service
  echo "    restored from $LATEST"
fi

systemctl daemon-reload
systemctl restart odii_backend
echo "==> Done. Note: the Let's Encrypt cert is left in place (harmless)."
