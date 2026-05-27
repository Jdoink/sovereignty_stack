---
title: Computers in About 3 Hours — Start Here
slug: computing-intro
domain: Computing
topics:
- computing
- intro
summary: A guided first pass — a superb video series to watch, the one book that builds a computer from a switch, and a short tour of how the internet actually moves your data.
status: reviewed
confidence: high
tier: intro
order: 0
verified: "2026-05-27"
sources:
- title: "Crash Course Computer Science (full series, ~40 short episodes)"
  author: Carrie Anne Philbin / PBS
  url: https://www.youtube.com/playlist?list=PL8dPuuaLjXtNlUrzyH5r6jN9ulIgZBpdo
  type: video
  retrieved: "2026-05-27"
- title: "Charles Petzold — Code: The Hidden Language of Computer Hardware and Software"
  author: Charles Petzold
  url: https://www.charlespetzold.com/code/
  type: book
  retrieved: "2026-05-27"
- title: "Cloudflare Learning Center — What is DNS?"
  url: https://www.cloudflare.com/learning/dns/what-is-dns/
  type: article
  retrieved: "2026-05-27"
media: []
related:
- computing-eli5
- computing-roadmap
- computing-bits-logic-gates
- computing-networking
---

If you have one evening, this is the highest-leverage way to spend it. You won't master computing in three hours — but you'll have a true mental model of the whole machine.

## 1. Watch (60–90 min) — the whole tower, fast

**Crash Course Computer Science**, episodes 1–10 ([playlist](https://www.youtube.com/playlist?list=PL8dPuuaLjXtNlUrzyH5r6jN9ulIgZBpdo)).

Carrie Anne Philbin builds the story from early computing and binary up through logic gates, the CPU, memory, and instructions — in punchy ten-minute episodes. Watch the first ten back-to-back. Don't take notes; just let the *layers* register: switches → gates → CPU → memory → software.

## 2. Read (browse 45 min) — a computer, from a single switch

**Charles Petzold, *Code*** ([book site](https://www.charlespetzold.com/code/)).

The classic that builds a working computer starting from a flashlight and a telegraph relay, one idea at a time, with no hand-waving. Read the early chapters on binary and logic; it makes the video click into place. (The 2nd edition has a free interactive companion site.)

## 3. Read (20 min) — how your request crosses the world

**Cloudflare, *What is DNS?*** ([article](https://www.cloudflare.com/learning/dns/what-is-dns/)).

DNS is "the phonebook of the internet" — it turns a name like `example.com` into a numeric address a machine can route to. Understanding this one lookup is the doorway to understanding networking.

## You should now be able to explain…

- Why everything inside a computer is ultimately **binary** (on/off), and that the meaning is a *code we chose*.
- What a **logic gate** is, and how gates build arithmetic, memory, and decisions.
- The CPU's basic loop: **fetch an instruction, do it, repeat** — billions of times a second.
- The rough difference between the **CPU**, **memory (RAM)**, and **storage**.
- What **DNS** does, and that data travels the internet as **packets** hopping between machines.

If those land, you're ready for the **Deep Dive** — six entries, one per layer, from logic gates to encrypted web connections.
