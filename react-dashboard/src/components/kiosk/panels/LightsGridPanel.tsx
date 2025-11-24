import { useState, useCallback, useRef } from 'react'
import { Lightbulb, LightbulbOff, X } from 'lucide-react'
import { useLightEntity } from '../../../hooks/useEntity'
import { Slider } from '../../common'
import { classNames } from '../../../utils/formatters'
import { LIGHTS } from '../../../config/entities'

interface LightCardProps {
  entityId: string
  name: string
  onOpenSettings: () => void
}

function LightCard({ entityId, name, onOpenSettings }: LightCardProps) {
  const {
    isOn,
    isAvailable,
    brightness,
    supportsBrightness,
    toggle,
  } = useLightEntity(entityId)

  const pressTimer = useRef<number | null>(null)
  const isLongPress = useRef(false)
  const startPos = useRef<{ x: number; y: number } | null>(null)
  const isCanceled = useRef(false)
  const [isPressing, setIsPressing] = useState(false)

  const MOVE_THRESHOLD = 10 // pixels

  const handlePressStart = useCallback((clientX: number, clientY: number) => {
    isLongPress.current = false
    isCanceled.current = false
    startPos.current = { x: clientX, y: clientY }
    setIsPressing(true)

    pressTimer.current = window.setTimeout(() => {
      if (!isCanceled.current) {
        isLongPress.current = true
        setIsPressing(false)
        onOpenSettings()
      }
    }, 500)
  }, [onOpenSettings])

  const handlePressMove = useCallback((clientX: number, clientY: number) => {
    if (!startPos.current || isCanceled.current) return

    const dx = Math.abs(clientX - startPos.current.x)
    const dy = Math.abs(clientY - startPos.current.y)

    if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
      // User is scrolling, cancel the press
      isCanceled.current = true
      setIsPressing(false)
      if (pressTimer.current) {
        clearTimeout(pressTimer.current)
        pressTimer.current = null
      }
    }
  }, [])

  const handlePressEnd = useCallback(() => {
    setIsPressing(false)

    if (pressTimer.current) {
      clearTimeout(pressTimer.current)
      pressTimer.current = null
    }

    if (!isLongPress.current && !isCanceled.current) {
      toggle()
    }

    startPos.current = null
  }, [toggle])

  const handlePressCancel = useCallback(() => {
    setIsPressing(false)
    isCanceled.current = true
    startPos.current = null

    if (pressTimer.current) {
      clearTimeout(pressTimer.current)
      pressTimer.current = null
    }
  }, [])

  if (!isAvailable) {
    return (
      <div className="flex flex-col items-center justify-center bg-surface rounded-xl p-3 opacity-50">
        <LightbulbOff className="w-8 h-8 text-text-secondary" />
        <p className="text-xs mt-1 text-center truncate w-full">{name}</p>
      </div>
    )
  }

  return (
    <button
      onTouchStart={(e) => {
        const touch = e.touches[0]
        handlePressStart(touch.clientX, touch.clientY)
      }}
      onTouchMove={(e) => {
        const touch = e.touches[0]
        handlePressMove(touch.clientX, touch.clientY)
      }}
      onTouchEnd={handlePressEnd}
      onTouchCancel={handlePressCancel}
      onMouseDown={(e) => handlePressStart(e.clientX, e.clientY)}
      onMouseMove={(e) => handlePressMove(e.clientX, e.clientY)}
      onMouseUp={handlePressEnd}
      onMouseLeave={handlePressCancel}
      className={classNames(
        'flex flex-col items-center justify-center bg-surface rounded-xl p-3 transition-all duration-150 select-none',
        isOn && 'bg-primary/20 ring-2 ring-primary/30',
        isPressing && 'scale-95 opacity-80'
      )}
    >
      {isOn ? (
        <Lightbulb
          className="w-10 h-10 text-yellow-400 drop-shadow-[0_0_8px_rgba(250,204,21,0.5)]"
        />
      ) : (
        <LightbulbOff className="w-10 h-10 text-text-secondary" />
      )}
      <p className="text-sm mt-2 text-center truncate w-full font-medium">{name}</p>
      {isOn && supportsBrightness && (
        <p className="text-xs text-text-secondary">{brightness}%</p>
      )}
    </button>
  )
}

// Simple color wheel component
interface ColorWheelProps {
  value: number // hue 0-360
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

  // Calculate indicator position
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
      {/* Color wheel background */}
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
      {/* Center white overlay for softer colors */}
      <div
        className="absolute rounded-full bg-surface"
        style={{
          top: '25%',
          left: '25%',
          width: '50%',
          height: '50%',
        }}
      />
      {/* Indicator */}
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

interface LightModalProps {
  entityId: string
  name: string
  onClose: () => void
}

function LightModal({ entityId, name, onClose }: LightModalProps) {
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
      // Convert RGB to hue
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
    // Send hs_color to Home Assistant
    await turnOn({ hs_color: [hue, 100] })
  }

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-surface rounded-2xl p-6 w-full max-w-sm max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold">{name}</h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-light"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Power toggle */}
        <button
          onClick={() => toggle()}
          className={classNames(
            'w-full flex items-center justify-center gap-3 p-4 mb-4 rounded-xl transition-colors',
            isOn ? 'bg-primary/20' : 'bg-surface-light'
          )}
        >
          {isOn ? (
            <Lightbulb className="w-8 h-8 text-yellow-400 drop-shadow-[0_0_8px_rgba(250,204,21,0.5)]" />
          ) : (
            <LightbulbOff className="w-8 h-8 text-text-secondary" />
          )}
          <span className="font-medium">{isOn ? 'On' : 'Off'}</span>
        </button>

        {/* Brightness slider */}
        {supportsBrightness && (
          <div className="mb-4">
            <div className="flex justify-between mb-2">
              <p className="text-sm text-text-secondary">Brightness</p>
              <p className="text-sm">{displayBrightness}%</p>
            </div>
            <Slider
              value={displayBrightness}
              onChange={handleBrightnessChange}
              onChangeEnd={handleBrightnessChangeEnd}
              trackColor={isOn ? 'bg-primary' : 'bg-surface-light'}
            />
          </div>
        )}

        {/* Color temperature slider */}
        {supportsColorTemp && (
          <div className="mb-4">
            <div className="flex justify-between mb-2">
              <p className="text-sm text-text-secondary">Temperature</p>
              <p className="text-sm">
                {displayColorTemp < 50 ? 'Cool' : displayColorTemp > 50 ? 'Warm' : 'Neutral'}
              </p>
            </div>
            <Slider
              value={displayColorTemp}
              onChange={handleColorTempChange}
              onChangeEnd={handleColorTempChangeEnd}
              trackColor="bg-gradient-to-r from-blue-200 via-white to-orange-300"
            />
          </div>
        )}

        {/* Color wheel */}
        {supportsColor && (
          <div>
            <p className="text-sm text-text-secondary mb-3">Color</p>
            <div className="flex justify-center">
              <ColorWheel
                value={localHue}
                onChange={handleHueChange}
                onChangeEnd={handleHueChangeEnd}
                size={140}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function LightsGridPanel() {
  const [selectedLight, setSelectedLight] = useState<{ entityId: string; name: string } | null>(null)

  const lights = Object.entries(LIGHTS)

  const handleSelect = useCallback((entityId: string, name: string) => {
    setSelectedLight({ entityId, name })
  }, [])

  const handleClose = useCallback(() => {
    setSelectedLight(null)
  }, [])

  return (
    <div className="h-full flex flex-col bg-surface rounded-2xl p-4">
      <h2 className="text-kiosk-xl font-bold mb-4">Lights</h2>

      {/* 2-row grid */}
      <div className="flex-1 grid grid-cols-4 grid-rows-2 gap-3 auto-rows-fr">
        {lights.map(([key, light]) => (
          <LightCard
            key={key}
            entityId={light.entity_id}
            name={light.name}
            onOpenSettings={() => handleSelect(light.entity_id, light.name)}
          />
        ))}
        {/* Fill remaining grid cells if less than 8 lights */}
        {lights.length < 8 && (
          <div className="bg-surface-light/30 rounded-xl" />
        )}
      </div>

      {/* Modal */}
      {selectedLight && (
        <LightModal
          entityId={selectedLight.entityId}
          name={selectedLight.name}
          onClose={handleClose}
        />
      )}
    </div>
  )
}
