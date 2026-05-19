# Sovereignty Stack — STACK_OVERVIEW.md

## Purpose

This document is a living operational snapshot of the current Sovereignty Stack environment.

Unlike `README.md` and `ARCHITECTURE.md`, which describe philosophy and long-term structure, this file is intended to answer:

```text
What is currently deployed?
What is currently working?
What still needs work?
What are the active priorities?
```

This file should be updated regularly as services, hardware, dashboards, and workflows evolve.

---

# Current Environment Summary

## Project State

Current project phase:

```text
FOUNDATION + VISUALIZATION
```

The system has successfully moved beyond:
- initial Linux setup
- initial networking setup
- basic homelab experimentation

The stack is now entering:
- operational dashboarding
- custom data services
- automation planning
- AI-assisted infrastructure development

---

# Current Hardware

## Primary Server

### Raspberry Pi 4

Purpose:
- central infrastructure node
- Docker host
- dashboard backend
- API aggregation
- storage coordination
- future automation/AI orchestration

Current status:

```text
WORKING
```

Current responsibilities:
- CasaOS host
- Docker runtime
- Immich backend
- Grafana backend
- Uptime Kuma
- Tailscale node
- future ticker-service host

---

## External Storage

### External HDD

Current status:

```text
CONNECTED + MOUNTED
```

Known current mount path:

```text
/media/devmon/umbrel
```

Known Immich storage path:

```text
/media/devmon/umbrel/immich
```

Purpose:
- media storage
- photo backup
- future archives
- future backup destination

Current notes:
- external drive permissions were manually corrected
- Immich now stores media on the HDD instead of the SD card

---

## Display Node

### HP TouchSmart

Current role:
- fullscreen dashboard display
- command center interface
- weather/radar visualization
- crypto dashboard display

Current status:

```text
WORKING
```

Current notes:
- modern browser installed
- Grafana fullscreen/kiosk mode functioning
- used primarily as a visualization layer

---

# Current Networking

## Local LAN

Current Raspberry Pi LAN address:

```text
192.168.1.189
```

Current status:

```text
WORKING
```

---

## Tailscale

Current Tailscale IP:

```text
100.82.61.96
```

Current status:

```text
WORKING
```

Current capabilities:
- remote dashboard access
- remote CasaOS access
- remote Immich access
- encrypted private networking

Current philosophy:
- private-only infrastructure
- no public port exposure

---

# Current Services

# CasaOS

## Status

```text
WORKING
```

## Purpose

Visual infrastructure management layer.

Current uses:
- app installation
- Docker management
- storage access
- visual administration

## Notes

CasaOS is running on top of Debian Linux.

It is not the operating system itself.

---

# Immich

## Status

```text
WORKING
```

## Current Functionality

- iPhone app connected
- remote/local login functioning
- photo uploads functioning
- external HDD storage functioning

## Current Access

### Local

```text
http://192.168.1.189:2283
```

### Tailscale

```text
http://100.82.61.96:2283
```

## Current Purpose

- self-hosted photo backup
- private Google Photos alternative
- future family archive/media system

## Current Known Working Flow

```text
iPhone
  ↓
Immich App
  ↓
Raspberry Pi
  ↓
External HDD
```

## Remaining Future Improvements

- backup redundancy
- second drive replication
- export strategy
- HTTPS/reverse proxy later if desired
- facial recognition exploration
- family accounts later

---

# Grafana

## Status

```text
WORKING
```

## Current Purpose

Primary dashboard and command center layer.

## Current Working Panels

### Weather
- Oklahoma radar
- forecast visualization

### System
- CPU metrics
- RAM metrics
- clock panel

### Crypto
- BTC price
- ETH price
- LINK price
- ticker experimentation

## Current Access

### Local

```text
http://192.168.1.189:3000
```

### Tailscale

```text
http://100.82.61.96:3000
```

---

# Grafana Plugins

## Infinity Datasource

### Status

```text
INSTALLED + WORKING
```

### Current Purpose

Pull external API data into Grafana.

Current APIs being explored:
- CoinGecko
- Etherscan
- DeFiLlama

---

## Business Ticker Plugin

### Status

```text
INSTALLED + WORKING
```

### Current Purpose

Scrolling command-center-style ticker.

Current experiments:
- crypto prices
- mixed metrics
- protocol metrics
- future alerts

---

# Uptime Kuma

## Status

```text
WORKING
```

## Current Purpose

Service health monitoring.

Current monitored services likely include:
- CasaOS
- Grafana
- Immich
- future ticker-service

---

# ticker-service

## Status

```text
PLANNING / IN DEVELOPMENT
```

## Current Goal

Replace messy Grafana transformations with a clean local JSON API.

## Current Planned Inputs

### CoinGecko
- BTC
- ETH
- LINK
- AAVE
- CRV

### Etherscan
- ETH gas

### DeFiLlama
- Aave TVL
- Curve TVL
- Chainlink TVL

## Planned Output

```json
[
  {"text":"BTC $76,982"},
  {"text":"ETH $2,129"},
  {"text":"LINK $9.61"}
]
```

## Planned Port

```text
8787
```

## Planned Stack

- FastAPI
- Docker
- httpx
- local caching
- environment variables

---

# Current Dashboard Direction

## Current Aesthetic Direction

Target vibe:

```text
retro-futuristic operations terminal
```

Inspirations:
- Bloomberg terminal
- NORAD command center
- crypto operations dashboard
- S&P-style monitoring systems
- cyberpunk/weather station hybrid

---

# Current Dashboard Categories

## Weather

Current/future:
- Oklahoma radar
- forecast
- weather alerts
- future weather oracle ideas

---

## Crypto / DeFi

Current/future:
- BTC
- ETH
- LINK
- AAVE
- CRV
- ETH gas
- Aave metrics
- Curve metrics
- Chainlink metrics
- future whale alerts
- future protocol fees/revenue

---

## Infrastructure

Current/future:
- CPU
- RAM
- disk usage
- uptime
- service health
- Docker status

---

## AI / Automation

Planned:
- Open WebUI
- Ollama
- n8n
- AI assistant panel
- automation status
- AI-generated summaries

---

# Current Security Model

## Current State

```text
PRIVATE-ONLY
```

Current protections:
- Tailscale encrypted access
- no public router ports
- no public admin services
- local-first architecture

## Important Current Rule

Do NOT expose publicly:
- CasaOS
- Grafana admin
- Immich admin
- Docker interfaces
- internal APIs

---

# Current Storage Philosophy

## SD Card

Current role:
- operating system
- lightweight configs only

Avoid:
- large media storage
- heavy write workloads

---

## External HDD

Current role:
- Immich uploads
- future archives
- future backups
- future datasets

---

# Current Backup Situation

## Current State

```text
NOT YET FULLY REDUNDANT
```

The system is operational but not yet fully “bulletproof.”

Current known priorities:
1. clone/backup Raspberry Pi SD card
2. second backup drive
3. export Grafana dashboards
4. backup Docker compose files
5. create recovery docs

---

# Current Workflow Philosophy

## Current Operational Style

The system is currently transitioning from:

```text
manual clicking / experimentation
```

toward:

```text
GitHub + Codex + version-controlled infrastructure
```

This is a major architectural shift.

---

# Current GitHub Direction

Current repo direction:

```text
sovereignty-stack
```

Current documentation priorities:
- README.md
- ARCHITECTURE.md
- STACK_OVERVIEW.md
- ROADMAP.md
- SECURITY.md
- HARDWARE.md

Purpose:
- improve maintainability
- improve Codex understanding
- improve reproducibility
- preserve institutional memory

---

# Current Immediate Priorities

## Priority 1

Finish:
```text
ticker-service
```

Goal:
clean crypto/protocol ticker feed for Grafana.

---

## Priority 2

Export and organize:
- Grafana dashboards
- Docker configs
- infrastructure docs

---

## Priority 3

Stabilize:
- backups
- shutdown routines
- recovery procedures

---

## Priority 4

Introduce:
- Open WebUI
- Ollama
- n8n

---

# Current Known Risks

## SD Card Failure

Risk:
Raspberry Pi SD cards eventually wear out.

Mitigation path:
- SD backup
- SSD boot later

---

## Single External Drive

Risk:
single-drive storage is not true backup.

Mitigation path:
- second drive
- offsite copy later

---

## Manual Configuration Drift

Risk:
manual dashboard changes become undocumented.

Mitigation path:
- GitHub exports
- version-controlled configs
- Codex-assisted development

---

# Current Long-Term Vision

Sovereignty Stack is intended to evolve into:

```text
private cloud
+
AI command center
+
crypto intelligence terminal
+
automation environment
+
personal archive system
+
self-hosted research platform
```

while remaining:
- understandable
- maintainable
- private
- modular
- reproducible

---

# Current Operational Milestone

The project has successfully completed:

```text
FOUNDATIONAL INFRASTRUCTURE PHASE
```

Key milestone achievements:
- self-hosted Linux server
- encrypted remote access
- external persistent storage
- private photo cloud
- operational dashboards
- live API-driven visualization
- GitHub/Codex-ready architecture

The next phase is:

```text
AUTOMATION + AI + CUSTOM SERVICES
```
