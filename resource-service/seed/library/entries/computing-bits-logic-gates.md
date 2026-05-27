---
title: "Bits & Logic Gates: The Atoms of Computation"
slug: computing-bits-logic-gates
domain: Computing
topics:
- computing
- binary
- logic-gates
summary: Everything a computer does reduces to two things — representing information as on/off bits, and transforming it with logic gates. From these atoms, arithmetic, memory, and decisions are built.
status: canonical
confidence: high
tier: deep-dive
order: 1
verified: "2026-05-27"
sources:
- title: "Charles Petzold — Code: The Hidden Language of Computer Hardware and Software"
  author: Charles Petzold
  url: https://www.charlespetzold.com/code/
  type: book
  retrieved: "2026-05-27"
- title: "nand2tetris — Project 1: Boolean Logic"
  url: https://www.nand2tetris.org/
  type: course
  retrieved: "2026-05-27"
media:
- computing/logic-gates.svg
related:
- computing-eli5
- computing-cpu
---

## Why everything is binary

Computers represent information with just two states because two states are **easy to keep reliable** in physical hardware: a wire is at high voltage or low, a switch is on or off, a transistor conducts or doesn't. Call those two states **1** and **0**. A single one is a **bit**; eight of them make a **byte**.

With a code agreed in advance, patterns of bits represent anything:
- **Numbers** — in binary (base-2), `1011` = 8+0+2+1 = 11.
- **Text** — a standard like ASCII/Unicode maps `01000001` → `A`.
- **Images, sound, video** — long sequences of numbers describing pixels or sound samples.

The crucial idea: **the bits carry no inherent meaning.** The same `01000001` is "65," "A," or a shade of gray depending only on the code we chose to interpret it with. Meaning is convention layered on top of physics.

## The transistor: a switch with no moving parts

Modern chips are built from **transistors** — tiny electronic switches with no moving parts, where one electrical signal controls whether another can pass. A chip packs *billions* of them. A transistor is the physical atom; the **logic gate** is the logical atom built from a few transistors.

## Logic gates: bits that react to bits

A gate takes one or two input bits and produces an output bit by a fixed rule:

![The three core logic gates](/library-assets/computing/logic-gates.svg)

- **AND** — output 1 only if *both* inputs are 1.
- **OR** — output 1 if *either* input is 1.
- **NOT** — flips the input (1→0, 0→1).
- (**XOR**, **NAND**, and others are combinations of these.)

A remarkable fact: the **NAND** gate alone is *universal* — any logic function whatsoever can be built from NAND gates. This is the starting point of the nand2tetris course (in the sources): begin with one gate, end with a working computer.

## Building up: from gates to capability

Wire gates together and capability emerges, layer by layer:

- Combine gates into an **adder** — a circuit that adds two binary numbers (XOR for the sum bit, AND for the carry). Chain adders and you can add any-size numbers.
- Arrange gates into a **latch / flip-flop** — a circuit that *holds* a bit even after the input changes. That's **memory**, built from pure logic.
- Use a gate's output to select between options — that's a **decision**.

Arithmetic, memory, and choice — the three things you need for general computation — all fall out of switches wired into gates. **Nothing else in a computer is fundamentally more mysterious than this.** Everything above is abstraction stacked on this foundation, which is exactly where the CPU picks up.
