---
title: How a Computer Thinks (ELI5)
slug: computing-eli5
domain: Computing
topics:
- computing
- basics
summary: A computer has no ideas and no understanding. It's a mountain of tiny light switches, wired so that patterns of on and off can stand for numbers, letters, pictures — and rules for changing them. That's the whole trick.
status: reviewed
confidence: high
tier: eli5
order: 0
verified: "2026-05-27"
sources: []
media: []
related:
- computing-bits-logic-gates
- computing-intro
---

## A wall of light switches

Picture a giant wall covered in millions of tiny light switches. Each one is either **on** or **off** — that's a **bit**. By itself a single switch means nothing. But agree on a code, and patterns of on/off can mean *anything*:

- `01000001` can mean the letter **A**.
- A different pattern can mean the number **65**, or one dot of color in a photo, or one tiny slice of a song.

The switches don't *know* what they mean — *we* decided the code. The computer just stores and shuffles on/off patterns very, very fast.

## Switches that make decisions

Here's the leap. You can wire switches together so that **the position of some switches controls others** — little circuits called **logic gates**. For example, a gate can be built so its output is "on" *only if both* of its inputs are on (an AND gate). With gates you can make patterns that *react* to other patterns.

Stack enough of those together and astonishing things appear:
- Gates that can **add two numbers**.
- Gates that can **remember** a bit (memory).
- Gates that can **choose** what to do next depending on a result.

That's it. Arithmetic, memory, and decisions — all from switches wired into gates. Everything else is built on top.

## Following a recipe, blindingly fast

A **program** is just a long list of simple instructions — "add these two numbers," "compare them," "if bigger, jump to step 40." The computer reads one instruction, does it, reads the next, and repeats — **billions of times per second.**

It never gets bored, never understands, never has a thought. It's the world's most patient recipe-follower, working in a language of on and off. The "intelligence" you see is the cleverness of the recipe (the software) and the code we chose — not the switches.

> Keep this picture as you climb the wing: **switches → gates → instructions → everything.** Next, see *Bits & Logic Gates* to watch the bottom layer up close — or take the **Basic Intro** for the full hour-long tour.
