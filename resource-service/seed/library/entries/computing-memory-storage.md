---
title: "Memory & Storage: Where the Bits Live"
slug: computing-memory-storage
domain: Computing
topics:
- computing
- memory
- storage
summary: RAM is the fast, forgetful workspace a CPU works in; storage is the slow, permanent shelf. The "memory hierarchy" — registers to cache to RAM to disk — is the trade-off between speed, size, and cost that shapes how every computer behaves.
status: canonical
confidence: high
tier: deep-dive
order: 3
verified: "2026-05-27"
sources:
- title: "Crash Course Computer Science — Memory & Storage"
  author: Carrie Anne Philbin / PBS
  url: https://www.youtube.com/playlist?list=PL8dPuuaLjXtNlUrzyH5r6jN9ulIgZBpdo
  type: video
  retrieved: "2026-05-27"
- title: "Operating Systems: Three Easy Pieces — Memory virtualization"
  author: Remzi & Andrea Arpaci-Dusseau
  url: https://pages.cs.wisc.edu/~remzi/OSTEP/
  type: book
  retrieved: "2026-05-27"
media: []
related:
- computing-cpu
- computing-operating-systems
---

## Two different jobs: workspace vs. shelf

People lump "memory" together, but there are two distinct things:

- **RAM (random-access memory)** — the CPU's **workspace**. Fast, and any location can be read in roughly the same tiny time ("random access"). But it's **volatile**: cut the power and it's wiped. This is where your running programs and their current data live.
- **Storage (SSD/HDD)** — the **shelf**. Much slower, but **non-volatile**: it keeps data with the power off. Your files, the OS, and installed programs sit here until needed.

The classic mental model: RAM is your **desk** (small, instantly reachable, cleared each night); storage is the **filing cabinet** (large, permanent, slower to fetch from). To work on a file, the computer copies it from the cabinet to the desk; to keep changes, it must write them back. This is exactly why **unsaved work is lost when the power drops** — it existed only on the volatile desk.

## Addresses: how the CPU finds anything

Memory is a vast array of byte-sized cells, each with a numeric **address**. The CPU reads or writes by address — "fetch the byte at address 5,001,234." Addresses are how a program counter points to the next instruction, and how variables are located. Everything is bytes at numbered addresses.

## The memory hierarchy: speed vs. size vs. cost

You can't have memory that is simultaneously huge, instant, permanent, and cheap — so computers layer it, fastest/smallest at the top:

1. **Registers** (inside the CPU) — a few dozen values, sub-nanosecond.
2. **Cache** (L1/L2/L3, on the CPU) — a few MB of recently used data, kept close to avoid the slow trip to RAM.
3. **RAM** — gigabytes, nanoseconds, volatile.
4. **Storage (SSD/HDD)** — terabytes, far slower, permanent.
5. **(Network/Cloud)** — effectively unlimited, slowest of all.

Each layer is bigger and slower than the one above. The CPU keeps what it's using *now* near the top and reaches down only when it must. **Most "why is this slow?" answers live here** — the CPU stalling while it waits for data to climb up from a lower, slower layer.

## Why this matters for your stack

- Your Pi has limited RAM; running too much at once forces it to "swap" to the much slower drive, and everything crawls.
- The Seagate is **storage** (permanent, the source of truth for your Library files); RAM only holds what's actively being served.
- Backups matter precisely because storage is your *only* non-volatile copy — and drives, unlike RAM, can still fail. The next layer up, the **operating system**, is what orchestrates all of this for you.
