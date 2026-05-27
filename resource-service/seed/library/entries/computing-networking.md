---
title: "Networking: How a Request Crosses the World (IP, TCP & DNS)"
slug: computing-networking
domain: Computing
topics:
- computing
- networking
- internet
summary: The internet has no central wire — just billions of machines following shared rules. Data is split into packets, addressed with IP, delivered reliably by TCP, and found by name through DNS. These few protocols carry everything online.
status: canonical
confidence: high
tier: deep-dive
order: 5
verified: "2026-05-27"
sources:
- title: "Cloudflare Learning Center — What is DNS?"
  url: https://www.cloudflare.com/learning/dns/what-is-dns/
  type: article
  retrieved: "2026-05-27"
- title: "Ilya Grigorik — High Performance Browser Networking (free, O'Reilly)"
  author: Ilya Grigorik
  url: https://hpbn.co/
  type: book
  retrieved: "2026-05-27"
media:
- computing/packet-journey.svg
related:
- computing-operating-systems
- computing-web-tls
---

## The big idea: no center, just shared rules

There is no master computer running the internet. It's a network *of* networks: billions of independent machines that cooperate only by agreeing on **protocols** — shared rules for formatting and exchanging data. A handful of these protocols do almost all the work.

![What happens when you open a web page](/library-assets/computing/packet-journey.svg)

## Packets: chop it up and send the pieces

Data doesn't travel as one continuous stream. It's chopped into small **packets**, each carrying a chunk of data plus addressing info — like mailing a book one page at a time, each page in its own addressed envelope. Packets can take different routes and arrive out of order; that's fine, because of the protocols below.

## IP — addressing and routing

The **Internet Protocol (IP)** gives every device an **IP address** (e.g., `192.168.1.189` on your LAN) and defines how **routers** pass packets toward their destination. Each router just forwards a packet one hop closer, based on its address — no router knows the whole path. IP is **best-effort**: it tries to deliver packets but makes no promises about order or success. That reliability is someone else's job.

## TCP — reliability on top of best-effort IP

The **Transmission Control Protocol (TCP)** runs *on top of* IP and adds the guarantees applications need:

- **Ordering** — reassembles packets into the original order.
- **Reliability** — detects lost packets and **retransmits** them.
- **Connections** — a handshake establishes a session between two programs.
- **Ports** — numbers (like 8789 for your service) that say *which program* on a machine the data is for.

(Its sibling **UDP** skips these guarantees for speed — used for video calls and games, where a late packet is worse than a lost one.)

## DNS — names instead of numbers

Humans use names like `github.com`, but routing needs numeric IP addresses. The **Domain Name System (DNS)** — "the phonebook of the internet" (Cloudflare, in the sources) — translates names to addresses. A **resolver** asks a chain of servers (root → top-level domain → the domain's authoritative server) and gets back the IP. This lookup almost always happens *first*, before any connection.

## Putting it together

When you open a page:
1. **DNS** turns the name into an IP address.
2. Your device opens a **TCP** connection to that IP, on the right **port**.
3. The request and response travel as **IP packets**, hopping router to router, with TCP ensuring nothing is lost or out of order.

That's the internet's machinery. What rides *on top* of it — the actual web page, and how it's encrypted — is the final layer.

## Why this matters for your stack

- Your Pi has an **IP address** on the LAN/tailnet; services listen on **ports** (8789, 3000…).
- `ping`, `traceroute`, and DNS lookups (in the **Mastery** tier) let you *watch* these protocols and diagnose "why can't I reach it?" — almost always DNS, IP/routing, or a port/firewall.
