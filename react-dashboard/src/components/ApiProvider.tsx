/**
 * API Provider Component
 *
 * Initializes the unified API service and manages connection state.
 * Must be rendered at the root of the app before any components that use entities.
 */

import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../services/api'
import { useEntityStoreConnected } from '../stores/entityStore'

interface ApiProviderProps {
  children: ReactNode
}

export function ApiProvider({ children }: ApiProviderProps) {
  const [initializing, setInitializing] = useState(true)
  const [initError, setInitError] = useState<string | null>(null)
  const connected = useEntityStoreConnected()

  useEffect(() => {
    let mounted = true

    async function initializeApi() {
      try {
        await api.initialize()
        if (mounted) {
          setInitializing(false)
          setInitError(null)
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to initialize API'
        if (mounted) {
          setInitError(message)
          setInitializing(false)
        }
      }
    }

    initializeApi()

    return () => {
      mounted = false
      // Cleanup on unmount
      api.disconnect()
    }
  }, [])

  // Show loading state during initial connection
  if (initializing) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary mx-auto"></div>
          <p className="text-text-secondary">Connecting to Home Assistant...</p>
        </div>
      </div>
    )
  }

  // Show error state if initialization failed
  if (initError && !connected) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="max-w-md p-6 bg-surface rounded-lg border border-error">
          <h2 className="text-xl font-bold text-error mb-2">Connection Error</h2>
          <p className="text-text-secondary mb-4">{initError}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // Render children once connected
  return <>{children}</>
}
