
---
title: migrate
description: Convert legacy plans or multi-file phase sets into the new 10-phase system.
arguments:
  source:
    type: string
    required: true
---

## Migration Logic
1. Detect if legacy file contains multiple phases.
2. Infer structure by headers, keywords, or sections.
3. Map legacy phases → new 10-phase structure.
4. Generate:
   - phase-0-overview.md
   - 10 new phase files
5. Move old content into appropriate phases.
6. Output migration summary.
