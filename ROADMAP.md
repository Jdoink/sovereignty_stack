# Sovereignty Stack — ROADMAP.md

## Purpose

This document outlines the intended development roadmap for Sovereignty Stack.

It is designed to:
- guide future development
- prioritize infrastructure decisions
- help Codex understand long-term direction
- prevent random tool sprawl
- maintain architectural cohesion

This roadmap is intentionally modular and adaptable.

Not every phase must be completed before beginning another, but the sequence reflects the preferred order of operations.

---

# Core Strategic Goal

Transform Sovereignty Stack from:

```text
basic homelab
```

into:

```text
private infrastructure platform
+
AI-assisted command center
+
crypto intelligence terminal
+
automation environment
+
long-term knowledge vault
```

while remaining:
- private
- modular
- understandable
- maintainable
- reproducible
- self-hosted-first

---

# Current Phase

## ACTIVE PHASE

```text
PHASE 1 — FOUNDATION + VISUALIZATION
```

Current achievements:
- Raspberry Pi infrastructure operational
- CasaOS operational
- Docker operational
- Tailscale operational
- Immich operational
- Grafana operational
- external storage operational
- crypto/weather dashboard experimentation operational
- GitHub/Codex workflow beginning

The project is transitioning from:
```text
manual experimentation
```

toward:
```text
version-controlled infrastructure
```

---

# PHASE 1 — FOUNDATION + VISUALIZATION

## Goal

Create a stable and visually compelling operational foundation.

---

## Infrastructure Goals

### Complete
- Raspberry Pi setup
- Debian setup
- CasaOS setup
- Docker setup
- Tailscale setup
- Immich setup
- external HDD setup
- Grafana setup

### Remaining
- dashboard export strategy
- infrastructure documentation
- service inventory
- backup verification
- SD card imaging strategy
- recovery procedures

---

## Dashboard Goals

### Current Working Panels
- weather radar
- weather forecast
- system telemetry
- clock
- crypto prices
- scrolling ticker

### Immediate Additions
- ETH gas
- Aave TVL
- Curve TVL
- Chainlink metrics
- uptime visualization
- storage monitoring

---

## Visual Direction

Target aesthetic:

```text
retro-futuristic command center
```

Inspirations:
- Bloomberg terminal
- NORAD operations room
- weather station
- cyberpunk telemetry
- institutional market terminals

---

## Primary Deliverable

### ticker-service

The first major custom-coded service.

Purpose:
- aggregate crypto/protocol APIs
- format clean ticker data
- reduce Grafana complexity
- create reusable local API layer

Status:
```text
IN DEVELOPMENT
```

---

# PHASE 2 — STABILIZATION + OPERATIONS

## Goal

Make the stack resilient, maintainable, and recoverable.

---

## Backup Goals

### Critical Tasks

- full SD card backup
- external drive backup
- Docker compose exports
- Grafana dashboard exports
- service configuration backups
- recovery documentation

---

## Reliability Goals

### Planned Improvements

- UPS battery backup
- restart policies
- health monitoring
- watchdog monitoring
- service auto-recovery
- disk health monitoring

---

## Documentation Goals

Create:
- troubleshooting docs
- recovery procedures
- deployment procedures
- service inventory
- architecture diagrams
- dependency maps

---

## GitHub Goals

Transition infrastructure toward:
```text
repo-driven management
```

Meaning:
- configs tracked in GitHub
- dashboards exported
- services documented
- changes reviewable
- Codex-aware architecture

---

# PHASE 3 — CRYPTO + DEFI INTELLIGENCE

## Goal

Turn Grafana into a live DeFi intelligence terminal.

---

## Core Dashboard Targets

### Markets
- BTC
- ETH
- LINK
- AAVE
- CRV
- stablecoins
- BTC dominance

### Ethereum
- gas
- blob fees
- validator metrics
- L2 activity

### DeFi
- TVL
- protocol revenue
- fees
- yields
- borrow rates
- liquidations

---

## Chainlink Focus

Future panels:
- CCIP metrics
- oracle usage
- staking metrics
- protocol integrations
- fee/revenue estimation
- ecosystem monitoring

---

## Aave Focus

Future panels:
- total supplied
- total borrowed
- utilization
- reserve health
- lending rates
- liquidation events

---

## Curve Focus

Future panels:
- TVL
- volume
- pool utilization
- crvUSD metrics
- peg health
- Convex ecosystem overlays

---

## Future Intelligence Features

- whale alerts
- onchain anomaly detection
- large transfers
- protocol alerts
- AI-generated summaries
- risk dashboards
- DeFi “mission control”

---

# PHASE 4 — AUTOMATION

## Goal

Automate repetitive infrastructure and intelligence workflows.

---

## Planned Tool

### n8n

Purpose:
workflow orchestration.

---

## Planned Automations

### Infrastructure
- health alerts
- restart alerts
- backup reminders
- disk usage warnings

### Crypto
- gas alerts
- whale alerts
- liquidation alerts
- protocol metric thresholds

### AI
- daily summaries
- market recaps
- protocol intelligence
- weather summaries

---

## Future Workflow Examples

```text
DeFiLlama metric spike
        ↓
n8n workflow
        ↓
AI summary generated
        ↓
Grafana ticker update
        ↓
phone notification
```

---

# PHASE 5 — AI LAYER

## Goal

Introduce local/private AI tooling.

---

## Planned Components

### Open WebUI

Purpose:
local ChatGPT-style interface.

### Ollama

Purpose:
local model hosting.

---

## Planned Capabilities

- private AI assistant
- local research assistant
- dashboard summaries
- local memory systems
- document Q&A
- API orchestration
- AI-generated alerts

---

## Important Architectural Principle

AI should ideally:
- run locally when practical
- remain modular
- not control infrastructure blindly
- operate through documented APIs/services

---

# PHASE 6 — KNOWLEDGE VAULT

## Goal

Create a durable long-term personal knowledge system.

---

## Planned Systems

- Obsidian-style vault
- WikiJS
- searchable archives
- project documentation
- family archives
- inheritance planning
- durable open-format storage

---

## Long-Term Vision

The knowledge layer should become:
```text
searchable
portable
AI-readable
long-term durable
```

---

# PHASE 7 — PUBLIC / SHARED SERVICES

## Goal

Carefully expose selected services publicly.

Important:
This phase should happen ONLY after:
- backups
- security
- monitoring
- recovery systems
- authentication layers

are mature.

---

## Possible Public Services

### Public Dashboards
- weather
- public telemetry
- market dashboards
- protocol visualizations

### Public Tools
- educational dashboards
- DeFi analytics
- weather oracle concepts

---

## Preferred Exposure Methods

Preferred:
- Cloudflare Tunnel
- reverse proxy
- HTTPS
- authentication layers

Avoid:
- raw router port forwarding

---

# PHASE 8 — ADVANCED INFRASTRUCTURE

## Goal

Expand beyond the initial Raspberry Pi foundation.

---

## Potential Future Hardware

### Compute
- mini PC
- dedicated NAS
- GPU server
- clustered nodes

### Storage
- SSD arrays
- RAID
- ZFS
- snapshots

### Networking
- VLANs
- segmented services
- dedicated firewall
- advanced monitoring

---

# PHASE 9 — ADVANCED AI + AGENTS

## Goal

Create AI-assisted operational systems.

---

## Future Concepts

### AI Operators
- monitor dashboards
- summarize protocol changes
- monitor weather
- generate reports

### Agent Systems
- API orchestration
- data enrichment
- automated research
- DeFi intelligence workflows

---

## Important Constraint

AI systems should:
- remain inspectable
- remain modular
- not become black boxes
- preserve user control

---

# Long-Term Sovereignty Goals

## Desired End State

A system that provides:

### Personal Infrastructure
- storage
- backup
- private networking

### Intelligence
- crypto analytics
- weather intelligence
- monitoring
- AI summaries

### Knowledge
- archives
- research
- notes
- long-term preservation

### Automation
- workflows
- alerts
- orchestration
- scheduled intelligence

---

# Architectural Guardrails

## Avoid

- random app sprawl
- undocumented changes
- public exposure too early
- cloud lock-in
- hardcoded secrets
- overly fragile dependencies
- overengineering

---

## Prioritize

- readability
- modularity
- backups
- portability
- security
- documentation
- maintainability

---

# Current Immediate Priorities

## 1. Finish ticker-service

Current top software priority.

---

## 2. Export Grafana dashboards

Move from manual-only dashboarding toward reproducible infrastructure.

---

## 3. Stabilize backups

The system is not considered production-safe until backup/recovery workflows exist.

---

## 4. Introduce Open WebUI + Ollama

This will begin the AI layer.

---

## 5. Add n8n

This begins the automation layer.

---

# Strategic Philosophy

Sovereignty Stack should continue evolving into:

```text
private cloud
+
AI command center
+
DeFi intelligence platform
+
automation environment
+
knowledge archive
```

without sacrificing:
- simplicity
- ownership
- privacy
- maintainability
- adaptability
