export interface EntityState {
  entity_id: string
  state: string
  attributes: EntityAttributes
  last_changed: string
  last_updated: string
  context: {
    id: string
    parent_id: string | null
    user_id: string | null
  }
}

export interface EntityAttributes {
  friendly_name?: string
  icon?: string
  unit_of_measurement?: string
  device_class?: string
  // Light attributes
  brightness?: number
  color_temp?: number
  rgb_color?: [number, number, number]
  hs_color?: [number, number]
  supported_features?: number
  // Climate attributes
  temperature?: number
  current_temperature?: number
  target_temp_high?: number
  target_temp_low?: number
  hvac_action?: string
  hvac_modes?: string[]
  preset_mode?: string
  preset_modes?: string[]
  // Weather attributes
  forecast?: WeatherForecast[]
  humidity?: number
  pressure?: number
  wind_speed?: number
  wind_bearing?: number
  // Media attributes
  media_title?: string
  media_artist?: string
  volume_level?: number
  is_volume_muted?: boolean
  // Generic
  [key: string]: unknown
}

export interface WeatherForecast {
  datetime: string
  temperature: number
  templow?: number
  condition: string
  precipitation?: number
  precipitation_probability?: number
  humidity?: number
  wind_speed?: number
}

export interface HistoryDataPoint {
  state: string
  last_changed: string
  attributes?: EntityAttributes
}

export type EntityDomain =
  | 'light'
  | 'switch'
  | 'climate'
  | 'sensor'
  | 'binary_sensor'
  | 'weather'
  | 'media_player'
  | 'cover'
  | 'fan'
  | 'automation'
  | 'scene'

export function getDomain(entityId: string): EntityDomain {
  return entityId.split('.')[0] as EntityDomain
}

export function isEntityOn(entity: EntityState): boolean {
  return ['on', 'playing', 'home', 'open'].includes(entity.state.toLowerCase())
}

export function formatEntityState(entity: EntityState): string {
  const { state, attributes } = entity

  if (attributes.unit_of_measurement) {
    return `${state} ${attributes.unit_of_measurement}`
  }

  switch (state) {
    case 'on':
      return 'On'
    case 'off':
      return 'Off'
    case 'unavailable':
      return 'Unavailable'
    case 'unknown':
      return 'Unknown'
    default:
      return state
  }
}
