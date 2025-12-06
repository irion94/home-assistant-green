
---
title: program
description: Execute a 10‑phase multi‑phase program automatically enabling/disabling feature flags inside each phase.
arguments:
  overview:
    type: string
    required: true
  phases:
    type: string
    required: false
---

## Feature‑Flag Logic
For each phase:
- Automatically enable flags *during execution*
- Disable them after completion unless the plan specifies persist=true

## Steps
1. Load overview.
2. Determine phases.
3. Loop through phases:
   - Enable feature-flags for phase
   - Call single-phase executor logic
   - Disable feature-flags unless persistent
4. Output total program summary.
