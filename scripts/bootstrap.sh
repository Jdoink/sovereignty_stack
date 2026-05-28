#!/usr/bin/env bash
# Bring a fresh Raspberry Pi from blank OS to a running Sovereignty Stack.
# Optionally restore /data from a backup drive first.
#
# Usage:
#   bash bootstrap.sh                        # install + bring up default services
#   bash bootstrap.sh --restore /mnt/backup/data
#   bash bootstrap.sh --services "resource-service ticker-service"
#
# Idempotent — safe to re-run.

set -euo pipefail

REPO="${REPO:-https://github.com/Jdoink/sovereignty_stack.git}"
DEST="${DEST:-$HOME/sovereignty_stack}"
DATA="${SOVEREIGNTY_DATA:-/data}"
RESTORE=""
SERVICES="resource-service"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --restore)  RESTORE="$2"; shift 2 ;;
    --services) SERVICES="$2"; shift 2 ;;
    --repo)     REPO="$2";    shift 2 ;;
    --dest)     DEST="$2";    shift 2 ;;
    -h|--help)
      sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

log() { printf '\n\033[1;32m==>\033[0m %s\n' "$*"; }

log "Installing docker (idempotent)"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
if ! docker compose version >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y docker-compose-plugin || true
fi
sudo usermod -aG docker "$USER" || true

log "Ensuring $DATA exists and is owned by $USER"
sudo mkdir -p "$DATA"
sudo chown -R "$USER":"$USER" "$DATA"

if [[ -n "$RESTORE" ]]; then
  log "Restoring data from $RESTORE → $DATA"
  if [[ ! -d "$RESTORE" ]]; then
    echo "restore path missing: $RESTORE" >&2; exit 1
  fi
  rsync -aHAX --info=stats2 "$RESTORE/" "$DATA/"
fi

log "Cloning $REPO → $DEST"
if [[ -d "$DEST/.git" ]]; then
  git -C "$DEST" pull --ff-only
else
  git clone "$REPO" "$DEST"
fi

for svc in $SERVICES; do
  if [[ -f "$DEST/$svc/docker-compose.yml" ]]; then
    log "Bringing up $svc"
    ( cd "$DEST/$svc" && docker compose up -d --build )
  else
    echo "WARN: $svc has no docker-compose.yml — skipping" >&2
  fi
done

log "Bootstrap complete."
echo "If this is the first install, log out and back in once so the docker"
echo "group membership takes effect for $USER."
