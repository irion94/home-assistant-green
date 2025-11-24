import { ReactNode } from 'react'
import { classNames } from '../../utils/formatters'

interface KioskPanelProps {
  children: ReactNode
  width?: string
  className?: string
  padding?: boolean
}

export default function KioskPanel({
  children,
  width = '100vw',
  className = '',
  padding = true,
}: KioskPanelProps) {
  return (
    <div
      className={classNames(
        'flex-shrink-0 h-full overflow-hidden',
        padding && 'p-4',
        className
      )}
      style={{
        width,
        scrollSnapAlign: 'start',
      }}
    >
      {children}
    </div>
  )
}
