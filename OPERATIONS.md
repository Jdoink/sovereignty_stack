# Sovereignty Stack — OPERATIONS.md

## Purpose

This document defines the day-to-day operational workflows for Sovereignty Stack.

It exists to:
- standardize infrastructure management
- reduce operational mistakes
- document routine procedures
- simplify troubleshooting
- preserve operational continuity
- help future automation efforts
- help Codex understand expected workflows

This is the practical “how the stack is actually operated” document.

---

# Current Operational Philosophy

Sovereignty Stack should be operated like:

```text
small modular infrastructure
```

—not:
```text
random experimental app sprawl
```

Every operational action should ideally be:
- intentional
- documented
- reversible
- understandable

---

# Current Operational Modes

## 1. Daily Passive Mode

Normal operational state.

Typical characteristics:
- Raspberry Pi online
- Docker services running
- Grafana dashboard active
- Immich available
- Tailscale connected

Purpose:
- passive monitoring
- dashboard visualization
- photo backup
- remote access

---

## 2. Maintenance Mode

Used when:
- updating services
- changing Docker configs
- troubleshooting
- changing storage mappings
- modifying dashboards
- deploying new services

During maintenance:
- backups should exist first
- screenshots/exports are encouraged
- changes should be documented if important

---

## 3. Expansion Mode

Used when introducing:
- new infrastructure
- AI tooling
- new APIs
- automation systems
- major dashboard changes

Current recommendation:
Expand slowly and intentionally.

Avoid:
```text
installing many random services rapidly
```

---

# Current Daily Workflow

## Typical Usage Pattern

### HP TouchSmart

Acts primarily as:
- command center display
- dashboard terminal
- weather station
- crypto monitoring interface

Typical state:
```text
Grafana fullscreen / kiosk mode
```

---

## iPhone

Typical uses:
- Immich uploads
- remote dashboard access
- Tailscale access
- infrastructure monitoring

---

## Laptop / Desktop

Typical uses:
- GitHub/Codex workflows
- SSH administration
- Grafana editing
- Docker troubleshooting
- documentation

---

# Service Access Reference

# CasaOS

## Local Access

```text
http://192.168.1.189
```

## Tailscale Access

```text
http://100.82.61.96
```

---

# Grafana

## Local Access

```text
http://192.168.1.189:3000
```

## Tailscale Access

```text
http://100.82.61.96:3000
```

---

# Immich

## Local Access

```text
http://192.168.1.189:2283
```

## Tailscale Access

```text
http://100.82.61.96:2283
```

---

# Future ticker-service

## Planned Access

```text
http://192.168.1.189:8787/ticker
```

---

# Current Core Operational Services

# CasaOS

## Current Purpose

Visual infrastructure management.

Used for:
- app deployment
- Docker management
- service visibility
- storage management

---

# Grafana

## Current Purpose

Primary visualization and telemetry layer.

Used for:
- crypto monitoring
- weather monitoring
- dashboard display
- future DeFi intelligence

---

# Immich

## Current Purpose

Private photo backup platform.

Current workflow:
```text
iPhone
   ↓
Immich App
   ↓
Raspberry Pi
   ↓
External HDD
```

---

# Tailscale

## Current Purpose

Encrypted remote access.

Current philosophy:
```text
remote access without public exposure
```

---

# Uptime Kuma

## Current Purpose

Service uptime monitoring.

Used to verify:
- services are reachable
- infrastructure is online
- future alerting possibilities

---

# Docker Operations

## Current Philosophy

Docker containers should:
- remain modular
- remain isolated
- use mapped storage intentionally
- avoid unnecessary privileges

---

# Current Docker Best Practices

## Before Deploying New Containers

Ask:
- does it need persistent storage?
- where should storage live?
- should it use external HDD?
- does it need public access?
- what ports does it expose?
- does it require backups?

---

# Storage Management

# Current Storage Philosophy

## SD Card

Use for:
- operating system
- lightweight configs

Avoid:
- large media storage
- heavy persistent writes

---

## External HDD

Use for:
- Immich uploads
- media
- archives
- large datasets
- future knowledge vaults

---

# Current Important Storage Paths

## External Drive Root

```text
/media/devmon/umbrel
```

---

## Immich Upload Path

```text
/media/devmon/umbrel/immich
```

---

# Current Dashboard Workflow

# Grafana Workflow

## Current Editing Style

Currently:
```text
manual panel editing
```

Future direction:
```text
GitHub + exported dashboard JSON
```

---

# Current Dashboard Categories

## Weather
- radar
- forecast
- alerts

## Infrastructure
- CPU
- RAM
- uptime
- service status

## Crypto / DeFi
- prices
- ETH gas
- protocol metrics
- future TVL/fees/revenue

---

# Current Visual Direction

Target aesthetic:

```text
retro-futuristic operations center
```

Important:
The dashboard should remain:
- readable
- information-dense
- visually coherent
- operationally useful

Avoid:
- clutter
- excessive animations
- random visual noise

---

# Current GitHub Workflow

# Current Repository

```text
sovereignty-stack
```

---

# Current Documentation Priority

Important root documents:
- README.md
- ARCHITECTURE.md
- STACK_OVERVIEW.md
- ROADMAP.md
- SECURITY.md
- HARDWARE.md
- OPERATIONS.md

---

# Current GitHub Philosophy

GitHub should become:
```text
source of truth
```

for:
- configs
- architecture
- docs
- deployment definitions
- exported dashboards

---

# Current Codex Workflow

## Current Goal

Move from:
```text
manual clicking
```

toward:
```text
AI-assisted infrastructure engineering
```

---

# Current Codex Rules

Codex should:
- read docs first
- avoid hardcoded secrets
- preserve private-first architecture
- use beginner-readable code
- explain assumptions
- avoid unnecessary complexity

---

# Current Planned Operational Shift

Current infrastructure is transitioning toward:

```text
repo-driven operations
```

Meaning:
- documented changes
- exported dashboards
- version-controlled services
- reproducible deployments

---

# Current Shutdown Workflow

# Preferred Shutdown Process

## Step 1

Stop important transfers if possible.

---

## Step 2

Initiate shutdown:

```bash
sudo shutdown now
```

or CasaOS shutdown.

---

## Step 3

Wait for:
- services to stop
- network access to disappear
- activity lights to settle

---

## Step 4

Remove power only AFTER shutdown completes.

---

# Startup Workflow

## Recommended Startup Sequence

### 1

Power on router/network first.

### 2

Power on Raspberry Pi.

### 3

Wait several minutes for:
- Docker
- CasaOS
- Immich
- Grafana
- Tailscale

to initialize.

### 4

Verify:
- Tailscale online
- Grafana reachable
- Immich reachable
- external drive mounted

---

# Current Maintenance Workflow

# Before Major Changes

## Recommended Checklist

### 1

Export:
- dashboards
- compose files
- configs

---

### 2

Ensure:
- external drive mounted
- enough storage available

---

### 3

Document:
- important changes
- new ports
- new services
- storage mappings

---

### 4

If risky:
- create backup first

---

# Current Troubleshooting Philosophy

## Prefer

- simple fixes
- documented fixes
- isolated debugging
- understanding root causes

---

## Avoid

- random command spam
- deleting configs blindly
- exposing services during troubleshooting

---

# Current Service Deployment Philosophy

## Prefer

- Dockerized services
- modular deployments
- isolated configs
- clear volume mappings

---

## Avoid

- monolithic setups
- undocumented installs
- mystery scripts
- fragile manual hacks

---

# Current Infrastructure Priorities

# Priority 1

Stabilize:
- backups
- exports
- documentation
- configs

---

# Priority 2

Finish:
```text
ticker-service
```

---

# Priority 3

Expand:
- DeFi dashboards
- crypto intelligence
- protocol metrics

---

# Priority 4

Add:
- Open WebUI
- Ollama
- n8n

---

# Future Operational Goals

Eventually Sovereignty Stack should support:

## Monitoring
- uptime
- storage health
- alerts
- service failures

## Intelligence
- crypto analytics
- AI summaries
- protocol monitoring

## Automation
- scheduled jobs
- notifications
- workflow orchestration

## Knowledge
- searchable archives
- documentation
- research workflows

---

# Long-Term Operational Goal

The stack should eventually operate as:

```text
private infrastructure platform
+
AI-assisted command center
+
DeFi intelligence terminal
+
automation environment
+
knowledge archive
```

while remaining:
- understandable
- maintainable
- private
- resilient
- modular
