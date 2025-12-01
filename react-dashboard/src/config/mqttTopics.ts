/**
 * MQTT topic configuration with versioning support.
 *
 * Phase 5: MQTT Decoupling
 * - Centralized topic structure
 * - Versioning support (v1/ prefix)
 * - Environment variable configuration
 */

export interface MQTTTopicConfig {
  version: string
  basePrefix: string
}

export class MQTTTopics {
  private config: MQTTTopicConfig

  constructor(config?: Partial<MQTTTopicConfig>) {
    this.config = {
      version: import.meta.env.VITE_MQTT_TOPIC_VERSION || 'v1',
      basePrefix: import.meta.env.VITE_MQTT_BASE_PREFIX || 'voice_assistant',
      ...config,
    }
  }

  private base(roomId: string, sessionId: string): string {
    return `${this.config.version}/${this.config.basePrefix}/room/${roomId}/session/${sessionId}`
  }

  // State topics
  state(roomId: string, sessionId: string): string {
    return `${this.base(roomId, sessionId)}/state`
  }

  // Transcript topics
  transcript(roomId: string, sessionId: string): string {
    return `${this.base(roomId, sessionId)}/transcript`
  }

  transcriptInterim(roomId: string, sessionId: string): string {
    return `${this.base(roomId, sessionId)}/transcript/interim`
  }

  transcriptFinal(roomId: string, sessionId: string): string {
    return `${this.base(roomId, sessionId)}/transcript/final`
  }

  transcriptRefined(roomId: string, sessionId: string): string {
    return `${this.base(roomId, sessionId)}/transcript/refined`
  }

  // Response topics
  response(roomId: string, sessionId: string): string {
    return `${this.base(roomId, sessionId)}/response`
  }

  responseStreamStart(roomId: string, sessionId: string): string {
    return `${this.base(roomId, sessionId)}/response/stream/start`
  }

  responseStreamChunk(roomId: string, sessionId: string): string {
    return `${this.base(roomId, sessionId)}/response/stream/chunk`
  }

  responseStreamComplete(roomId: string, sessionId: string): string {
    return `${this.base(roomId, sessionId)}/response/stream/complete`
  }

  // Display action
  displayAction(roomId: string, sessionId: string): string {
    return `${this.base(roomId, sessionId)}/display_action`
  }

  // Tool executed
  toolExecuted(roomId: string, sessionId: string): string {
    return `${this.base(roomId, sessionId)}/tool_executed`
  }

  // Overlay hint
  overlayHint(roomId: string, sessionId: string): string {
    return `${this.base(roomId, sessionId)}/overlay_hint`
  }

  // Subscription patterns (wildcards)
  subscribeAllSessions(roomId: string): string {
    return `${this.config.version}/${this.config.basePrefix}/room/${roomId}/session/+/#`
  }

  subscribeSession(roomId: string, sessionId: string): string {
    return `${this.base(roomId, sessionId)}/#`
  }

  // Legacy v0 topics (for backward compatibility during migration)
  private legacyBase(roomId: string, sessionId: string): string {
    return `${this.config.basePrefix}/room/${roomId}/session/${sessionId}`
  }

  legacyDisplayAction(roomId: string, sessionId: string): string {
    return `${this.legacyBase(roomId, sessionId)}/display_action`
  }

  subscribeLegacySessions(roomId: string): string {
    return `${this.config.basePrefix}/room/${roomId}/session/+/#`
  }
}

// Singleton instance
export const mqttTopics = new MQTTTopics()
