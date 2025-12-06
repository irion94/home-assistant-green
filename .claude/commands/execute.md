
---
title: execute
description: Execute a single phase plan with sanity checks, feature-flag awareness, and documentation updates.
arguments:
  plan:
    type: string
    required: true
---
You are an enhanced phase executor.

## Additional Sanity Checks
- Ensure all referenced files exist before modifications.
- Validate JSON/YAML files after edit.
- If feature-flags exist in the phase:
  - Respect them but do NOT enable automatically.

## Execution Steps
1. Load plan.
2. Parse implementation steps.
3. Perform sanity checks.
4. Execute modifications.
5. Validate syntax.
6. Update docs.
7. Output summary.
