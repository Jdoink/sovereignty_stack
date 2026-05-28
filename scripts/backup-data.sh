#!/usr/bin/env bash
# Mirror /data to a backup mount. Used both ways:
#   - cron nightly, target = the always-plugged-in 2nd USB on the Pi
#   - run manually, target = the rotating offsite drive when you swap it
#
# Usage:
#   sudo backup-data.sh /mnt/backup            # mirror
#   sudo backup-data.sh --dry-run /mnt/backup  # preview
#
# Behaviour:
#   - Exits 0 (no error) if the target is not mounted, so cron does not
#     spam errors when the rotating drive is off-site.
#   - Appends to /var/log/sovereignty-backup.log; override with BACKUP_LOG=.
#   - Preserves hardlinks, ACLs, extended attrs; deletes files removed at src.

set -euo pipefail

SRC="${SOVEREIGNTY_DATA:-/data}"
LOG="${BACKUP_LOG:-/var/log/sovereignty-backup.log}"

dry=""
if [[ "${1:-}" == "--dry-run" ]]; then dry="--dry-run"; shift; fi

DEST="${1:-}"
if [[ -z "$DEST" ]]; then
  echo "usage: $0 [--dry-run] <backup-mount>" >&2
  exit 2
fi

run() {
  echo
  echo "===== $(date -Iseconds) backup-data.sh ====="
  echo "src=$SRC  dest=$DEST  dry=${dry:-no}"

  if [[ ! -d "$SRC" ]]; then
    echo "WARN: source $SRC missing — nothing to back up"
    return 0
  fi
  if ! mountpoint -q "$DEST" 2>/dev/null && [[ ! -d "$DEST" ]]; then
    echo "WARN: $DEST is not mounted and not a directory — skipping"
    echo "      (this is expected when the rotating drive is off-site)"
    return 0
  fi

  mkdir -p "$DEST/data"
  # shellcheck disable=SC2086  # $dry is intentionally word-split (or empty)
  rsync -aHAX --delete --info=stats2 $dry "$SRC/" "$DEST/data/"
  echo "size: $(du -sh "$DEST/data" 2>/dev/null | awk '{print $1}')"
  echo "OK"
}

mkdir -p "$(dirname "$LOG")"
run 2>&1 | tee -a "$LOG"
exit "${PIPESTATUS[0]}"
