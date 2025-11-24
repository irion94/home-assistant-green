import { Activity, Download, Upload, Thermometer } from 'lucide-react'
import { useSensorEntity } from '../../../hooks/useEntity'
import { SENSORS } from '../../../config/entities'
import { formatTemperature } from '../../../utils/formatters'

export default function SensorsPanel() {
  const cpuTemp = useSensorEntity(SENSORS.cpuTemp)
  const downloadSpeed = useSensorEntity(SENSORS.downloadSpeed)
  const uploadSpeed = useSensorEntity(SENSORS.uploadSpeed)

  const sensors = [
    {
      name: 'CPU Temperature',
      icon: Thermometer,
      value: cpuTemp.entity?.state ? formatTemperature(parseFloat(cpuTemp.entity.state)) : '--',
      color: 'text-orange-400',
      isAvailable: cpuTemp.isAvailable,
    },
    {
      name: 'Download Speed',
      icon: Download,
      value: downloadSpeed.entity?.state
        ? `${parseFloat(downloadSpeed.entity.state).toFixed(1)} ${downloadSpeed.unit || 'Mbps'}`
        : '--',
      color: 'text-green-400',
      isAvailable: downloadSpeed.isAvailable,
    },
    {
      name: 'Upload Speed',
      icon: Upload,
      value: uploadSpeed.entity?.state
        ? `${parseFloat(uploadSpeed.entity.state).toFixed(1)} ${uploadSpeed.unit || 'Mbps'}`
        : '--',
      color: 'text-blue-400',
      isAvailable: uploadSpeed.isAvailable,
    },
  ]

  return (
    <div className="h-full flex flex-col bg-surface rounded-2xl p-6">
      {/* Header */}
      <h2 className="text-kiosk-xl font-bold mb-6">Sensors</h2>

      {/* Sensor Grid */}
      <div className="flex-1 grid grid-rows-3 gap-4">
        {sensors.map((sensor) => (
          <div
            key={sensor.name}
            className={`
              flex items-center gap-4 p-4 bg-surface-light rounded-xl
              ${!sensor.isAvailable && 'opacity-50'}
            `}
          >
            <div className={`p-3 rounded-full bg-background ${sensor.color}`}>
              <sensor.icon className="w-8 h-8" />
            </div>
            <div className="flex-1">
              <p className="text-sm text-text-secondary">{sensor.name}</p>
              <p className="text-kiosk-lg font-bold mt-1">{sensor.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* System Status */}
      <div className="mt-4 pt-4 border-t border-surface-light">
        <div className="flex items-center gap-2 text-text-secondary">
          <Activity className="w-4 h-4" />
          <span className="text-sm">System Monitoring</span>
        </div>
      </div>
    </div>
  )
}
