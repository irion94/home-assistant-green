import { SensorCard } from '../components/cards'
import { useSensors } from '../hooks/useEntities'
import { SENSORS } from '../config/entities'

export default function Sensors() {
  // Get all sensors from HA
  const allSensors = useSensors()

  // Featured sensors (from config)
  const featuredSensorIds = [
    SENSORS.cpuTemp,
    SENSORS.downloadSpeed,
    SENSORS.uploadSpeed,
    SENSORS.voiceStatus,
    SENSORS.voiceText,
  ]

  // Other sensors (not in featured list)
  const otherSensors = allSensors.filter(
    sensor => !featuredSensorIds.includes(sensor.entity_id as typeof featuredSensorIds[number])
  )

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-kiosk-lg font-bold">Sensors</h1>
        <p className="text-sm text-text-secondary">
          {allSensors.length} sensors available
        </p>
      </div>

      {/* System */}
      <section>
        <h2 className="text-sm font-medium text-text-secondary mb-3 px-1">
          System
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <SensorCard
            entityId={SENSORS.cpuTemp}
            name="CPU Temp"
            icon="temperature"
            size="lg"
          />
          <SensorCard
            entityId={SENSORS.voiceStatus}
            name="Voice Status"
            size="lg"
          />
          <SensorCard
            entityId={SENSORS.voiceText}
            name="Voice Text"
            size="lg"
          />
        </div>
      </section>

      {/* Network */}
      <section>
        <h2 className="text-sm font-medium text-text-secondary mb-3 px-1">
          Network
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <SensorCard
            entityId={SENSORS.downloadSpeed}
            name="Download"
          />
          <SensorCard
            entityId={SENSORS.uploadSpeed}
            name="Upload"
          />
        </div>
      </section>

      {/* Other sensors */}
      {otherSensors.length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-text-secondary mb-3 px-1">
            Other Sensors
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {otherSensors.slice(0, 12).map((sensor) => (
              <SensorCard
                key={sensor.entity_id}
                entityId={sensor.entity_id}
                size="sm"
              />
            ))}
          </div>
          {otherSensors.length > 12 && (
            <p className="text-sm text-text-secondary text-center mt-3">
              +{otherSensors.length - 12} more sensors
            </p>
          )}
        </section>
      )}
    </div>
  )
}
