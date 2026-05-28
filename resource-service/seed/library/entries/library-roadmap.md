---
title: Library Roadmap & Refinement Plan
slug: library-roadmap
domain: Meta
topics:
- library
- roadmap
- planning
summary: The living plan for the Library itself — what's built, what's next, and the decisions behind it. Kept here so it is never lost. Edit this entry as priorities change.
status: reviewed
confidence: high
tier: roadmap
order: 1
verified: "2026-05-27"
sources:
- title: "Sovereignty Stack — repository"
  url: https://github.com/Jdoink/sovereignty_stack
  type: primary
  retrieved: "2026-05-27"
media: []
related:
- about-the-library
---

> This is the **memory** for how the Library should evolve. If priorities are forgotten, start here. It is itself a Library entry — editable, versioned, and backed up like everything else.

## Guiding principles

- **Files-as-truth.** Every entry is Markdown + YAML on the Seagate. The search index is derived and disposable.
- **Generational.** Knowledge must survive decades, edits, mistakes, and hardware failure — so editing must be *easy* and every change must be *recoverable*.
- **Cited & honest.** Canonical entries require sources; mechanics are kept separate from interpretation; contested claims are flagged.
- **Seed = starter only.** Bundled wings seed onto `/data` on first run; after that, `/data` is the living source of truth and edits happen there (via the UI or directly). We do not re-ship edits through the seed.

## Status legend
`[x]` done · `[~]` in progress · `[ ]` planned

## A. Editable (make it a living archive)
- `[~]` **Edit in the reading room** — Edit button → prefilled author form → upsert (preserves slug even if the title changes).
- `[~]` **Delete from the room** — with a confirm step.
- `[~]` **Full schema in the editor** — tier, order, related links, confidence, media (not just the basic fields).
- `[~]` **Markdown preview** while editing.

## B. Generational (durability & history) — decision: BOTH, in order
- `[~]` **Version snapshots (NOW).** Before any overwrite or delete, the previous file is saved to `library/.versions/<slug>/`. Restore a prior version from the UI. Self-contained, no dependencies.
- `[ ]` **Git-backed `/data/library` (LATER).** Make the library a git repo; auto-commit every change; optional offsite push. Gold standard for history/diff/restore + offsite backup. Git is already on the Pi.
- `[ ]` **Export / portability.** One-click download of a wing or the whole Library as plain Markdown + assets; wire into the backup/recovery system.

## C. Navigation & quality polish (after A/B)
- `[ ]` **"Next in path" stepper** — move through a wing's ladder linearly like a course.
- `[ ]` **Table of contents** for long entries (heading anchors already render).
- `[ ]` **Topic / tag filtering** as wings grow.
- `[ ]` **Image / file upload** from the UI (small new endpoint) so diagrams can be added without touching the drive.

## D. Content backlog (wings)
- `[x]` **Money & Sound Economics** — full 5-tier wing.
- `[x]` **Computing & the Internet** — full 5-tier wing.
- `[ ]` **Cryptography & OpSec** — emblem (violet key) already wired; build the wing next.
- `[ ]` Remaining pillars from the original 10: Probability & Statistics, Logic & Clear Thinking, Health & Metabolism, Energy & Electricity, Food & Self-Provisioning, Power/Law/Governance, Systems Thinking.

## E. Known gaps / debts
- `[ ]` **Hybrid-media download** — the `seed/library/fetch.json` mechanism exists but isn't wired to store open texts locally and link the archived copy from resource entries.
- `[ ]` Each `server.py` change still needs a container rebuild on the Pi; frontend (`*.html`) ships live via GitHub.
