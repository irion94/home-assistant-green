export interface HAServiceCall {
  domain: string
  service: string
  service_data?: Record<string, unknown>
  target?: {
    entity_id?: string | string[]
    device_id?: string | string[]
    area_id?: string | string[]
  }
}

export interface HAWebSocketMessage {
  id?: number
  type: string
  [key: string]: unknown
}

export interface HAAuthMessage {
  type: 'auth'
  access_token: string
}

export interface HASubscribeMessage {
  id: number
  type: 'subscribe_events'
  event_type?: string
}

export interface HACallServiceMessage {
  id: number
  type: 'call_service'
  domain: string
  service: string
  service_data?: Record<string, unknown>
  target?: HAServiceCall['target']
}

export interface HAStateChangedEvent {
  event_type: 'state_changed'
  data: {
    entity_id: string
    old_state: import('./entity').EntityState | null
    new_state: import('./entity').EntityState | null
  }
  origin: string
  time_fired: string
  context: {
    id: string
    parent_id: string | null
    user_id: string | null
  }
}

export interface GatewayResponse {
  success: boolean
  message: string
  action?: string
  entities?: string[]
  error?: string
}

export interface ConversationResponse {
  status: string
  text: string
  session_id: string
  message?: string
  intent?: string
  entities?: string[]
}

export interface VoiceResponse {
  status: string
  text: string | null
  session_id: string
  message?: string
  transcription?: string
}
