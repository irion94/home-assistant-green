# Phase 3: Client Branch Strategy

## Objective
Define the branching model and client override pattern for react-dashboard, matching home-assistant-service conventions.

## Branch Naming Convention
```
main                    # Base code, shared components, default config
client/wojcik_igor      # Client: Igor Wójcik
client/kowalski_jan     # Client: Jan Kowalski
client/demo             # Demo/testing client
```

## What Goes Where

### Main Branch (shared code)
- All React components (`src/components/`)
- All hooks (`src/hooks/`)
- All utilities (`src/utils/`)
- Base styles (`src/styles/`)
- Default configuration (`src/config/defaults.ts`)
- Type definitions (`src/config/types.ts`)

### Client Branch (overrides only)
- `src/config/entities.ts` - Client's HA entities
- `src/config/theme.ts` - Client's branding/colors
- `src/config/features.ts` - Client's feature flags
- `public/logo.svg` - Client's logo (optional)
- `public/favicon.ico` - Client's favicon (optional)

## Merge Strategy

### Updating Client Branch from Main
```bash
# When main has new features, update client branch
git checkout client/wojcik_igor
git merge main --no-commit
# Resolve conflicts (keep client config files)
git commit -m "merge: sync with main branch"
```

### Protected Files (never overwrite on merge)
```gitattributes
# .gitattributes in client branches
src/config/entities.ts merge=ours
src/config/theme.ts merge=ours
src/config/features.ts merge=ours
```

## Creating New Client Branch
```bash
# 1. Branch from main
git checkout main
git pull origin main
git checkout -b client/new_client_name

# 2. Copy template config
cp src/config/entities.template.ts src/config/entities.ts

# 3. Edit with client's entities
# 4. Commit and push
git add .
git commit -m "feat: initial config for new_client_name"
git push origin client/new_client_name
```

## File: src/config/entities.template.ts
```typescript
import type { ClientConfig } from './types';

export const CLIENT_CONFIG: Partial<ClientConfig> = {
  lights: {
    // Add client's lights here
    // example: { name: 'Living Room', entity_id: 'light.living_room', icon: 'sofa' }
  },
  sensors: {
    // Add client's sensors here
  },
  climate: {
    // Add client's climate entities here
  },
};
```

## Validation
- [ ] Main branch has no client-specific entities
- [ ] Client branch only modifies config files
- [ ] Merge from main preserves client config
