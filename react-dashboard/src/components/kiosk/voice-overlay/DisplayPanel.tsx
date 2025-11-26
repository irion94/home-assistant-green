import { motion, AnimatePresence } from 'framer-motion'
import { DisplayAction } from './types'
import { getDisplayPanel } from './display-panels'

interface DisplayPanelProps {
  displayAction: DisplayAction | null
  roomId?: string
  onClose?: () => void
}

export default function DisplayPanel({ displayAction, roomId, onClose }: DisplayPanelProps) {
  const actionType = displayAction?.type ?? 'default'
  const PanelComponent = getDisplayPanel(actionType)

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={actionType}
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20 }}
        transition={{
          type: "spring",
          stiffness: 400,
          damping: 30,
          duration: 0.2
        }}
      >
        <PanelComponent
          action={displayAction ?? { type: 'default', data: {}, timestamp: Date.now() }}
          roomId={roomId}
          onClose={onClose}
        />
      </motion.div>
    </AnimatePresence>
  )
}
