import type { EntityState, HistoryDataPoint } from '../../types/entity'

const HA_URL = import.meta.env.VITE_HA_URL || 'http://localhost:8123'
const HA_TOKEN = import.meta.env.VITE_HA_TOKEN || ''

class HomeAssistantClient {
  private baseUrl: string
  private token: string

  constructor(baseUrl: string = HA_URL, token: string = HA_TOKEN) {
    this.baseUrl = baseUrl.replace(/\/$/, '')
    this.token = token
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`

    const response = await fetch(url, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`HA API error (${response.status}): ${errorText}`)
    }

    return response.json()
  }

  async getStates(): Promise<EntityState[]> {
    return this.fetch<EntityState[]>('/api/states')
  }

  async getState(entityId: string): Promise<EntityState> {
    return this.fetch<EntityState>(`/api/states/${entityId}`)
  }

  async callService(
    domain: string,
    service: string,
    data?: Record<string, unknown>
  ): Promise<EntityState[]> {
    return this.fetch<EntityState[]>(`/api/services/${domain}/${service}`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    })
  }

  async turnOn(entityId: string, data?: Record<string, unknown>): Promise<EntityState[]> {
    const domain = entityId.split('.')[0]
    return this.callService(domain, 'turn_on', {
      entity_id: entityId,
      ...data,
    })
  }

  async turnOff(entityId: string): Promise<EntityState[]> {
    const domain = entityId.split('.')[0]
    return this.callService(domain, 'turn_off', {
      entity_id: entityId,
    })
  }

  async toggle(entityId: string): Promise<EntityState[]> {
    const domain = entityId.split('.')[0]
    return this.callService(domain, 'toggle', {
      entity_id: entityId,
    })
  }

  async setBrightness(entityId: string, brightness: number): Promise<EntityState[]> {
    return this.callService('light', 'turn_on', {
      entity_id: entityId,
      brightness,
    })
  }

  async setTemperature(entityId: string, temperature: number): Promise<EntityState[]> {
    return this.callService('climate', 'set_temperature', {
      entity_id: entityId,
      temperature,
    })
  }

  async setHvacMode(entityId: string, hvacMode: string): Promise<EntityState[]> {
    return this.callService('climate', 'set_hvac_mode', {
      entity_id: entityId,
      hvac_mode: hvacMode,
    })
  }

  async getHistory(
    entityId: string,
    startTime?: Date,
    endTime?: Date
  ): Promise<HistoryDataPoint[][]> {
    const start = startTime || new Date(Date.now() - 24 * 60 * 60 * 1000)
    const end = endTime || new Date()

    const params = new URLSearchParams({
      filter_entity_id: entityId,
      end_time: end.toISOString(),
    })

    return this.fetch<HistoryDataPoint[][]>(
      `/api/history/period/${start.toISOString()}?${params}`
    )
  }

  async checkConnection(): Promise<boolean> {
    try {
      await this.fetch('/api/')
      return true
    } catch {
      return false
    }
  }
}

// Export class for use by unified API service
export { HomeAssistantClient }
export default HomeAssistantClient
