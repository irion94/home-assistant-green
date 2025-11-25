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

export interface ConversationMessage {
  id: string
  type: 'user' | 'assistant'
  text: string
  timestamp: number
  sttEngine?: string
}

interface VoiceStore {
  // Session state
  sessionId: string | null
  state: VoiceState
  messages: ConversationMessage[]
  conversationMode: boolean
  lastComparison: STTComparison | null

  // Connection state
  mqttConnected: boolean
  roomId: string

  // UI state
  overlayOpen: boolean
  startSessionOnOpen: boolean
  triggerState: VoiceState

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

  // Actions - Connection
  setMqttConnected: (connected: boolean) => void
  setRoomId: (roomId: string) => void

  // Actions - UI
  openOverlay: (startSession: boolean, initialState?: VoiceState) => void
  closeOverlay: () => void

  // Actions - Session lifecycle
  endSession: () => void
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
      mqttConnected: false,
      roomId: 'salon', // Default room
      overlayOpen: false,
      startSessionOnOpen: false,
      triggerState: 'idle',

      // Session actions
      setSessionId: (sessionId) => set({ sessionId }),

      setVoiceState: (state) => {
        const { overlayOpen, messages, conversationMode, closeOverlay } = get()

        // Auto-close in single-command mode when returning to idle with messages
        if (state === 'idle' && messages.length > 0 && !conversationMode && overlayOpen) {
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
          // Reset state for new session if starting from button
          ...(startSession ? { state: 'idle', lastComparison: null } : {})
        })
      },

      closeOverlay: () => set({
        overlayOpen: false,
        startSessionOnOpen: false,
        triggerState: 'idle'
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
      }
    }),
    {
      name: 'voice-store',
      // Only persist these fields
      partialize: (state) => ({
        roomId: state.roomId,
        conversationMode: state.conversationMode
      })
    }
  )
)

// Selector hooks for performance (avoid re-renders on unrelated state changes)
export const useVoiceState = () => useVoiceStore((state) => state.state)
export const useSessionId = () => useVoiceStore((state) => state.sessionId)
export const useMessages = () => useVoiceStore((state) => state.messages)
export const useConversationMode = () => useVoiceStore((state) => state.conversationMode)
export const useMqttConnected = () => useVoiceStore((state) => state.mqttConnected)
export const useRoomId = () => useVoiceStore((state) => state.roomId)
export const useOverlayOpen = () => useVoiceStore((state) => state.overlayOpen)
export const useLastComparison = () => useVoiceStore((state) => state.lastComparison)
