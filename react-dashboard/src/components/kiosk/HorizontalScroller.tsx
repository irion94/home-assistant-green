import { useRef, useEffect, useCallback, ReactNode } from 'react'

interface HorizontalScrollerProps {
  children: ReactNode
  initialOffset?: number
  resetTimeout?: number
  className?: string
}

export default function HorizontalScroller({
  children,
  initialOffset = 0,
  resetTimeout = 15000,
  className = '',
}: HorizontalScrollerProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const timeoutRef = useRef<number | null>(null)
  const initialOffsetRef = useRef<number>(initialOffset)

  // Scroll to initial offset on mount
  useEffect(() => {
    if (scrollRef.current && initialOffsetRef.current > 0) {
      scrollRef.current.scrollLeft = initialOffsetRef.current
    }
  }, [])

  // Reset scroll position to initial offset
  const resetScroll = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        left: initialOffsetRef.current,
        behavior: 'smooth',
      })
    }
  }, [])

  // Clear existing timeout and set new one
  const resetTimer = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    timeoutRef.current = window.setTimeout(resetScroll, resetTimeout)
  }, [resetScroll, resetTimeout])

  // Handle user interaction
  const handleInteraction = useCallback(() => {
    resetTimer()
  }, [resetTimer])

  // Set up event listeners
  useEffect(() => {
    const element = scrollRef.current
    if (!element) return

    // Start initial timer
    resetTimer()

    // Touch and scroll events
    element.addEventListener('touchstart', handleInteraction)
    element.addEventListener('touchmove', handleInteraction)
    element.addEventListener('scroll', handleInteraction)
    element.addEventListener('mousedown', handleInteraction)

    return () => {
      element.removeEventListener('touchstart', handleInteraction)
      element.removeEventListener('touchmove', handleInteraction)
      element.removeEventListener('scroll', handleInteraction)
      element.removeEventListener('mousedown', handleInteraction)
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [handleInteraction, resetTimer])

  // Update initial offset if it changes
  useEffect(() => {
    initialOffsetRef.current = initialOffset
  }, [initialOffset])

  return (
    <div
      ref={scrollRef}
      className={`flex overflow-x-auto overflow-y-hidden h-screen w-screen scrollbar-hide ${className}`}
      style={{
        scrollSnapType: 'x mandatory',
        WebkitOverflowScrolling: 'touch',
      }}
    >
      {children}
    </div>
  )
}

// Helper to calculate panel offset for initial scroll position
export function calculatePanelOffset(panelIndex: number, panelWidths: number[]): number {
  let offset = 0
  for (let i = 0; i < panelIndex && i < panelWidths.length; i++) {
    offset += panelWidths[i]
  }
  return offset
}
