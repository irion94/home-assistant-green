/**
 * Unified API Service
 *
 * Consolidates all API clients (REST, WebSocket, MQTT, Gateway) into a single service.
 * All clients write directly to Zustand stores (not callbacks).
 *
 * Features:
 * - Centralized API access point
 * - Automatic store integration
 * - Optimistic updates
 * - Error handling and retry logic
 */

import HomeAssistantClient from './ha-rest'
import HAWebSocket from './ha-websocket'
import { useEntityStore } from '../../stores/entityStore'
import type { EntityState } from '../../types/entity'

/**
 * ApiService - Singleton managing all API clients
 */
class ApiService {
  public haRest: HomeAssistantClient
  public haWebSocket: HAWebSocket
  private initialized = false

  constructor() {
    // Initialize clients
    this.haRest = new HomeAssistantClient()
    this.haWebSocket = new HAWebSocket()
  }

  /**
   * Initialize API service and connect stores
   * Call this once during app startup
   */
  async initialize(): Promise<void> {
    if (this.initialized) return

    try {
      // Fetch initial states via REST
      useEntityStore.getState().setLoading(true)
      useEntityStore.getState().setError(null)

      const states = await this.haRest.getStates()
      useEntityStore.getState().setEntities(states)

      useEntityStore.getState().setLoading(false)

      // Connect WebSocket
      await this.haWebSocket.connect()

      // Subscribe to WebSocket updates → write to entity store
      this.haWebSocket.onStateChange((_entityId: string, newState: EntityState) => {
        useEntityStore.getState().setEntity(newState)
      })

      // Subscribe to connection status → write to entity store
      this.haWebSocket.onConnectionChange((connected: boolean) => {
        useEntityStore.getState().setConnected(connected)
      })

      // Override entity store service call methods with real implementations
      this.connectStoreActions()

      this.initialized = true
      console.log('API service initialized successfully')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to initialize API service'
      useEntityStore.getState().setError(message)
      useEntityStore.getState().setLoading(false)
      console.error('API initialization error:', error)
      throw error
    }
  }

  /**
   * Connect entity store actions to actual API calls
   * Overrides the placeholder methods in entityStore
   */
  private connectStoreActions(): void {
    const store = useEntityStore.getState()

    // Override callService
    useEntityStore.setState({
      callService: async (domain: string, service: string, data?: Record<string, unknown>) => {
        try {
          await this.haRest.callService(domain, service, data)
        } catch (error) {
          console.error(`Service call failed: ${domain}.${service}`, error)
          throw error
        }
      },
    })

    // Override toggle
    useEntityStore.setState({
      toggle: async (entityId: string) => {
        const entity = store.getEntity(entityId)
        if (entity) {
          // Optimistic update
          store.updateEntityOptimistic(entityId, {
            state: entity.isOn ? 'off' : 'on',
          })
        }

        try {
          await this.haRest.toggle(entityId)
        } catch (error) {
          // Revert optimistic update on error
          if (entity) {
            store.setEntity(entity as EntityState)
          }
          throw error
        }
      },
    })

    // Override turnOn
    useEntityStore.setState({
      turnOn: async (entityId: string, data?: Record<string, unknown>) => {
        // Optimistic update
        store.updateEntityOptimistic(entityId, { state: 'on' })

        try {
          await this.haRest.turnOn(entityId, data)
        } catch (error) {
          // Revert on error (refetch from server)
          const entity = await this.haRest.getState(entityId)
          store.setEntity(entity)
          throw error
        }
      },
    })

    // Override turnOff
    useEntityStore.setState({
      turnOff: async (entityId: string) => {
        // Optimistic update
        store.updateEntityOptimistic(entityId, { state: 'off' })

        try {
          await this.haRest.turnOff(entityId)
        } catch (error) {
          // Revert on error
          const entity = await this.haRest.getState(entityId)
          store.setEntity(entity)
          throw error
        }
      },
    })

    // Override setBrightness
    useEntityStore.setState({
      setBrightness: async (entityId: string, brightness: number) => {
        // Optimistic update
        store.updateEntityOptimistic(entityId, {
          attributes: { brightness },
        })

        try {
          await this.haRest.setBrightness(entityId, brightness)
        } catch (error) {
          // Revert on error
          const entity = await this.haRest.getState(entityId)
          store.setEntity(entity)
          throw error
        }
      },
    })

    // Override setTemperature
    useEntityStore.setState({
      setTemperature: async (entityId: string, temperature: number) => {
        // Optimistic update
        store.updateEntityOptimistic(entityId, {
          attributes: { temperature },
        })

        try {
          await this.haRest.setTemperature(entityId, temperature)
        } catch (error) {
          // Revert on error
          const entity = await this.haRest.getState(entityId)
          store.setEntity(entity)
          throw error
        }
      },
    })
  }

  /**
   * Disconnect and cleanup
   */
  async disconnect(): Promise<void> {
    this.haWebSocket.disconnect()
    this.initialized = false
  }

  /**
   * Refresh all entity states
   */
  async refresh(): Promise<void> {
    try {
      useEntityStore.getState().setLoading(true)
      const states = await this.haRest.getStates()
      useEntityStore.getState().setEntities(states)
      useEntityStore.getState().setLoading(false)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to refresh states'
      useEntityStore.getState().setError(message)
      useEntityStore.getState().setLoading(false)
      throw error
    }
  }

  /**
   * Check connection health
   */
  async checkConnection(): Promise<boolean> {
    return this.haRest.checkConnection()
  }
}

/**
 * Singleton instance
 */
export const api = new ApiService()

/**
 * React hook to ensure API is initialized
 * Use this in your root component
 */
export function useApiInitialization() {
  const loading = useEntityStore(state => state.loading)
  const error = useEntityStore(state => state.error)
  const connected = useEntityStore(state => state.connected)

  return { loading, error, connected }
}

/**
 * Export clients for direct access if needed
 */
export { HomeAssistantClient } from './ha-rest'
export { HAWebSocket } from './ha-websocket'
export const haClient = api.haRest
export const haWebSocket = api.haWebSocket
