import { Lightbulb, LightbulbOff, X } from 'lucide-react'
import { motion } from 'framer-motion'
import { DisplayPanelProps, LightControlData } from '../types'
import { classNames } from '../../../../utils/formatters'

const ROOM_LABELS: Record<string, string> = {
  salon: 'Living Room',
  kuchnia: 'Kitchen',
  sypialnia: 'Bedroom',
  biurko: 'Desk',
  all: 'All Lights'
}

export default function LightControlPanel({ action, onClose }: DisplayPanelProps) {
  const data = action.data as LightControlData
  const { room, entities, action: lightAction } = data

  const roomLabel = ROOM_LABELS[room] || room
  const isOn = lightAction === 'on'

  return (
    <div className="p-4 bg-black/20 backdrop-blur-md border-b border-white/10">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {isOn ? (
            <Lightbulb className="w-6 h-6 text-yellow-400" />
          ) : (
            <LightbulbOff className="w-6 h-6 text-text-secondary" />
          )}
          <div>
            <h3 className="text-lg font-semibold">
              {roomLabel} {isOn ? 'On' : 'Off'}
            </h3>
            <p className="text-sm text-text-secondary">
              {entities.length} {entities.length === 1 ? 'light' : 'lights'} controlled
            </p>
          </div>
        </div>

        {onClose && (
          <button
            onClick={onClose}
            className="p-2 rounded-full bg-white/5 hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Entity indicators */}
      <div className="flex flex-wrap gap-2">
        {entities.map((entityId, idx) => (
          <motion.div
            key={entityId}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: idx * 0.05 }}
            className={classNames(
              "px-3 py-1 rounded-full text-xs border",
              isOn
                ? "bg-yellow-500/20 border-yellow-500/30 text-yellow-300"
                : "bg-white/5 border-white/10 text-text-secondary"
            )}
          >
            {entityId.split('.')[1].split('_').slice(0, 2).join(' ')}
          </motion.div>
        ))}
      </div>

      {/* Visual indicator */}
      <div className="mt-4 flex items-center justify-center">
        <motion.div
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{
            type: "spring",
            stiffness: 200,
            damping: 15
          }}
          className={classNames(
            "w-24 h-24 rounded-full flex items-center justify-center",
            isOn
              ? "bg-yellow-500/30 shadow-xl shadow-yellow-500/50"
              : "bg-white/5"
          )}
        >
          {isOn ? (
            <Lightbulb className="w-12 h-12 text-yellow-400" />
          ) : (
            <LightbulbOff className="w-12 h-12 text-text-secondary" />
          )}
        </motion.div>
      </div>
    </div>
  )
}
