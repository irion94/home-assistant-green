/**
 * EntityCard Component
 *
 * Generic card wrapper for entity displays.
 * Reduces all card components from 100 LOC to 20-30 LOC by providing common structure.
 *
 * Usage:
 * <EntityCard
 *   icon={<Lightbulb />}
 *   title="Living Room"
 *   subtitle="On"
 *   active={isOn}
 *   available={isAvailable}
 *   onClick={() => toggle()}
 * >
 *   <BrightnessControl value={brightness} onChange={setBrightness} />
 * </EntityCard>
 */

import { type ReactNode } from 'react'
import { Card, CardContent } from '../ui/card'
import { cn } from '../../lib/utils'

export interface EntityCardProps {
  /**
   * Icon element to display
   */
  icon: ReactNode

  /**
   * Primary title text
   */
  title: string

  /**
   * Optional subtitle text (state, value, etc.)
   */
  subtitle?: string

  /**
   * Whether the entity is in active state (on, playing, etc.)
   */
  active?: boolean

  /**
   * Whether the entity is available (not unavailable/unknown)
   */
  available?: boolean

  /**
   * Click handler for the card
   */
  onClick?: () => void

  /**
   * Optional children content (controls, details, etc.)
   */
  children?: ReactNode

  /**
   * Display variant
   * - compact: Minimal padding, small text
   * - normal: Standard card size
   * - large: Larger padding and text for kiosk
   */
  variant?: 'compact' | 'normal' | 'large'

  /**
   * Optional className for custom styling
   */
  className?: string
}

export function EntityCard({
  icon,
  title,
  subtitle,
  active = false,
  available = true,
  onClick,
  children,
  variant = 'normal',
  className,
}: EntityCardProps) {
  const isClickable = Boolean(onClick)

  return (
    <Card
      className={cn(
        'transition-all duration-150',
        // Base styling
        'bg-surface border-surface-light',
        // Active state
        active && 'bg-primary/10 border-primary/30',
        // Unavailable state
        !available && 'opacity-50',
        // Clickable
        isClickable && 'cursor-pointer hover:bg-surface-light active:scale-95',
        // Variant sizing
        variant === 'compact' && 'p-3',
        variant === 'normal' && 'p-4',
        variant === 'large' && 'p-6',
        className
      )}
      onClick={isClickable ? onClick : undefined}
    >
      <CardContent className="p-0 space-y-3">
        {/* Header: Icon + Title + Subtitle */}
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'flex items-center justify-center rounded-lg transition-colors',
              active ? 'text-primary' : 'text-text-secondary',
              variant === 'compact' && 'w-8 h-8 text-base',
              variant === 'normal' && 'w-10 h-10 text-lg',
              variant === 'large' && 'w-12 h-12 text-xl'
            )}
          >
            {icon}
          </div>
          <div className="flex-1 min-w-0">
            <h3
              className={cn(
                'font-medium text-text-primary truncate',
                variant === 'compact' && 'text-sm',
                variant === 'normal' && 'text-base',
                variant === 'large' && 'text-kiosk-lg'
              )}
            >
              {title}
            </h3>
            {subtitle && (
              <p
                className={cn(
                  'text-text-secondary truncate',
                  variant === 'compact' && 'text-xs',
                  variant === 'normal' && 'text-sm',
                  variant === 'large' && 'text-kiosk-base'
                )}
              >
                {subtitle}
              </p>
            )}
          </div>
        </div>

        {/* Optional children content */}
        {children && <div className="space-y-2">{children}</div>}
      </CardContent>
    </Card>
  )
}
