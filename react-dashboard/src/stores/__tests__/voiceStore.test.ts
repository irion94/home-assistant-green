import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useVoiceStore } from '../voiceStore'

describe('voiceStore', () => {
  beforeEach(() => {
    const { result } = renderHook(() => useVoiceStore())
    act(() => {
      result.current.clearMessages()
      result.current.setSessionId(null)
      result.current.closeOverlay()
    })
  })

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useVoiceStore())
    expect(result.current.sessionId).toBeNull()
    expect(result.current.state).toBe('idle')
    expect(result.current.messages).toEqual([])
    expect(result.current.overlayOpen).toBe(false)
  })

  it('should add user message', () => {
    const { result } = renderHook(() => useVoiceStore())

    act(() => {
      result.current.addMessage({
        id: 'msg-1',
        type: 'user',
        text: 'Test message',
        timestamp: Date.now(),
      })
    })

    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0].text).toBe('Test message')
    expect(result.current.messages[0].type).toBe('user')
  })

  it('should handle streaming state', () => {
    const { result } = renderHook(() => useVoiceStore())

    // Start streaming
    act(() => {
      result.current.startStreaming()
    })

    expect(result.current.isStreaming).toBe(true)
    expect(result.current.messages).toHaveLength(1) // Streaming message added
    expect(result.current.messages[0].isStreaming).toBe(true)

    // Append tokens
    act(() => {
      result.current.appendStreamingToken('Hello ', 1)
      result.current.appendStreamingToken('World', 2)
    })

    expect(result.current.streamingContent).toBe('Hello World')
    expect(result.current.messages[0].text).toBe('Hello World')

    // Finish streaming
    act(() => {
      result.current.finishStreaming('Hello World!')
    })

    expect(result.current.isStreaming).toBe(false)
    expect(result.current.messages[0].isStreaming).toBe(false)
    expect(result.current.messages[0].text).toBe('Hello World!')
  })

  it('should open and close overlay', () => {
    const { result } = renderHook(() => useVoiceStore())

    act(() => {
      result.current.openOverlay(true, 'listening')
    })

    expect(result.current.overlayOpen).toBe(true)
    expect(result.current.startSessionOnOpen).toBe(true)
    expect(result.current.triggerState).toBe('listening')

    act(() => {
      result.current.closeOverlay()
    })

    expect(result.current.overlayOpen).toBe(false)
  })

  it('should manage left panel visibility', () => {
    const { result } = renderHook(() => useVoiceStore())

    act(() => {
      result.current.showLeftPanel('light_control_detailed')
    })

    expect(result.current.leftPanelVisible).toBe(true)
    expect(result.current.activeTool).toBe('light_control_detailed')

    act(() => {
      result.current.hideLeftPanel()
    })

    expect(result.current.leftPanelVisible).toBe(false)
    expect(result.current.activeTool).toBeNull()
  })
})
