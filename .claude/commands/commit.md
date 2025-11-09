---
title: commit-split
description: Split current changes into logical commits (or single commit if small), using Conventional Commits with optional task scope. Enforces 78-char header limit and automatically resets staging area before starting.
arguments:
  task:
    type: string
    required: false
    description: Optional task key used as scope, e.g. FOR-99
  auto:
    type: string
    required: false
    description: "Set to yes to auto-apply after plan approval (default: ask)"
---

You are a careful Git co-author. Your job:

1. **Pre-check & reset:**
  - Run `!git reset` at the very beginning to unstage all files.
  - Confirm that `!git diff --cached --name-only` returns nothing before continuing.

2. Inspect the working tree and group changes into commits:
  - If changes are small and cohesive → **make one single commit**.
  - Otherwise → split into multiple logical commits.

3. Commit rules:
  - Choose a Conventional Commit **type** from:
    feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
  - If `$TASK` is provided, include it as scope: `fix($TASK): …`
  - Enforce ≤ 78 characters total (including prefix).
    - Compute prefix = `type: ` or `type($TASK): `
    - Truncate message to fit.
  - Use imperative mood, no trailing periods.

4. Workflow:
  - Step A: Show `!git status --porcelain` and `!git diff --name-only`.
  - Step B: Propose commit plan (table format).
  - Step C: Ask for approval (unless `$AUTO` = yes).
  - Step D: Apply commits:
    - Stage exact files for each commit: `!git add <files>`
    - Commit with the prepared header.
  - Step E: Show summary of created commits (hash + header).

5. Constraints:
  - Never mix unrelated changes in one commit.
  - Never exceed 78 chars per commit header.
  - If in doubt, group by responsibility or file path.
  - No commits should proceed unless staging area is clean (guaranteed by Step 1).

Variables:
- `$TASK` = "{{task}}"
- `$AUTO` = "{{auto}}"

Now begin Step 1: run `!git reset` to clear the staging area.
