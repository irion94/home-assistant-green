import { motion } from 'framer-motion'
import { Info, Lightbulb, Thermometer, Power, Speaker, Cloud } from 'lucide-react'
import { DisplayPanelProps } from '../types'

export default function EntityDetailPanel({ action }: DisplayPanelProps) {
  const data = action.data as {
    domain: string
    entity_id?: string
    entities: Array<{
      entity_id: string
      state: string
      attributes?: Record<string, any>
    }>
    entity_count: number
  }
  const getDomainIcon = (domain: string) => {
    switch (domain) {
      case 'light':
        return <Lightbulb className="w-8 h-8 text-yellow-400" />
      case 'climate':
      case 'sensor':
        return <Thermometer className="w-8 h-8 text-red-400" />
      case 'switch':
        return <Power className="w-8 h-8 text-green-400" />
      case 'media_player':
        return <Speaker className="w-8 h-8 text-purple-400" />
      case 'weather':
        return <Cloud className="w-8 h-8 text-blue-300" />
      default:
        return <Info className="w-8 h-8 text-blue-400" />
    }
  }

  const getStateColor = (state: string) => {
    switch (state) {
      case 'on':
      case 'playing':
        return 'text-green-400'
      case 'off':
      case 'paused':
        return 'text-gray-500'
      case 'unavailable':
        return 'text-red-400'
      default:
        return 'text-gray-300'
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 space-y-4 h-full flex flex-col"
    >
      <div className="flex items-center gap-3 mb-2">
        {getDomainIcon(data.domain)}
        <div>
          <h3 className="text-xl font-semibold capitalize">{data.domain}</h3>
          <p className="text-sm text-gray-400">{data.entity_count} encji</p>
        </div>
      </div>

      {/* Single entity view */}
      {data.entity_id && data.entities.length === 1 && (
        <div className="bg-white/5 rounded-lg p-4 space-y-3">
          <div className="text-sm text-gray-400">Entity ID</div>
          <div className="font-mono text-sm">{data.entities[0].entity_id}</div>

          <div className="text-sm text-gray-400 mt-4">State</div>
          <div className={`text-3xl font-bold ${getStateColor(data.entities[0].state)}`}>
            {data.entities[0].state}
          </div>

          {data.entities[0].attributes && Object.keys(data.entities[0].attributes).length > 0 && (
            <>
              <div className="text-sm text-gray-400 mt-4">Atrybuty</div>
              <div className="text-xs font-mono bg-gray-800/50 p-3 rounded max-h-40 overflow-y-auto scrollbar-hide">
                {JSON.stringify(data.entities[0].attributes, null, 2)}
              </div>
            </>
          )}
        </div>
      )}

      {/* Multiple entities view */}
      {data.entities.length > 1 && (
        <div className="flex-1 overflow-y-auto space-y-2 scrollbar-hide">
          {data.entities.map((entity, idx) => {
            const friendlyName = entity.attributes?.friendly_name || entity.entity_id

            return (
              <motion.div
                key={entity.entity_id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="bg-white/5 rounded-lg p-3 flex items-center justify-between"
              >
                <div className="flex-1 min-w-0">
                  <div className="font-semibold truncate">{friendlyName}</div>
                  <div className="text-xs text-gray-500 font-mono truncate">{entity.entity_id}</div>
                </div>
                <div className={`text-sm font-semibold ml-3 ${getStateColor(entity.state)}`}>
                  {entity.state}
                </div>
              </motion.div>
            )
          })}
        </div>
      )}
    </motion.div>
  )
}
