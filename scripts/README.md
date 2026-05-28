# scripts/

Operational scripts for backup and recovery of the Sovereignty Stack.
See also: `../RECOVERY_AND_BACKUP.md` for the philosophy.

## `backup-data.sh` — mirror `/data` to a backup mount

Mirrors `/data` (which holds the Library, future Time-Capsule, and any other
app state) to a destination directory, typically a USB drive mountpoint.
Used in two ways:

1. **Nightly cron**, target = the always-plugged-in 2nd USB on the Pi —
   protects against the primary drive dying.
2. **Manual run when swapping the rotating drive**, target = the offsite drive
   — protects against losing the whole box.

```sh
# preview
sudo scripts/backup-data.sh --dry-run /mnt/backup
# real run
sudo scripts/backup-data.sh /mnt/backup
```

Behaviour:
- If the destination is not mounted, **exits 0 silently** (so cron does not
  spam when the rotating drive is off-site).
- Logs to `/var/log/sovereignty-backup.log` (override with `BACKUP_LOG=`).
- Source is `/data` (override with `SOVEREIGNTY_DATA=`).
- Uses `rsync -aHAX --delete` — hardlinks, ACLs, xattrs preserved; deletions
  propagate; **the destination becomes a faithful mirror**.

### Cron line (nightly 03:15)
```cron
15 3 * * * /home/<user>/sovereignty_stack/scripts/backup-data.sh /mnt/backup
```

### Rotating-drive workflow
1. Label two USB drives the same (e.g. `SS-OFFSITE`) and `/etc/fstab` mount
   either of them at the same path (`/mnt/offsite`) by `LABEL=`.
2. Each month: unmount and unplug the currently-attached drive; bring it to
   your trusted person. Take the other drive home and plug it in.
3. Once plugged in, run:
   ```sh
   sudo scripts/backup-data.sh /mnt/offsite
   ```
4. Track which drive is where in a Library entry (Meta → "Offsite drive
   rotation log") — when, who, which serial. The Library now keeps its own
   history (`/data/library/.git`), so that entry survives the swap.

## `bootstrap.sh` — fresh-Pi to running stack

Installs docker + compose, clones this repo, optionally restores `/data` from
a backup drive, and brings up the services. Idempotent.

```sh
# fresh Pi, no data yet:
bash <(curl -fsSL https://raw.githubusercontent.com/Jdoink/sovereignty_stack/main/scripts/bootstrap.sh)

# fresh Pi, restoring from a recovered backup drive:
bash scripts/bootstrap.sh --restore /mnt/backup/data

# bring up more services than just resource-service:
bash scripts/bootstrap.sh --services "resource-service ticker-service wallet-service"
```

Disaster-recovery flow (Pi died):
1. Flash Pi OS Lite onto a new SD card, boot, set hostname/SSH/user.
2. Plug in the backup drive (the on-Pi 2nd USB if that survives, or the
   offsite drive after retrieval).
3. Mount it (e.g. `/mnt/backup`).
4. `bash bootstrap.sh --restore /mnt/backup/data`.
5. Log out / back in once so the new `docker` group membership applies.

## SD-card image (manual, not scripted)

Image the Pi's boot media periodically so even the OS layer is recoverable:
- Power down the Pi, take the SD out, plug it into another machine.
- `sudo dd if=/dev/sdX bs=4M status=progress | gzip > pi-$(date +%F).img.gz`
- Store the resulting `.img.gz` on the backup drive next to `data/`.
- To restore: `gunzip -c pi-YYYY-MM-DD.img.gz | sudo dd of=/dev/sdX bs=4M`.

A monthly SD image is plenty — `bootstrap.sh` rebuilds the OS layer from
scratch in under an hour if you don't have one.
