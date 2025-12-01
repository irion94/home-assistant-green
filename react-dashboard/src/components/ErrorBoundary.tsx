import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

/**
 * ErrorBoundary component for catching React errors in panels.
 * Phase 4: Performance optimization and error handling.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('[ErrorBoundary] Panel error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="p-4 text-red-400 bg-red-900/10 rounded-lg">
            <h3 className="font-semibold mb-2">Panel Failed to Load</h3>
            <p className="text-sm text-red-300">{this.state.error?.message}</p>
          </div>
        )
      )
    }

    return this.props.children
  }
}
