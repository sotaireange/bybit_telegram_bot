#!/bin/bash
set -e

mkdir -p /etc/nginx/ssl

if [ ! -f /etc/nginx/ssl/fullchain.pem ] || [ ! -f /etc/nginx/ssl/privkey.pem ]; then
    echo "SSL certificates not found, running nginx without HTTPS..."
else
    echo "SSL certificates found."
fi

if [ ! -f /etc/nginx/conf.d/default.conf ]; then
    echo "Nginx configuration not found!"
    exit 1
fi

echo "Checking Nginx configuration..."
nginx -t

exec nginx -g 'daemon off;'
