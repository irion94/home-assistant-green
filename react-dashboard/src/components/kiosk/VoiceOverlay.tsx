import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { mqttService, VoiceState } from '../../services/mqttService'
import { useConversationStore } from '../../stores/conversationStore'
import { useUIStore } from '../../stores/uiStore'
import { useDeviceStore } from '../../stores/deviceStore'
import { useBrowserTTS } from '../../hooks/useBrowserTTS'
import { browserSTT } from '../../services/browserSTT'
import ChatSection from './voice-overlay/ChatSection'
import StatusIndicator from './voice-overlay/StatusIndicator'
import { ToolPanelSlider } from './voice-overlay/ToolPanelSlider'
import DefaultDisplayPanel from './voice-overlay/display-panels/DefaultDisplayPanel'

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
  // Phase 6: Use split stores for better performance
  const messages = useConversationStore((state) => state.messages)
  const conversationMode = useConversationStore((state) => state.conversationMode)
  const state = useUIStore((state) => state.state)
  const setVoiceState = useUIStore((state) => state.setVoiceState)

  // Loading state for center button feedback
  const [isStarting, setIsStarting] = useState(false)

  // Interim transcript state for browser STT
  const [interimTranscript, setInterimTranscript] = useState('')

  // Browser TTS for dashboard sessions
  const { speak, stop } = useBrowserTTS()

  // Track last message streaming state to detect completion
  const lastMessageIdRef = useRef<string | null>(null)
  const wasStreamingRef = useRef<boolean>(false)
  const hasInitializedRef = useRef<boolean>(false)

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

  // Speak assistant responses when they complete streaming
  // Only triggers when a message transitions from streaming → complete
  useEffect(() => {
    if (!isOpen || messages.length === 0) return

    // Get the last message
    const lastMessage = messages[messages.length - 1]

    // Check if this is an assistant message
    if (!lastMessage || lastMessage.type !== 'assistant') {
      return
    }

    // Detect streaming → complete transition
    const currentlyStreaming = lastMessage.isStreaming || false
    const justFinishedStreaming = wasStreamingRef.current && !currentlyStreaming
    const isNewMessage = lastMessage.id !== lastMessageIdRef.current

    // On first run, just initialize state without speaking (skip old messages)
    if (!hasInitializedRef.current) {
      hasInitializedRef.current = true
      lastMessageIdRef.current = lastMessage.id
      wasStreamingRef.current = currentlyStreaming
      console.log('[VoiceOverlay] Initialized TTS tracking, skipping old messages')
      return
    }

    // Update refs for next check
    const shouldSpeak = (justFinishedStreaming || (isNewMessage && !currentlyStreaming))
      && lastMessage.text
      && lastMessage.text.trim().length > 0

    lastMessageIdRef.current = lastMessage.id
    wasStreamingRef.current = currentlyStreaming

    // Speak when:
    // 1. Message transitions from streaming to complete (streaming responses)
    // 2. New non-streaming message appears (Quick Actions, direct API calls)
    if (shouldSpeak) {
      console.log('[VoiceOverlay] Speaking assistant response via browser TTS')
      speak(lastMessage.text)
    }
  }, [isOpen, messages, speak])

  // Reset TTS tracking when overlay closes
  useEffect(() => {
    if (!isOpen) {
      // Reset tracking refs when overlay closes
      hasInitializedRef.current = false
      lastMessageIdRef.current = null
      wasStreamingRef.current = false
    }
  }, [isOpen])

  // Handle manual close
  const handleClose = () => {
    browserSTT.stop() // Stop browser STT
    stop() // Cancel any ongoing browser TTS
    mqttService.stopSession()
    onClose()
  }

  // Handle start session from center button (Browser-First Architecture)
  const handleStartSession = () => {
    if (state !== 'idle') return

    // Check browser STT availability
    if (!browserSTT.isAvailable()) {
      console.error('[VoiceOverlay] Browser STT not available')
      // TODO: Show error to user
      return
    }

    // Clear previous messages
    useConversationStore.getState().clearMessages()

    // Start listening state
    setVoiceState('listening')
    setInterimTranscript('')

    // Start browser speech recognition
    const success = browserSTT.start({
      lang: 'pl-PL',
      continuous: false,

      onStart: () => {
        console.log('[VoiceOverlay] Browser STT started')
        setVoiceState('listening')
      },

      onInterim: (transcript) => {
        console.log('[VoiceOverlay] Interim:', transcript)
        setInterimTranscript(transcript)
      },

      onFinal: async (transcript) => {
        console.log('[VoiceOverlay] Final:', transcript)
        setInterimTranscript('')

        if (!transcript || transcript.trim().length === 0) {
          setVoiceState('idle')
          return
        }

        // Add user message
        useConversationStore.getState().addMessage({
          id: `user-${Date.now()}`,
          type: 'user',
          text: transcript,
          timestamp: Date.now(),
        })

        // Send to AI Gateway
        setVoiceState('processing')

        try {
          const sessionId = useConversationStore.getState().sessionId || `browser-${Date.now()}`
          const storeRoomId = useDeviceStore.getState().roomId

          const response = await fetch(`${import.meta.env.VITE_GATEWAY_URL}/conversation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              text: transcript,
              session_id: sessionId,
              room_id: storeRoomId,
            }),
          })

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`)
          }

          const data = await response.json()

          // Validate response (backend returns 'text' field)
          if (!data.text || typeof data.text !== 'string') {
            console.error('[VoiceOverlay] Invalid response from AI Gateway:', data)
            setVoiceState('idle')
            return
          }

          // Add assistant message
          useConversationStore.getState().addMessage({
            id: `assistant-${Date.now()}`,
            type: 'assistant',
            text: data.text,
            timestamp: Date.now(),
          })

          // Speak response via browser TTS
          speak(data.text)

          setVoiceState('idle')

        } catch (error) {
          console.error('[VoiceOverlay] Error:', error)
          setVoiceState('idle')
        }
      },

      onError: (error) => {
        console.error('[VoiceOverlay] STT error:', error)
        setVoiceState('idle')
        setInterimTranscript('')
      },

      onEnd: () => {
        console.log('[VoiceOverlay] Browser STT ended')
        // State already handled in onFinal or onError
      },
    })

    if (!success) {
      console.error('[VoiceOverlay] Failed to start browser STT')
      setVoiceState('idle')
    }
  }

  // Clear loading state when state changes from idle
  useEffect(() => {
    if (state !== 'idle') {
      setIsStarting(false)
    }
  }, [state])

  // Calculate panel width in pixels (same for both panels)
  const panelWidth = typeof window !== 'undefined' ? (window.innerWidth * 0.5) - 100 : 0

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 1 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-[100] flex flex-col bg-black/20 backdrop-blur-md"
        >
          {/* Row 1: Header with status and controls */}
          <div className="flex-shrink-0">
            <DefaultDisplayPanel
              action={{ type: 'default', data: {}, timestamp: Date.now() }}
              roomId={roomId}
              onClose={handleClose}
            />
          </div>

          {/* Row 2: Main Content - 3-column layout with absolute positioned panels */}
          <div className="flex-1 relative overflow-hidden">
            {/* Left Panel: Tool Slider - always visible, switches between default and tool-specific panels */}
            <motion.div
              initial={{ x: -panelWidth }}
              animate={{ x: 0 }}
              exit={{ x: -panelWidth }}
              transition={{
                duration: 0.3,
                ease: 'easeOut',
              }}
              className="absolute left-0 top-0 bottom-0 overflow-hidden my-4 pl-4 pr-2 z-10"
              style={{ width: 'calc(50% - 100px)' }}
            >
              <ToolPanelSlider roomId={roomId} />
            </motion.div>

            {/* Center Panel: Status indicator (fixed width, centered) */}
            <div className="absolute left-1/2 top-0 bottom-0 my-4 z-20" style={{ width: '200px', marginLeft: '-100px' }}>
              {/* Text centered in middle */}
              {state === 'idle' && !conversationMode && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center">
                    <p className="text-white/60 text-lg">
                      Say "Hey Jarvis" to start
                    </p>
                    <p className="text-white/40 text-sm mt-2">
                      or tap the microphone button
                    </p>
                  </div>
                </div>
              )}

              {/* StatusIndicator at bottom */}
              <div className="absolute bottom-0 left-0 right-0 flex items-end justify-center pb-6">
                <StatusIndicator
                  state={isStarting ? 'waiting' : state}
                  conversationMode={conversationMode}
                  onStartSession={handleStartSession}
                />
              </div>
            </div>

            {/* Right Panel: Chat messages - always visible, slides in from right */}
            <motion.div
              initial={{ x: panelWidth }}
              animate={{ x: 0 }}
              exit={{ x: panelWidth }}
              transition={{
                duration: 0.3,
                ease: 'easeOut',
              }}
              className="absolute right-0 top-0 bottom-0 overflow-hidden my-4 pr-4 pl-2 z-10"
              style={{ width: 'calc(50% - 100px)' }} // Half screen minus half of center panel
            >
              <div className="h-full overflow-y-auto scrollbar-hide">
                {/* Rounded wrapper with subtle background */}
                <div className="h-full bg-black/[0.25] backdrop-blur-md border-l border-white/20 shadow-xl p-6 overflow-y-auto scrollbar-hide flex flex-col rounded-l-3xl">
                  {/* Show interim transcript while listening */}
                  {interimTranscript && state === 'listening' && (
                    <div className="text-white/60 italic p-4 border-b border-white/10">
                      {interimTranscript}
                    </div>
                  )}
                  <ChatSection messages={messages} />
                </div>
              </div>
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
