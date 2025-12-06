/**
 * Zustand store for centralized voice assistant state management.
 *
 * This resolves the callback conflict issue (Bug 11) where both KioskHome
 * and VoiceOverlay were competing to set MQTT callbacks, causing race
 * conditions and lost messages.
 *
 * With Zustand:
 * - MQTT service writes directly to the store
 * - Components subscribe to store slices they need
 * - No callback conflicts, no stale closures
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { VoiceState, STTComparison, VoiceMessage } from '../services/mqttService'
import { DisplayAction } from '../components/kiosk/voice-overlay/types'

export interface ConversationMessage {
  id: string
  type: 'user' | 'assistant'
  text: string
  timestamp: number
  sttEngine?: string
  isStreaming?: boolean  // True while tokens are being received
}

export type DebugLogType = 'STATE' | 'MQTT' | 'TIMING' | 'ERROR'

export interface DebugLogEntry {
  id: string
  timestamp: Date
  type: DebugLogType
  message: string
}

const MAX_DEBUG_LOGS = 100

interface VoiceStore {
  // Session state
  sessionId: string | null
  state: VoiceState
  messages: ConversationMessage[]
  conversationMode: boolean
  lastComparison: STTComparison | null

  // Streaming state
  isStreaming: boolean
  streamingContent: string
  streamingSequence: number
  streamingStartedAt: number | null

  // Connection state
  mqttConnected: boolean
  roomId: string

  // UI state
  overlayOpen: boolean
  startSessionOnOpen: boolean
  triggerState: VoiceState

  // Debug state
  debugEnabled: boolean
  debugLogs: DebugLogEntry[]

  // Display action state
  displayAction: DisplayAction | null

  // Left panel state
  leftPanelVisible: boolean
  activeTool: string | null
  autoCloseTimerId: NodeJS.Timeout | null

  // Hybrid STT state
  hybridSTTEnabled: boolean
  browserSTTAvailable: boolean

  // Actions - Session
  setSessionId: (sessionId: string | null) => void
  setVoiceState: (state: VoiceState) => void
  setConversationMode: (enabled: boolean) => void

  // Actions - Messages
  addMessage: (message: ConversationMessage) => void
  addTranscript: (voiceMessage: VoiceMessage) => void
  addResponse: (voiceMessage: VoiceMessage) => void
  clearMessages: () => void
  setLastComparison: (comparison: STTComparison | null) => void

  // Actions - Streaming
  startStreaming: () => void
  appendStreamingToken: (token: string, sequence: number) => void
  finishStreaming: (fullText: string) => void
  cancelStreaming: () => void

  // Actions - Connection
  setMqttConnected: (connected: boolean) => void
  setRoomId: (roomId: string) => void

  // Actions - UI
  openOverlay: (startSession: boolean, initialState?: VoiceState) => void
  closeOverlay: () => void

  // Actions - Session lifecycle
  endSession: () => void

  // Actions - Debug
  addDebugLog: (type: DebugLogType, message: string) => void
  clearDebugLogs: () => void
  toggleDebug: () => void

  // Actions - Display
  setDisplayAction: (action: DisplayAction | null) => void
  clearDisplayAction: () => void

  // Actions - Left Panel
  showLeftPanel: (toolType: string) => void
  hideLeftPanel: () => void
  setAutoCloseTimer: (timerId: NodeJS.Timeout | null) => void

  // Actions - Hybrid STT
  setHybridSTTEnabled: (enabled: boolean) => void
  setBrowserSTTAvailable: (available: boolean) => void
}

export const useVoiceStore = create<VoiceStore>()(
  persist(
    (set, get) => ({
      // Initial state
      sessionId: null,
      state: 'idle',
      messages: [],
      conversationMode: false,
      lastComparison: null,
      isStreaming: false,
      streamingContent: '',
      streamingSequence: 0,
      streamingStartedAt: null,
      mqttConnected: false,
      roomId: 'salon', // Default room
      overlayOpen: false,
      startSessionOnOpen: false,
      triggerState: 'idle',
      debugEnabled: false,
      debugLogs: [],
      displayAction: null,
      leftPanelVisible: false,
      activeTool: null,
      autoCloseTimerId: null,
      hybridSTTEnabled: true, // Enable by default in kiosk mode
      browserSTTAvailable: false, // Will be set by useRemoteSTT hook

      // Session actions
      setSessionId: (sessionId) => set({ sessionId }),

      setVoiceState: (state) => {
        const { overlayOpen, messages, conversationMode, isStreaming, closeOverlay } = get()

        // Auto-close in single-command mode when returning to idle with messages
        // BUT: Don't close if streaming is active (response is still being received)
        if (state === 'idle' && messages.length > 0 && !conversationMode && overlayOpen && !isStreaming) {
          // Delay close to show final state
          setTimeout(() => {
            closeOverlay()
          }, 3000)
        }

        set({ state })
      },

      setConversationMode: (enabled) => set({ conversationMode: enabled }),

      // Message actions
      addMessage: (message) => set((state) => ({
        messages: [...state.messages, message]
      })),

      addTranscript: (voiceMessage) => set((state) => ({
        messages: [...state.messages, {
          id: `user-${voiceMessage.timestamp}`,
          type: 'user' as const,
          text: voiceMessage.text,
          timestamp: voiceMessage.timestamp
        }]
      })),

      addResponse: (voiceMessage) => set((state) => ({
        messages: [...state.messages, {
          id: `assistant-${voiceMessage.timestamp}`,
          type: 'assistant' as const,
          text: voiceMessage.text,
          timestamp: voiceMessage.timestamp
        }]
      })),

      clearMessages: () => set({ messages: [], lastComparison: null }),

      setLastComparison: (comparison) => set({ lastComparison: comparison }),

      // Streaming actions
      startStreaming: () => {
        const timestamp = Date.now()

        // Create new streaming message
        const streamingMessage: ConversationMessage = {
          id: `assistant-${timestamp}`,
          type: 'assistant',
          text: '',
          timestamp,
          isStreaming: true
        }

        set((state) => ({
          isStreaming: true,
          streamingContent: '',
          streamingSequence: 0,
          streamingStartedAt: timestamp,
          messages: [...state.messages, streamingMessage]
        }))
      },

      appendStreamingToken: (token, sequence) => {
        set((state) => {
          if (!state.isStreaming) {
            return state // Ignore tokens if not streaming
          }

          const newContent = state.streamingContent + token

          // Update the last message (which should be the streaming one)
          const updatedMessages = state.messages.map((msg, idx) => {
            if (idx === state.messages.length - 1 && msg.isStreaming) {
              return {
                ...msg,
                text: newContent
              }
            }
            return msg
          })

          return {
            streamingContent: newContent,
            streamingSequence: sequence,
            messages: updatedMessages
          }
        })
      },

      finishStreaming: (fullText) => {
        set((state) => {
          // Mark streaming message as complete
          const updatedMessages = state.messages.map((msg, idx) => {
            if (idx === state.messages.length - 1 && msg.isStreaming) {
              return {
                ...msg,
                text: fullText,
                isStreaming: false
              }
            }
            return msg
          })

          return {
            isStreaming: false,
            streamingContent: '',
            streamingSequence: 0,
            streamingStartedAt: null,
            messages: updatedMessages
          }
        })
      },

      cancelStreaming: () => {
        set((state) => {
          // Remove incomplete streaming message
          const filteredMessages = state.messages.filter(msg => !msg.isStreaming)

          return {
            isStreaming: false,
            streamingContent: '',
            streamingSequence: 0,
            streamingStartedAt: null,
            messages: filteredMessages
          }
        })
      },

      // Connection actions
      setMqttConnected: (connected) => set({ mqttConnected: connected }),

      setRoomId: (roomId) => {
        localStorage.setItem('roomId', roomId)
        set({ roomId })
      },

      // UI actions
      openOverlay: (startSession, initialState = 'idle') => {
        set({
          overlayOpen: true,
          startSessionOnOpen: startSession,
          triggerState: initialState,
          // Show left panel with default tabs when overlay opens
          leftPanelVisible: true,
          activeTool: 'default',
          // Reset state for new session if starting from button
          ...(startSession ? { state: 'idle', lastComparison: null } : {})
        })
      },

      closeOverlay: () => set({
        overlayOpen: false,
        startSessionOnOpen: false,
        triggerState: 'idle',
        // Hide left panel when overlay closes
        leftPanelVisible: false,
        activeTool: null,
        autoCloseTimerId: null
      }),

      // Session lifecycle
      endSession: () => {
        const { overlayOpen } = get()

        // Close overlay after short delay when session ends
        if (overlayOpen) {
          setTimeout(() => {
            set({
              overlayOpen: false,
              startSessionOnOpen: false,
              triggerState: 'idle',
              sessionId: null,
              state: 'idle'
            })
          }, 1500)
        }

        set({ sessionId: null, state: 'idle' })
      },

      // Debug actions
      addDebugLog: (type, message) => set((state) => {
        const newLog: DebugLogEntry = {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
          timestamp: new Date(),
          type,
          message
        }
        // Keep only last MAX_DEBUG_LOGS entries
        const logs = [...state.debugLogs, newLog].slice(-MAX_DEBUG_LOGS)
        return { debugLogs: logs }
      }),

      clearDebugLogs: () => set({ debugLogs: [] }),

      toggleDebug: () => set((state) => ({ debugEnabled: !state.debugEnabled })),

      // Display actions
      setDisplayAction: (action) => {
        get().addDebugLog('MQTT', `display_action: ${action?.type ?? 'null'}`)

        // Show left panel when display action is received (atomic update)
        if (action && action.type !== 'default') {
          // Clear existing timer
          const currentTimer = get().autoCloseTimerId
          if (currentTimer) clearTimeout(currentTimer)

          // Atomic update of all related state
          set({
            displayAction: action,
            leftPanelVisible: true,
            activeTool: action.type,
            autoCloseTimerId: null
          })
          get().addDebugLog('STATE', `Left panel opened: ${action.type}`)
        } else {
          // Just update displayAction if it's default/null
          set({ displayAction: action })
        }
      },

      clearDisplayAction: () => set({ displayAction: null }),

      // Left panel actions
      showLeftPanel: (toolType) => {
        // Clear existing timer
        const currentTimer = get().autoCloseTimerId
        if (currentTimer) clearTimeout(currentTimer)

        set({
          leftPanelVisible: true,
          activeTool: toolType,
          autoCloseTimerId: null
        })
        get().addDebugLog('STATE', `Left panel opened: ${toolType}`)
      },

      hideLeftPanel: () => {
        // Clear timer
        const currentTimer = get().autoCloseTimerId
        if (currentTimer) clearTimeout(currentTimer)

        set({
          leftPanelVisible: false,
          activeTool: null,
          autoCloseTimerId: null
        })
        get().addDebugLog('STATE', 'Left panel closed')
      },

      setAutoCloseTimer: (timerId) => set({ autoCloseTimerId: timerId }),

      // Hybrid STT actions
      setHybridSTTEnabled: (enabled) => set({ hybridSTTEnabled: enabled }),
      setBrowserSTTAvailable: (available) => set({ browserSTTAvailable: available })
    }),
    {
      name: 'voice-store',
      // Only persist these fields
      partialize: (state) => ({
        roomId: state.roomId,
        conversationMode: state.conversationMode,
        debugEnabled: state.debugEnabled
      })
    }
  )
)

// Selector hooks for performance (avoid re-renders on unrelated state changes)
export const useVoiceState = () => useVoiceStore((state) => state.state)
export const useSessionId = () => useVoiceStore((state) => state.sessionId)
export const useMessages = () => useVoiceStore((state) => state.messages)
export const useConversationMode = () => useVoiceStore((state) => state.conversationMode)
export const useIsStreaming = () => useVoiceStore((state) => state.isStreaming)
export const useStreamingContent = () => useVoiceStore((state) => state.streamingContent)
export const useMqttConnected = () => useVoiceStore((state) => state.mqttConnected)
export const useRoomId = () => useVoiceStore((state) => state.roomId)
export const useOverlayOpen = () => useVoiceStore((state) => state.overlayOpen)
export const useLastComparison = () => useVoiceStore((state) => state.lastComparison)
export const useDebugEnabled = () => useVoiceStore((state) => state.debugEnabled)
export const useDebugLogs = () => useVoiceStore((state) => state.debugLogs)
export const useDisplayAction = () => useVoiceStore((state) => state.displayAction)
