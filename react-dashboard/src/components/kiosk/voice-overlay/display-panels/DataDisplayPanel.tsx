import { Clock, Home, Info } from 'lucide-react'
import { motion } from 'framer-motion'
import { DisplayPanelProps, DataDisplayAction, TimeData, HomeData, EntityData, DataDisplayMode } from '../types'

export default function DataDisplayPanel({ action }: DisplayPanelProps) {
  // Type guard to ensure this is a data_display action
  if (action.type !== 'data_display') {
    return null
  }

  const dataAction = action as DataDisplayAction
  const { mode, content } = dataAction.data

  // Icon and title based on mode
  const config: Record<DataDisplayMode, { icon: typeof Clock; title: string; color: string }> = {
    time: { icon: Clock, title: 'Time', color: 'text-blue-400' },
    home_data: { icon: Home, title: 'Home Status', color: 'text-green-400' },
    entity: { icon: Info, title: 'Entity Details', color: 'text-purple-400' },
  }

  const panelConfig = config[mode]
  const Icon = panelConfig.icon

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Icon className={`w-6 h-6 ${panelConfig.color}`} />
        <h2 className="text-xl font-semibold text-white">{panelConfig.title}</h2>
      </div>

      {/* Content based on mode */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {mode === 'time' && <TimeContent data={content as TimeData} />}
        {mode === 'home_data' && <HomeDataContent data={content as HomeData} />}
        {mode === 'entity' && <EntityContent data={content as EntityData} />}
      </motion.div>
    </div>
  )
}

// Time display
function TimeContent({ data }: { data: TimeData }) {
  return (
    <div className="space-y-6">
      {/* Large clock */}
      <div className="text-center">
        <div className="text-6xl font-bold text-white">{data.time}</div>
        <div className="text-xl text-white/60 mt-2">{data.date}</div>
        <div className="text-lg text-white/40 mt-1">{data.day}</div>
      </div>
      {/* Timezone */}
      <div className="text-center text-sm text-white/40">
        {data.timezone}
      </div>
    </div>
  )
}

// Home data display
function HomeDataContent({ data }: { data: HomeData }) {
  return (
    <div className="space-y-4">
      {/* Lights indicator */}
      <div className="flex items-center justify-between bg-white/5 rounded-lg p-4">
        <span className="text-white/80">Lights</span>
        <span className="text-xl font-semibold text-white">
          {data.lights_on}/{data.lights_total}
        </span>
      </div>

      {/* Sensors grid */}
      <div className="grid grid-cols-2 gap-3">
        {data.sensors.map((sensor, idx) => (
          <div key={idx} className="bg-white/5 rounded-lg p-3">
            <div className="text-sm text-white/60">{sensor.name}</div>
            <div className="text-lg font-semibold text-white mt-1">
              {sensor.value}
              {sensor.unit && <span className="text-sm ml-1">{sensor.unit}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// Entity details display
function EntityContent({ data }: { data: EntityData }) {
  return (
    <div className="space-y-4">
      {/* Entity name and state */}
      <div className="bg-white/5 rounded-lg p-4">
        <div className="text-sm text-white/60">Entity ID</div>
        <div className="text-white mt-1">{data.entity_id}</div>
        <div className="text-2xl font-semibold text-white mt-3">{data.state}</div>
      </div>

      {/* Attributes */}
      <div className="space-y-2">
        <div className="text-sm text-white/60 font-medium">Attributes</div>
        {Object.entries(data.attributes).slice(0, 8).map(([key, value]) => (
          <div key={key} className="flex justify-between bg-white/5 rounded p-2">
            <span className="text-white/80 text-sm">{key}</span>
            <span className="text-white text-sm font-mono truncate max-w-[200px]">
              {typeof value === 'object' ? JSON.stringify(value).slice(0, 40) : String(value).slice(0, 40)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
