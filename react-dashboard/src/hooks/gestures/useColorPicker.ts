/**
 * useColorPicker Hook
 *
 * Manages color picker drag interactions for HSL color selection.
 * Extracted from LightsGridPanel ColorWheel component.
 *
 * Features:
 * - Touch and mouse drag support
 * - Circular color wheel calculations
 * - Hue and saturation selection
 * - Drag state tracking
 */

import { useState, useCallback, useRef } from 'react'

export interface ColorValue {
  hue: number        // 0-360
  saturation: number // 0-100
}

export interface UseColorPickerOptions {
  /**
   * Current color value
   */
  value: ColorValue

  /**
   * Callback fired during color change (dragging)
   */
  onChange: (color: ColorValue) => void

  /**
   * Optional callback fired when dragging ends
   */
  onChangeEnd?: (color: ColorValue) => void

  /**
   * Size of the color picker in pixels
   * @default 200
   */
  size?: number
}

export interface UseColorPickerResult {
  /**
   * Event handlers for the color picker element
   */
  handlers: {
    onPointerDown: (e: React.PointerEvent) => void
    onPointerMove: (e: React.PointerEvent) => void
    onPointerUp: (e: React.PointerEvent) => void
    onPointerCancel: () => void
  }

  /**
   * Whether color picker is being dragged
   */
  isDragging: boolean

  /**
   * Position of color indicator (x, y in pixels from center)
   */
  indicatorPosition: { x: number; y: number }
}

/**
 * Calculate color from pointer position within circular picker
 */
function calculateColor(
  x: number,
  y: number,
  centerX: number,
  centerY: number,
  radius: number
): ColorValue {
  const dx = x - centerX
  const dy = y - centerY
  const distance = Math.sqrt(dx * dx + dy * dy)

  // Calculate hue (angle around circle, 0° = top)
  let hue = (Math.atan2(dx, -dy) * 180) / Math.PI
  if (hue < 0) hue += 360

  // Calculate saturation (distance from center, capped at radius)
  const saturation = Math.min((distance / radius) * 100, 100)

  return { hue, saturation }
}

/**
 * Calculate indicator position from color value
 */
function calculateIndicatorPosition(color: ColorValue, radius: number): { x: number; y: number } {
  const angle = (color.hue * Math.PI) / 180
  const distance = (color.saturation / 100) * radius

  return {
    x: distance * Math.sin(angle),
    y: -distance * Math.cos(angle),
  }
}

/**
 * Hook for color picker drag interactions
 *
 * @example
 * const { handlers, isDragging, indicatorPosition } = useColorPicker({
 *   value: { hue: 180, saturation: 50 },
 *   onChange: (color) => console.log('Dragging:', color),
 *   onChangeEnd: (color) => console.log('Committed:', color),
 *   size: 200,
 * })
 *
 * return (
 *   <div {...handlers} style={{ width: size, height: size, position: 'relative' }}>
 *     <div style={{ transform: `translate(${indicatorPosition.x}px, ${indicatorPosition.y}px)` }} />
 *   </div>
 * )
 */
export function useColorPicker(options: UseColorPickerOptions): UseColorPickerResult {
  const { value, onChange, onChangeEnd, size = 200 } = options

  const [isDragging, setIsDragging] = useState(false)
  const elementRef = useRef<HTMLElement | null>(null)

  const radius = size / 2

  const handlePointerEvent = useCallback(
    (e: React.PointerEvent, isEnd: boolean = false) => {
      const target = e.currentTarget as HTMLElement
      elementRef.current = target

      const rect = target.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2

      const color = calculateColor(e.clientX, e.clientY, centerX, centerY, radius)

      if (isEnd) {
        if (onChangeEnd) {
          onChangeEnd(color)
        }
      } else {
        onChange(color)
      }
    },
    [onChange, onChangeEnd, radius]
  )

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      e.currentTarget.setPointerCapture(e.pointerId)
      setIsDragging(true)
      handlePointerEvent(e)
    },
    [handlePointerEvent]
  )

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (isDragging) {
        handlePointerEvent(e)
      }
    },
    [isDragging, handlePointerEvent]
  )

  const handlePointerUp = useCallback(
    (e: React.PointerEvent) => {
      e.currentTarget.releasePointerCapture(e.pointerId)
      setIsDragging(false)
      handlePointerEvent(e, true)
    },
    [handlePointerEvent]
  )

  const handlePointerCancel = useCallback(() => {
    setIsDragging(false)
  }, [])

  const indicatorPosition = calculateIndicatorPosition(value, radius)

  return {
    handlers: {
      onPointerDown: handlePointerDown,
      onPointerMove: handlePointerMove,
      onPointerUp: handlePointerUp,
      onPointerCancel: handlePointerCancel,
    },
    isDragging,
    indicatorPosition,
  }
}
