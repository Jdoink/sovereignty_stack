---
title: "From Gates to the CPU: The Fetch–Decode–Execute Cycle"
slug: computing-cpu
domain: Computing
topics:
- computing
- cpu
- processor
summary: A CPU is logic gates organized to do one simple loop — fetch an instruction, decode it, execute it — billions of times a second. Understand that loop and the processor stops being a black box.
status: canonical
confidence: high
tier: deep-dive
order: 2
verified: "2026-05-27"
sources:
- title: "nand2tetris — building the CPU and computer architecture (Projects 4–5)"
  url: https://www.nand2tetris.org/
  type: course
  retrieved: "2026-05-27"
- title: "Crash Course Computer Science — The CPU & Instructions/Programs"
  author: Carrie Anne Philbin / PBS
  url: https://www.youtube.com/playlist?list=PL8dPuuaLjXtNlUrzyH5r6jN9ulIgZBpdo
  type: video
  retrieved: "2026-05-27"
media:
- computing/cpu-cycle.svg
related:
- computing-bits-logic-gates
- computing-memory-storage
---

## What a CPU is made of

The **CPU (central processing unit)** is the part that actually *does* the computing. Built entirely from the gates of the previous entry, it has a few key pieces:

- **Registers** — a handful of tiny, ultra-fast storage slots that hold the numbers the CPU is working on *right now*.
- **ALU (arithmetic logic unit)** — the gate circuits that add, subtract, compare, and do logic (AND/OR) on those numbers.
- **Control unit** — decodes instructions and steers signals to the right place.
- **Program counter** — a register holding the address of the *next* instruction to run.
- **Clock** — a signal that ticks billions of times per second, marching the CPU through its steps in lockstep. "3 GHz" means 3 billion ticks per second.

## The one loop it runs forever

A program is a list of **instructions** stored in memory, each a binary pattern the CPU understands (its *machine code*). The CPU executes them by repeating a simple cycle:

![The fetch–decode–execute cycle](/library-assets/computing/cpu-cycle.svg)

1. **Fetch** — read the instruction at the address in the program counter, from memory.
2. **Decode** — the control unit works out what that instruction means (add? load? jump?).
3. **Execute** — carry it out: do math in the ALU, read/write memory, or change the program counter.
4. **Store / repeat** — write back any result, advance the program counter, and loop.

That's the entire essence of a processor. Every app, game, and AI model is ultimately this loop, run an astronomical number of times over the right instructions.

## Instructions and the ISA

The exact set of instructions a CPU understands is its **instruction set architecture (ISA)** — e.g., x86 (most desktops/laptops) or ARM (most phones, and the Raspberry Pi in your stack). Instructions are deliberately primitive: load a number, add two registers, compare, jump to another instruction if a condition holds. **Software is just enormous stacks of these tiny steps** — written by humans in higher-level languages, then translated down (compiled) into machine code the CPU can fetch.

## Why this matters for your stack

- **"It's fast because it's simple, repeated."** A CPU's power comes from doing trivial steps billions of times per second, not from any single clever step.
- **The Pi's ARM chip** runs this same cycle; understanding it demystifies "why is this slow?" (too many instructions, or waiting on memory — see the next entry).
- The leap from *gates* to *CPU* is the single most satisfying "aha" in computing, and you can do it yourself in a simulator — see the **Mastery** tier.
