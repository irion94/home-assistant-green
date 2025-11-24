import { Outlet } from 'react-router-dom'
import Navigation from './Navigation'
import Header from './Header'
import { useHomeAssistant } from '../../hooks/useHomeAssistant'

export default function KioskLayout() {
  const { connected, loading, error } = useHomeAssistant()

  return (
    <div className="h-screen w-screen flex flex-col bg-background overflow-hidden">
      {/* Header */}
      <Header />

      {/* Connection status */}
      {!connected && !loading && (
        <div className="bg-warning/20 text-warning px-4 py-2 text-center text-sm">
          Disconnected from Home Assistant - Reconnecting...
        </div>
      )}

      {error && (
        <div className="bg-error/20 text-error px-4 py-2 text-center text-sm">
          {error}
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 overflow-auto p-4">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin w-12 h-12 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-text-secondary">Loading...</p>
            </div>
          </div>
        ) : (
          <Outlet />
        )}
      </main>

      {/* Bottom navigation */}
      <Navigation />
    </div>
  )
}
