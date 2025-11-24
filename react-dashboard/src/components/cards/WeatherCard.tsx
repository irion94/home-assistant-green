import {
  Sun,
  Cloud,
  CloudRain,
  CloudSnow,
  CloudLightning,
  CloudFog,
  Wind,
  Droplets,
} from 'lucide-react'
import { useEntity } from '../../hooks/useEntity'
import { formatTemperature } from '../../utils/formatters'
import type { WeatherForecast } from '../../types/entity'

interface WeatherCardProps {
  entityId: string
  showForecast?: boolean
}

const weatherIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  'clear-night': Sun,
  'cloudy': Cloud,
  'fog': CloudFog,
  'hail': CloudSnow,
  'lightning': CloudLightning,
  'lightning-rainy': CloudLightning,
  'partlycloudy': Cloud,
  'pouring': CloudRain,
  'rainy': CloudRain,
  'snowy': CloudSnow,
  'snowy-rainy': CloudSnow,
  'sunny': Sun,
  'windy': Wind,
  'windy-variant': Wind,
  'exceptional': Cloud,
}

export default function WeatherCard({
  entityId,
  showForecast = true,
}: WeatherCardProps) {
  const { entity, state, isAvailable, attributes } = useEntity(entityId)

  if (!isAvailable || !entity) {
    return (
      <div className="card opacity-50">
        <p className="text-text-secondary">Weather unavailable</p>
      </div>
    )
  }

  const Icon = weatherIcons[state] || Cloud
  const temperature = attributes.temperature ?? 0
  const humidity = attributes.humidity ?? 0
  const windSpeed = attributes.wind_speed ?? 0
  const forecast = (attributes.forecast ?? []) as WeatherForecast[]

  return (
    <div className="card">
      {/* Current weather */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <Icon className="w-12 h-12 text-primary" />
          <div>
            <p className="text-kiosk-2xl font-bold">
              {formatTemperature(temperature)}
            </p>
            <p className="text-sm text-text-secondary capitalize">{state.replace('-', ' ')}</p>
          </div>
        </div>

        {/* Additional info */}
        <div className="text-right">
          <div className="flex items-center gap-1 text-sm text-text-secondary">
            <Droplets className="w-4 h-4" />
            <span>{humidity}%</span>
          </div>
          <div className="flex items-center gap-1 text-sm text-text-secondary mt-1">
            <Wind className="w-4 h-4" />
            <span>{windSpeed} km/h</span>
          </div>
        </div>
      </div>

      {/* Forecast */}
      {showForecast && forecast.length > 0 && (
        <div className="border-t border-surface-light pt-4 mt-4">
          <div className="grid grid-cols-4 gap-2">
            {forecast.slice(0, 4).map((day, index) => {
              const ForecastIcon = weatherIcons[day.condition] || Cloud
              const date = new Date(day.datetime)
              const dayName = index === 0 ? 'Today' : date.toLocaleDateString('en', { weekday: 'short' })

              return (
                <div key={day.datetime} className="text-center">
                  <p className="text-xs text-text-secondary mb-1">{dayName}</p>
                  <ForecastIcon className="w-6 h-6 mx-auto text-text-secondary mb-1" />
                  <p className="text-sm font-medium">
                    {Math.round(day.temperature)}°
                  </p>
                  {day.templow !== undefined && (
                    <p className="text-xs text-text-secondary">
                      {Math.round(day.templow)}°
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
