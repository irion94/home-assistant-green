import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { classNames } from '../../utils/formatters'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'icon' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading, children, disabled, ...props }, ref) => {
    const baseClasses = 'inline-flex items-center justify-center font-medium transition-all duration-200 active:scale-95 disabled:opacity-50 disabled:pointer-events-none'

    const variantClasses = {
      primary: 'bg-primary hover:bg-primary-dark text-white rounded-xl',
      secondary: 'bg-surface-light hover:bg-surface text-text-primary rounded-xl',
      icon: 'bg-transparent hover:bg-surface-light text-text-primary rounded-full',
      ghost: 'bg-transparent hover:bg-surface-light/50 text-text-secondary hover:text-text-primary rounded-xl',
    }

    const sizeClasses = {
      sm: 'min-h-[36px] min-w-[36px] px-3 text-sm',
      md: 'min-h-touch min-w-touch px-4 text-base',
      lg: 'min-h-[56px] min-w-[56px] px-6 text-lg',
    }

    return (
      <button
        ref={ref}
        className={classNames(
          baseClasses,
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        ) : (
          children
        )}
      </button>
    )
  }
)

Button.displayName = 'Button'

export default Button
