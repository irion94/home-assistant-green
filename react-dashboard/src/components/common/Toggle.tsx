import { classNames } from '../../utils/formatters'

interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export default function Toggle({
  checked,
  onChange,
  disabled = false,
  size = 'md',
  className,
}: ToggleProps) {
  const sizeClasses = {
    sm: {
      track: 'w-10 h-6',
      thumb: 'w-4 h-4',
      translate: 'translate-x-4',
    },
    md: {
      track: 'w-14 h-8',
      thumb: 'w-6 h-6',
      translate: 'translate-x-6',
    },
    lg: {
      track: 'w-18 h-10',
      thumb: 'w-8 h-8',
      translate: 'translate-x-8',
    },
  }

  const sizes = sizeClasses[size]

  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => !disabled && onChange(!checked)}
      className={classNames(
        'relative inline-flex shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        sizes.track,
        checked ? 'bg-primary' : 'bg-surface-light',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
      disabled={disabled}
    >
      <span
        className={classNames(
          'pointer-events-none inline-block rounded-full bg-white shadow-lg transform ring-0 transition duration-200 ease-in-out',
          sizes.thumb,
          'translate-y-1 translate-x-1',
          checked && sizes.translate
        )}
      />
    </button>
  )
}
