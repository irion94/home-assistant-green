/**
 * Gesture Hooks
 *
 * Re-exports all gesture-related hooks for convenient importing.
 *
 * Usage:
 * import { useLongPress, useBrightnessControl, useColorPicker } from '@/hooks/gestures'
 */

export { useLongPress, type UseLongPressOptions, type UseLongPressResult } from './useLongPress'
export {
  useBrightnessControl,
  type UseBrightnessControlOptions,
  type UseBrightnessControlResult,
} from './useBrightnessControl'
export {
  useColorPicker,
  type ColorValue,
  type UseColorPickerOptions,
  type UseColorPickerResult,
} from './useColorPicker'
