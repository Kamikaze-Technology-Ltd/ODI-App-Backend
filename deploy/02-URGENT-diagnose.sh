#!/usr/bin/env bash
# READ-ONLY. Run this FIRST.
#
# certbot reported:
#   "Successfully deployed certificate for odii.intelsof.com
#    to /etc/nginx/sites-enabled/invest-frontend"
#
# That is the wrong vhost. invest-frontend serves
#   intelsof.com  www.intelsof.com  *.intelsof.com
# and its ssl_certificate may now point at the odii-only certificate, which
# does NOT cover intelsof.com or www.intelsof.com. If so, your investment
# frontend is serving a mismatched cert to real visitors right now.

echo "===== 1. Which cert does invest-frontend currently use? ====="
grep -nE 'ssl_certificate|server_name|listen' /etc/nginx/sites-available/invest-frontend

echo
echo "===== 2. Certbot's backups of that file ====="
ls -la /etc/nginx/sites-available/ | grep -i invest

echo
echo "===== 3. What cert is actually being SERVED for each hostname? ====="
for H in intelsof.com www.intelsof.com odii.intelsof.com api.intelsof.com; do
  echo "--- $H ---"
  echo | openssl s_client -connect 127.0.0.1:443 -servername "$H" 2>/dev/null \
    | openssl x509 -noout -subject -ext subjectAltName 2>/dev/null \
    | sed 's/^/    /'
done

echo
echo "===== 4. nginx version (why 'http2 on;' failed) ====="
# 'http2 on;' is nginx >= 1.25.1 only. Older releases need the old form:
#   listen 443 ssl http2;
nginx -v

echo
echo "===== 5. Our odii vhost as certbot left it ====="
grep -nE 'ssl_certificate|server_name|listen|proxy_pass' /etc/nginx/sites-available/odii.intelsof.com
