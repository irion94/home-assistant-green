/**
 * Design System Tokens
 *
 * Centralized design tokens for the Home Assistant dashboard.
 * These tokens are used alongside Tailwind CSS and shadcn/ui CSS variables.
 *
 * Usage:
 * - Import tokens directly: `import { colors, spacing } from '@/design-system/tokens'`
 * - Use in components: `backgroundColor: colors.surface`
 * - Prefer Tailwind classes when possible: `className="bg-surface"`
 */

/**
 * Color Tokens
 *
 * Note: shadcn/ui colors (primary, secondary, etc.) use CSS variables
 * defined in src/styles/index.css and should be accessed via Tailwind classes.
 * These tokens are for custom colors not managed by shadcn/ui.
 */
export const colors = {
  // Surface colors
  background: '#0f0f0f',
  surface: '#1a1a1a',
  surfaceLight: '#2a2a2a',

  // Brand colors (for direct JS access)
  primaryDark: '#2563eb',

  // Semantic colors
  success: '#22c55e',
  successLight: '#4ade80',
  warning: '#f59e0b',
  warningLight: '#fbbf24',
  error: '#ef4444',
  errorLight: '#f87171',

  // Text colors
  textPrimary: '#ffffff',
  textSecondary: '#a1a1aa',
  textMuted: '#71717a',

  // Voice state colors (for visual feedback during voice interactions)
  voiceState: {
    idle: '#6b7280',        // Gray - waiting for wake word
    wakeDetected: '#8b5cf6', // Purple - wake word detected
    listening: '#3b82f6',   // Blue - recording user speech
    transcribing: '#06b6d4', // Cyan - converting speech to text
    processing: '#f59e0b',  // Orange - LLM processing request
    speaking: '#22c55e',    // Green - TTS response playing
    waiting: '#ec4899',     // Pink - conversation mode waiting for input
    error: '#ef4444',       // Red - error state
  },

  // Entity state colors (lights, switches, etc.)
  entityState: {
    on: '#22c55e',
    off: '#6b7280',
    unavailable: '#ef4444',
    unknown: '#f59e0b',
  },

  // Temperature gradient (for climate controls)
  temperature: {
    cold: '#3b82f6',
    cool: '#06b6d4',
    neutral: '#22c55e',
    warm: '#f59e0b',
    hot: '#ef4444',
  },
} as const

/**
 * Spacing Tokens
 *
 * Touch-friendly spacing for kiosk interface.
 * Minimum tap target size: 48px (WCAG AAA compliant)
 */
export const spacing = {
  // Touch targets
  touchTarget: 48,       // px - Minimum interactive element size
  touchGap: 8,           // px - Minimum gap between touch targets

  // Layout spacing
  panelPadding: 16,      // px - Standard panel padding
  panelGap: 16,          // px - Gap between panels
  cardPadding: 24,       // px - Card internal padding
  cardGap: 12,           // px - Gap between cards

  // Component spacing
  iconSize: {
    sm: 16,
    md: 24,
    lg: 32,
    xl: 48,
  },
} as const

/**
 * Typography Tokens
 *
 * Font sizes optimized for kiosk display (readable from 2-3 feet away).
 * These are defined in tailwind.config.js and should be accessed via Tailwind classes.
 *
 * Available sizes:
 * - kiosk-sm: 1rem (16px)
 * - kiosk-base: 1.125rem (18px)
 * - kiosk-lg: 1.5rem (24px)
 * - kiosk-xl: 2rem (32px)
 * - kiosk-2xl: 3rem (48px)
 * - kiosk-3xl: 4rem (64px)
 */
export const typography = {
  fontSize: {
    sm: '1rem',
    base: '1.125rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '3rem',
    '3xl': '4rem',
  },
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  lineHeight: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.75,
  },
} as const

/**
 * Border Radius Tokens
 *
 * Consistent border radius for rounded corners.
 */
export const borderRadius = {
  sm: 8,   // px - Small radius (buttons, badges)
  md: 12,  // px - Medium radius (cards)
  lg: 16,  // px - Large radius (panels)
  xl: 24,  // px - Extra large radius (modals)
  full: 9999, // px - Fully rounded (circles)
} as const

/**
 * Animation Durations
 *
 * Standard animation timings for consistent motion.
 */
export const animation = {
  duration: {
    fast: 150,    // ms - Quick transitions (hover states)
    normal: 300,  // ms - Standard transitions (panel changes)
    slow: 500,    // ms - Slow transitions (page transitions)
  },
  easing: {
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
} as const

/**
 * Breakpoints
 *
 * Responsive breakpoints (though kiosk is typically fixed resolution).
 */
export const breakpoints = {
  sm: 640,   // px
  md: 768,   // px
  lg: 1024,  // px
  xl: 1280,  // px
  '2xl': 1536, // px
} as const

/**
 * Z-Index Layers
 *
 * Consistent z-index layering to prevent overlap issues.
 */
export const zIndex = {
  base: 0,
  dropdown: 10,
  overlay: 20,
  modal: 30,
  popover: 40,
  toast: 50,
  tooltip: 60,
} as const

/**
 * Helper function to get voice state color
 */
export function getVoiceStateColor(state: keyof typeof colors.voiceState): string {
  return colors.voiceState[state] || colors.voiceState.idle
}

/**
 * Helper function to get entity state color
 */
export function getEntityStateColor(state: 'on' | 'off' | 'unavailable' | 'unknown'): string {
  return colors.entityState[state] || colors.entityState.unknown
}

/**
 * Type exports for TypeScript autocomplete
 */
export type VoiceState = keyof typeof colors.voiceState
export type EntityState = keyof typeof colors.entityState
export type IconSize = keyof typeof spacing.iconSize
