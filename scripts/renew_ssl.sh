#!/bin/bash

set -e

cd /home/bybit_telegram_bot


docker-compose run --rm certbot renew --quiet

if [ $? -eq 0 ]; then
    echo "✅ $(date): Сертификаты проверены успешно"

    docker-compose restart nginx
    echo "🔄 $(date): Nginx перезапущен"

    if curl -s -I https://bybit-telegram.site/health | grep -q "200 OK"; then
        echo "✅ $(date): Сайт работает корректно"
    else
        echo "❌ $(date): Ошибка: сайт не отвечает!"

    fi
else
    echo "❌ $(date): Ошибка при обновлении сертификатов"
fi

echo "📋 $(date): Проверка завершена"