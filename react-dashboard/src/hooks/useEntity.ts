import { useMemo, useCallback } from 'react'
import { useHomeAssistant } from './useHomeAssistant'
import type { EntityState } from '../types/entity'
import { isEntityOn } from '../types/entity'

interface UseEntityResult {
  entity: EntityState | undefined
  state: string
  isOn: boolean
  isAvailable: boolean
  attributes: EntityState['attributes']
  toggle: () => Promise<void>
  turnOn: (data?: Record<string, unknown>) => Promise<void>
  turnOff: () => Promise<void>
  setBrightness: (brightness: number) => Promise<void>
}

export function useEntity(entityId: string): UseEntityResult {
  const ha = useHomeAssistant()

  const entity = useMemo(
    () => ha.getState(entityId),
    [ha, entityId]
  )

  const state = entity?.state ?? 'unavailable'
  const isOn = entity ? isEntityOn(entity) : false
  const isAvailable = state !== 'unavailable' && state !== 'unknown'
  const attributes = entity?.attributes ?? {}

  const toggle = useCallback(async () => {
    await ha.toggle(entityId)
  }, [ha, entityId])

  const turnOn = useCallback(async (data?: Record<string, unknown>) => {
    await ha.turnOn(entityId, data)
  }, [ha, entityId])

  const turnOff = useCallback(async () => {
    await ha.turnOff(entityId)
  }, [ha, entityId])

  const setBrightness = useCallback(async (brightness: number) => {
    await ha.setBrightness(entityId, brightness)
  }, [ha, entityId])

  return {
    entity,
    state,
    isOn,
    isAvailable,
    attributes,
    toggle,
    turnOn,
    turnOff,
    setBrightness,
  }
}

export function useLightEntity(entityId: string) {
  const base = useEntity(entityId)

  const brightness = base.attributes.brightness
    ? Math.round((base.attributes.brightness / 255) * 100)
    : 0

  const colorTemp = base.attributes.color_temp
  const rgbColor = base.attributes.rgb_color
  const supportsBrightness = (base.attributes.supported_features ?? 0) & 1
  const supportsColorTemp = (base.attributes.supported_features ?? 0) & 2
  const supportsColor = (base.attributes.supported_features ?? 0) & 16

  return {
    ...base,
    brightness,
    colorTemp,
    rgbColor,
    supportsBrightness: Boolean(supportsBrightness),
    supportsColorTemp: Boolean(supportsColorTemp),
    supportsColor: Boolean(supportsColor),
  }
}

export function useClimateEntity(entityId: string) {
  const ha = useHomeAssistant()
  const base = useEntity(entityId)

  const currentTemperature = base.attributes.current_temperature ?? 0
  const targetTemperature = base.attributes.temperature ?? 0
  const hvacAction = base.attributes.hvac_action ?? 'off'
  const hvacModes = base.attributes.hvac_modes ?? []
  const presetMode = base.attributes.preset_mode
  const presetModes = base.attributes.preset_modes ?? []

  const setTemperature = useCallback(async (temperature: number) => {
    await ha.setTemperature(entityId, temperature)
  }, [ha, entityId])

  return {
    ...base,
    currentTemperature,
    targetTemperature,
    hvacAction,
    hvacModes,
    presetMode,
    presetModes,
    setTemperature,
  }
}

export function useSensorEntity(entityId: string) {
  const base = useEntity(entityId)

  const value = base.state
  const unit = base.attributes.unit_of_measurement ?? ''
  const deviceClass = base.attributes.device_class ?? ''

  return {
    ...base,
    value,
    unit,
    deviceClass,
  }
}

export default useEntity
