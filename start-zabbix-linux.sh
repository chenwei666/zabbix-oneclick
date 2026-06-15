#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

action="${1:-start}"

echo
echo "[Zabbix] One-click startup for Linux"
echo

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker was not found. Installing Docker Engine..."
  ./install-docker-linux.sh
fi

if ! docker info >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    docker_cmd="sudo docker"
  else
    echo "Docker is installed but not running, or your user cannot access Docker."
    echo "Start Docker, or log out and log back in after docker group changes."
    read -r -p "Press Enter to close..." _
    exit 1
  fi
else
  docker_cmd="docker"
fi

if ! $docker_cmd compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 was not found."
  echo "Install the Docker Compose plugin, then run this script again."
  read -r -p "Press Enter to close..." _
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example."
fi

compose_images() {
  $docker_cmd compose --env-file .env config --images | sort -u
}

image_id() {
  $docker_cmd image inspect --format '{{.Id}}' "$1" 2>/dev/null || true
}

refresh_images() {
  local apply="${1:-false}"
  local changed="false"

  echo "Images in this stack:"
  compose_images | sed 's/^/  - /'
  echo

  while IFS= read -r image; do
    [[ -z "$image" ]] && continue
    before="$(image_id "$image")"
    echo "Checking $image ..."
    $docker_cmd pull "$image"
    after="$(image_id "$image")"

    if [[ -z "$before" ]]; then
      echo "  Downloaded: $image"
      changed="true"
    elif [[ "$before" != "$after" ]]; then
      echo "  Updated: $image"
      changed="true"
    else
      echo "  Current: $image"
    fi
  done < <(compose_images)

  if [[ "$apply" == "true" ]]; then
    echo
    if [[ "$changed" == "true" ]]; then
      echo "Image updates were downloaded. Recreating containers..."
    else
      echo "No new image IDs were found. Recreating containers with the current images..."
    fi
    $docker_cmd compose up -d
  elif [[ "$changed" == "false" ]]; then
    echo
    echo "No image updates were found."
  fi
}

case "$action" in
  check-update)
    refresh_images false
    read -r -p "Press Enter to close..." _
    exit 0
    ;;
  update)
    refresh_images true
    read -r -p "Press Enter to close..." _
    exit 0
    ;;
  start)
    ;;
  *)
    echo "Usage: $0 [start|check-update|update]"
    read -r -p "Press Enter to close..." _
    exit 1
    ;;
esac

web_port="$(
  awk -F= '/^ZABBIX_WEB_PORT=/ {print $2}' .env | tail -n 1
)"
web_port="${web_port:-8080}"

echo "Pulling Zabbix images. This may take several minutes the first time."
$docker_cmd compose pull

echo "Starting Zabbix..."
$docker_cmd compose up -d

echo
echo "Zabbix is starting in the background."
echo "Open: http://localhost:${web_port}"
echo "Login: Admin / zabbix"
echo
echo "First startup can take 1-3 minutes while the database initializes."

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:${web_port}" >/dev/null 2>&1 || true
fi

read -r -p "Press Enter to close..." _
