import { useEffect, useRef } from 'react'
import { Mic, X, Loader2, Volume2, Wifi, WifiOff, MessageCircle, Radio } from 'lucide-react'
import { mqttService, VoiceState } from '../../services/mqttService'
import { classNames } from '../../utils/formatters'
import { useVoiceStore } from '../../stores/voiceStore'

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
  // Zustand store - single source of truth
  const {
    state,
    sessionId,
    messages,
    conversationMode,
    mqttConnected: connected,
    lastComparison,
    setVoiceState
  } = useVoiceStore()

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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

        {/* Mode indicator - click to start conversation mode */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              console.log('[VoiceOverlay] Button clicked, conversationMode:', conversationMode, 'connected:', connected)
              if (!conversationMode) {
                // Start conversation mode via MQTT
                console.log('[VoiceOverlay] Calling mqttService.startSession("conversation")')
                mqttService.startSession('conversation')
                console.log('[VoiceOverlay] startSession called')
              }
            }}
            disabled={conversationMode}
            className={classNames(
              "flex items-center gap-3 px-5 py-3 rounded-full transition-all duration-300",
              conversationMode
                ? "bg-orange-500 text-white shadow-xl shadow-orange-500/50 animate-pulse cursor-default ring-4 ring-orange-400/50"
                : "bg-surface-light/30 text-text-secondary hover:bg-surface-light/50 cursor-pointer border-2 border-transparent hover:border-orange-400/50"
            )}
          >
            <MessageCircle className={classNames("w-5 h-5", conversationMode && "animate-bounce")} />
            <span className="text-base font-semibold">
              {conversationMode ? "🔥 In conversation" : "Start conversation"}
            </span>
          </button>

          {/* Close button */}
          <button
            onClick={handleClose}
            className="p-4 rounded-full bg-surface-light/50 hover:bg-red-500/80 hover:text-white transition-colors"
          >
            <X className="w-7 h-7" />
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
