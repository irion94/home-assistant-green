/**
 * MQTT Service for connecting to voice assistant messages.
 * Subscribes to room-scoped MQTT topics for real-time updates.
 *
 * Topic Structure (Phase 4):
 * voice_assistant/room/{room_id}/
 *   ├── session/
 *   │   ├── active                  # Current session ID or "none"
 *   │   └── {session_id}/
 *   │       ├── state               # listening/processing/speaking/waiting/idle
 *   │       ├── transcript          # Latest user message JSON
 *   │       ├── response            # Latest AI response JSON
 *   │       └── ended               # Session end signal
 *   ├── command/
 *   │   ├── start                   # Start session (payload: {mode, source})
 *   │   └── stop                    # End current session
 *   └── config/
 *       └── conversation_mode       # Room preference
 *
 * Now with Zustand integration (Phase 5):
 * - Writes directly to voiceStore for centralized state management
 * - Eliminates callback conflicts between KioskHome and VoiceOverlay
 * - Callbacks still available for backward compatibility
 */

import mqtt, { MqttClient } from 'mqtt'
import { useVoiceStore } from '../stores/voiceStore'

export interface VoiceMessage {
  type: 'transcript' | 'response'
  text: string
  session_id: string
  timestamp: number
}

export interface STTComparison {
  vosk: {
    text: string
    duration: number
  }
  whisper: {
    text: string
    duration: number
  }
  selected: 'vosk' | 'whisper'
  reason: string
}

export type VoiceState =
  | 'idle'
  | 'wake_detected'
  | 'listening'
  | 'transcribing'
  | 'processing'
  | 'speaking'
  | 'waiting'

export interface SessionInfo {
  session_id: string
  room_id: string
  state: VoiceState
  conversation_mode: boolean
  started_at: number
}

export interface SessionStartPayload {
  mode: 'single' | 'multi'  // 'multi' for conversation mode (wake-word service format)
  source: 'dashboard' | 'wake_word' | 'api'
}

export interface MqttServiceCallbacks {
  onStateChange?: (state: VoiceState, session_id: string | null) => void
  onTranscript?: (message: VoiceMessage) => void
  onResponse?: (message: VoiceMessage) => void
  onSTTComparison?: (comparison: STTComparison) => void
  onConnectionChange?: (connected: boolean) => void
  onConversationModeChange?: (enabled: boolean) => void
  onSessionStart?: (session_id: string) => void
  onSessionEnd?: (session_id: string) => void
  onActiveSessionChange?: (session_id: string | null) => void
}

// Legacy status type for backward compatibility
export type AssistantStatus = 'idle' | 'listening' | 'processing' | 'speaking' | 'transcribed' | 'conversation'

class MqttService {
  private client: MqttClient | null = null
  private callbacks: MqttServiceCallbacks = {}
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private roomId: string = 'default'
  private currentSessionId: string | null = null

  /**
   * Set the room ID for topic subscriptions.
   * @param roomId - Room identifier (e.g., 'living_room', 'bedroom')
   */
  setRoomId(roomId: string): void {
    const wasConnected = this.client?.connected
    if (wasConnected) {
      // Unsubscribe from old room topics
      this.unsubscribeRoom()
    }

    this.roomId = roomId
    // Sync to store
    useVoiceStore.getState().setRoomId(roomId)
    console.log(`[MQTT] Room ID set to: ${roomId}`)

    if (wasConnected) {
      // Subscribe to new room topics
      this.subscribeRoom()
    }
  }

  /**
   * Get current room ID.
   */
  getRoomId(): string {
    return this.roomId
  }

  /**
   * Get current session ID.
   */
  getCurrentSessionId(): string | null {
    return this.currentSessionId
  }

  /**
   * Connect to MQTT broker via WebSocket.
   * @param brokerUrl - WebSocket URL (e.g., ws://localhost:9001)
   */
  connect(brokerUrl: string = 'ws://localhost:9001'): void {
    if (this.client?.connected) {
      console.log('[MQTT] Already connected')
      return
    }

    console.log(`[MQTT] Connecting to ${brokerUrl}`)

    this.client = mqtt.connect(brokerUrl, {
      clientId: `kiosk-${this.roomId}-${Date.now()}`,
      clean: true,
      reconnectPeriod: 5000,
      connectTimeout: 10000,
    })

    this.client.on('connect', () => {
      console.log('[MQTT] Connected')
      this.reconnectAttempts = 0
      // Write to store
      useVoiceStore.getState().setMqttConnected(true)
      // Legacy callback
      this.callbacks.onConnectionChange?.(true)
      this.subscribeRoom()
    })

    this.client.on('error', (error) => {
      console.error('[MQTT] Error:', error)
    })

    this.client.on('close', () => {
      console.log('[MQTT] Connection closed')
      // Write to store
      useVoiceStore.getState().setMqttConnected(false)
      // Legacy callback
      this.callbacks.onConnectionChange?.(false)
    })

    this.client.on('reconnect', () => {
      this.reconnectAttempts++
      console.log(`[MQTT] Reconnecting (attempt ${this.reconnectAttempts})`)

      if (this.reconnectAttempts > this.maxReconnectAttempts) {
        console.error('[MQTT] Max reconnection attempts reached')
        this.client?.end()
      }
    })

    this.client.on('message', (topic, payload) => {
      this.handleMessage(topic, payload.toString())
    })
  }

  /**
   * Subscribe to room-scoped voice assistant topics.
   */
  private subscribeRoom(): void {
    if (!this.client) return

    const roomPrefix = `voice_assistant/room/${this.roomId}`
    const topics = [
      // Session management (room-scoped only - no legacy topics)
      `${roomPrefix}/session/active`,
      `${roomPrefix}/session/+/state`,
      `${roomPrefix}/session/+/transcript`,
      `${roomPrefix}/session/+/response`,
      `${roomPrefix}/session/+/ended`,
      // Configuration
      `${roomPrefix}/config/conversation_mode`,
      // STT comparison (optional debug)
      `${roomPrefix}/stt_comparison`,
    ]

    this.client.subscribe(topics, (err) => {
      if (err) {
        console.error('[MQTT] Subscribe error:', err)
      } else {
        console.log(`[MQTT] Subscribed to room ${this.roomId} topics`)
      }
    })
  }

  /**
   * Unsubscribe from current room topics.
   */
  private unsubscribeRoom(): void {
    if (!this.client) return

    const roomPrefix = `voice_assistant/room/${this.roomId}`
    const topics = [
      `${roomPrefix}/session/active`,
      `${roomPrefix}/session/+/state`,
      `${roomPrefix}/session/+/transcript`,
      `${roomPrefix}/session/+/response`,
      `${roomPrefix}/session/+/ended`,
      `${roomPrefix}/config/conversation_mode`,
      `${roomPrefix}/stt_comparison`,
    ]

    this.client.unsubscribe(topics, (err) => {
      if (err) {
        console.error('[MQTT] Unsubscribe error:', err)
      } else {
        console.log(`[MQTT] Unsubscribed from room ${this.roomId} topics`)
      }
    })
  }

  /**
   * Handle incoming MQTT messages.
   */
  private handleMessage(topic: string, payload: string): void {
    try {
      const roomPrefix = `voice_assistant/room/${this.roomId}`

      // Room-scoped topics
      if (topic.startsWith(roomPrefix)) {
        const subTopic = topic.substring(roomPrefix.length + 1)
        this.handleRoomMessage(subTopic, payload)
        return
      }

      // Unknown topic - log for debugging
      console.log(`[MQTT] Unknown topic: ${topic}`)
    } catch (error) {
      console.error(`[MQTT] Error parsing message from ${topic}:`, error)
    }
  }

  /**
   * Handle room-scoped messages.
   * Writes directly to Zustand store AND calls legacy callbacks.
   */
  private handleRoomMessage(subTopic: string, payload: string): void {
    const store = useVoiceStore.getState()

    // session/active
    if (subTopic === 'session/active') {
      const sessionId = payload === 'none' ? null : payload
      this.currentSessionId = sessionId
      // Write to store
      store.setSessionId(sessionId)
      // Legacy callback
      this.callbacks.onActiveSessionChange?.(sessionId)
      console.log(`[MQTT] Active session: ${sessionId ?? 'none'}`)
      return
    }

    // session/{session_id}/state
    const stateMatch = subTopic.match(/^session\/([^/]+)\/state$/)
    if (stateMatch) {
      const sessionId = stateMatch[1]
      // State can be JSON object {"status": "listening", ...} or plain string
      let state: VoiceState
      try {
        const data = JSON.parse(payload)
        state = (data.status || data.state || 'idle') as VoiceState
      } catch {
        state = payload as VoiceState
      }

      // Write to store - this handles auto-opening overlay
      store.setVoiceState(state)

      // Auto-open overlay on voice activity (replaces KioskHome callback logic)
      const { overlayOpen } = store
      if ((state === 'wake_detected' || state === 'listening' || state === 'waiting') && !overlayOpen) {
        console.log(`[MQTT] Voice activity detected (${state}), opening overlay via store`)
        store.openOverlay(false, state)  // false = don't start session (wake-word already did)
      }

      // Legacy callback
      this.callbacks.onStateChange?.(state, sessionId)
      return
    }

    // session/{session_id}/transcript
    const transcriptMatch = subTopic.match(/^session\/([^/]+)\/transcript$/)
    if (transcriptMatch) {
      const sessionId = transcriptMatch[1]
      console.log(`[MQTT] Transcript received for session ${sessionId}:`, payload)
      let message: VoiceMessage
      try {
        const data = JSON.parse(payload)
        message = {
          type: 'transcript',
          text: data.text || payload,
          session_id: sessionId,
          timestamp: data.timestamp || Date.now(),
        }
      } catch {
        // Plain text payload
        message = {
          type: 'transcript',
          text: payload,
          session_id: sessionId,
          timestamp: Date.now(),
        }
      }
      // Write to store
      store.addTranscript(message)
      // Legacy callback
      console.log('[MQTT] Calling onTranscript callback with:', message)
      this.callbacks.onTranscript?.(message)
      return
    }

    // session/{session_id}/response
    const responseMatch = subTopic.match(/^session\/([^/]+)\/response$/)
    if (responseMatch) {
      const sessionId = responseMatch[1]
      let message: VoiceMessage
      try {
        const data = JSON.parse(payload)
        message = {
          type: 'response',
          text: data.text || payload,
          session_id: sessionId,
          timestamp: data.timestamp || Date.now(),
        }
      } catch {
        // Plain text payload
        message = {
          type: 'response',
          text: payload,
          session_id: sessionId,
          timestamp: Date.now(),
        }
      }
      // Write to store
      store.addResponse(message)
      // Legacy callback
      this.callbacks.onResponse?.(message)
      return
    }

    // session/{session_id}/ended
    const endedMatch = subTopic.match(/^session\/([^/]+)\/ended$/)
    if (endedMatch) {
      const sessionId = endedMatch[1]
      // Write to store - handles overlay close
      store.endSession()
      // Update local tracking
      if (this.currentSessionId === sessionId) {
        this.currentSessionId = null
      }
      // Legacy callback
      this.callbacks.onSessionEnd?.(sessionId)
      console.log(`[MQTT] Session ended: ${sessionId}`)
      return
    }

    // config/conversation_mode
    if (subTopic === 'config/conversation_mode') {
      const enabled = payload.toLowerCase() === 'true'
      // Write to store
      store.setConversationMode(enabled)
      // Legacy callback
      this.callbacks.onConversationModeChange?.(enabled)
      console.log(`[MQTT] Conversation mode synced: ${enabled}`)
      return
    }

    // stt_comparison
    if (subTopic === 'stt_comparison') {
      const comparison = JSON.parse(payload) as STTComparison
      // Write to store
      store.setLastComparison(comparison)
      // Legacy callback
      this.callbacks.onSTTComparison?.(comparison)
      return
    }

    console.log(`[MQTT] Unknown room topic: ${subTopic}`)
  }

  /**
   * Set callbacks for MQTT events.
   * Merges with existing callbacks instead of replacing them.
   */
  setCallbacks(callbacks: MqttServiceCallbacks): void {
    this.callbacks = { ...this.callbacks, ...callbacks }
  }

  /**
   * Clear all callbacks.
   */
  clearCallbacks(): void {
    this.callbacks = {}
  }

  /**
   * Publish a message to a topic.
   */
  publish(topic: string, payload: string): void {
    if (!this.client?.connected) {
      console.warn('[MQTT] Not connected, cannot publish')
      return
    }

    this.client.publish(topic, payload)
  }

  /**
   * Publish to room-scoped topic.
   */
  private publishRoom(subTopic: string, payload: string): void {
    const topic = `voice_assistant/room/${this.roomId}/${subTopic}`
    this.publish(topic, payload)
  }

  /**
   * Start a new voice session.
   * @param mode - 'single' for single command, 'conversation' for multi-turn
   */
  startSession(mode: 'single' | 'conversation' = 'single'): void {
    // Wake-word service expects 'multi' for conversation mode
    const payload: SessionStartPayload = {
      mode: mode === 'conversation' ? 'multi' : 'single',
      source: 'dashboard',
    }
    this.publishRoom('command/start', JSON.stringify(payload))
    console.log(`[MQTT] Starting ${mode} session in room ${this.roomId}`)
  }

  /**
   * Stop the current voice session.
   */
  stopSession(): void {
    this.publishRoom('command/stop', '')
    console.log(`[MQTT] Stopping session in room ${this.roomId}`)
  }

  /**
   * Set conversation mode (single-command vs multi-turn).
   * @param enabled - true for multi-turn conversation, false for single-command
   */
  setConversationMode(enabled: boolean): void {
    this.publishRoom('config/conversation_mode', enabled ? 'true' : 'false')
    // Also publish to legacy topic for backward compatibility
    this.publish('voice_assistant/config/conversation_mode', enabled ? 'true' : 'false')
    console.log(`[MQTT] Conversation mode ${enabled ? 'enabled' : 'disabled'}`)
  }

  // Legacy methods for backward compatibility

  /**
   * @deprecated Use startSession('conversation') instead
   */
  startConversation(): void {
    this.startSession('conversation')
  }

  /**
   * @deprecated Use stopSession() instead
   */
  stopConversation(): void {
    this.stopSession()
  }

  /**
   * Disconnect from MQTT broker.
   */
  disconnect(): void {
    if (this.client) {
      this.client.end()
      this.client = null
      this.currentSessionId = null
      console.log('[MQTT] Disconnected')
    }
  }

  /**
   * Check if connected.
   */
  isConnected(): boolean {
    return this.client?.connected ?? false
  }
}

// Singleton instance
export const mqttService = new MqttService()
export default MqttService
