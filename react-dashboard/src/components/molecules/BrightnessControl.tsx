/**
 * BrightnessControl Component
 *
 * Reusable brightness slider with local state management.
 * Eliminates ~60 LOC duplication across LightCard, LightPanel, LightModal.
 *
 * Usage:
 * <BrightnessControl
 *   value={50}
 *   onChange={(v) => setLocalBrightness(v)}
 *   onChangeEnd={(v) => entity.setBrightness(Math.round(v * 2.55))}
 *   variant="inline"
 *   showLabel
 * />
 */

import { useBrightnessControl } from '../../hooks/gestures'
import { Slider } from '../ui/slider'
import { cn } from '../../lib/utils'

export interface BrightnessControlProps {
  /**
   * Current brightness value (0-100)
   */
  value: number

  /**
   * Callback fired during brightness change
   */
  onChange: (value: number) => void

  /**
   * Callback fired when dragging ends
   */
  onChangeEnd?: (value: number) => void

  /**
   * Whether the control is disabled
   */
  disabled?: boolean

  /**
   * Display variant
   * - inline: Compact horizontal slider
   * - modal: Larger slider for full-screen modals
   */
  variant?: 'inline' | 'modal'

  /**
   * Whether to show the brightness percentage label
   */
  showLabel?: boolean

  /**
   * Optional className for custom styling
   */
  className?: string
}

export function BrightnessControl({
  value,
  onChange,
  onChangeEnd,
  disabled = false,
  variant = 'inline',
  showLabel = true,
  className,
}: BrightnessControlProps) {
  const { localValue, isDragging, handleChange, handleChangeEnd } = useBrightnessControl({
    value,
    onChange,
    onChangeEnd,
  })

  // Use local value during drag, otherwise use prop value
  const displayValue = isDragging ? localValue : value

  return (
    <div
      className={cn(
        'flex items-center gap-3',
        variant === 'modal' && 'flex-col gap-2',
        className
      )}
    >
      {showLabel && (
        <div
          className={cn(
            'text-sm font-medium text-text-secondary',
            variant === 'modal' && 'text-lg w-full text-center'
          )}
        >
          {Math.round(displayValue)}%
        </div>
      )}
      <Slider
        value={[displayValue]}
        onValueChange={handleChange}
        onValueCommit={handleChangeEnd}
        min={0}
        max={100}
        step={1}
        disabled={disabled}
        className={cn(
          'flex-1',
          variant === 'modal' && 'w-full'
        )}
      />
    </div>
  )
}
