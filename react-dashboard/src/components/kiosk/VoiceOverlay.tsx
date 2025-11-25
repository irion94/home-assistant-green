import { useState, useEffect, useRef, useCallback } from 'react'
import { Mic, X, Loader2, Volume2, Wifi, WifiOff, MessageCircle, Radio } from 'lucide-react'
import { mqttService, VoiceState, VoiceMessage, STTComparison } from '../../services/mqttService'
import { classNames } from '../../utils/formatters'

interface ConversationMessage {
  id: string
  type: 'user' | 'assistant'
  text: string
  timestamp: number
  sttEngine?: string
}

interface VoiceOverlayProps {
  isOpen: boolean
  onClose: () => void
  roomId?: string
  /** If true, start a session immediately when overlay opens (for button click) */
  startOnOpen?: boolean
  /** Initial state to display when opened via wake-word detection */
  initialState?: VoiceState
}

// Map VoiceState to display colors
const stateColors: Record<VoiceState, string> = {
  idle: 'bg-surface-light',
  wake_detected: 'bg-info',
  listening: 'bg-error shadow-lg shadow-error/50',
  transcribing: 'bg-warning',
  processing: 'bg-warning',
  speaking: 'bg-success animate-pulse',
  waiting: 'bg-primary',
}

// Map VoiceState to display text
const stateLabels: Record<VoiceState, string> = {
  idle: 'Ready',
  wake_detected: 'Wake word detected!',
  listening: 'Listening...',
  transcribing: 'Transcribing...',
  processing: 'Processing...',
  speaking: 'Speaking...',
  waiting: 'Waiting for response...',
}

export default function VoiceOverlay({ isOpen, onClose, roomId = 'default', startOnOpen = false, initialState = 'idle' }: VoiceOverlayProps) {
  const [state, setState] = useState<VoiceState>(initialState)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ConversationMessage[]>([])
  const [connected, setConnected] = useState(false)
  const [lastComparison, setLastComparison] = useState<STTComparison | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Conversation mode toggle state (persisted to localStorage, default to single-command)
  const [conversationMode, setConversationMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('conversationMode')
    // Default to false (single-command mode) if not set
    return saved === 'true'
  })

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Persist conversation mode to localStorage (mode is AI-controlled, not user-toggled)
  useEffect(() => {
    localStorage.setItem('conversationMode', conversationMode.toString())
    console.log(`[VoiceOverlay] Mode indicator: ${conversationMode ? 'conversation' : 'command'}`)
  }, [conversationMode])

  // Set room ID when it changes
  useEffect(() => {
    mqttService.setRoomId(roomId)
  }, [roomId])

  // Sync state when initialState prop changes (for wake-word triggered opening)
  useEffect(() => {
    if (isOpen && initialState !== 'idle') {
      setState(initialState)
    }
  }, [isOpen, initialState])

  // Handle transcript message
  const handleTranscript = useCallback((message: VoiceMessage) => {
    console.log('[VoiceOverlay] Transcript received:', message)
    setMessages(prev => [...prev, {
      id: `user-${message.timestamp}`,
      type: 'user',
      text: message.text,
      timestamp: message.timestamp
    }])
  }, [])

  // Handle response message
  const handleResponse = useCallback((message: VoiceMessage) => {
    setMessages(prev => [...prev, {
      id: `assistant-${message.timestamp}`,
      type: 'assistant',
      text: message.text,
      timestamp: message.timestamp
    }])
  }, [])

  // Handle state change
  const handleStateChange = useCallback((newState: VoiceState, _sessionId: string | null) => {
    setState(newState)

    // Auto-close only in single-command mode when returning to idle
    if (newState === 'idle' && messages.length > 0 && !conversationMode) {
      // Keep overlay open for 3 seconds to show final state, then close
      const timeoutId = setTimeout(() => {
        onClose()
      }, 3000)

      // Store timeout ID for potential cleanup
      return () => clearTimeout(timeoutId)
    }
  }, [messages.length, conversationMode, onClose])

  // Handle STT comparison
  const handleSTTComparison = useCallback((comparison: STTComparison) => {
    setLastComparison(comparison)
  }, [])

  // Handle conversation mode change from MQTT (sync across devices)
  const handleConversationModeChange = useCallback((enabled: boolean) => {
    setConversationMode(enabled)
    localStorage.setItem('conversationMode', enabled.toString())
  }, [])

  // Handle active session change
  const handleActiveSessionChange = useCallback((newSessionId: string | null) => {
    setSessionId(newSessionId)
    if (newSessionId) {
      console.log(`[VoiceOverlay] Active session: ${newSessionId}`)
    }
  }, [])

  // Handle session end
  const handleSessionEnd = useCallback((endedSessionId: string) => {
    console.log(`[VoiceOverlay] Session ended: ${endedSessionId}`)
    setSessionId(null)
    setState('idle')
    // Always close overlay when session ends (both modes)
    // Single mode: command completed, Conversation mode: user said "koniec"
    setTimeout(() => onClose(), 1500)
  }, [onClose])

  // Connect to MQTT when overlay opens
  useEffect(() => {
    if (isOpen) {
      // Reset state when opening (but preserve message history)
      if (startOnOpen) {
        // Don't clear messages - preserve conversation history
        setLastComparison(null)
        setState('idle')
      }

      // Set up MQTT callbacks
      mqttService.setCallbacks({
        onStateChange: handleStateChange,
        onTranscript: handleTranscript,
        onResponse: handleResponse,
        onSTTComparison: handleSTTComparison,
        onConnectionChange: setConnected,
        onConversationModeChange: handleConversationModeChange,
        onActiveSessionChange: handleActiveSessionChange,
        onSessionEnd: handleSessionEnd,
      })

      // Check if already connected, if not connect
      const mqttHost = import.meta.env.VITE_MQTT_URL || `ws://${window.location.hostname}:9001`
      if (!mqttService.isConnected()) {
        mqttService.connect(mqttHost)
      }

      // Get current session if any
      setSessionId(mqttService.getCurrentSessionId())

      // If startOnOpen is true, start a session (wait for connection if needed)
      if (startOnOpen) {
        const tryStartSession = () => {
          if (mqttService.isConnected()) {
            mqttService.startSession('single')
            console.log(`[VoiceOverlay] Starting command session via MQTT (AI will decide mode)`)
          } else {
            // Not connected yet, retry after short delay
            console.log(`[VoiceOverlay] Waiting for MQTT connection...`)
            setTimeout(tryStartSession, 100)
          }
        }
        // Small delay to ensure callbacks are registered before messages arrive
        setTimeout(tryStartSession, 50)
      }
    }

    return () => {
      // Cleanup on unmount (connection remains active, managed by KioskHome)
    }
  }, [
    isOpen,
    startOnOpen,
    handleStateChange,
    handleTranscript,
    handleResponse,
    handleSTTComparison,
    handleConversationModeChange,
    handleActiveSessionChange,
    handleSessionEnd,
  ])

  // Handle manual close
  const handleClose = () => {
    mqttService.stopSession()
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[100] flex flex-col bg-black/90 backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-center justify-between p-4">
        {/* Connection status and room info */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-surface-light/50 text-sm">
            {connected ? (
              <>
                <Wifi className="w-4 h-4 text-success" />
                <span className="text-success">Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-error" />
                <span className="text-error">Connecting...</span>
              </>
            )}
          </div>

          {/* Room indicator */}
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-surface-light/30 text-sm text-text-secondary">
            <Radio className="w-4 h-4" />
            <span>{roomId}</span>
          </div>

          {/* Session ID (if active) */}
          {sessionId && (
            <div className="px-3 py-1 rounded-full bg-primary/20 text-sm text-primary">
              Session: {sessionId.slice(-8)}
            </div>
          )}
        </div>

        {/* Mode indicator - read-only, AI decides mode */}
        <div className="flex items-center gap-3">
          <div
            className={classNames(
              "flex items-center gap-2 px-4 py-2 rounded-full transition-colors",
              conversationMode
                ? "bg-primary/20 text-primary"
                : "bg-surface-light/30 text-text-secondary"
            )}
          >
            <MessageCircle className="w-4 h-4" />
            <span className="text-sm font-medium">
              {conversationMode ? "In conversation" : "Command mode"}
            </span>
          </div>

          {/* Close button */}
          <button
            onClick={handleClose}
            className="p-3 rounded-full bg-surface-light/50 hover:bg-surface-light"
          >
            <X className="w-6 h-6" />
          </button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-2">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-text-secondary">
            <Mic className="w-16 h-16 mb-4 opacity-50" />
            <p className="text-lg">Say "Hey Jarvis" to start</p>
            <p className="text-sm mt-2">or wait for wake-word detection</p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={classNames(
                  'max-w-[85%] p-4 rounded-2xl',
                  message.type === 'user'
                    ? 'ml-auto bg-primary/20 rounded-br-sm'
                    : 'mr-auto bg-surface rounded-bl-sm'
                )}
              >
                <p className="text-sm text-text-secondary mb-1">
                  {message.type === 'user' ? 'You' : 'Assistant'}
                </p>
                <p className="text-lg">{message.text}</p>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Status indicator */}
      <div className="p-6">
        <div className="flex flex-col items-center gap-4">
          {/* Pulsing indicator */}
          <div className="relative">
            {state === 'listening' && (
              <>
                <div className="absolute inset-0 rounded-full bg-error/30 animate-ping" style={{ animationDuration: '1.5s' }} />
                <div className="absolute -inset-4 rounded-full bg-error/20 animate-ping" style={{ animationDuration: '2s' }} />
              </>
            )}

            {state === 'wake_detected' && (
              <>
                <div className="absolute inset-0 rounded-full bg-info/30 animate-ping" style={{ animationDuration: '0.5s' }} />
              </>
            )}

            <div
              className={classNames(
                'relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300',
                stateColors[state]
              )}
            >
              {(state === 'processing' || state === 'transcribing') ? (
                <Loader2 className="w-8 h-8 text-white animate-spin" />
              ) : state === 'speaking' ? (
                <Volume2 className="w-8 h-8 text-white" />
              ) : (
                <Mic className="w-8 h-8 text-white" />
              )}
            </div>
          </div>

          {/* Status text */}
          <div className="text-center">
            <p className={classNames(
              'text-lg font-medium',
              state === 'listening' && 'text-error animate-pulse',
              state === 'wake_detected' && 'text-info',
              (state === 'processing' || state === 'transcribing') && 'text-warning',
              state === 'speaking' && 'text-success',
              state === 'waiting' && 'text-primary',
              state === 'idle' && 'text-text-secondary'
            )}>
              {stateLabels[state]}
            </p>
            {state === 'idle' && conversationMode && (
              <p className="text-sm text-text-secondary mt-1">
                Say 'koniec' to end conversation
              </p>
            )}
            {state === 'idle' && !conversationMode && messages.length > 0 && (
              <p className="text-sm text-text-secondary mt-1">
                Done - closing shortly...
              </p>
            )}
          </div>

          {/* STT Comparison (debug info) */}
          {lastComparison && (
            <div className="w-full max-w-md p-3 bg-surface/50 rounded-lg text-xs">
              <div className="flex justify-between mb-1">
                <span className={lastComparison.selected === 'vosk' ? 'text-success font-bold' : 'text-text-secondary'}>
                  Vosk: {lastComparison.vosk.duration}s
                </span>
                <span className={lastComparison.selected === 'whisper' ? 'text-success font-bold' : 'text-text-secondary'}>
                  Whisper: {lastComparison.whisper.duration}s
                </span>
              </div>
              <p className="text-text-secondary text-center">
                Selected: {lastComparison.selected} ({lastComparison.reason})
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
