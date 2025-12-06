/**
 * useBrightnessControl Hook
 *
 * Manages local brightness state with optimistic updates.
 * Extracted from LightCard, LightPanel, and LightsGridPanel to eliminate duplication.
 *
 * Features:
 * - Local state for smooth dragging
 * - Optimistic updates during interaction
 * - Debounced API calls on drag end
 * - Drag state tracking
 */

import { useState, useCallback, useEffect } from 'react'

export interface UseBrightnessControlOptions {
  /**
   * Current brightness value (0-100)
   */
  value: number

  /**
   * Callback fired during brightness change (dragging)
   * Use for optimistic local updates
   */
  onChange: (value: number) => void

  /**
   * Optional callback fired when dragging ends
   * Use for API calls to persist the value
   */
  onChangeEnd?: (value: number) => void
}

export interface UseBrightnessControlResult {
  /**
   * Current local brightness value (may differ from prop during drag)
   */
  localValue: number

  /**
   * Whether the slider is currently being dragged
   */
  isDragging: boolean

  /**
   * Handler for slider change events
   */
  handleChange: (value: number[]) => void

  /**
   * Handler for slider commit events (drag end)
   */
  handleChangeEnd: (value: number[]) => void
}

/**
 * Hook for managing brightness control state
 *
 * @example
 * const { localValue, isDragging, handleChange, handleChangeEnd } = useBrightnessControl({
 *   value: entity.brightness,
 *   onChange: (v) => {
 *     // Optimistic local update
 *     setLocalBrightness(v)
 *   },
 *   onChangeEnd: (v) => {
 *     // Persist to API
 *     entity.setBrightness(Math.round(v * 2.55))
 *   },
 * })
 *
 * return <Slider value={[localValue]} onValueChange={handleChange} onValueCommit={handleChangeEnd} />
 */
export function useBrightnessControl(
  options: UseBrightnessControlOptions
): UseBrightnessControlResult {
  const { value, onChange, onChangeEnd } = options

  const [localValue, setLocalValue] = useState(value)
  const [isDragging, setIsDragging] = useState(false)

  // Sync local value when prop changes (but not during drag)
  useEffect(() => {
    if (!isDragging) {
      setLocalValue(value)
    }
  }, [value, isDragging])

  const handleChange = useCallback(
    (newValue: number[]) => {
      const brightness = newValue[0]
      setIsDragging(true)
      setLocalValue(brightness)
      onChange(brightness)
    },
    [onChange]
  )

  const handleChangeEnd = useCallback(
    (newValue: number[]) => {
      const brightness = newValue[0]
      setIsDragging(false)
      setLocalValue(brightness)

      if (onChangeEnd) {
        onChangeEnd(brightness)
      }
    },
    [onChangeEnd]
  )

  return {
    localValue,
    isDragging,
    handleChange,
    handleChangeEnd,
  }
}
