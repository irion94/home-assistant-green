/**
 * DebugLogPanel - Terminal-style scrolling debug log for VoiceOverlay.
 *
 * Shows real-time debug information:
 * - STATE: Voice state transitions (idle → listening → processing)
 * - MQTT: Raw MQTT messages (topics and payloads)
 * - TIMING: Latency metrics (STT, LLM, TTS durations)
 * - ERROR: Error messages and connection failures
 */

import { useEffect, useRef } from 'react'
import { useDebugLogs, useVoiceStore, DebugLogType } from '../../stores/voiceStore'

const formatTime = (date: Date): string => {
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const seconds = date.getSeconds().toString().padStart(2, '0')
  const ms = date.getMilliseconds().toString().padStart(3, '0')
  return `${hours}:${minutes}:${seconds}.${ms}`
}

const getLogTypeColor = (type: DebugLogType): string => {
  switch (type) {
    case 'STATE':
      return 'text-blue-400'
    case 'MQTT':
      return 'text-green-400'
    case 'TIMING':
      return 'text-yellow-400'
    case 'ERROR':
      return 'text-red-400'
    default:
      return 'text-gray-300'
  }
}

export function DebugLogPanel() {
  const debugLogs = useDebugLogs()
  const clearDebugLogs = useVoiceStore((s) => s.clearDebugLogs)
  const logEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new logs
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [debugLogs])

  return (
    <div className="flex-1 flex flex-col bg-black/30 h-full">
      <div className="flex justify-between items-center mb-2 flex-shrink-0">
        <span className="text-xs text-gray-400 font-medium">
          Debug Log ({debugLogs.length})
        </span>
        <button
          onClick={clearDebugLogs}
          className="text-xs text-gray-500 hover:text-red-400 transition-colors px-2 py-0.5 rounded hover:bg-white/5"
        >
          Clear
        </button>
      </div>
      <div className="flex-1 overflow-y-auto bg-black/60 rounded-lg font-mono text-xs p-2 scrollbar-hide">
        {debugLogs.length === 0 ? (
          <div className="text-gray-500 italic">No logs yet...</div>
        ) : (
          debugLogs.map((log) => (
            <div key={log.id} className="leading-relaxed">
              <span className="text-gray-500">{formatTime(log.timestamp)}</span>
              {' '}
              <span className={`font-bold ${getLogTypeColor(log.type)}`}>[{log.type}]</span>
              {' '}
              <span className="text-gray-200">{log.message}</span>
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  )
}
