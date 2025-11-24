import { useState, useEffect } from 'react'
import { Wifi, WifiOff } from 'lucide-react'
import { useHomeAssistant } from '../../hooks/useHomeAssistant'
import { formatTime, formatDate } from '../../utils/formatters'

export default function Header() {
  const { connected } = useHomeAssistant()
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <header className="flex items-center justify-between px-4 py-3 bg-surface border-b border-surface-light">
      {/* Date */}
      <div className="text-text-secondary text-sm">
        {formatDate(time)}
      </div>

      {/* Time */}
      <div className="text-kiosk-lg font-bold">
        {formatTime(time)}
      </div>

      {/* Connection status */}
      <div className="flex items-center gap-2">
        {connected ? (
          <Wifi className="w-5 h-5 text-success" />
        ) : (
          <WifiOff className="w-5 h-5 text-error" />
        )}
      </div>
    </header>
  )
}
