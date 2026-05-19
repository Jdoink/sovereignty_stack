# Sovereignty Stack

**Sovereignty Stack** is a local-first, privacy-preserving personal command center built on self-hosted infrastructure.

The project began as a Raspberry Pi + CasaOS homelab and is evolving into a modular private operating environment for storage, dashboards, automation, AI tools, crypto/DeFi monitoring, weather intelligence, research workflows, and long-term digital ownership.

The core idea is simple:

> Own the infrastructure. Control the data. Keep services private by default. Expand modularly.

---

## Current Status

The current stack is already operational as a private homelab foundation.

### Working Base Layer

- Raspberry Pi 4 running Debian/Linux
- CasaOS as the visual self-hosting control panel
- Docker-based app deployment through CasaOS
- Tailscale for private encrypted remote access
- External 2TB drive mounted for persistent storage
- Uptime Kuma for service monitoring
- Immich for self-hosted photo backup
- Grafana for command center dashboards
- Infinity data source plugin for API-based dashboard panels
- Business Ticker plugin for scrolling market/system intelligence
- HP TouchSmart repurposed as a fullscreen command center display

---

## Project Vision

Sovereignty Stack is intended to become a personal/private command center that combines:

- private cloud storage
- photo and media backup
- local dashboards
- weather/radar display
- crypto and DeFi intelligence
- Chainlink/Aave/Curve protocol monitoring
- AI-assisted research
- local knowledge vaults
- project management
- automation workflows
- long-term family/personal archive
- future local LLM and agent orchestration

The long-term direction is a private “home Bloomberg terminal + AI command center + personal data vault” that runs on hardware controlled by the user.

---

## Design Principles

### 1. Local-first

Core services should run locally whenever practical. Cloud services may be used selectively, but the foundation should remain self-owned and portable.

### 2. Private by default

Services should not be exposed publicly unless there is a clear reason and a proper security layer. Tailscale is the default remote-access model.

### 3. Modular

Each major function should be its own service, folder, dashboard, or container so it can be replaced or upgraded without breaking the whole system.

### 4. Beginner-maintainable

This project should stay understandable to a motivated beginner. Avoid needless complexity unless it solves a real problem.

### 5. Codex-readable

Documentation should be detailed enough for Codex or another AI coding assistant to understand the current architecture before making changes.

### 6. No hardcoded secrets

API keys, passwords, and credentials must never be committed to the repository. Use `.env` files, Docker environment variables, or secret managers.

---

## Current Architecture

```text
Phone / Laptop / HP TouchSmart
        ↓
Tailscale encrypted private network
        ↓
Raspberry Pi 4
        ↓
Debian Linux
        ↓
CasaOS
        ↓
Docker containers / services
        ↓
Grafana, Immich, Uptime Kuma, future services
        ↓
External 2TB drive for persistent data
```

---

## Current Services

### CasaOS

CasaOS acts as the visual control panel for the Raspberry Pi server.

It provides:

- app management
- container management
- storage visibility
- file access
- simplified self-hosting workflows

CasaOS is not the actual operating system. The underlying OS is Debian/Linux. CasaOS is the beginner-friendly management layer on top.

---

### Tailscale

Tailscale provides private encrypted remote access.

It allows trusted devices, such as a phone or laptop, to access the Raspberry Pi from outside the home without opening public router ports.

Current model:

```text
iPhone / Laptop
      ↓
Tailscale encrypted tunnel
      ↓
Raspberry Pi at home
```

This is preferred over public exposure.

---

### Immich

Immich is the self-hosted photo backup system.

It functions like a private Google Photos/iCloud Photos alternative.

Current goal:

- iPhone photos/videos back up to the Raspberry Pi
- media is stored on the external hard drive
- access remains private through local network or Tailscale

Important storage path currently used for Immich uploads:

```text
/media/devmon/umbrel/immich
```

---

### Uptime Kuma

Uptime Kuma monitors service health.

It is used to check whether key services are online and responsive.

Typical monitored services may include:

- CasaOS
- Immich
- Grafana
- ticker service
- external websites/APIs
- future local apps

---

### Grafana

Grafana is the main dashboard layer for the command center.

Current/future panels include:

- system telemetry
- weather/radar
- clock
- crypto prices
- ETH gas
- protocol metrics
- DeFi TVL
- uptime/service health
- scrolling intelligence ticker

---

### Grafana Plugins

The current Grafana setup includes:

- Infinity data source plugin
- Business Ticker panel/plugin

Infinity allows Grafana to pull data from HTTP APIs.

Business Ticker allows scrolling text/ticker-style dashboard output.

---

## Current Dashboard Direction

The dashboard is intended to become a live operational display.

Initial dashboard categories:

### Weather

- Oklahoma radar
- OKC forecast
- weather alerts
- future weather oracle experiments

### System Health

- Raspberry Pi uptime
- CPU/RAM usage
- storage usage
- service status
- network status

### Crypto/DeFi

- BTC, ETH, LINK, AAVE, CRV prices
- ETH mainnet gas
- Aave TVL
- Curve TVL
- Chainlink metrics
- future fees, revenue, whale alerts, and protocol-specific analytics

### AI / Automation

Future panels may connect to:

- Open WebUI
- Ollama
- n8n
- local agents
- local research assistants
- API summarizers

---

## Repository Structure

Suggested root structure:

```text
sovereignty-stack/
│
├── README.md
├── ARCHITECTURE.md
├── STACK_OVERVIEW.md
├── ROADMAP.md
├── SECURITY.md
├── HARDWARE.md
│
├── ticker-service/
│   ├── server.py
│   ├── requirements.txt
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── .gitignore
│   └── README.md
│
├── grafana/
│   ├── dashboards/
│   └── notes/
│
├── docker/
│   └── compose-files/
│
├── docs/
│   ├── setup-notes/
│   ├── recovery/
│   └── troubleshooting/
│
└── scripts/
```

This structure can evolve over time.

---

## Active Build: Crypto Ticker Service

The first custom service planned for this repo is:

```text
ticker-service
```

Purpose:

Take messy external API data and return one clean local JSON feed for Grafana Business Ticker.

Target local endpoint:

```text
http://192.168.1.189:8787/ticker
```

or through Tailscale:

```text
http://100.82.61.96:8787/ticker
```

Expected JSON output:

```json
[
  {"text": "BTC $76,982"},
  {"text": "ETH $2,129"},
  {"text": "LINK $9.61"},
  {"text": "AAVE $265"},
  {"text": "CRV $0.62"},
  {"text": "ETH GAS Safe 1 / Std 2 / Fast 3 gwei"},
  {"text": "Aave TVL $22.4B"},
  {"text": "Curve TVL $2.1B"},
  {"text": "Chainlink TVL $18.8B"}
]
```

Initial data sources:

- CoinGecko simple price API
- Etherscan gas oracle
- DeFiLlama protocol TVL endpoints

The service should use caching, graceful error handling, and environment variables for secrets.

---

## Important Local Addresses

These are current known/local addresses and may change depending on network configuration.

### Raspberry Pi local LAN

```text
192.168.1.189
```

### Raspberry Pi Tailscale IP

```text
100.82.61.96
```

### CasaOS

```text
http://192.168.1.189
```

or:

```text
http://100.82.61.96
```

### Immich

```text
http://192.168.1.189:2283
```

or:

```text
http://100.82.61.96:2283
```

### Grafana

Usually:

```text
http://192.168.1.189:3000
```

or:

```text
http://100.82.61.96:3000
```

### Future ticker service

```text
http://192.168.1.189:8787/ticker
```

---

## Storage Notes

The external drive is used for storage-heavy services.

Known Immich upload/storage path:

```text
/media/devmon/umbrel/immich
```

Important:

- Do not store large media collections on the Raspberry Pi SD card.
- Storage-heavy services should use the external drive.
- Any new app that stores media, databases, or archives should have its storage path reviewed before deployment.

---

## Backup Philosophy

This system is not considered fully backed up until it follows a 3-2-1 style approach.

Short version:

- 3 copies of important data
- 2 different storage devices/media
- 1 offsite copy

Immediate backup priorities:

1. Back up the Raspberry Pi SD card.
2. Back up the external drive.
3. Save service configs and Docker compose files.
4. Keep recovery notes updated.
5. Use a UPS battery backup when possible.

Critical folders to protect:

```text
/DATA/AppData
/DATA/Gallery
/media/devmon/umbrel/immich
```

---

## Shutdown / Power Notes

The Raspberry Pi should be shut down cleanly before power is removed.

Safe shutdown command:

```bash
sudo shutdown now
```

Avoid hard power cuts while the system is running because they can corrupt:

- SD card
- Docker containers
- Immich database
- app configuration files

Once the shutdown completes and activity lights settle, power can be safely removed.

---

## Security Model

Current security model:

- private local network
- Tailscale for remote access
- no public router port forwarding
- no exposed admin panels
- no committed secrets
- app access limited to trusted devices

Do not publicly expose:

- CasaOS
- Immich
- Grafana admin
- Uptime Kuma
- internal APIs
- ticker-service
- Docker management interfaces

Public dashboards may be created later, but should be separated from private admin systems.

---

## Environment Variables and Secrets

Any service requiring API keys should use a `.env` file or Docker environment variables.

Never commit:

```text
.env
API keys
passwords
tokens
private keys
wallet seed phrases
database credentials
```

Every service folder should include:

```text
.env.example
```

but not the real `.env`.

---

## Codex / AI Development Guidelines

When Codex or another AI coding assistant works in this repo, it should:

1. Read `README.md` first.
2. Read relevant architecture/security docs before changing infrastructure.
3. Avoid hardcoding secrets.
4. Prefer simple Docker Compose deployments.
5. Keep service code beginner-readable.
6. Add README instructions for every new service.
7. Use clear folder boundaries.
8. Avoid breaking existing services.
9. Prioritize local-first and private-by-default design.
10. Explain assumptions before making major architectural changes.

---

## Near-Term Roadmap

### Phase 1: Stabilize Foundation

- Verify Immich storage on external drive
- Confirm backup routine
- Document recovery steps
- Export Grafana dashboards
- Keep Tailscale access working

### Phase 2: Crypto Dashboard

- Build ticker-service
- Add clean Grafana Business Ticker feed
- Add ETH gas panel
- Add DeFi protocol metrics
- Add Chainlink-focused panels
- Add Aave and Curve metrics

### Phase 3: Automation

- Add n8n
- Build scheduled data pulls
- Add alerting
- Add daily summaries
- Add service health notifications

### Phase 4: AI Layer

- Add Open WebUI
- Add Ollama or remote/local model routing
- Create private research assistant workflows
- Connect AI to local docs and dashboards

### Phase 5: Knowledge Vault

- Add Obsidian/WikiJS-style knowledge management
- Build searchable family/project archive
- Add long-term digital inheritance planning
- Store useful documents in durable open formats

---

## Future Service Ideas

Potential services to add later:

- Open WebUI
- Ollama
- n8n
- Postgres
- Redis
- Vector database
- WikiJS
- File Browser
- Jellyfin
- Homepage
- Watchtower
- Prometheus
- Loki
- Grafana Alloy
- Node Exporter
- Cloudflare Tunnel for carefully selected public services

---

## Project Identity

Sovereignty Stack is not just a homelab. It is a personal infrastructure project focused on:

- digital sovereignty
- self-hosting
- local AI
- private data ownership
- crypto/DeFi intelligence
- operational dashboards
- long-term knowledge preservation
- resilient personal computing

This repo should remain practical, readable, and adaptable as the system grows.

---

## Current Priority

The immediate priority is to complete the first custom data service:

```text
ticker-service
```

This will make Grafana’s Business Ticker clean, reliable, and extensible.

Once ticker-service is running, future dashboard development should increasingly happen through version-controlled code instead of manual Grafana clicking.
