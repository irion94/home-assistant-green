# Phase 7: Theme System

## Objective
Implement client-specific theming for colors, branding, and visual customization.

## Theme Configuration

### src/config/types.ts (theme section)
```typescript
export interface ThemeConfig {
  // Colors
  primaryColor: string;
  secondaryColor: string;
  accentColor: string;
  backgroundColor: string;
  surfaceColor: string;
  textColor: string;
  textSecondaryColor: string;

  // Branding
  clientName: string;
  logoUrl?: string;
  faviconUrl?: string;

  // UI Options
  borderRadius: 'none' | 'small' | 'medium' | 'large';
  darkMode: boolean;
}

export const DEFAULT_THEME: ThemeConfig = {
  primaryColor: '#03a9f4',
  secondaryColor: '#ff9800',
  accentColor: '#4caf50',
  backgroundColor: '#0a0a0a',
  surfaceColor: '#1a1a1a',
  textColor: '#ffffff',
  textSecondaryColor: '#a0a0a0',
  clientName: 'Smart Home',
  borderRadius: 'medium',
  darkMode: true,
};
```

### Client Theme Override (client branch)
```typescript
// src/config/theme.ts
import type { ThemeConfig } from './types';

export const CLIENT_THEME: Partial<ThemeConfig> = {
  primaryColor: '#6366f1',     // Indigo for this client
  secondaryColor: '#f59e0b',
  clientName: 'Dom Wójcików',
  logoUrl: '/assets/wojcik-logo.svg',
};
```

## CSS Variables Integration

### src/styles/theme.css
```css
:root {
  /* These are set dynamically by ThemeProvider */
  --color-primary: #03a9f4;
  --color-secondary: #ff9800;
  --color-accent: #4caf50;
  --color-background: #0a0a0a;
  --color-surface: #1a1a1a;
  --color-text: #ffffff;
  --color-text-secondary: #a0a0a0;

  --radius-none: 0;
  --radius-small: 4px;
  --radius-medium: 8px;
  --radius-large: 16px;

  --radius: var(--radius-medium);
}
```

### src/providers/ThemeProvider.tsx
```typescript
import { createContext, useContext, useEffect, ReactNode } from 'react';
import { useConfig } from './ConfigProvider';
import type { ThemeConfig } from '@/config/types';
import { DEFAULT_THEME } from '@/config/types';

const ThemeContext = createContext<ThemeConfig>(DEFAULT_THEME);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const config = useConfig();
  const theme = { ...DEFAULT_THEME, ...config.theme };

  useEffect(() => {
    // Apply CSS variables
    const root = document.documentElement;
    root.style.setProperty('--color-primary', theme.primaryColor);
    root.style.setProperty('--color-secondary', theme.secondaryColor);
    root.style.setProperty('--color-accent', theme.accentColor);
    root.style.setProperty('--color-background', theme.backgroundColor);
    root.style.setProperty('--color-surface', theme.surfaceColor);
    root.style.setProperty('--color-text', theme.textColor);
    root.style.setProperty('--color-text-secondary', theme.textSecondaryColor);
    root.style.setProperty('--radius', `var(--radius-${theme.borderRadius})`);

    // Update favicon if provided
    if (theme.faviconUrl) {
      const favicon = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
      if (favicon) favicon.href = theme.faviconUrl;
    }

    // Update document title
    document.title = `${theme.clientName} Dashboard`;
  }, [theme]);

  return (
    <ThemeContext.Provider value={theme}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeConfig {
  return useContext(ThemeContext);
}
```

## Component Usage

### Using CSS Variables (recommended)
```css
/* src/components/Card.module.css */
.card {
  background: var(--color-surface);
  color: var(--color-text);
  border-radius: var(--radius);
}

.card-header {
  color: var(--color-primary);
}
```

### Using Theme Hook (for dynamic values)
```typescript
import { useTheme } from '@/providers/ThemeProvider';

function Header() {
  const theme = useTheme();

  return (
    <header>
      {theme.logoUrl ? (
        <img src={theme.logoUrl} alt={theme.clientName} />
      ) : (
        <h1>{theme.clientName}</h1>
      )}
    </header>
  );
}
```

## Tailwind Integration (if using)

### tailwind.config.js
```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: 'var(--color-primary)',
        secondary: 'var(--color-secondary)',
        accent: 'var(--color-accent)',
        surface: 'var(--color-surface)',
      },
      borderRadius: {
        DEFAULT: 'var(--radius)',
      },
    },
  },
};
```

## Validation
- [ ] Theme colors applied via CSS variables
- [ ] Client logo displayed when configured
- [ ] Favicon updates per client
- [ ] Document title shows client name
- [ ] Dark/light mode toggle works (future)
