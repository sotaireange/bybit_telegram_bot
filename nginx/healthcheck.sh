#!/bin/sh
set -e

nginx -t

nc -z localhost 80 || exit 1

if command -v curl > /dev/null; then
  curl -f http://localhost/ || exit 1
fia

exit 0