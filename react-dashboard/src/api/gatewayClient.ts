import type { GatewayResponse, ConversationResponse, VoiceResponse } from '../types/api'

const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8080'

class AIGatewayClient {
  private baseUrl: string

  constructor(baseUrl: string = GATEWAY_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, '')
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Gateway error (${response.status}): ${errorText}`)
    }

    return response.json()
  }

  async sendCommand(text: string): Promise<GatewayResponse> {
    return this.fetch<GatewayResponse>('/ask', {
      method: 'POST',
      body: JSON.stringify({ text }),
    })
  }

  async conversation(text: string, sessionId?: string): Promise<ConversationResponse> {
    return this.fetch<ConversationResponse>('/conversation', {
      method: 'POST',
      body: JSON.stringify({
        text,
        session_id: sessionId,
      }),
    })
  }

  async voiceCommand(audio: Blob, sessionId?: string): Promise<VoiceResponse> {
    const formData = new FormData()
    formData.append('audio', audio, 'recording.wav')
    if (sessionId) {
      formData.append('session_id', sessionId)
    }

    const response = await fetch(`${this.baseUrl}/conversation/voice`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Gateway error (${response.status}): ${errorText}`)
    }

    return response.json()
  }

  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`)
      return response.ok
    } catch {
      return false
    }
  }
}

export const gatewayClient = new AIGatewayClient()
export default AIGatewayClient
