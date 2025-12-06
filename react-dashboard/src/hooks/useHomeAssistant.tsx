import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from 'react'
import { haClient, haWebSocket } from '../api'
import type { EntityState } from '../types/entity'

interface HomeAssistantContextType {
  states: Map<string, EntityState>
  connected: boolean
  loading: boolean
  error: string | null
  getState: (entityId: string) => EntityState | undefined
  callService: (domain: string, service: string, data?: Record<string, unknown>) => Promise<void>
  toggle: (entityId: string) => Promise<void>
  turnOn: (entityId: string, data?: Record<string, unknown>) => Promise<void>
  turnOff: (entityId: string) => Promise<void>
  setBrightness: (entityId: string, brightness: number) => Promise<void>
  setTemperature: (entityId: string, temperature: number) => Promise<void>
  refresh: () => Promise<void>
}

const HomeAssistantContext = createContext<HomeAssistantContextType | null>(null)

export function HomeAssistantProvider({ children }: { children: ReactNode }) {
  const [states, setStates] = useState<Map<string, EntityState>>(new Map())
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Initial fetch of all states
  const fetchStates = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const allStates = await haClient.getStates()
      const stateMap = new Map<string, EntityState>()
      allStates.forEach(state => {
        stateMap.set(state.entity_id, state)
      })
      setStates(stateMap)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch states'
      setError(message)
      console.error('Failed to fetch states:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Connect WebSocket and subscribe to updates
  useEffect(() => {
    fetchStates()

    // Set up WebSocket connection
    haWebSocket.connect().catch(err => {
      console.error('WebSocket connection failed:', err)
    })

    // Handle state changes from WebSocket
    const unsubscribeState = haWebSocket.onStateChange((entityId, newState) => {
      setStates(prev => {
        const updated = new Map(prev)
        updated.set(entityId, newState)
        return updated
      })
    })

    // Handle connection status
    const unsubscribeConnection = haWebSocket.onConnectionChange(setConnected)

    return () => {
      unsubscribeState()
      unsubscribeConnection()
      haWebSocket.disconnect()
    }
  }, [fetchStates])

  const getState = useCallback(
    (entityId: string) => states.get(entityId),
    [states]
  )

  const callService = useCallback(
    async (domain: string, service: string, data?: Record<string, unknown>) => {
      try {
        await haClient.callService(domain, service, data)
      } catch (err) {
        console.error(`Service call failed: ${domain}.${service}`, err)
        throw err
      }
    },
    []
  )

  const toggle = useCallback(
    async (entityId: string) => {
      await haClient.toggle(entityId)
    },
    []
  )

  const turnOn = useCallback(
    async (entityId: string, data?: Record<string, unknown>) => {
      await haClient.turnOn(entityId, data)
    },
    []
  )

  const turnOff = useCallback(
    async (entityId: string) => {
      await haClient.turnOff(entityId)
    },
    []
  )

  const setBrightness = useCallback(
    async (entityId: string, brightness: number) => {
      await haClient.setBrightness(entityId, brightness)
    },
    []
  )

  const setTemperature = useCallback(
    async (entityId: string, temperature: number) => {
      await haClient.setTemperature(entityId, temperature)
    },
    []
  )

  const value: HomeAssistantContextType = {
    states,
    connected,
    loading,
    error,
    getState,
    callService,
    toggle,
    turnOn,
    turnOff,
    setBrightness,
    setTemperature,
    refresh: fetchStates,
  }

  return (
    <HomeAssistantContext.Provider value={value}>
      {children}
    </HomeAssistantContext.Provider>
  )
}

/**
 * @deprecated This hook is deprecated. Use entity hooks from useEntity.ts instead.
 *
 * Migration guide:
 * - Replace `useHomeAssistant()` with `useEntity(entityId)` or domain-specific hooks
 * - Use `useLightEntity()`, `useClimateEntity()`, `useSensorEntity()` instead
 * - Entity state is now managed by Zustand entityStore instead of React Context
 *
 * This hook will be removed in Phase 6 of the refactoring.
 */
export function useHomeAssistant() {
  console.warn(
    'useHomeAssistant() is deprecated. Migrate to useEntity() hooks. ' +
    'See src/hooks/useEntity.ts for the new API.'
  )

  const context = useContext(HomeAssistantContext)
  if (!context) {
    throw new Error('useHomeAssistant must be used within HomeAssistantProvider')
  }
  return context
}

export default useHomeAssistant
