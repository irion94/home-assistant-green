import { motion } from 'framer-motion'
import { Clock } from 'lucide-react'
import { DisplayPanelProps } from '../types'

export default function TimeDisplayPanel({ action }: DisplayPanelProps) {
  const data = action.data as {
    time: string
    date?: string
    day?: string
    timezone?: string
  }
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center p-8 space-y-4 h-full"
    >
      <Clock className="w-16 h-16 text-blue-400" />
      <div className="text-6xl font-bold">{data.time}</div>
      {data.day && (
        <div className="text-xl text-gray-300">{data.day}</div>
      )}
      {data.date && (
        <div className="text-sm text-gray-400">{data.date}</div>
      )}
      {data.timezone && (
        <div className="text-xs text-gray-500">{data.timezone}</div>
      )}
    </motion.div>
  )
}
