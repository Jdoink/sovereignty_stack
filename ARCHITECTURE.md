# Sovereignty Stack — ARCHITECTURE.md

## Purpose

This document explains the current and intended architecture of Sovereignty Stack.

It is designed for:
- future maintenance
- onboarding
- Codex/AI-assisted development
- infrastructure planning
- debugging
- long-term scalability

The goal is to make the system understandable at both:
1. a beginner operational level
2. a systems architecture level

---

# Core Philosophy

Sovereignty Stack is designed around:

```text
local-first
private-by-default
modular infrastructure
self-hosted services
AI-assisted operations
long-term digital sovereignty
```

The system should remain:
- portable
- inspectable
- adaptable
- reproducible
- understandable

Avoid unnecessary cloud dependencies whenever practical.

---

# High-Level System Topology

```text
iPhone / Laptop / HP TouchSmart
            ↓
      Tailscale VPN Mesh
            ↓
     Raspberry Pi 4 Server
            ↓
        Debian Linux
            ↓
           CasaOS
            ↓
    Docker Container Layer
            ↓
 Grafana / Immich / Kuma / APIs
            ↓
      External HDD Storage
```

---

# Hardware Layer

## Primary Compute Node

### Raspberry Pi 4

Current role:
- central orchestration node
- low-power always-on server
- Docker host
- dashboard backend
- automation hub
- future AI gateway

Current strengths:
- low power draw
- silent
- reliable
- easy replacement
- excellent Linux compatibility

Current limitations:
- limited RAM
- limited CPU
- SD card wear
- not ideal for large local AI models

Future upgrade path:
- SSD boot
- mini PC
- dedicated NAS
- clustered nodes
- GPU-capable local AI server

---

## External Storage

### External HDD

Purpose:
- persistent media storage
- Immich uploads
- future archives
- future backups
- long-term knowledge storage

Current known path:

```text
/media/devmon/umbrel
```

Immich upload path:

```text
/media/devmon/umbrel/immich
```

Design rule:
Storage-heavy services should use external storage instead of the SD card whenever possible.

---

## Dashboard Display Node

### HP TouchSmart

Purpose:
- fullscreen dashboard display
- command center terminal
- weather/radar display
- monitoring station
- future AI interface
- operational visualization layer

Current role:
visual interface only

The HP does not run core infrastructure logic.

The Raspberry Pi remains the backend.

---

# Networking Layer

## Local Network

Primary local access currently uses LAN IP:

```text
192.168.1.189
```

Services communicate over the local home network.

Benefits:
- low latency
- simple setup
- no external exposure
- easy troubleshooting

---

## Tailscale Mesh VPN

### Purpose

Tailscale provides encrypted remote access without exposing services publicly.

This avoids:
- port forwarding
- open router ports
- public attack surface
- manual VPN configuration complexity

### Architecture

```text
Remote Device
      ↓
Encrypted Tailscale Tunnel
      ↓
Raspberry Pi
```

### Current Benefits

- remote dashboard access
- remote Immich access
- secure administration
- encrypted device mesh
- identity-based access control

### Security Model

Only authenticated Tailscale devices should access infrastructure services.

Current philosophy:

```text
private network first
public exposure later (carefully)
```

---

# Operating System Layer

## Debian Linux

Current base operating system.

Purpose:
- stable Linux environment
- Docker host
- networking
- filesystem management
- service orchestration support

Debian is preferred because:
- stable
- lightweight
- widely supported
- excellent Docker compatibility

---

# Management Layer

## CasaOS

CasaOS acts as the visual infrastructure management layer.

It is NOT the actual operating system.

It runs on top of Debian/Linux.

### Current Responsibilities

- app installation
- Docker container management
- visual dashboard
- storage browsing
- simplified administration
- beginner-friendly orchestration

### Why CasaOS Was Chosen

- low friction
- visual interface
- easier onboarding
- good Docker abstraction
- useful for mixed technical skill levels

### Important Concept

```text
CasaOS = management layer
Docker = runtime layer
Debian = operating system
```

---

# Containerization Layer

## Docker

Docker is the core service runtime.

Every major service should ideally run:
- isolated
- reproducibly
- independently
- containerized

Benefits:
- portability
- reproducibility
- easy upgrades
- rollback capability
- isolated services

Current major services:
- Immich
- Grafana
- Uptime Kuma
- future ticker-service

---

# Current Services

# 1. Immich

## Purpose

Private photo/video backup platform.

Self-hosted alternative to:
- Google Photos
- iCloud Photos

### Current Architecture

```text
iPhone
   ↓
Immich mobile app
   ↓
Raspberry Pi
   ↓
External HDD storage
```

### Current Goals

- automatic backup
- local ownership
- remote access via Tailscale
- external-drive storage
- scalable media archive

### Important Notes

Immich databases and uploads should be backed up regularly.

Avoid storing large uploads on the Raspberry Pi SD card.

---

# 2. Grafana

## Purpose

Visualization and operational dashboard layer.

Grafana is the visual heart of Sovereignty Stack.

### Current Uses

- crypto prices
- weather/radar
- ETH gas
- protocol metrics
- scrolling ticker
- system telemetry
- clocks
- uptime visualization

### Current Plugins

#### Infinity Datasource

Purpose:
HTTP API integration.

Allows Grafana to pull:
- CoinGecko
- DeFiLlama
- Etherscan
- custom APIs
- future local endpoints

#### Business Ticker

Purpose:
scrolling terminal-style ticker output.

Used for:
- prices
- protocol metrics
- alerts
- future AI summaries
- future whale alerts

---

# 3. Uptime Kuma

## Purpose

Service health monitoring.

### Current Responsibilities

- service uptime checks
- availability monitoring
- operational visibility

### Future Possibilities

- notifications
- alert routing
- service degradation detection
- public status pages

---

# 4. ticker-service (in development)

## Purpose

Local data aggregation service for Grafana.

### Problem It Solves

Grafana transformations become messy when combining:
- CoinGecko
- Etherscan
- DeFiLlama
- future APIs

### Solution

```text
External APIs
      ↓
ticker-service
      ↓
Clean JSON endpoint
      ↓
Grafana Business Ticker
```

### Benefits

- cleaner Grafana setup
- centralized formatting
- caching
- rate-limit protection
- easier future expansion
- reusable data layer

### Planned Stack

- FastAPI
- httpx
- Docker
- local caching
- environment variables

---

# Data Layer

## Current Data Sources

### CoinGecko

Purpose:
crypto pricing.

Current assets:
- BTC
- ETH
- LINK
- AAVE
- CRV

### Etherscan

Purpose:
Ethereum gas metrics.

### DeFiLlama

Purpose:
protocol TVL and ecosystem metrics.

Current targets:
- Aave
- Curve
- Chainlink

---

# Security Architecture

## Current Philosophy

```text
private first
minimal exposure
least privilege
local ownership
```

### Current Security Decisions

- no public router ports
- Tailscale for remote access
- environment variables for secrets
- no committed API keys
- local-only admin services

### Services That Should NOT Be Public

- CasaOS
- Grafana admin
- Immich admin
- Docker interfaces
- internal APIs
- ticker-service
- future AI tools

---

# Storage Architecture

## Current Design

### SD Card

Use only for:
- OS
- lightweight configs
- minimal persistent writes

### External HDD

Use for:
- media
- archives
- dashboards exports
- large datasets
- backups
- future knowledge vault

---

# Backup Architecture

## Current Backup Priorities

### Critical Components

1. Raspberry Pi SD card
2. Immich uploads
3. Docker compose files
4. CasaOS configs
5. Grafana dashboards
6. Future databases

### Current Philosophy

Follow approximate:

```text
3-2-1 backup strategy
```

Meaning:
- 3 copies
- 2 storage types
- 1 offsite copy

---

# AI Architecture (Future)

## Planned Components

### Open WebUI

Purpose:
local/private ChatGPT-style interface.

### Ollama

Purpose:
local model serving.

### Future Goals

- local agents
- research assistants
- dashboard summaries
- protocol analysis
- document indexing
- private memory systems

---

# Knowledge Architecture (Future)

## Planned Systems

- Obsidian-style vault
- WikiJS
- searchable archives
- project documentation
- family archive system
- inheritance planning
- durable/open formats

---

# Automation Architecture (Future)

## Planned Layer

### n8n

Purpose:
workflow orchestration.

Potential workflows:
- market alerts
- protocol alerts
- weather alerts
- AI summaries
- scheduled jobs
- service automation

---

# Future Infrastructure Expansion

## Potential Future Additions

### Storage

- NAS
- RAID
- SSD arrays
- ZFS
- snapshots

### Monitoring

- Prometheus
- Loki
- Grafana Alloy
- Node Exporter

### Networking

- Cloudflare Tunnel
- reverse proxy
- HTTPS
- segmented public/private services

### AI

- local GPU node
- vector DB
- agent orchestration
- RAG pipelines

---

# Architectural Priorities

## Immediate Priority

```text
ticker-service
```

Goal:
replace messy Grafana transformations with a clean local API layer.

---

## Near-Term Priority

Stabilize:
- backups
- documentation
- dashboard exports
- Docker structure
- GitHub repo structure

---

## Long-Term Priority

Transform Sovereignty Stack into:

```text
private cloud
+
AI operations center
+
DeFi intelligence terminal
+
knowledge archive
+
automation platform
```

while remaining:
- understandable
- maintainable
- portable
- private
