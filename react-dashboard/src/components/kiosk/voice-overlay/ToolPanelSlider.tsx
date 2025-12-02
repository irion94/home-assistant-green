import { useEffect, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Loader2 } from 'lucide-react'
import { useUIStore } from '@/stores/uiStore'
import { useDeviceStore } from '@/stores/deviceStore'
import { panelRegistry } from './display-panels/registry'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { PanelError } from './PanelError'
import ToolPanel from './ToolPanel'

// IMPORTANT: Import display-panels index to trigger panel registration
import './display-panels'

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
  const clearDisplayAction = useDeviceStore((state) => state.clearDisplayAction)
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

  // Auto-close timer - uses timeout from registry
  useEffect(() => {
    if (!activeTool || activeTool === 'default') return

    const timeout = panelRegistry.getAutoCloseTimeout(activeTool)

    if (timeout === null) {
      console.log('[ToolPanelSlider] No auto-close for', activeTool)
      return // Never auto-close
    }

    console.log(`[ToolPanelSlider] Auto-close ${activeTool} in ${timeout}ms`)

    const timerId = setTimeout(() => {
      console.log('[ToolPanelSlider] Auto-close timer fired, resetting to default')
      clearDisplayAction()
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
    console.log('[ToolPanelSlider] renderPanel:', { activeTool, displayAction: displayAction?.type })

    // Default panel - 3-tab ToolPanel
    if (!activeTool || activeTool === 'default') {
      console.log('[ToolPanelSlider] Showing default ToolPanel')
      return <ToolPanel roomId={roomId} />
    }

    // If displayAction doesn't match activeTool, show default
    if (!displayAction || displayAction.type !== activeTool) {
      console.log('[ToolPanelSlider] Mismatch - showing default ToolPanel')
      return <ToolPanel roomId={roomId} />
    }

    // Get panel from registry (eliminates switch statement)
    const panelConfig = panelRegistry.get(activeTool)
    console.log('[ToolPanelSlider] Panel registry lookup:', { activeTool, found: !!panelConfig })

    if (!panelConfig) {
      console.warn(`[ToolPanelSlider] Panel not found in registry: ${activeTool}`)
      console.log('[ToolPanelSlider] Available panels:', Array.from(panelRegistry['panels'].keys()))
      return <ToolPanel roomId={roomId} />
    }

    console.log('[ToolPanelSlider] Showing panel:', panelConfig.title, 'Component:', panelConfig.component.name, 'Action:', displayAction)
    const PanelComponent = panelConfig.component

    return (
      <ErrorBoundary fallback={<div className="text-white p-4">Error loading panel</div>}>
        <Suspense fallback={<PanelLoadingSpinner />}>
          <PanelComponent action={displayAction} />
        </Suspense>
      </ErrorBoundary>
    )
  }

  return (
    <div className="h-full w-full relative">
      <div className="h-full w-full flex flex-col">
        {/* Close button - only show for non-default panels */}
        {activeTool !== 'default' && (
          <button
            onClick={() => {
              clearDisplayAction()
              showLeftPanel('default')
            }}
            className="absolute top-4 right-4 z-20 p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
            aria-label="Close panel"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        )}

        {/* Panel content - takes full height */}
        <div className="flex-1 overflow-y-auto scrollbar-hide">
          {/* Rounded wrapper with solid background */}
          <div className="min-h-full bg-black/80 backdrop-blur-md border-r border-white/30 shadow-xl p-6 rounded-r-3xl">
            <ErrorBoundary fallback={<PanelError />}>
              <Suspense fallback={<PanelLoadingSpinner />}>
                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeTool} // Key ensures re-animation on tool change
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{
                      duration: 0.15,
                      ease: 'easeOut',
                    }}
                  >
                    {renderPanel()}
                  </motion.div>
                </AnimatePresence>
              </Suspense>
            </ErrorBoundary>
          </div>
        </div>
      </div>
    </div>
  )
}
