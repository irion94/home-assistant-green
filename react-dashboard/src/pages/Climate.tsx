import { SensorCard, WeatherCard } from '../components/cards'
import { SENSORS } from '../config/entities'

export default function Climate() {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-kiosk-lg font-bold">Climate</h1>
        <p className="text-sm text-text-secondary">
          Weather and system monitoring
        </p>
      </div>

      {/* Weather */}
      <section>
        <h2 className="text-sm font-medium text-text-secondary mb-3 px-1">
          Weather
        </h2>
        <WeatherCard entityId={SENSORS.weather} showForecast={true} />
      </section>

      {/* System sensors */}
      <section>
        <h2 className="text-sm font-medium text-text-secondary mb-3 px-1">
          System
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <SensorCard
            entityId={SENSORS.cpuTemp}
            name="CPU Temperature"
            icon="temperature"
            size="lg"
          />
          <SensorCard
            entityId={SENSORS.voiceStatus}
            name="Voice Status"
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
            size="lg"
          />
          <SensorCard
            entityId={SENSORS.uploadSpeed}
            name="Upload"
            size="lg"
          />
        </div>
      </section>

      {/* Note: Add climate control when climate entities are available */}
    </div>
  )
}
