
---
title: plan
description: Generate a 10-phase project plan from a prompt.
arguments:
  prompt:
    type: string
    required: true
  id:
    type: string
    required: false
---

Always generate **exactly 10 phases**.

Steps:
1. Derive project id.
2. Create folder: .claude/plans/<id>
3. Create phase-0-overview.md with 10-phase table.
4. Create 10 phase files:
   - phase-1-xxx.md
   - ...
   - phase-10-xxx.md
5. Tailor phase names to prompt.
