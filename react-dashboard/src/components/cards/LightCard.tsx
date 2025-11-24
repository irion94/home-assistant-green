import { useState } from 'react'
import { Lightbulb, LightbulbOff } from 'lucide-react'
import { useLightEntity } from '../../hooks/useEntity'
import { Toggle, Slider } from '../common'
import { classNames } from '../../utils/formatters'

interface LightCardProps {
  entityId: string
  name?: string
  icon?: string
  showBrightness?: boolean
}

export default function LightCard({
  entityId,
  name,
  showBrightness = true,
}: LightCardProps) {
  const {
    entity,
    isOn,
    isAvailable,
    brightness,
    supportsBrightness,
    toggle,
    setBrightness,
  } = useLightEntity(entityId)

  const [localBrightness, setLocalBrightness] = useState(brightness)
  const [isDragging, setIsDragging] = useState(false)

  const displayName = name || entity?.attributes.friendly_name || entityId
  const displayBrightness = isDragging ? localBrightness : brightness

  const handleBrightnessChange = (value: number) => {
    setLocalBrightness(value)
    setIsDragging(true)
  }

  const handleBrightnessChangeEnd = async (value: number) => {
    setIsDragging(false)
    if (value > 0) {
      // Convert percentage to 0-255 range
      await setBrightness(Math.round((value / 100) * 255))
    } else {
      await toggle()
    }
  }

  if (!isAvailable) {
    return (
      <div className="card opacity-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <LightbulbOff className="w-6 h-6 text-text-secondary" />
            <span className="font-medium">{displayName}</span>
          </div>
          <span className="text-sm text-text-secondary">Unavailable</span>
        </div>
      </div>
    )
  }

  return (
    <div
      className={classNames(
        'card transition-all duration-300',
        isOn && 'bg-primary/20 border border-primary/30'
      )}
    >
      {/* Header with toggle */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {isOn ? (
            <Lightbulb className="w-6 h-6 text-primary" />
          ) : (
            <LightbulbOff className="w-6 h-6 text-text-secondary" />
          )}
          <div>
            <p className="font-medium">{displayName}</p>
            {showBrightness && supportsBrightness && isOn && (
              <p className="text-sm text-text-secondary">{displayBrightness}%</p>
            )}
          </div>
        </div>
        <Toggle checked={isOn} onChange={() => toggle()} />
      </div>

      {/* Brightness slider */}
      {showBrightness && supportsBrightness && (
        <Slider
          value={displayBrightness}
          onChange={handleBrightnessChange}
          onChangeEnd={handleBrightnessChangeEnd}
          disabled={!isOn}
          trackColor={isOn ? 'bg-primary' : 'bg-surface-light'}
        />
      )}
    </div>
  )
}
