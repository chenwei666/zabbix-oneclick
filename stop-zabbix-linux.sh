#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo
echo "[Zabbix] Stopping Linux stack"
echo

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker was not found."
  read -r -p "Press Enter to close..." _
  exit 1
fi

docker_cmd="docker"
if ! docker info >/dev/null 2>&1 && command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
  docker_cmd="sudo docker"
fi

$docker_cmd compose down
read -r -p "Press Enter to close..." _
