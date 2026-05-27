---
title: About the Library
slug: about-the-library
domain: Meta
topics:
- library
- how-to
- curation
summary: How this knowledge substrate works — files-as-truth, cited sources, tiered learning paths, and a curation lifecycle built for longevity.
status: canonical
confidence: high
tier: roadmap
order: 0
verified: "2026-05-27"
sources:
- title: Sovereignty Stack — repository & architecture
  url: https://github.com/Jdoink/sovereignty_stack
  type: primary
  retrieved: "2026-05-27"
media: []
related: []
---

The Library is a **curated knowledge substrate** — a place to record, categorize, search, and *preserve* high-value knowledge, rather than let it scatter across bookmarks and notes.

## Files as the source of truth

Every entry is a plain **Markdown file with YAML front-matter**, stored on the Seagate under `library/entries/`. Media and **archived snapshots of cited sources** live alongside in `library/assets/`. The search index is *derived* from these files and can be rebuilt at any time — so the files themselves, readable in any text editor, are what endures.

## Learning paths, in five tiers

Each subject (a **Domain**, or wing) is organized as a ladder you can climb from zero:

1. **ELI5** — the core idea in plain language and one good analogy.
2. **Intro (1–3 hr)** — a guided starting point with a few hand-picked pieces.
3. **Deep Dive** — one cited entry per core concept; the real substance.
4. **Mastery** — projects and primary texts that turn understanding into ability.
5. **Resources** — the curated, archived library of books, courses, and tools.

## Curation lifecycle

Entries move through three states:

- **Seedling** — a capture or draft, not yet verified.
- **Reviewed** — checked over and tidied.
- **Canonical** — trusted; *requires at least one cited source*.

## Citations that outlive the web

Each source records its URL **and** a saved local copy, so the knowledge survives even when the original page disappears. Every entry shows when it was last verified, so stale knowledge is visible rather than hidden.
