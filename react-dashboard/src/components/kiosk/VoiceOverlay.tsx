import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { mqttService, VoiceState } from '../../services/mqttService'
import { useVoiceStore, useDisplayAction } from '../../stores/voiceStore'
import DisplayPanel from './voice-overlay/DisplayPanel'
import ChatSection from './voice-overlay/ChatSection'
import StatusIndicator from './voice-overlay/StatusIndicator'
import ToolPanel from './voice-overlay/ToolPanel'
import { DebugLogPanel } from './DebugLogPanel'

// Feature flag for Phase 4 Tool Dashboard
const TOOL_DASHBOARD_ENABLED = import.meta.env.VITE_TOOL_DASHBOARD_ENABLED === 'true'

interface VoiceOverlayProps {
  isOpen: boolean
  onClose: () => void
  roomId?: string
  /** If true, start a session immediately when overlay opens (for button click) */
  startOnOpen?: boolean
  /** Initial state to display when opened via wake-word detection */
  initialState?: VoiceState
}

export default function VoiceOverlay({ isOpen, onClose, roomId = 'default', startOnOpen = false, initialState = 'idle' }: VoiceOverlayProps) {
  // Zustand store - single source of truth
  const {
    state,
    messages,
    conversationMode,
    setVoiceState
  } = useVoiceStore()
  const displayAction = useDisplayAction()

  // Set room ID when it changes
  useEffect(() => {
    mqttService.setRoomId(roomId)
  }, [roomId])

  // Sync state when initialState prop changes (for wake-word triggered opening)
  useEffect(() => {
    if (isOpen && initialState !== 'idle') {
      setVoiceState(initialState)
    }
  }, [isOpen, initialState, setVoiceState])

  // Start session when overlay opens via button click
  // Note: MQTT service now writes directly to Zustand store
  // No callbacks needed - eliminates all race conditions!
  useEffect(() => {
    if (isOpen && startOnOpen) {
      const tryStartSession = () => {
        if (mqttService.isConnected()) {
          mqttService.startSession('single')
          console.log(`[VoiceOverlay] Starting command session via MQTT (AI will decide mode)`)
        } else {
          console.log(`[VoiceOverlay] Waiting for MQTT connection...`)
          setTimeout(tryStartSession, 100)
        }
      }
      // Small delay to ensure store is ready
      setTimeout(tryStartSession, 50)
    }
  }, [isOpen, startOnOpen])

  // Handle manual close
  const handleClose = () => {
    mqttService.stopSession()
    onClose()
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-[100] flex flex-col bg-black/90 backdrop-blur-sm"
        >
          {/* Row 1: Header - Statuses, buttons, etc */}
          <div className="flex-shrink-0">
            <DisplayPanel
              displayAction={displayAction}
              roomId={roomId}
              onClose={handleClose}
            />
          </div>

          {/* Row 2: Three-column layout */}
          <div className="flex-1 flex overflow-hidden">
            {/* Left Panel: Tool Dashboard (Phase 4) or Debug Logs (legacy) - flex to take available space */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {TOOL_DASHBOARD_ENABLED ? (
                <ToolPanel roomId={roomId} />
              ) : (
                <DebugLogPanel />
              )}
            </div>

            {/* Center Panel: Status indicator (fixed width) */}
            <div className="flex items-end justify-center p-6" style={{ flexBasis: '200px', flexShrink: 0, flexGrow: 0 }}>
              <StatusIndicator state={state} conversationMode={conversationMode} />
            </div>

            {/* Right Panel: Chat messages - flex to take available space */}
            <div className="flex-1 flex flex-col overflow-y-auto scrollbar-hide">
              <ChatSection messages={messages} />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
