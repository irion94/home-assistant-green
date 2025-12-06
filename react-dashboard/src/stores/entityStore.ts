/**
 * Entity Store - Unified Zustand store for Home Assistant entities
 *
 * Replaces React Context pattern with centralized Zustand state.
 * Provides normalized entity storage, capability detection, and service call actions.
 *
 * Features:
 * - Normalized entity state (compute capabilities once, cache)
 * - Real-time WebSocket updates
 * - Optimistic UI updates for service calls
 * - Memoized selectors for performance
 * - Domain and room filtering
 */

import { create } from 'zustand'
import type { EntityState, EntityDomain } from '../types/entity'
import { getDomain, isEntityOn } from '../types/entity'

/**
 * Entity capabilities detected from attributes
 * Computed once and cached in the store
 */
export interface EntityCapabilities {
  // Light capabilities
  brightness?: boolean
  colorTemp?: boolean
  rgbColor?: boolean
  hsColor?: boolean

  // Climate capabilities
  setTemperature?: boolean
  setHvacMode?: boolean
  setPresetMode?: boolean

  // Media player capabilities
  play?: boolean
  pause?: boolean
  volume?: boolean

  // Switch/toggle
  turnOn?: boolean
  turnOff?: boolean
  toggle?: boolean
}

/**
 * Normalized entity with computed properties
 */
export interface NormalizedEntity extends EntityState {
  // Computed properties (cached)
  isOn: boolean
  isAvailable: boolean
  domain: EntityDomain
  capabilities: EntityCapabilities

  // UI metadata
  displayName: string
  room?: string  // Will be populated by discovery service in Phase 4
}

/**
 * Entity Store State
 */
interface EntityStore {
  // State
  entities: Record<string, NormalizedEntity>
  loading: boolean
  connected: boolean
  error: string | null

  // Selectors (memoized in consumers via Zustand)
  getEntity: (entityId: string) => NormalizedEntity | undefined
  getEntitiesByDomain: (domain: EntityDomain) => NormalizedEntity[]
  getEntitiesByRoom: (room: string) => NormalizedEntity[]
  getLightEntities: () => NormalizedEntity[]
  getClimateEntities: () => NormalizedEntity[]
  getSensorEntities: () => NormalizedEntity[]
  getSwitchEntities: () => NormalizedEntity[]
  getMediaPlayerEntities: () => NormalizedEntity[]

  // Actions
  setEntity: (entity: EntityState) => void
  setEntities: (entities: EntityState[]) => void
  setLoading: (loading: boolean) => void
  setConnected: (connected: boolean) => void
  setError: (error: string | null) => void
  updateEntityOptimistic: (entityId: string, updates: Partial<EntityState>) => void

  // Service calls (will be implemented by API layer)
  callService: (domain: string, service: string, data?: Record<string, unknown>) => Promise<void>
  toggle: (entityId: string) => Promise<void>
  turnOn: (entityId: string, data?: Record<string, unknown>) => Promise<void>
  turnOff: (entityId: string) => Promise<void>
  setBrightness: (entityId: string, brightness: number) => Promise<void>
  setTemperature: (entityId: string, temperature: number) => Promise<void>
}

/**
 * Detect entity capabilities from attributes
 */
function detectCapabilities(entity: EntityState): EntityCapabilities {
  const { attributes } = entity
  const domain = getDomain(entity.entity_id)
  const capabilities: EntityCapabilities = {}

  // Light capabilities
  if (domain === 'light') {
    const colorModes = attributes.supported_color_modes as string[] | undefined
    const features = (attributes.supported_features as number) ?? 0

    if (colorModes && colorModes.length > 0) {
      // Modern detection via supported_color_modes
      capabilities.brightness = colorModes.some(mode =>
        ['brightness', 'color_temp', 'hs', 'rgb', 'rgbw', 'rgbww', 'xy'].includes(mode)
      )
      capabilities.colorTemp = colorModes.includes('color_temp')
      capabilities.rgbColor = colorModes.some(mode =>
        ['rgb', 'rgbw', 'rgbww'].includes(mode)
      )
      capabilities.hsColor = colorModes.some(mode =>
        ['hs', 'xy'].includes(mode)
      )
    } else {
      // Legacy detection via supported_features bitmask
      capabilities.brightness = Boolean(features & 1)
      capabilities.colorTemp = Boolean(features & 2)
      capabilities.rgbColor = Boolean(features & 16)
      capabilities.hsColor = Boolean(features & 16)
    }
  }

  // Climate capabilities
  if (domain === 'climate') {
    capabilities.setTemperature = Array.isArray(attributes.hvac_modes)
    capabilities.setHvacMode = Array.isArray(attributes.hvac_modes)
    capabilities.setPresetMode = Array.isArray(attributes.preset_modes)
  }

  // Media player capabilities
  if (domain === 'media_player') {
    const features = (attributes.supported_features as number) ?? 0
    capabilities.play = Boolean(features & 16)
    capabilities.pause = Boolean(features & 1)
    capabilities.volume = Boolean(features & 4)
  }

  // Universal capabilities for most domains
  capabilities.turnOn = ['light', 'switch', 'fan', 'climate', 'media_player', 'cover'].includes(domain)
  capabilities.turnOff = capabilities.turnOn
  capabilities.toggle = capabilities.turnOn

  return capabilities
}

/**
 * Normalize entity with computed properties
 */
function normalizeEntity(entity: EntityState): NormalizedEntity {
  const domain = getDomain(entity.entity_id)
  const isOnState = isEntityOn(entity)
  const isAvailable = entity.state !== 'unavailable' && entity.state !== 'unknown'
  const capabilities = detectCapabilities(entity)
  const displayName = entity.attributes.friendly_name || entity.entity_id

  return {
    ...entity,
    isOn: isOnState,
    isAvailable,
    domain,
    capabilities,
    displayName,
    room: undefined, // Will be populated by discovery service
  }
}

/**
 * Entity Store Implementation
 */
export const useEntityStore = create<EntityStore>((set, get) => ({
  // Initial state
  entities: {},
  loading: false,
  connected: false,
  error: null,

  // Selectors
  getEntity: (entityId: string) => {
    return get().entities[entityId]
  },

  getEntitiesByDomain: (domain: EntityDomain) => {
    return Object.values(get().entities).filter(e => e.domain === domain)
  },

  getEntitiesByRoom: (room: string) => {
    return Object.values(get().entities).filter(e => e.room === room)
  },

  getLightEntities: () => {
    return get().getEntitiesByDomain('light')
  },

  getClimateEntities: () => {
    return get().getEntitiesByDomain('climate')
  },

  getSensorEntities: () => {
    return get().getEntitiesByDomain('sensor')
  },

  getSwitchEntities: () => {
    return get().getEntitiesByDomain('switch')
  },

  getMediaPlayerEntities: () => {
    return get().getEntitiesByDomain('media_player')
  },

  // Actions
  setEntity: (entity: EntityState) => {
    const normalized = normalizeEntity(entity)
    set(state => ({
      entities: {
        ...state.entities,
        [entity.entity_id]: normalized,
      },
    }))
  },

  setEntities: (entities: EntityState[]) => {
    const normalized: Record<string, NormalizedEntity> = {}
    entities.forEach(entity => {
      normalized[entity.entity_id] = normalizeEntity(entity)
    })
    set({ entities: normalized })
  },

  setLoading: (loading: boolean) => {
    set({ loading })
  },

  setConnected: (connected: boolean) => {
    set({ connected })
  },

  setError: (error: string | null) => {
    set({ error })
  },

  updateEntityOptimistic: (entityId: string, updates: Partial<EntityState>) => {
    const entity = get().entities[entityId]
    if (!entity) return

    const updatedEntity: EntityState = {
      ...entity,
      ...updates,
      attributes: {
        ...entity.attributes,
        ...(updates.attributes || {}),
      },
    }

    get().setEntity(updatedEntity)
  },

  // Service calls (placeholder - will be implemented by API service)
  callService: async (_domain: string, _service: string, _data?: Record<string, unknown>) => {
    // Will be overridden by API service in Phase 2.2
    console.warn('callService not yet connected to API layer')
  },

  toggle: async (entityId: string) => {
    // Optimistic update
    const entity = get().entities[entityId]
    if (entity) {
      get().updateEntityOptimistic(entityId, {
        state: entity.isOn ? 'off' : 'on',
      })
    }

    // Will be overridden by API service
    console.warn('toggle not yet connected to API layer')
  },

  turnOn: async (entityId: string, _data?: Record<string, unknown>) => {
    // Optimistic update
    get().updateEntityOptimistic(entityId, { state: 'on' })

    // Will be overridden by API service
    console.warn('turnOn not yet connected to API layer')
  },

  turnOff: async (entityId: string) => {
    // Optimistic update
    get().updateEntityOptimistic(entityId, { state: 'off' })

    // Will be overridden by API service
    console.warn('turnOff not yet connected to API layer')
  },

  setBrightness: async (entityId: string, brightness: number) => {
    // Optimistic update
    get().updateEntityOptimistic(entityId, {
      attributes: { brightness },
    })

    // Will be overridden by API service
    console.warn('setBrightness not yet connected to API layer')
  },

  setTemperature: async (entityId: string, temperature: number) => {
    // Optimistic update
    get().updateEntityOptimistic(entityId, {
      attributes: { temperature },
    })

    // Will be overridden by API service
    console.warn('setTemperature not yet connected to API layer')
  },
}))

/**
 * Convenience hooks for specific entity domains
 * These provide granular selectors to prevent unnecessary re-renders
 */
export const useEntity = (entityId: string) => useEntityStore(state => state.getEntity(entityId))
export const useLightEntities = () => useEntityStore(state => state.getLightEntities())
export const useClimateEntities = () => useEntityStore(state => state.getClimateEntities())
export const useSensorEntities = () => useEntityStore(state => state.getSensorEntities())
export const useSwitchEntities = () => useEntityStore(state => state.getSwitchEntities())
export const useMediaPlayerEntities = () => useEntityStore(state => state.getMediaPlayerEntities())

/**
 * Connection state hooks
 */
export const useEntityStoreConnected = () => useEntityStore(state => state.connected)
export const useEntityStoreLoading = () => useEntityStore(state => state.loading)
export const useEntityStoreError = () => useEntityStore(state => state.error)
