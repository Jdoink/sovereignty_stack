---
title: "Mastery Path: Build It, Trace It, Map It"
slug: computing-mastery
domain: Computing
topics:
- computing
- mastery
- projects
summary: Three projects that turn the layers into instinct — build a working CPU from logic gates in a simulator, trace a real packet across the internet, and map your own stack end to end.
status: reviewed
confidence: high
tier: mastery
order: 0
verified: "2026-05-27"
sources:
- title: "nand2tetris — From Nand to Tetris (course + software)"
  url: https://www.nand2tetris.org/
  type: course
  retrieved: "2026-05-27"
- title: "Ben Eater — Build an 8-bit computer from scratch"
  author: Ben Eater
  url: https://eater.net/8bit
  type: video
  retrieved: "2026-05-27"
media: []
related:
- computing-resources
- computing-cpu
- computing-networking
---

Reading about the layers is good; *building and watching* them is what makes the knowledge permanent. Do these in order.

## Project 1 — Build a computer from a single gate (the big one)

Work through **nand2tetris** ([course](https://www.nand2tetris.org/)). Starting from one NAND gate, you build — in a free simulator, no hardware needed — logic gates, an adder, memory, a CPU, and finally a machine that runs real programs. Aim for **Projects 1–5** (hardware): you will *construct* the exact chain this wing describes, gates → CPU.

Prefer something more game-like? **Turing Complete** (a paid puzzle game) covers the same journey. Want real hardware on a breadboard? **Ben Eater's 8-bit computer** ([eater.net/8bit](https://eater.net/8bit)) is the gold standard.

**Goal:** the single most satisfying "aha" in computing — *I built a CPU and I know exactly how it works.*

## Project 2 — Trace a packet across the planet (½ hour)

On your Pi or laptop, run these and read the output:

- `ping github.com` — watch round-trip times; see that a name resolved to an IP.
- `traceroute github.com` (or `tracert` on Windows) — see **every router hop** between you and the server. This is the packet journey from the *Networking* entry, live.
- `nslookup github.com` or `dig github.com` — watch **DNS** turn a name into an address.
- Optional: install **Wireshark** and watch a TLS handshake and HTTP request actually happen on the wire.

**Goal:** make IP, DNS, and TCP concrete by *seeing* them, and gain the exact tools you'll use to debug your own stack.

## Project 3 — Map your own stack end to end (½ day)

Write a new Library entry that traces what happens when you load your Vault from your phone:

- Which **IP/port** is the Pi on? Which **process/container** serves each page?
- Walk the full path: **DNS/host → TCP → TLS → HTTP → the OS handing it to your service → the response rendering in the browser.**
- Note where the **Seagate (storage)** vs **RAM** are involved.

**Goal:** connect the abstract layers to *your* hardware. If you can narrate your own stack with no gaps, you've understood the machine.

## You've mastered this wing when…

- You've built (in sim or hardware) the chain from logic gates to a running CPU.
- You can run `traceroute`/`dig` and explain every line.
- You can trace a request through your own stack — DNS, TCP, TLS, HTTP, OS, CPU, memory, storage — without hand-waving.
- "Why is this slow / unreachable?" becomes a layered diagnosis, not a mystery.
