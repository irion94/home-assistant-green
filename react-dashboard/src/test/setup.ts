import { expect, afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return []
  }
  unobserve() {}
} as any

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn()

// Mock mqttService globally
vi.mock('@/services/mqttService', () => ({
  mqttService: {
    connect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn(),
    publish: vi.fn(),
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    startSession: vi.fn(),
    stopSession: vi.fn(),
    setRoomId: vi.fn(),
    isConnected: vi.fn().mockReturnValue(true),
  },
  VoiceState: {},
}))
