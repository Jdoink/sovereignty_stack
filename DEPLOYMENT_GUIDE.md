# Sovereignty Stack — DEPLOYMENT_GUIDE.md

## Purpose

This document defines the preferred deployment patterns, service standards, and infrastructure conventions for Sovereignty Stack.

It exists to:
- standardize future deployments
- reduce configuration drift
- improve reproducibility
- simplify troubleshooting
- help Codex deploy services consistently
- avoid fragile infrastructure practices

This document is focused on:
```text
HOW services should be deployed
```

—not just what services exist.

---

# Core Deployment Philosophy

Sovereignty Stack should prioritize:

```text
simple
modular
documented
recoverable
containerized deployments
```

The system should avoid:
- undocumented installs
- mystery scripts
- random port sprawl
- hidden dependencies
- hardcoded secrets
- overly complex orchestration

---

# Preferred Deployment Stack

## Current Standard Stack

```text
Debian Linux
    ↓
CasaOS
    ↓
Docker
    ↓
Service Containers
```

This is the current operational foundation.

---

# Current Deployment Model

## Preferred Pattern

Each major service should ideally have:

```text
dedicated folder
docker compose file
README
environment variables
persistent storage mapping
```

---

# Standard Service Structure

## Preferred Layout

Example:

```text
service-name/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── config/
├── data/
└── backups/
```

---

# Docker Philosophy

## Preferred Container Model

Services should be:
- isolated
- modular
- replaceable
- reproducible

Containers should:
- expose minimal ports
- use persistent volumes intentionally
- avoid privileged mode unless required

---

# Docker Compose Standards

## Preferred Compose Practices

### Use Explicit Names

Example:

```yaml
container_name: ticker-service
```

---

### Use Restart Policies

Preferred:

```yaml
restart: unless-stopped
```

---

### Use Environment Variables

Never hardcode:
- API keys
- passwords
- secrets

Use:

```yaml
env_file:
  - .env
```

or:
```yaml
environment:
```

---

### Use Persistent Volumes Carefully

Storage-heavy services should map to:
```text
external HDD
```

when appropriate.

---

# Storage Mapping Philosophy

# SD Card

## Use For

- operating system
- lightweight configs
- small service metadata

---

## Avoid For

- media
- archives
- databases with heavy writes
- large datasets

---

# External HDD

## Preferred Uses

- Immich uploads
- archives
- datasets
- exported dashboards
- backups
- media-heavy services

---

# Current Important Storage Paths

## External Drive Root

```text
/media/devmon/umbrel
```

---

## Immich Storage

```text
/media/devmon/umbrel/immich
```

---

# Port Management Philosophy

## Current Recommendation

Maintain a documented list of:
- ports
- services
- access methods

Avoid:
```text
random undocumented port usage
```

---

# Current Known Service Ports

## CasaOS

```text
80
```

---

## Grafana

```text
3000
```

---

## Immich

```text
2283
```

---

## Planned ticker-service

```text
8787
```

---

# Networking Philosophy

# Current Security Model

```text
private-first
```

Preferred access:
- LAN
- Tailscale

Avoid:
- public router exposure
- anonymous admin access

---

# Current Remote Access Standard

## Preferred

```text
Tailscale
```

---

## Avoid

```text
raw public exposure
manual router forwarding
```

unless intentional and documented.

---

# Deployment Environment Standards

## Preferred Deployment Targets

### Raspberry Pi 4

Current primary deployment target.

Current strengths:
- low power
- lightweight services
- dashboard hosting
- APIs
- automation

---

# Future Deployment Targets

Potential future:
- mini PC
- NAS
- AI node
- GPU-capable system

---

# Documentation Requirements

# Every Service Should Include

## Required

### README.md

Should explain:
- purpose
- deployment
- ports
- dependencies
- storage
- environment variables

---

### .env.example

Should show:
- required variables
- placeholders only

Never include real secrets.

---

### docker-compose.yml

Should be:
- readable
- commented when useful
- beginner-understandable

---

# Logging Philosophy

## Current Recommendation

Services should:
- log clearly
- fail visibly
- avoid silent failure

Important failures should be:
- understandable
- searchable
- recoverable

---

# Backup-Aware Deployment

## Before Deploying New Services

Ask:
- where does data live?
- does it require backups?
- how is it recovered?
- what happens if container is deleted?
- what happens if storage disappears?

---

# Current Service Categories

# Category 1 — Critical Personal Data

Examples:
- Immich
- future knowledge vaults

Requirements:
- external storage
- backup planning
- careful updates

---

# Category 2 — Infrastructure

Examples:
- Grafana
- Uptime Kuma
- future monitoring tools

Requirements:
- exported configs
- reproducibility
- documented ports

---

# Category 3 — Experimental Services

Examples:
- AI experiments
- temporary dashboards
- prototype APIs

Requirements:
- isolated deployment
- easy removal
- low risk to core stack

---

# Current Deployment Workflow

# Recommended Workflow

## Step 1

Document:
- purpose
- ports
- storage needs

---

## Step 2

Create:
```text
dedicated service folder
```

---

## Step 3

Add:
- docker-compose.yml
- README.md
- .env.example

---

## Step 4

Deploy locally first.

---

## Step 5

Verify:
- logs
- storage
- networking
- restart behavior

---

## Step 6

Add to:
- GitHub
- documentation
- dashboards if needed

---

# Current GitHub Philosophy

## GitHub Should Become

```text
source of truth
```

for:
- configs
- architecture
- deployment definitions
- dashboard exports
- service documentation

---

# Current Codex Philosophy

## Codex Should

- read docs before modifying infra
- preserve architecture consistency
- avoid hardcoded secrets
- avoid overengineering
- prefer readable implementations
- use Dockerized services

---

# Current Infrastructure Guardrails

## Avoid

- random installations
- undocumented services
- hidden cron jobs
- mystery scripts
- giant monolithic deployments

---

## Prefer

- modular services
- documented configs
- version-controlled deployments
- reproducible infrastructure

---

# Future Deployment Goals

Eventually Sovereignty Stack should support:

## AI Services
- Open WebUI
- Ollama
- vector databases
- AI agents

## Automation
- n8n
- scheduled workflows
- notifications

## Analytics
- DeFi dashboards
- weather intelligence
- protocol monitoring

## Knowledge
- WikiJS
- searchable archives
- documentation systems

---

# Future Public Exposure Strategy

Public services should eventually use:
- HTTPS
- reverse proxy
- authentication
- Cloudflare Tunnel

Avoid:
```text
raw internet exposure
```

---

# Current Operational Priority

## Immediate Priority

Complete:
```text
ticker-service
```

and establish:
```text
clean repeatable deployment patterns
```

before rapidly expanding infrastructure.

---

# Long-Term Deployment Goal

Sovereignty Stack should eventually become:

```text
self-documenting
reproducible
modular
recoverable
AI-assisted infrastructure
```

without sacrificing:
- simplicity
- ownership
- maintainability
- visibility
