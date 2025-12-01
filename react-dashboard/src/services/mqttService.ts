/**
 * MQTT Service for connecting to voice assistant messages.
 * Subscribes to room-scoped MQTT topics for real-time updates.
 *
 * Phase 5: MQTT Decoupling
 * - Centralized topic configuration
 * - Dual v0/v1 subscription during migration
 * - Zustand integration for state management
 *
 * Topic Structure:
 * {version}/voice_assistant/room/{room_id}/session/{session_id}/
 *   ├── state               # listening/processing/speaking/waiting/idle
 *   ├── transcript          # Latest user message JSON
 *   ├── response            # Latest AI response JSON
 *   ├── display_action      # Panel switching commands
 *   └── overlay_hint        # Overlay behavior hints
 */

import mqtt, { MqttClient } from 'mqtt'
import { useVoiceStore } from '../stores/voiceStore'
import { mqttTopics } from '../config/mqttTopics'

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
   * Phase 5: Dual subscription to v1 (new) and v0 (legacy) topics during migration.
   */
  private subscribeRoom(): void {
    if (!this.client) return

    // Phase 5: Subscribe to both v1 (new) and v0 (legacy) topics
    const topics = [
      // v1 topics (new format with versioning)
      mqttTopics.subscribeAllSessions(this.roomId),

      // v0 legacy topics (backward compatibility during migration)
      mqttTopics.subscribeLegacySessions(this.roomId),
    ]

    this.client.subscribe(topics, (err) => {
      if (err) {
        console.error('[MQTT] Subscribe error:', err)
      } else {
        console.log(`[MQTT] Subscribed to room ${this.roomId} (v1 + v0 legacy)`)
      }
    })
  }

  /**
   * Unsubscribe from current room topics.
   * Phase 5: Unsubscribe from both v1 and v0 topics.
   */
  private unsubscribeRoom(): void {
    if (!this.client) return

    const topics = [
      mqttTopics.subscribeAllSessions(this.roomId),
      mqttTopics.subscribeLegacySessions(this.roomId),
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
   * Phase 5: Detect topic version (v0 legacy vs v1 new).
   */
  private handleMessage(topic: string, payload: string): void {
    try {
      // Phase 5: Detect topic version
      const isV1 = topic.startsWith('v1/')
      const isV0 = !topic.startsWith('v')

      if (isV0) {
        console.debug(`[MQTT] Received v0 topic (legacy): ${topic}`)
      }

      // Extract subtopic after room prefix (handle both v0 and v1 formats)
      const roomPrefix = isV1
        ? `v1/voice_assistant/room/${this.roomId}`
        : `voice_assistant/room/${this.roomId}`

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
      store.addDebugLog('MQTT', `session/active = ${sessionId ?? 'none'}`)
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
      const prevState = store.state
      try {
        const data = JSON.parse(payload)
        state = (data.status || data.state || 'idle') as VoiceState
      } catch {
        state = payload as VoiceState
      }

      // Debug log state transition
      store.addDebugLog('STATE', `${prevState} → ${state}`)

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

    // session/{session_id}/transcript/interim (streaming STT - Debug Panel only)
    const interimMatch = subTopic.match(/^session\/([^/]+)\/transcript\/interim$/)
    if (interimMatch) {
      try {
        const data = JSON.parse(payload)
        const text = data.text || ''
        const sequence = data.sequence || 0
        // Debug Panel only (per user preference) - not added to chat messages
        store.addDebugLog('MQTT', `[STT interim #${sequence}] "${text.slice(0, 60)}${text.length > 60 ? '...' : ''}"`)
        console.log(`[MQTT] Interim transcript [${sequence}]: "${text}"`)
      } catch (e) {
        console.error('[MQTT] Failed to parse interim transcript:', e)
      }
      return
    }

    // session/{session_id}/transcript/final (streaming STT - final result)
    const finalMatch = subTopic.match(/^session\/([^/]+)\/transcript\/final$/)
    if (finalMatch) {
      const sessionId = finalMatch[1]
      try {
        const data = JSON.parse(payload)
        const text = data.text || ''
        const confidence = data.confidence || 0
        const engine = data.engine || 'vosk'

        // Add debug log with confidence info
        store.addDebugLog('MQTT', `[STT final] "${text.slice(0, 50)}${text.length > 50 ? '...' : ''}" (${engine}, conf=${confidence.toFixed(2)})`)

        // Add to chat messages (like regular transcript)
        const message: VoiceMessage = {
          type: 'transcript',
          text: text,
          session_id: sessionId,
          timestamp: data.timestamp || Date.now(),
        }
        store.addTranscript(message)

        // Legacy callback
        this.callbacks.onTranscript?.(message)
        console.log(`[MQTT] Final transcript: "${text}" (confidence=${confidence.toFixed(2)}, engine=${engine})`)
      } catch (e) {
        console.error('[MQTT] Failed to parse final transcript:', e)
      }
      return
    }

    // session/{session_id}/transcript/refined (Whisper refinement when Vosk confidence was low)
    const refinedMatch = subTopic.match(/^session\/([^/]+)\/transcript\/refined$/)
    if (refinedMatch) {
      const sessionId = refinedMatch[1]
      try {
        const data = JSON.parse(payload)
        const text = data.text || ''

        // Debug log for refinement (includes sessionId for traceability)
        store.addDebugLog('MQTT', `[STT refined] Whisper: "${text.slice(0, 50)}${text.length > 50 ? '...' : ''}" (session=${sessionId.slice(0, 8)})`)

        // Note: Refined transcript replaces the previous final transcript
        // For now, just add to debug panel - the final transcript is already in chat
        // If we wanted to update the last message, we'd need an updateLastTranscript action
        console.log(`[MQTT] Refined transcript (Whisper) for session ${sessionId}: "${text}"`)
      } catch (e) {
        console.error('[MQTT] Failed to parse refined transcript:', e)
      }
      return
    }

    // session/{session_id}/response/stream/start (Phase 9 - streaming response start)
    const streamStartMatch = subTopic.match(/^session\/([^/]+)\/response\/stream\/start$/)
    if (streamStartMatch) {
      const sessionId = streamStartMatch[1]
      try {
        // Initialize streaming state in store
        store.startStreaming()
        store.addDebugLog('MQTT', `[Stream start] session=${sessionId.slice(0, 8)}`)
        console.log(`[MQTT] Streaming response started for session ${sessionId}`)
      } catch (e) {
        console.error('[MQTT] Failed to parse stream start:', e)
      }
      return
    }

    // session/{session_id}/response/stream/chunk (Phase 9 - streaming response token)
    const streamChunkMatch = subTopic.match(/^session\/([^/]+)\/response\/stream\/chunk$/)
    if (streamChunkMatch) {
      try {
        const data = JSON.parse(payload)
        const token = data.content || ''
        const sequence = data.sequence || 0

        // Append token to streaming message
        store.appendStreamingToken(token, sequence)

        // Debug log only every 10 tokens to avoid spam
        if (sequence % 10 === 0 || sequence === 1) {
          store.addDebugLog('MQTT', `[Stream chunk #${sequence}] "${token.slice(0, 20)}${token.length > 20 ? '...' : ''}"`)
        }
      } catch (e) {
        console.error('[MQTT] Failed to parse stream chunk:', e)
      }
      return
    }

    // session/{session_id}/response/stream/complete (Phase 9 - streaming response complete)
    const streamCompleteMatch = subTopic.match(/^session\/([^/]+)\/response\/stream\/complete$/)
    if (streamCompleteMatch) {
      try {
        const data = JSON.parse(payload)
        const fullText = data.text || ''
        const duration = data.duration || 0
        const totalTokens = data.total_tokens || 0

        // Finalize streaming message
        store.finishStreaming(fullText)
        store.addDebugLog('MQTT', `[Stream complete] ${totalTokens} tokens in ${duration.toFixed(2)}s`)
        console.log(`[MQTT] Streaming response complete: ${totalTokens} tokens in ${duration.toFixed(2)}s`)
      } catch (e) {
        console.error('[MQTT] Failed to parse stream complete:', e)
      }
      return
    }

    // session/{session_id}/display_action (Phase 12 - action-dependent display panels)
    const displayActionMatch = subTopic.match(/^session\/([^/]+)\/display_action$/)
    if (displayActionMatch) {
      try {
        const action = JSON.parse(payload)
        store.setDisplayAction(action)
        console.log(`[MQTT] Display action: ${action.type}`, action.data)
      } catch (e) {
        console.error('[MQTT] Failed to parse display_action:', e)
      }
      return
    }

    // session/{session_id}/tool_executed (Tool history tracking)
    const toolExecutedMatch = subTopic.match(/^session\/([^/]+)\/tool_executed$/)
    if (toolExecutedMatch) {
      try {
        const toolEvent = JSON.parse(payload)
        const status = toolEvent.success ? '✓' : '✗'
        const latency = toolEvent.latency_ms.toFixed(1)
        store.addDebugLog(
          'MQTT',
          `TOOL ${status} ${toolEvent.tool_name} (${latency}ms) → ${toolEvent.content || 'no result'}`
        )
        console.log(`[MQTT] Tool executed: ${toolEvent.tool_name}`, toolEvent)
      } catch (e) {
        console.error('[MQTT] Failed to parse tool_executed:', e)
      }
      return
    }

    // session/{session_id}/transcript (legacy - plain transcript without streaming info)
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
      store.addDebugLog('MQTT', `transcript = "${message.text.slice(0, 50)}${message.text.length > 50 ? '...' : ''}"`)
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
      store.addDebugLog('MQTT', `response = "${message.text.slice(0, 50)}${message.text.length > 50 ? '...' : ''}"`)
      // Legacy callback
      this.callbacks.onResponse?.(message)
      return
    }

    // session/{session_id}/ended
    const endedMatch = subTopic.match(/^session\/([^/]+)\/ended$/)
    if (endedMatch) {
      const sessionId = endedMatch[1]
      store.addDebugLog('MQTT', `session/ended = ${sessionId}`)
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
      store.addDebugLog('MQTT', `conversation_mode = ${enabled}`)
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
      store.addDebugLog('TIMING', `STT: vosk=${comparison.vosk.duration.toFixed(2)}s, whisper=${comparison.whisper.duration.toFixed(2)}s → ${comparison.selected}`)
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
    console.log(`[MQTT] publish called: topic=${topic}, connected=${this.client?.connected}`)
    if (!this.client?.connected) {
      console.warn('[MQTT] Not connected, cannot publish')
      return
    }

    this.client.publish(topic, payload)
    console.log(`[MQTT] Message published to ${topic}`)
  }

  /**
   * Publish to room-scoped topic.
   * Phase 5: Uses v1 topic format.
   */
  private publishRoom(subTopic: string, payload: string): void {
    const topic = `v1/voice_assistant/room/${this.roomId}/${subTopic}`
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
   * Subscribe to STT request topic for hybrid STT.
   * Uses wildcard to receive requests for any session in this room.
   * @param roomId - Room identifier
   * @param callback - Callback function to handle STT requests
   */
  subscribeToSTTRequests(roomId: string, callback: (payload: any) => void): void {
    // Phase 5: Use v1 topic format for hybrid STT
    const topic = `v1/voice_assistant/room/${roomId}/session/+/stt/request`;

    this.client?.subscribe(topic, (err) => {
      if (err) {
        console.error(`[MQTT] Failed to subscribe to ${topic}:`, err);
      } else {
        console.log(`[MQTT] Subscribed to STT requests: ${topic}`);
      }
    });

    // Store handler reference for cleanup
    const messageHandler = (receivedTopic: string, message: Buffer) => {
      // Check if topic matches our wildcard pattern (v1 format)
      if (receivedTopic.startsWith(`v1/voice_assistant/room/${roomId}/session/`) &&
          receivedTopic.endsWith('/stt/request')) {
        try {
          const payload = JSON.parse(message.toString());
          console.log(`[MQTT] Received STT request:`, payload);
          callback(payload);
        } catch (error) {
          console.error('[MQTT] Failed to parse STT request:', error);
        }
      }
    };

    // Remove old handler if exists, add new one
    if (this.sttRequestHandler) {
      this.client?.off('message', this.sttRequestHandler);
    }
    this.sttRequestHandler = messageHandler;
    this.client?.on('message', messageHandler);
  }

  private sttRequestHandler?: (topic: string, message: Buffer) => void;

  /**
   * Unsubscribe from STT requests.
   * @param roomId - Room identifier
   */
  unsubscribeFromSTTRequests(roomId: string): void {
    // Phase 5: Use v1 topic format
    const topic = `v1/voice_assistant/room/${roomId}/session/+/stt/request`;

    this.client?.unsubscribe(topic, (err) => {
      if (err) {
        console.error(`[MQTT] Failed to unsubscribe from ${topic}:`, err);
      } else {
        console.log(`[MQTT] Unsubscribed from STT requests: ${topic}`);
      }
    });

    // Remove message handler
    if (this.sttRequestHandler) {
      this.client?.off('message', this.sttRequestHandler);
      this.sttRequestHandler = undefined;
    }
  }

  /**
   * Publish browser STT response.
   * @param roomId - Room identifier
   * @param sessionId - Session identifier
   * @param text - Transcribed text
   * @param confidence - Confidence score (0-1)
   */
  publishBrowserSTTResponse(roomId: string, sessionId: string, text: string, confidence: number): void {
    // Phase 5: Use v1 topic format
    const topic = `v1/voice_assistant/room/${roomId}/session/${sessionId}/stt/response`;
    const payload = {
      source: 'browser',
      text,
      confidence,
      timestamp: Date.now()
    };

    this.client?.publish(topic, JSON.stringify(payload), { qos: 1 }, (err) => {
      if (err) {
        console.error(`[MQTT] Failed to publish STT response:`, err);
      } else {
        console.log(`[MQTT] Published STT response: "${text.substring(0, 50)}..."`);
      }
    });
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
