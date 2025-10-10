docker compose run --rm \
  -v certbot_data:/etc/letsencrypt \
  -v certbot_www:/var/www/certbot \
  certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    -d bybit-telegram.site \
    --email vstomsk@gmail.com \
    --agree-tos \
    --no-eff-email
