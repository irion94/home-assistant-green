import { LightCard } from '../components/cards'
import { Button } from '../components/common'
import { useHomeAssistant } from '../hooks/useHomeAssistant'
import { LIGHTS } from '../config/entities'
import { Lightbulb, LightbulbOff } from 'lucide-react'

export default function Lights() {
  const { callService, states } = useHomeAssistant()

  const lightConfigs = Object.values(LIGHTS)
  const lightIds = lightConfigs.map(l => l.entity_id)

  // Count lights that are on
  const lightsOn = lightIds.filter(id => {
    const state = states.get(id)
    return state?.state === 'on'
  })

  const handleAllLights = async (turnOn: boolean) => {
    const service = turnOn ? 'turn_on' : 'turn_off'
    await callService('light', service, {
      entity_id: lightIds,
    })
  }

  const handleBrightnessPreset = async (brightness: number) => {
    await callService('light', 'turn_on', {
      entity_id: lightIds,
      brightness: Math.round((brightness / 100) * 255),
    })
  }

  return (
    <div className="space-y-4">
      {/* Header with all lights toggle */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-kiosk-lg font-bold">Lights</h1>
          <p className="text-sm text-text-secondary">
            {lightsOn.length} of {lightIds.length} on
          </p>
        </div>
        <Button
          variant={lightsOn.length > 0 ? 'primary' : 'secondary'}
          onClick={() => handleAllLights(lightsOn.length === 0)}
        >
          {lightsOn.length > 0 ? (
            <>
              <LightbulbOff className="w-5 h-5 mr-2" />
              All Off
            </>
          ) : (
            <>
              <Lightbulb className="w-5 h-5 mr-2" />
              All On
            </>
          )}
        </Button>
      </div>

      {/* Brightness presets */}
      <div className="flex gap-2">
        {[25, 50, 75, 100].map((level) => (
          <Button
            key={level}
            variant="secondary"
            size="sm"
            onClick={() => handleBrightnessPreset(level)}
            className="flex-1"
          >
            {level}%
          </Button>
        ))}
      </div>

      {/* Light cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {lightConfigs.map((light) => (
          <LightCard
            key={light.entity_id}
            entityId={light.entity_id}
            name={light.name}
            showBrightness={true}
          />
        ))}
      </div>
    </div>
  )
}
