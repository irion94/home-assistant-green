import { Thermometer, Flame, Snowflake, Power } from 'lucide-react'
import { useHomeAssistant } from '../../hooks/useHomeAssistant'
import { useEntity } from '../../hooks/useEntity'
import { Button } from '../common'
import { formatTemperature } from '../../utils/formatters'

interface ClimateCardProps {
  entityId: string
  name?: string
}

export default function ClimateCard({ entityId, name }: ClimateCardProps) {
  const { setTemperature, callService } = useHomeAssistant()
  const { state, isAvailable, attributes } = useEntity(entityId)

  const displayName = name || attributes.friendly_name || entityId
  const currentTemp = attributes.current_temperature ?? 0
  const targetTemp = attributes.temperature ?? 0
  const hvacAction = attributes.hvac_action ?? 'off'
  const hvacModes = attributes.hvac_modes ?? []

  const getHvacIcon = () => {
    switch (hvacAction) {
      case 'heating':
        return <Flame className="w-5 h-5 text-orange-500" />
      case 'cooling':
        return <Snowflake className="w-5 h-5 text-blue-400" />
      case 'idle':
        return <Thermometer className="w-5 h-5 text-text-secondary" />
      default:
        return <Power className="w-5 h-5 text-text-secondary" />
    }
  }

  const handleTempChange = async (delta: number) => {
    const newTemp = targetTemp + delta
    await setTemperature(entityId, newTemp)
  }

  const handleModeChange = async (mode: string) => {
    await callService('climate', 'set_hvac_mode', {
      entity_id: entityId,
      hvac_mode: mode,
    })
  }

  if (!isAvailable) {
    return (
      <div className="card opacity-50">
        <div className="flex items-center gap-3">
          <Thermometer className="w-6 h-6 text-text-secondary" />
          <span className="font-medium">{displayName}</span>
        </div>
        <p className="text-sm text-text-secondary mt-2">Unavailable</p>
      </div>
    )
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {getHvacIcon()}
          <div>
            <p className="font-medium">{displayName}</p>
            <p className="text-sm text-text-secondary capitalize">{hvacAction}</p>
          </div>
        </div>
      </div>

      {/* Temperature display */}
      <div className="flex items-center justify-between mb-6">
        {/* Current temperature */}
        <div className="text-center">
          <p className="text-sm text-text-secondary mb-1">Current</p>
          <p className="text-kiosk-xl font-bold">
            {formatTemperature(currentTemp)}
          </p>
        </div>

        {/* Target temperature with controls */}
        <div className="text-center">
          <p className="text-sm text-text-secondary mb-1">Target</p>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleTempChange(-0.5)}
              disabled={state === 'off'}
            >
              −
            </Button>
            <span className="text-kiosk-lg font-bold min-w-[80px]">
              {formatTemperature(targetTemp)}
            </span>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleTempChange(0.5)}
              disabled={state === 'off'}
            >
              +
            </Button>
          </div>
        </div>
      </div>

      {/* Mode buttons */}
      {hvacModes.length > 0 && (
        <div className="flex gap-2">
          {hvacModes.map((mode) => (
            <Button
              key={mode}
              variant={state === mode ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => handleModeChange(mode)}
              className="flex-1 capitalize"
            >
              {mode}
            </Button>
          ))}
        </div>
      )}
    </div>
  )
}
