#!/bin/sh
set -e

# Проверяем синтаксис конфигурации Nginx
nginx -t

# Проверяем, что процесс Nginx запущен
nc -z localhost 80 || exit 1

# Проверяем, что Nginx отвечает на localhost
# Если curl не установлен, можно использовать только предыдущие проверки
if command -v curl > /dev/null; then
  curl -f http://localhost/ || exit 1
fi

# Если дошли до этой строки, значит все проверки прошли успешно
exit 0