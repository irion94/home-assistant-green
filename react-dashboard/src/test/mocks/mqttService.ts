import { vi } from 'vitest'

export const mockMqttService = {
  connect: vi.fn().mockResolvedValue(undefined),
  disconnect: vi.fn(),
  publish: vi.fn(),
  subscribe: vi.fn(),
  unsubscribe: vi.fn(),
  startSession: vi.fn(),
  stopSession: vi.fn(),
  setRoomId: vi.fn(),
  isConnected: vi.fn().mockReturnValue(true),
}

vi.mock('@/services/mqttService', () => ({
  default: mockMqttService,
  mqttService: mockMqttService,
}))
