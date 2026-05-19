# Sovereignty Stack — SECURITY.md

## Purpose

This document defines the security philosophy, operational practices, exposure rules, and infrastructure safeguards for Sovereignty Stack.

The goal is not enterprise-grade perfection.

The goal is:

```text
reasonable security
+
private-by-default architecture
+
maintainable operational discipline
```

This document exists to:
- guide future infrastructure decisions
- prevent accidental exposure
- document operational security assumptions
- help Codex understand architectural constraints
- reduce risk as the stack grows

---

# Core Security Philosophy

Sovereignty Stack is built around:

```text
private-first infrastructure
```

The default assumption should always be:

```text
local access first
remote access through encrypted mesh
public exposure only when intentional
```

The stack should prioritize:
- simplicity
- visibility
- control
- recoverability
- compartmentalization

over:
- maximum complexity
- premature internet exposure
- unnecessary services
- fragile enterprise tooling

---

# Current Security Model

## Current Operational State

```text
PRIVATE-ONLY
```

The infrastructure is currently intended for:
- personal use
- trusted-device access
- private experimentation
- internal dashboards
- local/self-hosted services

The current system is NOT intended to be:
- publicly exposed
- internet-facing
- anonymous-user accessible
- multi-tenant

---

# Current Access Model

## Local Network Access

Primary local access occurs over the home LAN.

Example current LAN address:

```text
192.168.1.189
```

Benefits:
- simple
- fast
- private
- low attack surface

---

## Tailscale Remote Access

### Current Preferred Remote Access Method

```text
Tailscale
```

### Why Tailscale Is Used

Tailscale provides:
- encrypted remote access
- device authentication
- VPN mesh networking
- minimal router configuration
- reduced public exposure

### Current Model

```text
Remote Device
      ↓
Tailscale encrypted tunnel
      ↓
Raspberry Pi
```

### Current Advantages

- no public router ports
- minimal attack surface
- easy remote access
- identity-based access
- encrypted traffic

---

# Current Public Exposure Policy

## Current Rule

```text
DO NOT EXPOSE SERVICES PUBLICLY
```

unless:
- there is a specific reason
- authentication exists
- monitoring exists
- backups exist
- recovery exists
- the exposure is intentional

---

# Services That Must Remain Private

The following services should currently NEVER be publicly exposed:

```text
CasaOS
Grafana admin
Immich admin
Docker management interfaces
ticker-service
SSH
future AI systems
future vector databases
internal APIs
```

These services may contain:
- admin controls
- private files
- infrastructure access
- API keys
- internal metadata
- operational controls

---

# Router / Network Policy

## Current Policy

### Avoid

```text
manual public port forwarding
```

unless absolutely necessary.

---

## Preferred Alternatives

### Preferred

```text
Tailscale
Cloudflare Tunnel (future)
reverse proxy with auth (future)
```

### Avoid

```text
open router ports
raw service exposure
anonymous admin access
```

---

# Authentication Philosophy

## Current Goal

Every important service should eventually have:
- authentication
- unique credentials
- minimal access permissions

---

# Password Practices

## Current Recommendations

### Use

- long passwords
- unique passwords
- password manager
- generated credentials

### Avoid

- reused passwords
- short passwords
- plaintext credential storage

---

# Secret Management

## Critical Rule

```text
Never hardcode secrets into code repositories.
```

This includes:
- API keys
- passwords
- tokens
- wallet seeds
- SSH keys
- database credentials

---

# Current Secret Storage Strategy

## Preferred Methods

### Use

```text
.env files
Docker environment variables
password manager
```

### Avoid

```text
hardcoded credentials
plaintext repo commits
screenshots with secrets
shared plaintext notes
```

---

# GitHub Security Rules

## Current Repo Philosophy

The repository should be:
- safe to publish
- safe to clone
- safe to share with Codex

---

# Never Commit

```text
.env
private keys
wallet seed phrases
API keys
Tailscale auth keys
SSH private keys
database credentials
```

---

# Required Repo Files

Every service should ideally include:

```text
.env.example
.gitignore
README.md
```

---

# Current API Key Practices

## Current Rule

If an API key is:
- pasted publicly
- uploaded in screenshot
- committed accidentally

then:
```text
ROTATE IT IMMEDIATELY
```

This already occurred during development with an Etherscan key and was corrected.

---

# SSH Security

## Current SSH Usage

SSH is currently used for:
- Raspberry Pi administration
- Docker troubleshooting
- permissions fixes
- service management

---

# SSH Best Practices

## Current Recommendations

### Use

- trusted devices only
- strong passwords
- local/Tailscale-only access

### Future Upgrade Path

Eventually:
- SSH keys
- disabled password login
- fail2ban
- tighter firewall rules

---

# Docker Security

## Current Philosophy

Docker containers should:
- remain isolated
- expose only necessary ports
- use environment variables
- avoid unnecessary privileges

---

# Current Recommendations

### Avoid

- privileged containers
- unnecessary host mounts
- exposing admin ports publicly

### Prefer

- minimal port exposure
- isolated services
- explicit volume mappings

---

# CasaOS Security

## Current Role

CasaOS is a management layer.

It should currently remain:
```text
private-only
```

---

# Important Rule

Do not expose CasaOS publicly.

A compromised CasaOS instance could potentially:
- control Docker containers
- expose storage
- affect infrastructure

---

# Grafana Security

## Current State

Grafana is currently internal/private.

---

# Current Recommendations

### Allow

- local access
- Tailscale access

### Avoid

- public anonymous admin
- exposing dashboards publicly too early

---

# Future Public Dashboards

Public dashboards may exist later, but:
- should be separated from admin dashboards
- should have restricted data
- should not expose infrastructure internals

---

# Immich Security

## Current State

Immich currently stores:
- private photos
- personal media
- future family archive data

Therefore:
```text
Immich should remain private.
```

---

# Current Recommendations

### Use

- Tailscale access
- local-only access
- strong passwords

### Avoid

- public exposure
- weak credentials
- anonymous access

---

# AI / Future Model Security

## Future Risk Area

Future AI systems may eventually access:
- notes
- archives
- dashboards
- APIs
- personal data

This creates additional security considerations.

---

# Future AI Security Principles

AI systems should:
- remain inspectable
- remain modular
- use scoped permissions
- avoid unrestricted shell access
- avoid unrestricted internet access
- avoid automatic infrastructure control

---

# Storage Security

## Current Storage Layout

### SD Card

Current use:
- OS
- configs
- lightweight persistent data

### External HDD

Current use:
- Immich uploads
- future archives
- future datasets

---

# Current Storage Risks

## SD Card Failure

Risk:
Raspberry Pi SD cards wear out over time.

Mitigation:
- backups
- future SSD migration

---

## Single Drive Risk

Risk:
A single external drive is NOT true backup.

Mitigation path:
- second drive
- offsite backups
- export workflows

---

# Backup Security

## Current Philosophy

Backups should be:
- isolated
- testable
- recoverable
- documented

---

# Current Backup Priorities

Critical data:
- Immich uploads
- Docker configs
- Grafana dashboards
- service documentation
- infrastructure notes

---

# Recommended Backup Model

Approximate:

```text
3-2-1 backup strategy
```

Meaning:
- 3 copies
- 2 storage types
- 1 offsite

---

# Operational Security Practices

## Current Recommendations

### Before Deploying New Services

Ask:
- does it need internet access?
- does it store sensitive data?
- does it need external exposure?
- does it require persistent storage?
- does it require backups?
- what happens if it breaks?

---

# Current Infrastructure Discipline

## Prefer

- documented changes
- GitHub-tracked configs
- version-controlled infrastructure
- small modular services

## Avoid

- undocumented clicking
- random experimental containers
- abandoned services
- mystery configs

---

# Codex / AI Development Security Rules

## Important Constraints

When Codex or AI tooling modifies infrastructure:

### It should:

- read security docs first
- avoid hardcoded secrets
- avoid public exposure assumptions
- prefer Dockerized services
- preserve private-by-default architecture

### It should NOT:

- expose ports unnecessarily
- commit secrets
- assume cloud deployment
- bypass authentication intentionally

---

# Future Security Improvements

## Planned Improvements

### Infrastructure

- UPS battery backup
- SSD boot
- automated backups
- health monitoring

### Networking

- Cloudflare Tunnel
- reverse proxy
- HTTPS
- segmented public/private services

### Authentication

- SSH keys
- tighter permissions
- service-specific accounts

### Monitoring

- intrusion monitoring
- failed login tracking
- resource anomaly monitoring

---

# Current Threat Model

Sovereignty Stack currently assumes the biggest realistic risks are:

```text
misconfiguration
accidental exposure
hardware failure
credential leaks
lack of backups
```

—not nation-state adversaries.

Security decisions should remain:
- practical
- understandable
- maintainable

---

# Security Priority Order

Current recommended priority order:

1. backups
2. private networking
3. secret hygiene
4. documentation
5. access control
6. monitoring
7. public exposure hardening

---

# Current Strategic Security Goal

The long-term goal is:

```text
personally-controlled infrastructure
without unnecessary exposure
without cloud dependence
without losing maintainability
```

while preserving:
- usability
- portability
- modularity
- recoverability
