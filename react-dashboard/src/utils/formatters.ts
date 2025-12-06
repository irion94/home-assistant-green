export function formatTemperature(value: number | string, unit: string = '°C'): string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '--'
  return `${num.toFixed(1)}${unit}`
}

export function formatPower(value: number | string, unit: string = 'W'): string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '--'

  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)} kW`
  }
  return `${num.toFixed(0)} ${unit}`
}

export function formatEnergy(value: number | string): string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '--'
  return `${num.toFixed(1)} kWh`
}

export function formatPercentage(value: number | string): string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '--'
  return `${Math.round(num)}%`
}

export function formatBrightness(brightness: number): number {
  // Convert HA brightness (0-255) to percentage (0-100)
  return Math.round((brightness / 255) * 100)
}

export function toBrightness(percentage: number): number {
  // Convert percentage (0-100) to HA brightness (0-255)
  return Math.round((percentage / 100) * 255)
}

export function formatTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' })
}

export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('pl-PL', { weekday: 'short', day: 'numeric', month: 'short' })
}

export function formatRelativeTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diff = now.getTime() - d.getTime()

  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  return `${days}d ago`
}

export function classNames(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ')
}
