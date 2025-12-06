import { useState, useRef, useCallback } from 'react'
import { Lightbulb, LightbulbOff, X } from 'lucide-react'
import { motion } from 'framer-motion'
import { DisplayPanelProps, LightControlDetailedData } from '../types'
import { useLightEntity } from '../../../../hooks/useEntity'
import { Slider } from '../../../ui/slider'
import { classNames } from '../../../../utils/formatters'

// Color wheel component (same as dashboard)
interface ColorWheelProps {
  value: number
  saturation?: number
  onChange: (hue: number) => void
  onChangeEnd: (hue: number) => void
  size?: number
}

function ColorWheel({ value, saturation = 100, onChange, onChangeEnd, size = 120 }: ColorWheelProps) {
  const wheelRef = useRef<HTMLDivElement>(null)
  const isDragging = useRef(false)

  const calculateHue = useCallback((clientX: number, clientY: number) => {
    if (!wheelRef.current) return value
    const rect = wheelRef.current.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    const angle = Math.atan2(clientY - centerY, clientX - centerX)
    let hue = (angle * 180) / Math.PI + 90
    if (hue < 0) hue += 360
    return Math.round(hue) % 360
  }, [value])

  const handleStart = useCallback((clientX: number, clientY: number) => {
    isDragging.current = true
    const hue = calculateHue(clientX, clientY)
    onChange(hue)
  }, [calculateHue, onChange])

  const handleMove = useCallback((clientX: number, clientY: number) => {
    if (!isDragging.current) return
    const hue = calculateHue(clientX, clientY)
    onChange(hue)
  }, [calculateHue, onChange])

  const handleEnd = useCallback(() => {
    if (isDragging.current) {
      isDragging.current = false
      onChangeEnd(value)
    }
  }, [onChangeEnd, value])

  const indicatorAngle = ((value - 90) * Math.PI) / 180
  const indicatorRadius = size / 2 - 8
  const indicatorX = Math.cos(indicatorAngle) * indicatorRadius
  const indicatorY = Math.sin(indicatorAngle) * indicatorRadius

  return (
    <div
      ref={wheelRef}
      className="relative cursor-pointer touch-none"
      style={{ width: size, height: size }}
      onMouseDown={(e) => handleStart(e.clientX, e.clientY)}
      onMouseMove={(e) => handleMove(e.clientX, e.clientY)}
      onMouseUp={handleEnd}
      onMouseLeave={handleEnd}
      onTouchStart={(e) => {
        const touch = e.touches[0]
        handleStart(touch.clientX, touch.clientY)
      }}
      onTouchMove={(e) => {
        const touch = e.touches[0]
        handleMove(touch.clientX, touch.clientY)
      }}
      onTouchEnd={handleEnd}
    >
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `conic-gradient(
            hsl(0, ${saturation}%, 50%),
            hsl(60, ${saturation}%, 50%),
            hsl(120, ${saturation}%, 50%),
            hsl(180, ${saturation}%, 50%),
            hsl(240, ${saturation}%, 50%),
            hsl(300, ${saturation}%, 50%),
            hsl(360, ${saturation}%, 50%)
          )`,
        }}
      />
      <div
        className="absolute rounded-full bg-surface"
        style={{
          top: '25%',
          left: '25%',
          width: '50%',
          height: '50%',
        }}
      />
      <div
        className="absolute w-4 h-4 rounded-full border-2 border-white shadow-lg"
        style={{
          backgroundColor: `hsl(${value}, ${saturation}%, 50%)`,
          left: `calc(50% + ${indicatorX}px - 8px)`,
          top: `calc(50% + ${indicatorY}px - 8px)`,
        }}
      />
    </div>
  )
}

// Individual light entity control (uses useLightEntity hook)
function LightEntityControl({ entityId, name, idx }: { entityId: string; name: string; idx: number }) {
  const {
    isOn,
    brightness,
    supportsBrightness,
    supportsColorTemp,
    supportsColor,
    colorTemp,
    rgbColor,
    toggle,
    turnOn,
    setBrightness,
  } = useLightEntity(entityId)

  const [localBrightness, setLocalBrightness] = useState(brightness)
  const [localColorTemp, setLocalColorTemp] = useState(
    colorTemp ? Math.round(((colorTemp - 153) / (500 - 153)) * 100) : 50
  )
  const [localHue, setLocalHue] = useState(() => {
    if (rgbColor) {
      const [r, g, b] = rgbColor
      const max = Math.max(r, g, b)
      const min = Math.min(r, g, b)
      if (max === min) return 0
      let hue = 0
      if (max === r) hue = ((g - b) / (max - min)) * 60
      else if (max === g) hue = (2 + (b - r) / (max - min)) * 60
      else hue = (4 + (r - g) / (max - min)) * 60
      return hue < 0 ? hue + 360 : hue
    }
    return 0
  })
  const [isDragging, setIsDragging] = useState(false)

  const displayBrightness = isDragging ? localBrightness : brightness
  const colorTempPercent = colorTemp ? Math.round(((colorTemp - 153) / (500 - 153)) * 100) : 50
  const displayColorTemp = isDragging ? localColorTemp : colorTempPercent

  const handleBrightnessChange = (value: number) => {
    setLocalBrightness(value)
    setIsDragging(true)
  }

  const handleBrightnessChangeEnd = async (value: number) => {
    setIsDragging(false)
    if (value > 0) {
      await setBrightness(Math.round((value / 100) * 255))
    }
  }

  const handleColorTempChange = (value: number) => {
    setLocalColorTemp(value)
    setIsDragging(true)
  }

  const handleColorTempChangeEnd = async (value: number) => {
    setIsDragging(false)
    const mireds = Math.round(153 + (value / 100) * (500 - 153))
    await turnOn({ color_temp: mireds })
  }

  const handleHueChange = (hue: number) => {
    setLocalHue(hue)
  }

  const handleHueChangeEnd = async (hue: number) => {
    await turnOn({ hs_color: [hue, 100] })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.05 }}
      className="p-4 bg-black/30 rounded-lg border border-white/10"
    >
      {/* Toggle button */}
      <button
        onClick={() => toggle()}
        className={classNames(
          'w-full flex items-center justify-center gap-3 p-3 mb-3 rounded-xl transition-colors',
          isOn ? 'bg-primary/20' : 'bg-surface-light'
        )}
      >
        {isOn ? (
          <Lightbulb className="w-6 h-6 text-yellow-400 drop-shadow-[0_0_8px_rgba(250,204,21,0.5)]" />
        ) : (
          <LightbulbOff className="w-6 h-6 text-text-secondary" />
        )}
        <span className="font-medium text-sm">{name}</span>
        <span className="text-xs ml-auto">{isOn ? 'ON' : 'OFF'}</span>
      </button>

      {/* Brightness slider */}
      {supportsBrightness && (
        <div className="mb-3">
          <div className="flex justify-between mb-2">
            <p className="text-xs text-text-secondary">Brightness</p>
            <p className="text-xs">{displayBrightness}%</p>
          </div>
          <Slider
            value={[displayBrightness]}
            onValueChange={([v]) => handleBrightnessChange(v)}
            onValueCommit={([v]) => handleBrightnessChangeEnd(v)}
            max={100}
            step={1}
            disabled={!isOn}
          />
        </div>
      )}

      {/* Color temperature slider */}
      {supportsColorTemp && (
        <div className="mb-3">
          <div className="flex justify-between mb-2">
            <p className="text-xs text-text-secondary">Temperature</p>
            <p className="text-xs">
              {displayColorTemp < 50 ? 'Cool' : displayColorTemp > 50 ? 'Warm' : 'Neutral'}
            </p>
          </div>
          <Slider
            value={[displayColorTemp]}
            onValueChange={([v]) => handleColorTempChange(v)}
            onValueCommit={([v]) => handleColorTempChangeEnd(v)}
            max={100}
            step={1}
          />
        </div>
      )}

      {/* Color wheel */}
      {supportsColor && (
        <div>
          <p className="text-xs text-text-secondary mb-2">Color</p>
          <div className="flex justify-center">
            <ColorWheel
              value={localHue}
              onChange={handleHueChange}
              onChangeEnd={handleHueChangeEnd}
              size={120}
            />
          </div>
        </div>
      )}
    </motion.div>
  )
}

export default function LightControlDetailedPanel({ action, onClose }: DisplayPanelProps) {
  const data = action.data as LightControlDetailedData

  return (
    <div className="flex flex-col h-full bg-black/20 backdrop-blur-md">
      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-black/30 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-primary" />
          <div>
            <span className="font-medium text-text-primary capitalize">{data.room} Lights</span>
            <p className="text-xs text-text-secondary">{data.entities.length} device{data.entities.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
        {onClose && (
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded transition-colors" title="Close">
            <X className="w-5 h-5 text-text-secondary hover:text-text-primary" />
          </button>
        )}
      </div>

      {/* Entity Controls */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="w-full max-w-md mx-auto space-y-3">
          {data.entities.map((entity, idx) => (
            <LightEntityControl
              key={entity.entity_id}
              entityId={entity.entity_id}
              name={entity.friendly_name}
              idx={idx}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
