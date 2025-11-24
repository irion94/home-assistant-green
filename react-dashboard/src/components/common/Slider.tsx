import { useCallback, useRef, useState, type PointerEvent } from 'react'
import { classNames } from '../../utils/formatters'

interface SliderProps {
  value: number
  min?: number
  max?: number
  step?: number
  onChange: (value: number) => void
  onChangeEnd?: (value: number) => void
  disabled?: boolean
  className?: string
  trackColor?: string
  thumbColor?: string
}

export default function Slider({
  value,
  min = 0,
  max = 100,
  step = 1,
  onChange,
  onChangeEnd,
  disabled = false,
  className,
  trackColor = 'bg-primary',
  thumbColor = 'bg-white',
}: SliderProps) {
  const trackRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  const calculateValue = useCallback(
    (clientX: number) => {
      if (!trackRef.current) return value

      const rect = trackRef.current.getBoundingClientRect()
      const percentage = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
      const rawValue = min + percentage * (max - min)
      const steppedValue = Math.round(rawValue / step) * step
      return Math.max(min, Math.min(max, steppedValue))
    },
    [min, max, step, value]
  )

  const handlePointerDown = useCallback(
    (e: PointerEvent) => {
      if (disabled) return

      e.preventDefault()
      setIsDragging(true)
      const newValue = calculateValue(e.clientX)
      onChange(newValue)

      const handlePointerMove = (e: globalThis.PointerEvent) => {
        const newValue = calculateValue(e.clientX)
        onChange(newValue)
      }

      const handlePointerUp = (e: globalThis.PointerEvent) => {
        setIsDragging(false)
        const finalValue = calculateValue(e.clientX)
        onChangeEnd?.(finalValue)
        document.removeEventListener('pointermove', handlePointerMove)
        document.removeEventListener('pointerup', handlePointerUp)
      }

      document.addEventListener('pointermove', handlePointerMove)
      document.addEventListener('pointerup', handlePointerUp)
    },
    [disabled, calculateValue, onChange, onChangeEnd]
  )

  const percentage = ((value - min) / (max - min)) * 100

  return (
    <div
      ref={trackRef}
      className={classNames(
        'relative h-12 flex items-center touch-none',
        disabled && 'opacity-50 pointer-events-none',
        className
      )}
      onPointerDown={handlePointerDown}
    >
      {/* Track background */}
      <div className="absolute inset-x-0 h-2 bg-surface-light rounded-full overflow-hidden">
        {/* Filled track */}
        <div
          className={classNames('h-full rounded-full transition-all', trackColor)}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Thumb */}
      <div
        className={classNames(
          'absolute w-6 h-6 rounded-full shadow-lg transition-transform',
          thumbColor,
          isDragging && 'scale-125'
        )}
        style={{ left: `calc(${percentage}% - 12px)` }}
      />
    </div>
  )
}
