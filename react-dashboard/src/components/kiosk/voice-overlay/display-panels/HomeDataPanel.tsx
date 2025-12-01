import { motion } from 'framer-motion'
import { Home, Lightbulb, Thermometer, Droplets, CloudRain } from 'lucide-react'
import { DisplayPanelProps } from '../types'

export default function HomeDataPanel({ action }: DisplayPanelProps) {
  const data = action.data as {
    sensor_type?: string
    sensors?: Record<string, any>
    state?: string
    attributes?: Record<string, any>
    summary: string
  }
  // Extract sensor data for display
  const renderSensorIcon = (type: string) => {
    switch (type) {
      case 'temperature':
      case 'temperature_outside':
        return <Thermometer className="w-5 h-5 text-red-400" />
      case 'humidity':
        return <Droplets className="w-5 h-5 text-blue-400" />
      case 'weather':
        return <CloudRain className="w-5 h-5 text-blue-300" />
      default:
        return <Home className="w-5 h-5 text-gray-400" />
    }
  }

  // Count lights if available
  const lightsCount = data.sensors ? Object.keys(data.sensors).filter(k => k.includes('light')).length : 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 space-y-4 h-full"
    >
      <div className="flex items-center gap-3 mb-4">
        <Home className="w-8 h-8 text-blue-400" />
        <h3 className="text-xl font-semibold">Status Domu</h3>
      </div>

      {/* Main summary */}
      <div className="bg-white/5 rounded-lg p-4">
        <div className="text-sm text-gray-300 whitespace-pre-line">{data.summary}</div>
      </div>

      {/* Sensor breakdown */}
      {data.sensors && Object.keys(data.sensors).length > 0 && (
        <div className="space-y-3 mt-4">
          <div className="text-sm text-gray-400 font-semibold">Status:</div>
          {Object.entries(data.sensors).map(([type, sensorData]: [string, any], idx) => (
            <motion.div
              key={type}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="flex items-center gap-3 bg-white/5 rounded px-3 py-2"
            >
              {type === 'lights' ? (
                <Lightbulb className="w-5 h-5 text-yellow-400" />
              ) : (
                renderSensorIcon(type)
              )}
              <div className="flex-1">
                <div className="text-xs text-gray-400 capitalize">
                  {type === 'lights' ? 'Światła' : type.replace('_', ' ')}
                </div>
                <div className="font-semibold">
                  {type === 'lights' ? (
                    `${sensorData.on}/${sensorData.total} włączone`
                  ) : (
                    `${sensorData.state} ${sensorData.attributes?.unit_of_measurement || ''}`
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Single sensor state */}
      {data.state && !data.sensors && (
        <div className="space-y-3 mt-4">
          <div className="flex items-center gap-3 bg-white/5 rounded-lg p-4">
            {renderSensorIcon(data.sensor_type || '')}
            <div className="flex-1">
              <div className="text-xs text-gray-400 capitalize">
                {data.sensor_type?.replace('_', ' ') || 'Sensor'}
              </div>
              <div className="text-2xl font-bold">
                {data.state} {data.attributes?.unit_of_measurement || ''}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Lights indicator if available */}
      {lightsCount > 0 && (
        <div className="flex items-center gap-3 mt-4 text-sm text-gray-400">
          <Lightbulb className="w-4 h-4 text-yellow-400" />
          <span>{lightsCount} światło/a aktywne</span>
        </div>
      )}
    </motion.div>
  )
}
