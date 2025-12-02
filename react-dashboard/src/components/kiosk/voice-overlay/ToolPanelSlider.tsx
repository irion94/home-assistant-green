import { useEffect, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Loader2 } from 'lucide-react'
import { useUIStore } from '@/stores/uiStore'
import { useDeviceStore } from '@/stores/deviceStore'
import { panelRegistry } from './display-panels/registry'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import ToolPanel from './ToolPanel'

// Panel loading spinner component
const PanelLoadingSpinner = () => (
  <div className="flex items-center justify-center h-full">
    <Loader2 className="w-8 h-8 animate-spin text-primary" />
  </div>
)

interface ToolPanelSliderProps {
  roomId?: string
}

export const ToolPanelSlider = ({ roomId }: ToolPanelSliderProps) => {
  const displayAction = useDeviceStore((state) => state.displayAction)
  const activeTool = useUIStore((state) => state.activeTool)
  const showLeftPanel = useUIStore((state) => state.showLeftPanel)
  const setAutoCloseTimer = useUIStore((state) => state.setAutoCloseTimer)

  // Show specific panel when displayAction changes
  useEffect(() => {
    if (displayAction && displayAction.type !== 'default') {
      // Panel switch handled by parent component via displayAction
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayAction?.timestamp]) // Watch timestamp to detect new actions even if same type

  // Auto-close timer - uses PanelRegistry configuration
  useEffect(() => {
    if (!activeTool || activeTool === 'default') return

    // Get timeout from PanelRegistry (eliminates AUTO_CLOSE_TIMEOUTS object)
    const timeout = panelRegistry.getAutoCloseTimeout(activeTool)
    if (timeout === null) return // Never auto-close

    const timerId = setTimeout(() => {
      // Revert to default panel after timeout
      showLeftPanel('default')
    }, timeout)

    setAutoCloseTimer(timerId)

    return () => {
      clearTimeout(timerId)
      setAutoCloseTimer(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTool])

  // Render appropriate panel based on active tool - uses PanelRegistry (no switch statement)
  const renderPanel = () => {
    // Default panel - 3-tab ToolPanel
    if (!activeTool || activeTool === 'default') {
      return <ToolPanel roomId={roomId} />
    }

    // If displayAction doesn't match activeTool, show default
    if (!displayAction || displayAction.type !== activeTool) {
      return <ToolPanel roomId={roomId} />
    }

    // Get panel from registry (eliminates switch statement)
    const panelConfig = panelRegistry.get(activeTool)
    if (!panelConfig) {
      console.warn(`[ToolPanelSlider] Panel not found in registry: ${activeTool}`)
      return <ToolPanel roomId={roomId} />
    }

    const PanelComponent = panelConfig.component

    return (
      <ErrorBoundary>
        <Suspense fallback={<PanelLoadingSpinner />}>
          <PanelComponent action={displayAction} />
        </Suspense>
      </ErrorBoundary>
    )
  }

  return (
    <div className="h-full w-full">
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTool} // Key ensures re-animation on tool change
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{
            duration: 0.2,
            ease: 'easeOut',
          }}
          className="bg-transparent absolute inset-0"
        >
          {/* Close button - only show for non-default panels */}
          {activeTool !== 'default' && (
            <button
              onClick={() => showLeftPanel('default')}
              className="absolute top-4 right-4 z-20 p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
              aria-label="Close panel"
            >
              <X className="w-5 h-5" />
            </button>
          )}

          {/* Panel content */}
          <div className="h-full w-full overflow-y-auto scrollbar-hide">
            {/* Rounded wrapper with subtle background */}
            <div className="h-full bg-black/[0.25] backdrop-blur-md border-r border-white/20 shadow-xl p-6 overflow-y-auto scrollbar-hide rounded-r-3xl">
              {renderPanel()}
            </div>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
