#!/usr/bin/env bash
set -Eeuo pipefail

echo
echo "[Docker] Linux installer"
echo

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "Docker and Docker Compose are already installed."
  exit 0
fi

if [[ "$(id -u)" -ne 0 ]]; then
  if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo was not found. Run this script as root."
    exit 1
  fi
  sudo_cmd="sudo"
else
  sudo_cmd=""
fi

if ! command -v curl >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    $sudo_cmd apt-get update
    $sudo_cmd apt-get install -y ca-certificates curl
  elif command -v dnf >/dev/null 2>&1; then
    $sudo_cmd dnf install -y curl ca-certificates
  elif command -v yum >/dev/null 2>&1; then
    $sudo_cmd yum install -y curl ca-certificates
  else
    echo "curl is required, and no supported package manager was found."
    exit 1
  fi
fi

tmp_script="$(mktemp)"
trap 'rm -f "$tmp_script"' EXIT

echo "Downloading Docker official install script..."
curl -fsSL https://get.docker.com -o "$tmp_script"

echo "Installing Docker Engine..."
$sudo_cmd sh "$tmp_script"

if command -v systemctl >/dev/null 2>&1; then
  $sudo_cmd systemctl enable --now docker || true
else
  $sudo_cmd service docker start || true
fi

if [[ "$(id -u)" -ne 0 ]]; then
  $sudo_cmd usermod -aG docker "$USER" || true
  echo
  echo "The current user was added to the docker group."
  echo "You may need to log out and log back in before docker works without sudo."
fi

docker --version || $sudo_cmd docker --version
docker compose version || $sudo_cmd docker compose version

echo
echo "Docker installation finished."
