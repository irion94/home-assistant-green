import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import VoiceOverlay from '../VoiceOverlay'
import { useVoiceStore } from '@/stores/voiceStore'

// Mock hooks
vi.mock('@/stores/voiceStore')
vi.mock('@/hooks/useBrowserTTS', () => ({
  useBrowserTTS: () => ({
    speak: vi.fn(),
    stop: vi.fn(),
  }),
}))

describe('VoiceOverlay', () => {
  it('should render when open', () => {
    vi.mocked(useVoiceStore).mockReturnValue({
      state: 'idle',
      messages: [],
      conversationMode: false,
      setVoiceState: vi.fn(),
    } as any)

    render(<VoiceOverlay isOpen={true} onClose={vi.fn()} />)

    expect(screen.getByText(/say "hey jarvis" to start/i)).toBeInTheDocument()
  })

  it('should not render when closed', () => {
    const { container } = render(<VoiceOverlay isOpen={false} onClose={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('should display chat messages', () => {
    vi.mocked(useVoiceStore).mockReturnValue({
      state: 'idle',
      messages: [
        { id: '1', type: 'user', text: 'Turn on lights', timestamp: Date.now() },
        { id: '2', type: 'assistant', text: 'Lights turned on', timestamp: Date.now() },
      ],
      conversationMode: false,
      setVoiceState: vi.fn(),
    } as any)

    render(<VoiceOverlay isOpen={true} onClose={vi.fn()} />)

    expect(screen.getByText('Turn on lights')).toBeInTheDocument()
    expect(screen.getByText('Lights turned on')).toBeInTheDocument()
  })
})
