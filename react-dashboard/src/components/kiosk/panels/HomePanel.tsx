import { useState, useEffect } from 'react'
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
import { useEntity } from '../../../hooks/useEntity'
import { SENSORS } from '../../../config/entities'
import { formatTime, formatDate, formatTemperature } from '../../../utils/formatters'

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

export default function HomePanel() {
  const [currentTime, setCurrentTime] = useState(new Date())
  const { entity, state, isAvailable, attributes } = useEntity(SENSORS.weather)

  // Update time every second
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const Icon = weatherIcons[state] || Cloud
  const temperature = attributes?.temperature ?? 0
  const humidity = attributes?.humidity ?? 0
  const windSpeed = attributes?.wind_speed ?? 0

  return (
    <div className="h-full flex flex-col">
      {/* Time Section - Top Half */}
      <div className="flex-1 flex flex-col items-center justify-between bg-surface rounded-2xl mb-2 p-2">
        <div className="flex-1" />
        <time className="text-[18vw] font-bold tracking-tight leading-none">
          {formatTime(currentTime)}
        </time>
        <div className="flex-1 flex items-end pb-2">
          <p className="text-kiosk-lg text-text-secondary">
            {formatDate(currentTime)}
          </p>
        </div>
      </div>

      {/* Weather Section - Bottom Half */}
      <div className="flex-1 flex flex-col bg-surface rounded-2xl p-4">
        {isAvailable && entity ? (
          <>
            {/* Main weather display */}
            <div className="flex-1 flex items-center justify-center gap-8">
              <Icon className="w-24 h-24 text-primary" />
              <div>
                <p className="text-[6vw] font-bold leading-none">
                  {formatTemperature(temperature)}
                </p>
                <p className="text-lg text-text-secondary capitalize mt-1">
                  {state.replace('-', ' ')}
                </p>
              </div>
            </div>

            {/* Weather details */}
            <div className="flex justify-center gap-10 pt-4 border-t border-surface-light">
              <div className="flex items-center gap-3">
                <Droplets className="w-7 h-7 text-blue-400" />
                <span className="text-xl">{humidity}%</span>
              </div>
              <div className="flex items-center gap-3">
                <Wind className="w-7 h-7 text-text-secondary" />
                <span className="text-xl">{windSpeed} km/h</span>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-text-secondary">Weather unavailable</p>
          </div>
        )}
      </div>
    </div>
  )
}
