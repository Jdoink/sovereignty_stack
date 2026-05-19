# Sovereignty Stack — HARDWARE.md

## Purpose

This document tracks the physical hardware currently used by Sovereignty Stack, its role within the architecture, current operational status, limitations, and future upgrade paths.

The goal is to:
- document infrastructure dependencies
- simplify troubleshooting
- preserve operational knowledge
- help future hardware upgrades
- help Codex understand physical constraints
- maintain continuity as the stack evolves

This document should remain grounded in the actual deployed hardware and should be updated whenever infrastructure changes.

---

# Current Hardware Summary

## Active Core Components

### Compute
- Raspberry Pi 4

### Display / Visualization
- HP TouchSmart all-in-one PC

### Storage
- External HDD

### Networking
- Home router + Tailscale mesh VPN

### User Devices
- iPhone
- laptop/desktop browsers

---

# Primary Compute Node

# Raspberry Pi 4

## Current Role

The Raspberry Pi 4 is the central infrastructure node for Sovereignty Stack.

Current responsibilities include:
- Docker host
- CasaOS host
- Grafana backend
- Immich backend
- Uptime Kuma
- API aggregation
- future automation layer
- future AI gateway/orchestration

---

## Current Status

```text
WORKING
```

---

## Current Operating System

```text
Debian Linux
```

with:
```text
CasaOS
```

installed on top.

---

## Why The Raspberry Pi Was Chosen

### Advantages

- inexpensive
- low power usage
- silent
- widely supported
- excellent Linux compatibility
- strong self-hosting ecosystem
- easy to replace
- good learning platform

### Architectural Benefit

The Raspberry Pi is ideal for:
- lightweight services
- dashboards
- APIs
- automation
- storage orchestration
- remote infrastructure access

---

## Current Limitations

### CPU

The Raspberry Pi 4 is not ideal for:
- heavy AI inference
- large local LLMs
- large databases
- many simultaneous users

### RAM

RAM constraints may become noticeable with:
- many Docker containers
- local AI tools
- vector databases
- heavy analytics pipelines

### Storage Medium

The OS currently relies on:
```text
microSD storage
```

which has limitations:
- write endurance
- corruption risk
- performance bottlenecks

---

## Future Raspberry Pi Improvements

## Planned Upgrade Paths

### SSD Boot

High-priority future improvement.

Benefits:
- reliability
- speed
- reduced SD wear
- faster container performance

---

### Cooling Improvements

Potential future additions:
- active cooling
- better heatsinks
- improved airflow

---

### UPS Battery Backup

Future improvement.

Purpose:
- graceful shutdowns
- corruption prevention
- uptime stability

---

# External Storage

# External HDD

## Current Role

The external hard drive acts as the primary persistent storage layer.

---

## Current Known Mount Path

```text
/media/devmon/umbrel
```

---

## Current Immich Storage Path

```text
/media/devmon/umbrel/immich
```

---

## Current Responsibilities

- Immich media storage
- photo/video archive
- future datasets
- future backups
- future knowledge vault storage

---

## Current Status

```text
WORKING
```

---

## Current Design Philosophy

The external HDD exists to:
- avoid SD card wear
- separate storage from compute
- enable larger archives
- simplify future migrations

---

## Current Risks

### Single Drive Risk

The current external drive is NOT a complete backup solution.

Current risk:
```text
single point of failure
```

Mitigation path:
- second drive
- offsite backups
- replication workflows

---

## Future Storage Improvements

### Possible Future Additions

- SSD storage
- NAS
- RAID
- ZFS
- snapshots
- mirrored backup drives

---

# Dashboard / Visualization Layer

# HP TouchSmart

## Current Role

The HP TouchSmart serves as the primary visualization and interaction node.

It functions as:
- command center display
- fullscreen dashboard terminal
- weather/radar station
- crypto operations display
- future AI interaction screen

---

## Current Status

```text
WORKING
```

---

## Current Usage Pattern

Typical workflow:
- Raspberry Pi handles backend services
- HP TouchSmart displays dashboards
- browser runs Grafana in fullscreen/kiosk mode

---

## Current Browser Situation

A modern browser was installed to improve:
- Grafana compatibility
- Immich compatibility
- dashboard rendering
- fullscreen stability

---

## Current Aesthetic Direction

Target vibe:

```text
retro-futuristic operations terminal
```

The HP TouchSmart aesthetic is intentionally being embraced as part of the command-center experience.

---

## Architectural Importance

The HP TouchSmart is important because it:
- creates a persistent visual interface
- encourages dashboard-driven workflows
- makes infrastructure tangible/visible
- acts as a dedicated operational display

---

# Networking Hardware

# Home Router

## Current Role

The home router provides:
- LAN networking
- internet connectivity
- local service access

---

## Current Security Philosophy

Avoid:
```text
public port forwarding
```

Preferred remote-access method:
```text
Tailscale
```

---

# User Devices

# iPhone

## Current Uses

- Immich uploads
- remote dashboard access
- Tailscale access
- infrastructure monitoring

---

## Current Workflow

```text
iPhone
   ↓
Tailscale
   ↓
Raspberry Pi services
```

---

# Laptop / Desktop Browsers

## Current Uses

- CasaOS administration
- SSH access
- Grafana editing
- GitHub/Codex workflows
- Docker troubleshooting

---

# Current Networking Addresses

## Local LAN

### Raspberry Pi

```text
192.168.1.189
```

---

## Tailscale

### Raspberry Pi Tailscale IP

```text
100.82.61.96
```

---

# Current Power Philosophy

## Current Operational Style

The Raspberry Pi may be shut down nightly when:
- the router is powered down
- the system is not needed

---

## Important Operational Rule

The Raspberry Pi should ideally be:
```text
properly shut down before power removal
```

Recommended command:

```bash
sudo shutdown now
```

or equivalent CasaOS shutdown workflow.

---

## Current Known Risks

Hard power removal can risk:
- SD corruption
- container corruption
- database corruption
- filesystem inconsistencies

---

# Current Thermal Situation

The Raspberry Pi previously experienced elevated temperatures during heavier workloads.

Improvements already observed:
- cooling adjustments
- fan usage
- workload management

---

# Current Hardware Priorities

## Priority 1

Improve:
```text
backup redundancy
```

---

## Priority 2

Improve:
```text
storage reliability
```

Potentially:
- SSD boot
- second drive

---

## Priority 3

Improve:
```text
power stability
```

Potentially:
- UPS battery backup

---

## Priority 4

Improve:
```text
AI capability
```

Potential future hardware:
- mini PC
- GPU-capable node
- dedicated AI server

---

# Future Expansion Possibilities

# Compute Expansion

## Possible Future Hardware

### Mini PC

Benefits:
- better CPU
- better RAM capacity
- lower friction AI tooling
- stronger Docker performance

---

### Dedicated AI Node

Potential future role:
- Ollama
- local LLMs
- embeddings
- vector databases
- AI agents

---

# Storage Expansion

## Possible Future Hardware

### NAS

Potential role:
- centralized backups
- media storage
- snapshotting
- archive durability

---

### RAID / ZFS

Potential future goals:
- redundancy
- integrity checking
- snapshots
- recovery workflows

---

# Networking Expansion

## Potential Future Improvements

### Segmented Networks

Potential future:
- infrastructure VLAN
- public dashboard VLAN
- IoT separation

---

### Reverse Proxy

Potential future:
- HTTPS
- cleaner URLs
- selective exposure

---

# Hardware Philosophy

Sovereignty Stack intentionally began on:
```text
repurposed consumer hardware
```

This is a feature, not a weakness.

The philosophy is:
- learn deeply
- iterate gradually
- avoid premature enterprise complexity
- build modularly
- prioritize ownership and understanding

---

# Current Operational Reality

The system has already successfully achieved:

- self-hosted infrastructure
- remote encrypted access
- persistent external storage
- private photo cloud
- operational dashboards
- live API-based telemetry
- GitHub/Codex-ready workflows

using:
- low-cost hardware
- modular software
- self-hosted infrastructure principles

---

# Long-Term Hardware Vision

The long-term vision is not necessarily:
```text
massive enterprise hardware
```

Instead, the vision is:
```text
modular
private
efficient
understandable
maintainable
upgradeable
```

with hardware chosen intentionally based on:
- operational needs
- reliability
- maintainability
- ownership
- privacy
