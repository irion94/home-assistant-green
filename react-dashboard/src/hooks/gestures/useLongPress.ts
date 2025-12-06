/**
 * useLongPress Hook
 *
 * Detects long-press gestures on elements.
 * Extracted from LightsGridPanel to eliminate duplication.
 *
 * Features:
 * - Configurable press duration
 * - Movement threshold to cancel press
 * - Separate callbacks for press and long-press
 * - Touch and mouse event support
 */

import { useCallback, useRef } from 'react'

export interface UseLongPressOptions {
  /**
   * Callback fired on long press completion
   */
  onLongPress: () => void

  /**
   * Optional callback fired on regular press (without long press)
   */
  onPress?: () => void

  /**
   * Duration in milliseconds to trigger long press
   * @default 500
   */
  threshold?: number

  /**
   * Maximum movement in pixels before canceling long press
   * @default 10
   */
  moveThreshold?: number
}

export interface UseLongPressResult {
  /**
   * Event handlers to spread on the target element
   */
  handlers: {
    onPointerDown: (e: React.PointerEvent) => void
    onPointerUp: (e: React.PointerEvent) => void
    onPointerMove: (e: React.PointerEvent) => void
    onPointerCancel: () => void
  }

  /**
   * Whether the element is currently being pressed
   */
  isPressing: boolean
}

/**
 * Hook to detect long-press gestures
 *
 * @example
 * const { handlers, isPressing } = useLongPress({
 *   onLongPress: () => console.log('Long pressed!'),
 *   onPress: () => console.log('Short pressed'),
 *   threshold: 500,
 *   moveThreshold: 10,
 * })
 *
 * return <button {...handlers}>Press me</button>
 */
export function useLongPress(options: UseLongPressOptions): UseLongPressResult {
  const { onLongPress, onPress, threshold = 500, moveThreshold = 10 } = options

  const timeoutRef = useRef<number | null>(null)
  const startPos = useRef<{ x: number; y: number } | null>(null)
  const isPressingRef = useRef(false)
  const longPressTriggered = useRef(false)

  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
    startPos.current = null
    isPressingRef.current = false
    longPressTriggered.current = false
  }, [])

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      // Capture pointer for reliable tracking
      e.currentTarget.setPointerCapture(e.pointerId)

      isPressingRef.current = true
      longPressTriggered.current = false
      startPos.current = { x: e.clientX, y: e.clientY }

      // Start long-press timer
      timeoutRef.current = window.setTimeout(() => {
        if (isPressingRef.current) {
          longPressTriggered.current = true
          onLongPress()
        }
      }, threshold)
    },
    [onLongPress, threshold]
  )

  const handlePointerUp = useCallback(
    (e: React.PointerEvent) => {
      // Release pointer capture
      e.currentTarget.releasePointerCapture(e.pointerId)

      const wasLongPress = longPressTriggered.current

      cancel()

      // Trigger onPress only if long press wasn't triggered
      if (!wasLongPress && onPress) {
        onPress()
      }
    },
    [cancel, onPress]
  )

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!isPressingRef.current || !startPos.current) return

      // Calculate distance moved
      const deltaX = e.clientX - startPos.current.x
      const deltaY = e.clientY - startPos.current.y
      const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)

      // Cancel if moved beyond threshold
      if (distance > moveThreshold) {
        cancel()
      }
    },
    [cancel, moveThreshold]
  )

  const handlePointerCancel = useCallback(() => {
    cancel()
  }, [cancel])

  return {
    handlers: {
      onPointerDown: handlePointerDown,
      onPointerUp: handlePointerUp,
      onPointerMove: handlePointerMove,
      onPointerCancel: handlePointerCancel,
    },
    isPressing: isPressingRef.current,
  }
}
