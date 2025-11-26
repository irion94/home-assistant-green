import type { EntityState } from '../../types/entity'
import type { HAStateChangedEvent } from '../../types/api'

const HA_URL = import.meta.env.VITE_HA_URL || 'http://localhost:8123'
const HA_TOKEN = import.meta.env.VITE_HA_TOKEN || ''

type StateChangeCallback = (entityId: string, newState: EntityState) => void
type ConnectionCallback = (connected: boolean) => void

class HAWebSocket {
  private ws: WebSocket | null = null
  private messageId = 1
  private token: string
  private wsUrl: string
  private stateChangeCallbacks: StateChangeCallback[] = []
  private connectionCallbacks: ConnectionCallback[] = []
  private reconnectTimeout: number | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private isAuthenticated = false

  constructor(haUrl: string = HA_URL, token: string = HA_TOKEN) {
    const url = new URL(haUrl)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    url.pathname = '/api/websocket'
    this.wsUrl = url.toString()
    this.token = token
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      this.ws = new WebSocket(this.wsUrl)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
      }

      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data)
        this.handleMessage(message, resolve, reject)
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        reject(error)
      }

      this.ws.onclose = () => {
        console.log('WebSocket closed')
        this.isAuthenticated = false
        this.notifyConnectionChange(false)
        this.scheduleReconnect()
      }
    })
  }

  private handleMessage(
    message: Record<string, unknown>,
    resolve?: () => void,
    reject?: (error: Error) => void
  ) {
    switch (message.type) {
      case 'auth_required':
        this.authenticate()
        break

      case 'auth_ok':
        console.log('WebSocket authenticated')
        this.isAuthenticated = true
        this.notifyConnectionChange(true)
        this.subscribeToStateChanges()
        resolve?.()
        break

      case 'auth_invalid':
        console.error('WebSocket authentication failed')
        reject?.(new Error('Authentication failed'))
        break

      case 'event':
        if ((message.event as HAStateChangedEvent)?.event_type === 'state_changed') {
          const event = message.event as HAStateChangedEvent
          const { entity_id, new_state } = event.data
          if (new_state) {
            this.notifyStateChange(entity_id, new_state)
          }
        }
        break

      case 'result':
        // Handle results from commands if needed
        break
    }
  }

  private authenticate() {
    if (!this.ws) return

    this.ws.send(JSON.stringify({
      type: 'auth',
      access_token: this.token,
    }))
  }

  private subscribeToStateChanges() {
    if (!this.ws) return

    const id = this.messageId++
    this.ws.send(JSON.stringify({
      id,
      type: 'subscribe_events',
      event_type: 'state_changed',
    }))
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout) return
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)
    this.reconnectAttempts++

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    this.reconnectTimeout = window.setTimeout(() => {
      this.reconnectTimeout = null
      this.connect().catch(console.error)
    }, delay)
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  onStateChange(callback: StateChangeCallback): () => void {
    this.stateChangeCallbacks.push(callback)
    return () => {
      this.stateChangeCallbacks = this.stateChangeCallbacks.filter(cb => cb !== callback)
    }
  }

  onConnectionChange(callback: ConnectionCallback): () => void {
    this.connectionCallbacks.push(callback)
    return () => {
      this.connectionCallbacks = this.connectionCallbacks.filter(cb => cb !== callback)
    }
  }

  private notifyStateChange(entityId: string, newState: EntityState) {
    this.stateChangeCallbacks.forEach(cb => cb(entityId, newState))
  }

  private notifyConnectionChange(connected: boolean) {
    this.connectionCallbacks.forEach(cb => cb(connected))
  }

  callService(
    domain: string,
    service: string,
    data?: Record<string, unknown>
  ): void {
    if (!this.ws || !this.isAuthenticated) {
      console.error('WebSocket not connected')
      return
    }

    const id = this.messageId++
    this.ws.send(JSON.stringify({
      id,
      type: 'call_service',
      domain,
      service,
      service_data: data,
    }))
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN && this.isAuthenticated
  }
}

// Export class for use by unified API service
export { HAWebSocket }
export default HAWebSocket
