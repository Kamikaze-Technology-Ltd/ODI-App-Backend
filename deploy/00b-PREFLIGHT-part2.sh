#!/usr/bin/env bash
# Read-only. nginx is already running on this box serving OTHER sites, so we
# must know its existing layout before adding a vhost. Nothing here changes
# anything.

echo "===== A. Existing nginx sites ====="
ls -la /etc/nginx/sites-enabled/

echo
echo "===== B. Every server_name / listen already configured ====="
# CRITICAL: we are looking for a 'default_server' or a 'server_name _;' catch-all
# that would swallow odii.intelsof.com before our new vhost ever sees it.
nginx -T 2>/dev/null | grep -nE 'server_name|listen|default_server'

echo
echo "===== C. What is the OTHER app on 127.0.0.1:8000? ====="
# Do not disturb it. Just identify which unit owns it.
systemctl list-units --type=service --state=running | grep -iE 'gunicorn|django|web|api|uvicorn|daphne'
ps -o pid,unit,cmd -p 2047717,2047718,2047719 2>/dev/null

echo
echo "===== D. Certbot present? Existing certs? ====="
which certbot || echo "certbot NOT installed"
certbot certificates 2>/dev/null || true

echo
echo "===== E. DNS for the subdomain ====="
echo -n "odii.intelsof.com -> "; getent hosts odii.intelsof.com | awk '{print $1}' | head -1
echo -n "this box public IP -> "; curl -s https://api.ipify.org; echo

echo
echo "===== F. Firewall ====="
ufw status verbose 2>/dev/null || iptables -S | head -30

echo
echo "===== G. Confirm the ODII venv + packages ====="
V=/root/odii_backend/ODI-App-Backend/venv/bin
$V/pip show daphne        2>/dev/null | head -2 || echo "daphne NOT installed"
$V/pip show channels_redis 2>/dev/null | head -2 || echo "channels_redis NOT installed"

echo
echo "===== H. Is port 8001 reachable from the public internet right now? ====="
# It is bound to 0.0.0.0. If ufw is not blocking it, the API is fully open
# over plain http and anyone can read driver PII in transit.
curl -s -o /dev/null -w 'external :8001 -> HTTP %{http_code}\n' \
  --max-time 8 "http://$(curl -s https://api.ipify.org):8001/api/" || echo "no response (good)"
