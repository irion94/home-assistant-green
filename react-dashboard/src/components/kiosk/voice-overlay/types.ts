// VoiceOverlay component types

export type DisplayActionType = 'default' | 'web_view' | 'light_control' | 'search_results'

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
