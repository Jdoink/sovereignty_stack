---
title: "The Web & TLS: Clients, Servers, and Encrypted Connections"
slug: computing-web-tls
domain: Computing
topics:
- computing
- web
- http
- tls
summary: The web is built on a simple request/response conversation (HTTP) between a browser and a server, carrying HTML, CSS, and JavaScript. TLS wraps that conversation in encryption and identity checks — the "s" in https. Together they let you trace a page load end to end.
status: canonical
confidence: high
tier: deep-dive
order: 6
verified: "2026-05-27"
sources:
- title: "Ilya Grigorik — High Performance Browser Networking (free, O'Reilly)"
  author: Ilya Grigorik
  url: https://hpbn.co/
  type: book
  retrieved: "2026-05-27"
- title: "MDN Web Docs — An overview of HTTP"
  url: https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview
  type: docs
  retrieved: "2026-05-27"
media: []
related:
- computing-networking
- computing-operating-systems
---

## The web is a request/response conversation

The **web** rides on top of the networking layer as a simple pattern: a **client** (your browser) sends a **request**, a **server** sends back a **response**. The language of that conversation is **HTTP (HyperText Transfer Protocol)**.

A request says, in effect, *"GET me the document at this path."* Key parts:

- A **method** — `GET` (fetch), `POST` (send data), `DELETE`, etc. (Your Library's API uses exactly these.)
- A **URL** — names the server and the path (`https://github.com/Jdoink/sovereignty_stack`).
- **Headers** — metadata (what formats you accept, cookies, etc.).

The response carries a **status code** — `200` OK, `404` Not Found, `500` server error — plus headers and the content itself.

## What the server sends back

For a web page, the response body is usually **HTML** (the structure and text), which references:

- **CSS** — how it looks (layout, colors, fonts).
- **JavaScript** — what it does (interactivity; e.g., your Library page fetching entries and rendering the lobby).

The browser fetches the HTML, then makes *more* HTTP requests for each CSS file, script, and image, and assembles the final page. One page view is often dozens of requests.

## TLS — the "s" in https

Plain HTTP is readable by anyone the packets pass through. **TLS (Transport Layer Security)** wraps the HTTP conversation to provide:

- **Encryption** — eavesdroppers see only scrambled bytes.
- **Integrity** — tampering in transit is detectable.
- **Authentication** — a **certificate** proves the server really is who the name claims, validated against trusted certificate authorities.

`https://` simply means "HTTP carried inside TLS." Before any request is sent, client and server perform a **TLS handshake** to agree on keys. (The cryptography that makes this possible — public keys, signatures, certificates — is its own wing; this is where Computing hands off to **Cryptography**.)

## The whole journey, end to end

You now have every layer to trace what happens when you press Enter on a URL:

1. **DNS** resolves the name to an IP address. *(Networking)*
2. Your device opens a **TCP** connection to that IP and port. *(Networking)*
3. A **TLS handshake** sets up encryption and verifies the server's certificate. *(Web/Crypto)*
4. The browser sends an **HTTP GET** request over that secure connection. *(Web)*
5. The server's **OS** hands the request to the web server **process**. *(OS)*
6. The server responds with **HTML**; the browser fetches linked **CSS/JS**, then renders the page — its **CPU** running the rendering code, working in **RAM**. *(Web → CPU → Memory)*

Every step rests on a layer this wing has covered, all the way down to **logic gates**. That end-to-end trace — being able to narrate it without gaps — is the mark that you've understood the machine.

## Why this matters for your stack

- Your services *are* HTTP servers; the Library talks to them with `GET`/`POST`/`DELETE` exactly as above.
- Knowing status codes and the request/response model makes debugging your own stack straightforward: a `404` is a wrong path, a `500` is the server erroring, a hang is usually the network or a blocked process.
