# Sovereignty Stack — RECOVERY_AND_BACKUP.md

> **Concrete scripts live in [`scripts/`](scripts/README.md):**
> - `scripts/backup-data.sh <mount>` — mirror `/data` to a USB drive (cron nightly, or manually when swapping the offsite drive). Exits silently if the target isn't mounted, so cron never spams when the rotating drive is off-site.
> - `scripts/bootstrap.sh [--restore <path>]` — bring a fresh Pi from blank OS to a running stack, optionally restoring `/data` from a backup drive first. Idempotent.
> - The Library now backs *itself* up: `/data/library/.git` records every entry change, and the UI has a "Download the Library (.zip)" button — see [`scripts/README.md`](scripts/README.md) for how this composes with the drive rotation.

## Purpose

This document defines the current backup philosophy, recovery priorities, shutdown procedures, and disaster-recovery workflows for Sovereignty Stack.

The goal is not enterprise-grade disaster recovery.

The goal is:

```text
recoverability
+
operational continuity
+
data durability
+
maintainable backup discipline
```

This document should evolve over time as:
- services expand
- storage grows
- backups mature
- infrastructure becomes more critical

---

# Current Backup Philosophy

## Core Principle

If data exists in only one place:

```text
it is not truly backed up
```

The current stack is operational, but not yet fully redundant.

The current focus is:
1. preserving important data
2. documenting recovery
3. reducing catastrophic single points of failure

---

# Current Critical Assets

## Highest Priority Data

### 1. Immich Media

Importance:
```text
VERY HIGH
```

Contains:
- personal photos
- videos
- future family archives
- irreplaceable memories

Current known storage path:

```text
/media/devmon/umbrel/immich
```

---

### 2. Raspberry Pi System

Importance:
```text
HIGH
```

Contains:
- operating system
- Docker configs
- CasaOS configs
- service state
- networking setup

Current risk:
- SD card corruption/failure

---

### 3. Grafana Dashboards

Importance:
```text
HIGH
```

Contains:
- operational dashboards
- command center layouts
- telemetry visualizations
- crypto panels
- future custom analytics

Current risk:
- manual-only dashboard editing
- accidental deletion
- lack of exports/versioning

---

### 4. Docker Compose Files

Importance:
```text
HIGH
```

Contains:
- deployment definitions
- service architecture
- port mappings
- storage mappings

Current future strategy:
- GitHub version control

---

### 5. Documentation Repository

Importance:
```text
HIGH
```

Contains:
- architecture docs
- operational procedures
- roadmap
- recovery workflows
- Codex context

Current future strategy:
- GitHub-backed documentation

---

# Current Backup Weaknesses

## Current Risks

### Single External Drive

Current state:
```text
single point of failure
```

If the drive fails:
- Immich media could be lost
- future archives could be lost

---

### SD Card Dependence

Current state:
```text
OS dependent on microSD
```

Risk:
- SD wear
- corruption
- unexpected power loss

---

### Manual Configuration Drift

Risk:
- undocumented dashboard changes
- undocumented Docker changes
- forgotten configs

Mitigation path:
- GitHub
- exports
- documentation
- Codex-assisted infrastructure

---

# Current Recommended Backup Strategy

## Preferred Long-Term Model

Approximate:

```text
3-2-1 backup strategy
```

Meaning:
- 3 copies of important data
- 2 different storage types
- 1 offsite copy

---

# Immediate Backup Priorities

# Priority 1 — Raspberry Pi SD Backup

## Goal

Create a full image backup of the Raspberry Pi system.

---

## Why

Protects against:
- SD corruption
- failed updates
- accidental configuration damage

---

## Recommended Frequency

### Current Recommendation

```text
monthly
```

and:
- before major upgrades
- before major Docker changes
- before experimental AI tooling

---

## Suggested Future Tools

Possible options:
- Raspberry Pi Imager
- Win32DiskImager
- balenaEtcher cloning workflows
- Linux dd imaging

---

# Priority 2 — External HDD Backup

## Goal

Create at least one additional copy of critical media.

---

## Current Risk

The external HDD is currently:
```text
NOT a full backup
```

It is only:
```text
primary storage
```

---

## Recommended Future Improvement

### Add:
- second HDD
- SSD backup
- offsite archive
- periodic export workflows

---

# Priority 3 — GitHub Infrastructure Backup

## Goal

Move critical infrastructure definitions into GitHub.

---

## Important Items To Version Control

### Include

```text
README.md
ARCHITECTURE.md
ROADMAP.md
SECURITY.md
Grafana exports
Docker compose files
service READMEs
deployment scripts
```

---

## Never Commit

```text
.env
API keys
wallet seeds
passwords
private keys
```

---

# Priority 4 — Grafana Dashboard Exports

## Goal

Export dashboards regularly.

---

## Why

Protects against:
- accidental deletion
- corruption
- failed upgrades
- Grafana rebuilds

---

## Current Suggested Workflow

### Export:
- dashboard JSON
- screenshots
- panel notes

Store:
```text
GitHub repo
+
external storage
```

---

# Shutdown Procedures

# Current Preferred Shutdown Method

## Recommended

Use:
```bash
sudo shutdown now
```

or equivalent CasaOS shutdown functionality.

---

# Why Proper Shutdown Matters

Improper power loss can cause:
- SD corruption
- database corruption
- Docker corruption
- filesystem inconsistencies

---

# Current Known Workflow

Current household workflow may involve:
- turning off router nightly
- turning off Raspberry Pi nightly

This is acceptable IF:
```text
the Raspberry Pi is shut down cleanly first
```

---

# Safe Shutdown Checklist

## Recommended Process

### Step 1

Stop active file transfers if possible.

---

### Step 2

Initiate proper shutdown:
```bash
sudo shutdown now
```

or CasaOS shutdown.

---

### Step 3

Wait for:
- activity lights to settle
- network access to stop
- services to disappear

---

### Step 4

Remove power only AFTER shutdown completes.

---

# Startup Procedures

## Recommended Startup Flow

### Step 1

Power on router/network first.

---

### Step 2

Power on Raspberry Pi.

---

### Step 3

Wait several minutes for:
- Docker
- CasaOS
- Immich
- Grafana
- Tailscale

to fully initialize.

---

### Step 4

Verify:
- Tailscale online
- Grafana reachable
- Immich reachable
- external drive mounted

---

# Current Recovery Philosophy

## Goal

The system should eventually become:

```text
recoverable by documentation
```

—not by memory alone.

---

# Disaster Recovery Priorities

## If Raspberry Pi Fails

### Goal

Restore:
- operating system
- Docker services
- configs
- dashboards
- storage mappings

### Critical Dependencies

- SD image backup
- GitHub configs
- external HDD data

---

## If External HDD Fails

### Goal

Restore:
- Immich uploads
- archives
- datasets

### Current Risk

Without secondary backup:
```text
data may be unrecoverable
```

---

## If Dashboard Is Lost

### Goal

Restore:
- dashboard JSON exports
- Grafana configs
- panel definitions

---

## If GitHub Repo Is Lost

### Goal

Maintain:
- local copies
- external-drive copies
- exported archives

---

# Current Recommended Recovery Priorities

## Priority Order

### 1

Protect:
```text
Immich media
```

---

### 2

Protect:
```text
infrastructure configs
```

---

### 3

Protect:
```text
documentation + operational knowledge
```

---

### 4

Protect:
```text
dashboard exports
```

---

# Current Operational Recovery Milestones

## Milestone 1

Achieved:
```text
operational infrastructure
```

---

## Milestone 2

Current target:
```text
recoverable infrastructure
```

---

## Milestone 3

Future target:
```text
redundant infrastructure
```

---

# Future Backup Improvements

## Planned Future Enhancements

### Storage
- mirrored drives
- SSD boot
- NAS
- snapshots

### Automation
- scheduled backups
- backup health checks
- backup alerts

### Monitoring
- disk SMART monitoring
- backup verification
- storage health dashboards

---

# Future Offsite Strategy

Potential future approaches:
- encrypted offsite HDD
- trusted-family archive copy
- cloud cold-storage backups
- encrypted archive snapshots

---

# Future AI + Backup Integration

Potential future workflows:
- AI-generated recovery checklists
- infrastructure summaries
- automated config exports
- dashboard documentation generation

---

# Current Recovery Priority Summary

## Immediate Focus

### Complete:
- GitHub documentation
- dashboard exports
- Docker compose exports
- SD imaging strategy
- second-drive planning

---

# Operational Rule

The stack should gradually evolve toward:

```text
documented
recoverable
reproducible
version-controlled infrastructure
```

instead of:
```text
memory-based manual configuration
```

---

# Long-Term Goal

Eventually Sovereignty Stack should be able to survive:
- hardware replacement
- SD corruption
- service rebuilds
- migration to new hardware

with:
- minimal downtime
- minimal confusion
- minimal data loss
