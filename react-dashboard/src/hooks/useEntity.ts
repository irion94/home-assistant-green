/**
 * Entity Hooks - Migrated to use Zustand entity store
 *
 * Updated to use entityStore instead of React Context.
 * Provides the same API as before but with better performance and simpler state management.
 */

import { useMemo, useCallback } from 'react'
import { useEntityStore, useEntity as useEntityFromStore } from '../stores/entityStore'
import type { NormalizedEntity } from '../stores/entityStore'

interface UseEntityResult {
  entity: NormalizedEntity | undefined
  state: string
  isOn: boolean
  isAvailable: boolean
  attributes: NormalizedEntity['attributes']
  toggle: () => Promise<void>
  turnOn: (data?: Record<string, unknown>) => Promise<void>
  turnOff: () => Promise<void>
  setBrightness: (brightness: number) => Promise<void>
}

/**
 * Base hook for any entity type
 * Now uses Zustand store instead of Context
 */
export function useEntity(entityId: string): UseEntityResult {
  const entity = useEntityFromStore(entityId)
  const { toggle, turnOn, turnOff, setBrightness } = useEntityStore()

  const state = entity?.state ?? 'unavailable'
  const isOn = entity?.isOn ?? false
  const isAvailable = entity?.isAvailable ?? false
  const attributes = entity?.attributes ?? {}

  const handleToggle = useCallback(async () => {
    await toggle(entityId)
  }, [toggle, entityId])

  const handleTurnOn = useCallback(async (data?: Record<string, unknown>) => {
    await turnOn(entityId, data)
  }, [turnOn, entityId])

  const handleTurnOff = useCallback(async () => {
    await turnOff(entityId)
  }, [turnOff, entityId])

  const handleSetBrightness = useCallback(async (brightness: number) => {
    await setBrightness(entityId, brightness)
  }, [setBrightness, entityId])

  return {
    entity,
    state,
    isOn,
    isAvailable,
    attributes,
    toggle: handleToggle,
    turnOn: handleTurnOn,
    turnOff: handleTurnOff,
    setBrightness: handleSetBrightness,
  }
}

/**
 * Light entity hook with brightness, color, and color temp support
 */
export function useLightEntity(entityId: string) {
  const base = useEntity(entityId)
  const entity = base.entity

  const brightness = entity?.attributes.brightness
    ? Math.round((entity.attributes.brightness / 255) * 100)
    : 0

  const colorTemp = entity?.attributes.color_temp
  const rgbColor = entity?.attributes.rgb_color
  const hsColor = entity?.attributes.hs_color

  // Read capabilities from normalized entity (already computed)
  const supportsBrightness = entity?.capabilities.brightness ?? false
  const supportsColorTemp = entity?.capabilities.colorTemp ?? false
  const supportsColor = entity?.capabilities.rgbColor ?? false

  return {
    ...base,
    brightness,
    colorTemp,
    rgbColor,
    hsColor,
    supportsBrightness,
    supportsColorTemp,
    supportsColor,
  }
}

/**
 * Climate entity hook with temperature and HVAC controls
 */
export function useClimateEntity(entityId: string) {
  const base = useEntity(entityId)
  const entity = base.entity
  const { setTemperature } = useEntityStore()

  const currentTemperature = entity?.attributes.current_temperature ?? 0
  const targetTemperature = entity?.attributes.temperature ?? 0
  const hvacAction = entity?.attributes.hvac_action ?? 'off'
  const hvacModes = (entity?.attributes.hvac_modes as string[]) ?? []
  const presetMode = entity?.attributes.preset_mode as string | undefined
  const presetModes = (entity?.attributes.preset_modes as string[]) ?? []

  const handleSetTemperature = useCallback(async (temperature: number) => {
    await setTemperature(entityId, temperature)
  }, [setTemperature, entityId])

  return {
    ...base,
    currentTemperature,
    targetTemperature,
    hvacAction,
    hvacModes,
    presetMode,
    presetModes,
    setTemperature: handleSetTemperature,
  }
}

/**
 * Sensor entity hook for read-only sensors
 */
export function useSensorEntity(entityId: string) {
  const base = useEntity(entityId)
  const entity = base.entity

  const value = base.state
  const unit = entity?.attributes.unit_of_measurement ?? ''
  const deviceClass = entity?.attributes.device_class ?? ''

  return {
    ...base,
    value,
    unit,
    deviceClass,
  }
}

/**
 * Media player entity hook
 */
export function useMediaPlayerEntity(entityId: string) {
  const base = useEntity(entityId)
  const entity = base.entity

  const mediaTitle = entity?.attributes.media_title ?? ''
  const mediaArtist = entity?.attributes.media_artist ?? ''
  const volumeLevel = entity?.attributes.volume_level ?? 0
  const isVolumeMuted = entity?.attributes.is_volume_muted ?? false

  // Read capabilities from normalized entity
  const supportsPlay = entity?.capabilities.play ?? false
  const supportsPause = entity?.capabilities.pause ?? false
  const supportsVolume = entity?.capabilities.volume ?? false

  return {
    ...base,
    mediaTitle,
    mediaArtist,
    volumeLevel,
    isVolumeMuted,
    supportsPlay,
    supportsPause,
    supportsVolume,
  }
}

/**
 * Hook for multiple entities at once
 * Useful for fetching all entities of a specific type
 */
export function useEntities(entityIds: string[]): UseEntityResult[] {
  const entities = entityIds.map(id => useEntity(id))
  return entities
}

/**
 * Hook for entities by domain (e.g., all lights)
 */
export function useEntitiesByDomain(domain: 'light' | 'switch' | 'climate' | 'sensor' | 'media_player') {
  // Use pre-computed selectors from store for performance
  const getLightEntities = useEntityStore(state => state.getLightEntities)
  const getClimateEntities = useEntityStore(state => state.getClimateEntities)
  const getSensorEntities = useEntityStore(state => state.getSensorEntities)
  const getSwitchEntities = useEntityStore(state => state.getSwitchEntities)
  const getMediaPlayerEntities = useEntityStore(state => state.getMediaPlayerEntities)

  return useMemo(() => {
    switch (domain) {
      case 'light':
        return getLightEntities()
      case 'climate':
        return getClimateEntities()
      case 'sensor':
        return getSensorEntities()
      case 'switch':
        return getSwitchEntities()
      case 'media_player':
        return getMediaPlayerEntities()
      default:
        return []
    }
  }, [domain, getLightEntities, getClimateEntities, getSensorEntities, getSwitchEntities, getMediaPlayerEntities])
}

export default useEntity
