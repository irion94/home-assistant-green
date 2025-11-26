import { motion } from 'framer-motion'
import { Mic, Loader2, Volume2 } from 'lucide-react'
import { VoiceState } from '../../../services/mqttService'
import { classNames } from '../../../utils/formatters'

interface StatusIndicatorProps {
  state: VoiceState
  conversationMode: boolean
}

const stateColors: Record<VoiceState, string> = {
  idle: 'bg-primary shadow-lg shadow-primary/30',
  wake_detected: 'bg-info',
  listening: 'bg-error shadow-lg shadow-error/50',
  transcribing: 'bg-warning',
  processing: 'bg-warning',
  speaking: 'bg-success animate-pulse',
  waiting: 'bg-primary',
}

const stateLabels: Record<VoiceState, string> = {
  idle: 'Ready',
  wake_detected: 'Wake word detected!',
  listening: 'Listening...',
  transcribing: 'Transcribing...',
  processing: 'Processing...',
  speaking: 'Speaking...',
  waiting: 'Waiting for response...',
}

export default function StatusIndicator({ state, conversationMode }: StatusIndicatorProps) {
  return (
    <div className="flex flex-col items-center gap-4">
      {/* Pulsing rings for listening state */}
      <div className="relative">
        {state === 'listening' && (
          <>
            <div className="absolute inset-0 rounded-full bg-error/30 animate-ping" style={{ animationDuration: '1.5s' }} />
            <div className="absolute -inset-4 rounded-full bg-error/20 animate-ping" style={{ animationDuration: '2s' }} />
          </>
        )}

        {state === 'wake_detected' && (
          <div className="absolute inset-0 rounded-full bg-info/30 animate-ping" style={{ animationDuration: '0.5s' }} />
        )}

        {/* Shared element with FAB button - morphs from bottom-right to center */}
        <motion.div
          layoutId="voice-button"
          className={classNames(
            'relative w-20 h-20 rounded-full flex items-center justify-center transition-colors duration-300',
            stateColors[state]
          )}
          transition={{
            type: "spring",
            stiffness: 300,
            damping: 30
          }}
        >
          {(state === 'processing' || state === 'transcribing') ? (
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          ) : state === 'speaking' ? (
            <Volume2 className="w-8 h-8 text-white" />
          ) : (
            <Mic className="w-8 h-8 text-white" />
          )}
        </motion.div>
      </div>

      {/* Status label */}
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
    </div>
  )
}
