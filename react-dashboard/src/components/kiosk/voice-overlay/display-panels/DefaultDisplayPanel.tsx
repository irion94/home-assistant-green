import { Wifi, WifiOff, Radio, MessageCircle, X } from 'lucide-react'
import { useConversationStore } from '../../../../stores/conversationStore'
import { useDeviceStore } from '../../../../stores/deviceStore'
import { mqttService } from '../../../../services/mqttService'
import { classNames } from '../../../../utils/formatters'
import { DisplayPanelProps } from '../types'

export default function DefaultDisplayPanel({ roomId, onClose }: DisplayPanelProps) {
  const { sessionId, conversationMode } = useConversationStore()
  const { mqttConnected } = useDeviceStore()

  return (
    <div className="flex items-center justify-between p-4 bg-black/20 backdrop-blur-md border-b border-white/10">
      {/* Left: Status badges */}
      <div className="flex items-center gap-3">
        {/* Connection status */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 text-sm border border-white/10">
          {mqttConnected ? (
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
        {roomId && (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 text-sm border border-white/10">
            <Radio className="w-4 h-4 text-text-secondary" />
            <span className="text-text-secondary">{roomId}</span>
          </div>
        )}

        {/* Session ID */}
        {sessionId && (
          <div className="px-3 py-1 rounded-full bg-primary/20 text-sm text-primary border border-primary/30">
            {sessionId.slice(-8)}
          </div>
        )}
      </div>

      {/* Right: Action buttons */}
      <div className="flex items-center gap-3">
        {/* Conversation mode toggle */}
        <button
          onClick={() => {
            if (!conversationMode) {
              console.log('[DefaultDisplayPanel] Starting conversation mode')
              mqttService.startSession('conversation')
            }
          }}
          disabled={conversationMode}
          className={classNames(
            "flex items-center gap-3 px-5 py-3 rounded-full transition-all duration-300",
            conversationMode
              ? "bg-orange-500 text-white shadow-xl shadow-orange-500/50 animate-pulse cursor-default ring-4 ring-orange-400/50"
              : "bg-white/5 hover:bg-white/10 cursor-pointer border-2 border-transparent hover:border-orange-400/50"
          )}
        >
          <MessageCircle className={classNames("w-5 h-5", conversationMode && "animate-bounce")} />
          <span className="text-base font-semibold">
            {conversationMode ? "In conversation" : "Start conversation"}
          </span>
        </button>

        {/* Close button */}
        {onClose && (
          <button
            onClick={onClose}
            className="p-4 rounded-full bg-white/5 hover:bg-red-500/80 hover:text-white transition-colors"
          >
            <X className="w-7 h-7" />
          </button>
        )}
      </div>
    </div>
  )
}
