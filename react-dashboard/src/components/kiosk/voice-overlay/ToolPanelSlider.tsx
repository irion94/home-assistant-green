import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { useVoiceStore } from '@/stores/voiceStore'
import {
  WebViewPanel,
  SearchResultsPanel,
  LightControlDetailedPanel,
  MediaControlPanel,
  TimeDisplayPanel,
  HomeDataPanel,
  EntityDetailPanel,
  ResearchResultsPanel,
} from './display-panels'
import ToolPanel from './ToolPanel'

// Auto-close timeouts (ms)
const AUTO_CLOSE_TIMEOUTS: Record<string, number | null> = {
  light_control_detailed: 10000, // 10s
  media_control: null, // never auto-close
  web_view: null, // never auto-close
  search_results: 15000, // 15s
  research_results: null, // never auto-close
  get_time: 10000, // 10s
  get_home_data: 10000, // 10s
  get_entity: 10000, // 10s
}

interface ToolPanelSliderProps {
  roomId?: string
}

export const ToolPanelSlider = ({ roomId }: ToolPanelSliderProps) => {
  const {
    displayAction,
    activeTool,
    showLeftPanel,
    setAutoCloseTimer,
  } = useVoiceStore()

  // Show specific panel when displayAction changes
  useEffect(() => {
    if (displayAction && displayAction.type !== 'default') {
      // Panel switch handled by parent component via displayAction
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayAction?.timestamp]) // Watch timestamp to detect new actions even if same type

  // Auto-close timer - revert to default panel after timeout based on config
  useEffect(() => {
    if (!activeTool || activeTool === 'default') return

    const timeout = AUTO_CLOSE_TIMEOUTS[activeTool]
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

  // Render appropriate panel based on active tool
  const renderPanel = () => {
    // Default panel - 3-tab ToolPanel
    if (!activeTool || activeTool === 'default') {
      return <ToolPanel roomId={roomId} />
    }

    // If displayAction doesn't match activeTool, show default
    if (!displayAction || displayAction.type !== activeTool) {
      return <ToolPanel roomId={roomId} />
    }

    switch (activeTool) {
      case 'web_view':
        return <WebViewPanel action={displayAction} />
      case 'search_results':
        return <SearchResultsPanel action={displayAction} />
      case 'light_control_detailed':
        return <LightControlDetailedPanel action={displayAction} />
      case 'media_control':
        return <MediaControlPanel action={displayAction} />
      case 'research_results':
        return <ResearchResultsPanel action={displayAction} />
      case 'get_time':
        return <TimeDisplayPanel action={displayAction} />
      case 'get_home_data':
        return <HomeDataPanel action={displayAction} />
      case 'get_entity':
        return <EntityDetailPanel action={displayAction} />
      default:
        return <ToolPanel roomId={roomId} /> // Fallback to default panel
    }
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
