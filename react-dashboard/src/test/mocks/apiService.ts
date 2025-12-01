import { vi } from 'vitest'

export const mockApiService = {
  sendConversation: vi.fn(),
  getEntityStates: vi.fn(),
  callService: vi.fn(),
  healthCheck: vi.fn().mockResolvedValue({ status: 'ok' }),
}

vi.mock('@/services/api', () => ({
  apiService: mockApiService,
}))
