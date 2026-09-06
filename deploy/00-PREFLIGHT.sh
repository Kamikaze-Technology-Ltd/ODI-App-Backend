#!/usr/bin/env bash
# RUN THIS FIRST. It changes nothing - it only reports.
# server1.intelsof.com is clearly hosting more than just ODII, so we confirm
# what already owns ports 80/443 before installing anything.

echo "===== 1. What is REALLY in the running unit file? ====="
# Your pasted file says 'ODII Django Backend' but systemctl reports
# 'ODII Django API'. The unit on disk is NOT what you pasted, or it was never
# reloaded since Sep 1. This tells us the truth:
systemctl cat odii_backend

echo
echo "===== 2. What is actually listening, and on what address? ====="
ss -ltnp
# Look for :8001. If it says 0.0.0.0:8001 the API is publicly exposed over
# plain http right now. If it says 127.0.0.1:8001 it is already loopback-only
# - in which case something ELSE is already proxying it, find out what.

echo
echo "===== 3. Is there already a web server on 80/443? ====="
systemctl is-active nginx    2>/dev/null || echo "nginx: not active"
systemctl is-active apache2  2>/dev/null || echo "apache2: not active"
systemctl is-active httpd    2>/dev/null || echo "httpd: not active"
ss -ltnp 'sport = :80'  || true
ss -ltnp 'sport = :443' || true

echo
echo "===== 4. If nginx exists, what sites are already enabled? ====="
ls -la /etc/nginx/sites-enabled/ 2>/dev/null || echo "no sites-enabled dir"
nginx -T 2>/dev/null | grep -E 'server_name|listen' | head -40 || true

echo
echo "===== 5. Any certificates already issued on this box? ====="
certbot certificates 2>/dev/null || echo "certbot not installed"

echo
echo "===== 6. Does DNS for the subdomain point here yet? ====="
echo -n "odii.intelsof.com -> "; getent hosts odii.intelsof.com | awk '{print $1}' | head -1
echo -n "this box public IP -> "; curl -s https://api.ipify.org; echo

echo
echo "===== 7. Firewall ====="
ufw status verbose 2>/dev/null || iptables -L -n | head -20

echo
echo "===== 8. Is daphne installed in the venv? ====="
/root/odii_backend/ODI-App-Backend/venv/bin/pip show daphne 2>/dev/null | head -2 || echo "daphne NOT installed"
