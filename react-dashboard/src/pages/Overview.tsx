import { WeatherCard, LightCard, SensorCard } from '../components/cards'
import { useHomeAssistant } from '../hooks/useHomeAssistant'
import { Button } from '../components/common'
import { LIGHTS, SENSORS } from '../config/entities'
import { Lightbulb, LightbulbOff } from 'lucide-react'

export default function Overview() {
  const { callService, states } = useHomeAssistant()

  // Check if any lights are on
  const lightIds = Object.values(LIGHTS).map(l => l.entity_id)
  const lightsOn = lightIds.filter(id => {
    const state = states.get(id)
    return state?.state === 'on'
  })
  const anyLightsOn = lightsOn.length > 0

  const handleAllLights = async (turnOn: boolean) => {
    const service = turnOn ? 'turn_on' : 'turn_off'
    await callService('light', service, {
      entity_id: lightIds,
    })
  }

  return (
    <div className="space-y-4">
      {/* Weather section */}
      <section>
        <WeatherCard entityId={SENSORS.weather} />
      </section>

      {/* Quick actions */}
      <section>
        <h2 className="text-sm font-medium text-text-secondary mb-3 px-1">
          Quick Actions
        </h2>
        <div className="flex gap-3">
          <Button
            variant={anyLightsOn ? 'primary' : 'secondary'}
            onClick={() => handleAllLights(!anyLightsOn)}
            className="flex-1"
          >
            {anyLightsOn ? (
              <>
                <LightbulbOff className="w-5 h-5 mr-2" />
                All Lights Off
              </>
            ) : (
              <>
                <Lightbulb className="w-5 h-5 mr-2" />
                All Lights On
              </>
            )}
          </Button>
        </div>
      </section>

      {/* Main lights */}
      <section>
        <h2 className="text-sm font-medium text-text-secondary mb-3 px-1">
          Lights
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <LightCard
            entityId={LIGHTS.salon.entity_id}
            name={LIGHTS.salon.name}
          />
          <LightCard
            entityId={LIGHTS.sypialnia.entity_id}
            name={LIGHTS.sypialnia.name}
          />
        </div>
      </section>

      {/* Sensors grid */}
      <section>
        <h2 className="text-sm font-medium text-text-secondary mb-3 px-1">
          Sensors
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SensorCard
            entityId={SENSORS.cpuTemp}
            name="CPU Temp"
            icon="temperature"
          />
          <SensorCard
            entityId={SENSORS.downloadSpeed}
            name="Download"
            icon="default"
          />
          <SensorCard
            entityId={SENSORS.uploadSpeed}
            name="Upload"
            icon="default"
          />
          <SensorCard
            entityId={SENSORS.voiceStatus}
            name="Voice Status"
            icon="default"
          />
        </div>
      </section>
    </div>
  )
}
