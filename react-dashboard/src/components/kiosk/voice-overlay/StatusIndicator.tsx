import { motion } from 'framer-motion'
import { Mic, Loader2, Volume2 } from 'lucide-react'
import { VoiceState } from '../../../services/mqttService'
import { classNames } from '../../../utils/formatters'

interface StatusIndicatorProps {
  state: VoiceState
  conversationMode: boolean
  onStartSession?: () => void
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

// Map states to actual color values for inline styles
const stateColorValues: Record<VoiceState, string> = {
  idle: '#3b82f6', // blue-500
  wake_detected: '#06b6d4', // cyan-500
  listening: '#ef4444', // red-500
  transcribing: '#f59e0b', // amber-500
  processing: '#f59e0b', // amber-500
  speaking: '#22c55e', // green-500
  waiting: '#3b82f6', // blue-500
}

export default function StatusIndicator({ state, conversationMode, onStartSession }: StatusIndicatorProps) {
  const isIdle = state === 'idle'
  const canClick = isIdle && onStartSession

  const handleClick = () => {
    if (canClick) {
      onStartSession()
    }
  }

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
        <motion.button
          layoutId="voice-button"
          onClick={handleClick}
          disabled={!canClick}
          style={{ backgroundColor: stateColorValues[state] }}
          className={classNames(
            'relative w-20 h-20 rounded-full flex items-center justify-center border-0 outline-none disabled:opacity-100',
            state === 'idle' && 'shadow-lg shadow-primary/30',
            state === 'listening' && 'shadow-lg shadow-error/50',
            state === 'speaking' && 'animate-pulse',
            canClick && 'cursor-pointer active:scale-95',
            !canClick && 'cursor-default'
          )}
          whileHover={canClick ? { scale: 1.1 } : {}}
          whileTap={canClick ? { scale: 0.95 } : {}}
          transition={{
            duration: 0.3,
            ease: 'easeOut',
          }}
        >
          {(state === 'processing' || state === 'transcribing') ? (
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          ) : state === 'speaking' ? (
            <Volume2 className="w-8 h-8 text-white" />
          ) : (
            <Mic className="w-8 h-8 text-white" />
          )}
        </motion.button>
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
