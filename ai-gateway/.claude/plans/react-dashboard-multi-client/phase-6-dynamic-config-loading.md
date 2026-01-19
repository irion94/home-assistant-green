# Phase 6: Dynamic Config Loading

## Objective
Update react-dashboard to fetch configuration at runtime from AI Gateway, with fallback to static config.

## Loading Strategy
1. **Build time**: Static config from `src/config/entities.ts` (client branch)
2. **Runtime**: Fetch from `/api/dashboard/config` (optional enhancement)
3. **Fallback**: Use static config if API unavailable

## Implementation

### src/hooks/useClientConfig.ts
```typescript
import { useQuery } from '@tanstack/react-query';
import { ENV } from '@/config/env';
import { STATIC_CONFIG } from '@/config';
import type { ClientConfig } from '@/config/types';

const fetchConfig = async (): Promise<ClientConfig> => {
  const response = await fetch(`${ENV.gatewayUrl}/api/dashboard/config`);
  if (!response.ok) {
    throw new Error('Failed to fetch config');
  }
  return response.json();
};

export function useClientConfig() {
  return useQuery({
    queryKey: ['clientConfig'],
    queryFn: fetchConfig,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
    // Use static config as initial/fallback data
    initialData: STATIC_CONFIG,
    // Don't refetch on window focus for config
    refetchOnWindowFocus: false,
  });
}
```

### src/config/index.ts
```typescript
import { DEFAULT_CONFIG } from './defaults';
import { CLIENT_CONFIG } from './entities';
import type { ClientConfig } from './types';

// Merge defaults with client overrides (static)
export const STATIC_CONFIG: ClientConfig = {
  ...DEFAULT_CONFIG,
  ...CLIENT_CONFIG,
  lights: { ...DEFAULT_CONFIG.lights, ...CLIENT_CONFIG.lights },
  sensors: { ...DEFAULT_CONFIG.sensors, ...CLIENT_CONFIG.sensors },
  climate: { ...DEFAULT_CONFIG.climate, ...CLIENT_CONFIG.climate },
  theme: { ...DEFAULT_CONFIG.theme, ...CLIENT_CONFIG.theme },
  features: { ...DEFAULT_CONFIG.features, ...CLIENT_CONFIG.features },
};

// Re-export for convenience
export * from './types';
export { DEFAULT_CONFIG } from './defaults';
```

### src/providers/ConfigProvider.tsx
```typescript
import { createContext, useContext, ReactNode } from 'react';
import { useClientConfig } from '@/hooks/useClientConfig';
import type { ClientConfig } from '@/config/types';
import { STATIC_CONFIG } from '@/config';

const ConfigContext = createContext<ClientConfig>(STATIC_CONFIG);

export function ConfigProvider({ children }: { children: ReactNode }) {
  const { data: config } = useClientConfig();

  return (
    <ConfigContext.Provider value={config ?? STATIC_CONFIG}>
      {children}
    </ConfigContext.Provider>
  );
}

export function useConfig(): ClientConfig {
  return useContext(ConfigContext);
}

// Convenience hooks
export function useLights() {
  const config = useConfig();
  return config.lights;
}

export function useSensors() {
  const config = useConfig();
  return config.sensors;
}

export function useFeatures() {
  const config = useConfig();
  return config.features;
}
```

### src/App.tsx (updated)
```typescript
import { ConfigProvider } from '@/providers/ConfigProvider';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider>
        {/* ... rest of app */}
      </ConfigProvider>
    </QueryClientProvider>
  );
}
```

### Component Usage Example
```typescript
// Before (hardcoded import)
import { LIGHTS } from '@/config/entities';

// After (dynamic config)
import { useLights } from '@/providers/ConfigProvider';

function LightPanel() {
  const lights = useLights();

  return (
    <div>
      {Object.entries(lights).map(([key, light]) => (
        <LightCard key={key} {...light} />
      ))}
    </div>
  );
}
```

## Loading States

### src/components/ConfigLoader.tsx
```typescript
import { useClientConfig } from '@/hooks/useClientConfig';

export function ConfigLoader({ children }: { children: ReactNode }) {
  const { isLoading, isError, error } = useClientConfig();

  if (isLoading) {
    return <LoadingSpinner message="Loading configuration..." />;
  }

  if (isError) {
    console.warn('Config API unavailable, using static config:', error);
    // Continue with static config - don't block the app
  }

  return <>{children}</>;
}
```

## Validation
- [ ] Dashboard loads with static config (no API)
- [ ] Dashboard fetches and uses API config when available
- [ ] Graceful fallback when API fails
- [ ] Config changes reflected without rebuild (API mode)
