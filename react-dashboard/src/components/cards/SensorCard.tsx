import {
  Thermometer,
  Droplets,
  Zap,
  Sun,
  Battery,
  Gauge,
  Wind,
  Activity,
} from 'lucide-react'
import { useSensorEntity } from '../../hooks/useEntity'
import { classNames } from '../../utils/formatters'

interface SensorCardProps {
  entityId: string
  name?: string
  icon?: 'temperature' | 'humidity' | 'power' | 'solar' | 'battery' | 'pressure' | 'wind' | 'default'
  size?: 'sm' | 'md' | 'lg'
}

const iconMap = {
  temperature: Thermometer,
  humidity: Droplets,
  power: Zap,
  solar: Sun,
  battery: Battery,
  pressure: Gauge,
  wind: Wind,
  default: Activity,
}

export default function SensorCard({
  entityId,
  name,
  icon = 'default',
  size = 'md',
}: SensorCardProps) {
  const { entity, value, unit, deviceClass, isAvailable } = useSensorEntity(entityId)

  const displayName = name || entity?.attributes.friendly_name || entityId

  // Auto-detect icon based on device class
  const getIcon = () => {
    if (icon !== 'default') return icon

    switch (deviceClass) {
      case 'temperature':
        return 'temperature'
      case 'humidity':
        return 'humidity'
      case 'power':
      case 'energy':
        return 'power'
      case 'battery':
        return 'battery'
      case 'pressure':
        return 'pressure'
      default:
        return 'default'
    }
  }

  const Icon = iconMap[getIcon()]

  const sizeClasses = {
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  }

  const valueSizeClasses = {
    sm: 'text-lg',
    md: 'text-kiosk-lg',
    lg: 'text-kiosk-2xl',
  }

  const iconSizeClasses = {
    sm: 'w-5 h-5',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  }

  // Color based on device class
  const getIconColor = () => {
    switch (deviceClass) {
      case 'temperature':
        return 'text-orange-400'
      case 'humidity':
        return 'text-blue-400'
      case 'power':
      case 'energy':
        return 'text-yellow-400'
      case 'battery':
        const batteryLevel = parseFloat(value)
        if (batteryLevel > 60) return 'text-success'
        if (batteryLevel > 20) return 'text-warning'
        return 'text-error'
      default:
        return 'text-primary'
    }
  }

  if (!isAvailable) {
    return (
      <div className={classNames('card opacity-50', sizeClasses[size])}>
        <div className="flex items-center gap-2">
          <Icon className={classNames(iconSizeClasses[size], 'text-text-secondary')} />
          <span className="text-sm">{displayName}</span>
        </div>
        <p className="text-text-secondary mt-1">--</p>
      </div>
    )
  }

  return (
    <div className={classNames('card', sizeClasses[size])}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <Icon className={classNames(iconSizeClasses[size], getIconColor())} />
        <span className="text-sm text-text-secondary truncate">{displayName}</span>
      </div>

      {/* Value */}
      <p className={classNames('font-bold', valueSizeClasses[size])}>
        {value}
        {unit && <span className="text-text-secondary ml-1">{unit}</span>}
      </p>
    </div>
  )
}
