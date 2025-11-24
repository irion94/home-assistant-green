import { NavLink } from 'react-router-dom'
import { Home, Lightbulb, Thermometer, Activity, Mic } from 'lucide-react'
import { classNames } from '../../utils/formatters'

const navItems = [
  { to: '/', icon: Home, label: 'Home' },
  { to: '/lights', icon: Lightbulb, label: 'Lights' },
  { to: '/climate', icon: Thermometer, label: 'Climate' },
  { to: '/sensors', icon: Activity, label: 'Sensors' },
  { to: '/voice', icon: Mic, label: 'Voice' },
]

export default function Navigation() {
  return (
    <nav className="flex items-center justify-around bg-surface border-t border-surface-light py-2 safe-area-inset">
      {navItems.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            classNames(
              'flex flex-col items-center gap-1 px-4 py-2 rounded-xl transition-colors min-w-[64px]',
              isActive
                ? 'text-primary bg-primary/10'
                : 'text-text-secondary hover:text-text-primary hover:bg-surface-light'
            )
          }
        >
          <Icon className="w-6 h-6" />
          <span className="text-xs font-medium">{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
