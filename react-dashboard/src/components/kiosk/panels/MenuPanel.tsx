import { useState, useRef, useCallback } from 'react'
import { Mic, Settings, Power, PowerOff, Wifi, WifiOff, Thermometer, Sun } from 'lucide-react'
import { useHomeAssistant } from '../../../hooks/useHomeAssistant'
import { useSensorEntity } from '../../../hooks/useEntity'
import { getAllLightIds, SENSORS } from '../../../config/entities'
import { Button } from '../../ui/button'
import { Slider } from '../../ui/slider'
import { formatTemperature } from '../../../utils/formatters'

// Color wheel component for menu
interface ColorWheelProps {
  value: number
  onChange: (hue: number) => void
  onChangeEnd: (hue: number) => void
  size?: number
}

function ColorWheel({ value, onChange, onChangeEnd, size = 100 }: ColorWheelProps) {
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
  const indicatorRadius = size / 2 - 6
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
      onTouchStart={(e) => handleStart(e.touches[0].clientX, e.touches[0].clientY)}
      onTouchMove={(e) => handleMove(e.touches[0].clientX, e.touches[0].clientY)}
      onTouchEnd={handleEnd}
    >
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `conic-gradient(
            hsl(0, 100%, 50%), hsl(60, 100%, 50%), hsl(120, 100%, 50%),
            hsl(180, 100%, 50%), hsl(240, 100%, 50%), hsl(300, 100%, 50%), hsl(360, 100%, 50%)
          )`,
        }}
      />
      <div
        className="absolute rounded-full bg-surface"
        style={{ top: '30%', left: '30%', width: '40%', height: '40%' }}
      />
      <div
        className="absolute w-3 h-3 rounded-full border-2 border-white shadow-lg"
        style={{
          backgroundColor: `hsl(${value}, 100%, 50%)`,
          left: `calc(50% + ${indicatorX}px - 6px)`,
          top: `calc(50% + ${indicatorY}px - 6px)`,
        }}
      />
    </div>
  )
}

interface MenuPanelProps {
  onNavigate?: (path: string) => void
}

export default function MenuPanel({ onNavigate }: MenuPanelProps) {
  const { connected, callService } = useHomeAssistant()
  const cpuTemp = useSensorEntity(SENSORS.cpuTemp)
  const [globalBrightness, setGlobalBrightness] = useState(100)
  const [globalColorTemp, setGlobalColorTemp] = useState(50)
  const [globalHue, setGlobalHue] = useState(0)

  const lightIds = getAllLightIds()

  const handleAllLightsOn = async () => {
    await callService('light', 'turn_on', { entity_id: lightIds })
  }

  const handleAllLightsOff = async () => {
    await callService('light', 'turn_off', { entity_id: lightIds })
  }

  const handleGlobalBrightnessChange = (value: number) => {
    setGlobalBrightness(value)
  }

  const handleGlobalBrightnessChangeEnd = async (value: number) => {
    const brightness = Math.round((value / 100) * 255)
    await callService('light', 'turn_on', {
      entity_id: lightIds,
      brightness,
    })
  }

  const handleGlobalColorTempChange = (value: number) => {
    setGlobalColorTemp(value)
  }

  const handleGlobalColorTempChangeEnd = async (value: number) => {
    // Convert percentage to mireds (0%=153 cool, 100%=500 warm)
    const mireds = Math.round(153 + (value / 100) * (500 - 153))
    await callService('light', 'turn_on', {
      entity_id: lightIds,
      color_temp: mireds,
    })
  }

  const handleGlobalHueChange = (hue: number) => {
    setGlobalHue(hue)
  }

  const handleGlobalHueChangeEnd = async (hue: number) => {
    await callService('light', 'turn_on', {
      entity_id: lightIds,
      hs_color: [hue, 100],
    })
  }

  const cpuTempValue = cpuTemp.entity?.state
    ? formatTemperature(parseFloat(cpuTemp.entity.state))
    : '--'

  return (
    <div className="h-full flex flex-col bg-surface rounded-2xl p-6 overflow-y-auto">
      {/* Header */}
      <h2 className="text-kiosk-xl font-bold mb-6 flex-shrink-0">Menu</h2>

      {/* Navigation Links */}
      <div className="space-y-3 mb-8">
        <button
          onClick={() => onNavigate?.('/voice')}
          className="w-full flex items-center gap-4 p-4 bg-surface-light rounded-xl hover:bg-primary/20 transition-colors"
        >
          <Mic className="w-6 h-6 text-primary" />
          <span className="text-lg font-medium">Voice Assistant</span>
        </button>

        <button
          onClick={() => onNavigate?.('/settings')}
          className="w-full flex items-center gap-4 p-4 bg-surface-light rounded-xl hover:bg-primary/20 transition-colors"
        >
          <Settings className="w-6 h-6 text-text-secondary" />
          <span className="text-lg font-medium">Settings</span>
        </button>
      </div>

      {/* System Info */}
      <div className="mb-8">
        <h3 className="text-sm font-medium text-text-secondary mb-3 uppercase tracking-wider">
          System Status
        </h3>
        <div className="space-y-2">
          <div className="flex items-center justify-between p-3 bg-surface-light rounded-lg">
            <div className="flex items-center gap-3">
              {connected ? (
                <Wifi className="w-5 h-5 text-success" />
              ) : (
                <WifiOff className="w-5 h-5 text-error" />
              )}
              <span>Connection</span>
            </div>
            <span className={connected ? 'text-success' : 'text-error'}>
              {connected ? 'Online' : 'Offline'}
            </span>
          </div>

          <div className="flex items-center justify-between p-3 bg-surface-light rounded-lg">
            <div className="flex items-center gap-3">
              <Thermometer className="w-5 h-5 text-warning" />
              <span>CPU Temp</span>
            </div>
            <span>{cpuTempValue}</span>
          </div>
        </div>
      </div>

      {/* Global Light Controls */}
      <div className="mb-8">
        <h3 className="text-sm font-medium text-text-secondary mb-3 uppercase tracking-wider">
          All Lights
        </h3>
        <div className="space-y-4">
          {/* Global Brightness */}
          <div className="p-3 bg-surface-light rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Sun className="w-4 h-4 text-primary" />
              <span className="text-sm">Brightness</span>
              <span className="ml-auto text-sm text-text-secondary">{globalBrightness}%</span>
            </div>
            <Slider
              value={[globalBrightness]}
              onValueChange={([v]) => handleGlobalBrightnessChange(v)}
              onValueCommit={([v]) => handleGlobalBrightnessChangeEnd(v)}
              max={100}
              step={1}
            />
          </div>

          {/* Global Color Temperature */}
          <div className="p-3 bg-surface-light rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm">Temperature</span>
              <span className="ml-auto text-sm text-text-secondary">
                {globalColorTemp < 50 ? 'Cool' : globalColorTemp > 50 ? 'Warm' : 'Neutral'}
              </span>
            </div>
            <Slider
              value={[globalColorTemp]}
              onValueChange={([v]) => handleGlobalColorTempChange(v)}
              onValueCommit={([v]) => handleGlobalColorTempChangeEnd(v)}
              max={100}
              step={1}
            />
          </div>

          {/* Global Color */}
          <div className="p-3 bg-surface-light rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm">Color</span>
            </div>
            <div className="flex justify-center">
              <ColorWheel
                value={globalHue}
                onChange={handleGlobalHueChange}
                onChangeEnd={handleGlobalHueChangeEnd}
                size={80}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mt-auto">
        <h3 className="text-sm font-medium text-text-secondary mb-3 uppercase tracking-wider">
          Quick Actions
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <Button
            variant="default"
            className="flex items-center justify-center gap-2 py-4"
            onClick={handleAllLightsOn}
          >
            <Power className="w-5 h-5" />
            <span>All On</span>
          </Button>

          <Button
            variant="outline"
            className="flex items-center justify-center gap-2 py-4"
            onClick={handleAllLightsOff}
          >
            <PowerOff className="w-5 h-5" />
            <span>All Off</span>
          </Button>
        </div>
      </div>
    </div>
  )
}
