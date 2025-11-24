import { Mic, Settings, Power, PowerOff, Wifi, WifiOff, Thermometer } from 'lucide-react'
import { useHomeAssistant } from '../../../hooks/useHomeAssistant'
import { useSensorEntity } from '../../../hooks/useEntity'
import { getAllLightIds, SENSORS } from '../../../config/entities'
import { Button } from '../../common'
import { formatTemperature } from '../../../utils/formatters'

interface MenuPanelProps {
  onNavigate?: (path: string) => void
}

export default function MenuPanel({ onNavigate }: MenuPanelProps) {
  const { connected, callService } = useHomeAssistant()
  const cpuTemp = useSensorEntity(SENSORS.cpuTemp)

  const lightIds = getAllLightIds()

  const handleAllLightsOn = async () => {
    await callService('light', 'turn_on', { entity_id: lightIds })
  }

  const handleAllLightsOff = async () => {
    await callService('light', 'turn_off', { entity_id: lightIds })
  }

  const cpuTempValue = cpuTemp.entity?.state
    ? formatTemperature(parseFloat(cpuTemp.entity.state))
    : '--'

  return (
    <div className="h-full flex flex-col bg-surface rounded-2xl p-6">
      {/* Header */}
      <h2 className="text-kiosk-xl font-bold mb-8">Menu</h2>

      {/* Navigation Links */}
      <div className="space-y-3 mb-8">
        <button
          onClick={() => onNavigate?.('/voice')}
          className="w-full flex items-center gap-4 p-4 bg-surface-light rounded-xl hover:bg-primary/20 transition-colors"
        >
          <Mic className="w-6 h-6 text-primary" />
          <span className="text-lg font-medium">Voice Assistant</span>
        </button>

        <button
          onClick={() => onNavigate?.('/settings')}
          className="w-full flex items-center gap-4 p-4 bg-surface-light rounded-xl hover:bg-primary/20 transition-colors"
        >
          <Settings className="w-6 h-6 text-text-secondary" />
          <span className="text-lg font-medium">Settings</span>
        </button>
      </div>

      {/* System Info */}
      <div className="mb-8">
        <h3 className="text-sm font-medium text-text-secondary mb-3 uppercase tracking-wider">
          System Status
        </h3>
        <div className="space-y-2">
          <div className="flex items-center justify-between p-3 bg-surface-light rounded-lg">
            <div className="flex items-center gap-3">
              {connected ? (
                <Wifi className="w-5 h-5 text-success" />
              ) : (
                <WifiOff className="w-5 h-5 text-error" />
              )}
              <span>Connection</span>
            </div>
            <span className={connected ? 'text-success' : 'text-error'}>
              {connected ? 'Online' : 'Offline'}
            </span>
          </div>

          <div className="flex items-center justify-between p-3 bg-surface-light rounded-lg">
            <div className="flex items-center gap-3">
              <Thermometer className="w-5 h-5 text-warning" />
              <span>CPU Temp</span>
            </div>
            <span>{cpuTempValue}</span>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mt-auto">
        <h3 className="text-sm font-medium text-text-secondary mb-3 uppercase tracking-wider">
          Quick Actions
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <Button
            variant="primary"
            className="flex items-center justify-center gap-2 py-4"
            onClick={handleAllLightsOn}
          >
            <Power className="w-5 h-5" />
            <span>All On</span>
          </Button>

          <Button
            variant="secondary"
            className="flex items-center justify-center gap-2 py-4"
            onClick={handleAllLightsOff}
          >
            <PowerOff className="w-5 h-5" />
            <span>All Off</span>
          </Button>
        </div>
      </div>
    </div>
  )
}
