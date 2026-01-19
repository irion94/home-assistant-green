# Phase 10: Documentation & Testing

## Objective
Create comprehensive documentation for adding new clients and implement E2E tests to ensure multi-client architecture works correctly.

## Documentation

### README.md (react-dashboard repo)
```markdown
# React Dashboard

Smart home dashboard for Home Assistant, supporting multi-client deployments.

## Architecture

This dashboard uses a **branch-per-client** architecture:
- `main` branch: Base code, shared components
- `client/*` branches: Client-specific configurations

## Quick Start

### For Development
\`\`\`bash
git clone git@github.com:irion94/react-dashboard.git
cd react-dashboard
git checkout client/your_client_id
npm install
npm run dev
\`\`\`

### For Production
See [ha-enterprise-starter](https://github.com/irion94/ha-enterprise-starter) for full deployment instructions.

## Client Configuration

Client-specific files (in client branches):
- `src/config/entities.ts` - HA entity mappings
- `src/config/theme.ts` - Colors and branding
- `src/config/features.ts` - Feature flags

## Adding a New Client

See [docs/adding-new-client.md](docs/adding-new-client.md)
```

### docs/adding-new-client.md
```markdown
# Adding a New Client

## Prerequisites
- GitHub access to react-dashboard and home-assistant-service repos
- Client's Home Assistant entity IDs
- Client's branding preferences (optional)

## Step-by-Step Guide

### 1. Create Client Branch

\`\`\`bash
# Clone repo if not already
git clone git@github.com:irion94/react-dashboard.git
cd react-dashboard

# Create branch from main
git checkout main
git pull origin main
git checkout -b client/new_client_name
\`\`\`

### 2. Configure Entities

Edit `src/config/entities.ts`:
\`\`\`typescript
import type { ClientConfig } from './types';

export const CLIENT_CONFIG: Partial<ClientConfig> = {
  lights: {
    livingRoom: {
      name: 'Living Room',
      entity_id: 'light.living_room_main',
      icon: 'sofa',
    },
    // Add more lights...
  },
  sensors: {
    temperature: {
      name: 'Temperature',
      entity_id: 'sensor.living_room_temperature',
      icon: 'thermometer',
    },
    // Add more sensors...
  },
  climate: {
    // Add climate entities if available
  },
};
\`\`\`

### 3. Configure Theme (Optional)

Edit `src/config/theme.ts`:
\`\`\`typescript
import type { ThemeConfig } from './types';

export const CLIENT_THEME: Partial<ThemeConfig> = {
  primaryColor: '#your-color',
  clientName: 'Client Display Name',
  // logoUrl: '/assets/client-logo.svg',
};
\`\`\`

### 4. Add Logo (Optional)

Place logo file at `public/assets/client-logo.svg`

### 5. Commit and Push

\`\`\`bash
git add .
git commit -m "feat: initial config for new_client_name"
git push origin client/new_client_name
\`\`\`

### 6. Update Deployment Config

On the deployment server, update `.env`:
\`\`\`bash
CLIENT_ID=new_client_name
DASHBOARD_BRANCH=client/new_client_name
HA_SERVICE_BRANCH=client/new_client_name
\`\`\`

### 7. Deploy

\`\`\`bash
./scripts/deploy.sh --rebuild
\`\`\`

## Finding Entity IDs

1. Open Home Assistant
2. Go to Developer Tools → States
3. Search for the entity
4. Copy the `entity_id`

## Troubleshooting

### Dashboard shows "No entities"
- Verify entity IDs are correct
- Check HA connection in Developer Tools

### Theme not applied
- Clear browser cache
- Rebuild dashboard: `docker compose build react-dashboard`
```

## Testing

### E2E Tests (Playwright)

#### tests/e2e/config-loading.spec.ts
```typescript
import { test, expect } from '@playwright/test';

test.describe('Config Loading', () => {
  test('loads client configuration', async ({ page }) => {
    await page.goto('/');

    // Check client name in header
    const header = page.locator('[data-testid="client-name"]');
    await expect(header).toBeVisible();
    await expect(header).not.toHaveText('Default');
  });

  test('displays configured lights', async ({ page }) => {
    await page.goto('/');

    // Should have at least one light card
    const lightCards = page.locator('[data-testid="light-card"]');
    await expect(lightCards.first()).toBeVisible();
  });

  test('applies theme colors', async ({ page }) => {
    await page.goto('/');

    // Check CSS variable is set
    const primaryColor = await page.evaluate(() => {
      return getComputedStyle(document.documentElement)
        .getPropertyValue('--color-primary');
    });

    expect(primaryColor).not.toBe('');
  });
});
```

#### tests/e2e/multi-client.spec.ts
```typescript
import { test, expect } from '@playwright/test';

test.describe('Multi-Client Support', () => {
  test('different clients have different entities', async ({ page }) => {
    // This test would run against different deployments
    await page.goto('/');

    // Verify entities are client-specific
    const entityIds = await page.evaluate(() => {
      // Access config from window or DOM
      return window.__CLIENT_CONFIG__?.lights || {};
    });

    // Should have entities (not empty default)
    expect(Object.keys(entityIds).length).toBeGreaterThan(0);
  });
});
```

### Unit Tests (Vitest)

#### src/config/__tests__/config.test.ts
```typescript
import { describe, it, expect } from 'vitest';
import { STATIC_CONFIG } from '../index';
import { DEFAULT_CONFIG } from '../defaults';

describe('Config', () => {
  it('merges client config with defaults', () => {
    expect(STATIC_CONFIG).toBeDefined();
    expect(STATIC_CONFIG.theme).toBeDefined();
  });

  it('has valid entity structure', () => {
    Object.values(STATIC_CONFIG.lights).forEach(light => {
      expect(light).toHaveProperty('name');
      expect(light).toHaveProperty('entity_id');
      expect(light.entity_id).toMatch(/^light\./);
    });
  });

  it('preserves default values when not overridden', () => {
    // Features should have defaults
    expect(STATIC_CONFIG.features.voiceControl).toBeDefined();
  });
});
```

### CI/CD Pipeline

#### .github/workflows/test.yml
```yaml
name: Test

on:
  push:
    branches: [main, 'client/*']
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Type check
        run: npm run typecheck

      - name: Unit tests
        run: npm run test

      - name: Build
        run: npm run build

  e2e:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright
        run: npx playwright install --with-deps

      - name: Run E2E tests
        run: npm run test:e2e
```

## Validation Checklist

### Documentation
- [ ] README.md updated with multi-client info
- [ ] Adding new client guide complete
- [ ] Entity ID discovery instructions
- [ ] Troubleshooting section

### Testing
- [ ] Unit tests for config loading
- [ ] E2E tests for dashboard rendering
- [ ] CI pipeline runs on all branches
- [ ] Tests pass for main and client branches

### Final Verification
- [ ] New client can be added in < 30 minutes
- [ ] Zero code changes to main branch required
- [ ] Existing deployments unaffected
- [ ] Documentation matches implementation
