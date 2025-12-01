// VoiceOverlay component types

export type DisplayActionType =
  | 'default'
  | 'web_view'
  | 'light_control'
  | 'light_control_detailed'
  | 'search_results'
  | 'media_control'
  | 'get_time'
  | 'get_home_data'
  | 'get_entity'
  | 'research_results'

export interface DisplayAction {
  type: DisplayActionType
  data: Record<string, any>
  timestamp: number
}

// Display Panel props interface
export interface DisplayPanelProps {
  action: DisplayAction
  roomId?: string
  onClose?: () => void
}

// Light control panel specific data
export interface LightControlData {
  room: string
  entities: string[]
  action: 'on' | 'off' | 'toggle'
  brightness?: number
  color?: {
    r: number
    g: number
    b: number
  }
  kelvin?: number
}

// Search results panel specific data
export interface SearchResult {
  title: string
  url: string
  snippet: string
}

export interface SearchResultsData {
  query: string
  results: SearchResult[]
}

// Web view panel specific data
export interface WebViewData {
  url: string
  title?: string
}

// Detailed light control panel data
export interface LightEntity {
  entity_id: string
  friendly_name: string
  state: 'on' | 'off'
  brightness?: number
  brightness_pct?: number
  color_temp?: number
  rgb_color?: [number, number, number]
  supported_features?: string[]
}

export interface LightControlDetailedData {
  room: string
  entities: LightEntity[]
  action_performed: string
  supports_interaction: boolean
}

// Media control panel data
export interface MediaControlData {
  entity_id: string
  state: string
  media_title?: string
  media_artist?: string
  media_album?: string
  media_duration?: number
  media_position?: number
  volume_level?: number
  artwork_url?: string
}
