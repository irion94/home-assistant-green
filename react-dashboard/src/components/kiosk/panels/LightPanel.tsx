import { Lightbulb, LightbulbOff } from 'lucide-react'
import { useLightEntity } from '../../../hooks/useEntity'
import { Switch } from '../../ui/switch'
import { BrightnessControl } from '../../molecules'
import { classNames } from '../../../utils/formatters'

interface LightPanelProps {
  entityId: string
  name?: string
}

export default function LightPanel({ entityId, name }: LightPanelProps) {
  const {
    entity,
    isOn,
    isAvailable,
    brightness,
    supportsBrightness,
    toggle,
    setBrightness,
  } = useLightEntity(entityId)

  const displayName = name || entity?.attributes.friendly_name || entityId

  if (!isAvailable) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-surface rounded-2xl p-6 opacity-50">
        <LightbulbOff className="w-16 h-16 text-text-secondary mb-4" />
        <p className="text-lg font-medium">{displayName}</p>
        <p className="text-sm text-text-secondary mt-2">Unavailable</p>
      </div>
    )
  }

  return (
    <div
      className={classNames(
        'h-full flex flex-col bg-surface rounded-2xl p-6 transition-all duration-300',
        isOn && 'bg-primary/20 border-2 border-primary/30'
      )}
    >
      {/* Light Icon and Status */}
      <div className="flex-1 flex flex-col items-center justify-center">
        {isOn ? (
          <Lightbulb className="w-20 h-20 text-primary mb-4" />
        ) : (
          <LightbulbOff className="w-20 h-20 text-text-secondary mb-4" />
        )}

        <p className="text-xl font-bold text-center">{displayName}</p>

        {supportsBrightness && isOn && (
          <p className="text-kiosk-lg text-text-secondary mt-2">
            {brightness}%
          </p>
        )}
      </div>

      {/* Controls */}
      <div className="mt-auto space-y-4">
        {/* Brightness Control */}
        {supportsBrightness && (
          <div className="px-2">
            <BrightnessControl
              value={brightness}
              onChange={() => {}}
              onChangeEnd={(value) => {
                if (value > 0) {
                  setBrightness(Math.round((value / 100) * 255))
                } else {
                  toggle()
                }
              }}
              variant="inline"
              showLabel={false}
            />
          </div>
        )}

        {/* Toggle Switch */}
        <div className="flex items-center justify-center pt-4 border-t border-surface-light">
          <Switch
            checked={isOn}
            onCheckedChange={() => toggle()}
            className="scale-150"
          />
        </div>
      </div>
    </div>
  )
}
