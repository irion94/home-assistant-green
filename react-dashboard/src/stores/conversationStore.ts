/**
 * Conversation Store - Messages and Streaming State
 *
 * Phase 6: Split from monolithic voiceStore for better performance.
 * Handles conversation messages, streaming responses, and session state.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { VoiceMessage, STTComparison } from '../services/mqttService'

export interface ConversationMessage {
  id: string
  type: 'user' | 'assistant'
  text: string
  timestamp: number
  sttEngine?: string
  isStreaming?: boolean
}

interface ConversationState {
  // Message state
  messages: ConversationMessage[]
  sessionId: string | null
  conversationMode: boolean
  lastComparison: STTComparison | null

  // Streaming state
  isStreaming: boolean
  streamingContent: string
  streamingSequence: number
  streamingStartedAt: number | null

  // Message actions
  addMessage: (message: ConversationMessage) => void
  addTranscript: (voiceMessage: VoiceMessage) => void
  addResponse: (voiceMessage: VoiceMessage) => void
  clearMessages: () => void
  setLastComparison: (comparison: STTComparison | null) => void

  // Streaming actions
  startStreaming: () => void
  appendStreamingToken: (token: string, sequence: number) => void
  finishStreaming: (fullText: string) => void
  cancelStreaming: () => void

  // Session actions
  setSessionId: (id: string | null) => void
  setConversationMode: (enabled: boolean) => void
}

export const useConversationStore = create<ConversationState>()(
  persist(
    (set) => ({
      // Initial state
      messages: [],
      sessionId: null,
      conversationMode: false,
      lastComparison: null,
      isStreaming: false,
      streamingContent: '',
      streamingSequence: 0,
      streamingStartedAt: null,

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

        set((state) => ({
          isStreaming: true,
          streamingContent: '',
          streamingSequence: 0,
          streamingStartedAt: timestamp,
          messages: [...state.messages, {
            id: `assistant-${timestamp}`,
            type: 'assistant',
            text: '',
            timestamp,
            isStreaming: true
          }]
        }))
      },

      appendStreamingToken: (token, sequence) => {
        set((state) => {
          if (!state.isStreaming) return state

          const newContent = state.streamingContent + token
          const updatedMessages = state.messages.map((msg, idx) => {
            if (idx === state.messages.length - 1 && msg.isStreaming) {
              return { ...msg, text: newContent }
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
          const updatedMessages = state.messages.map((msg, idx) => {
            if (idx === state.messages.length - 1 && msg.isStreaming) {
              return { ...msg, text: fullText, isStreaming: false }
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
        set((state) => ({
          isStreaming: false,
          streamingContent: '',
          streamingSequence: 0,
          streamingStartedAt: null,
          messages: state.messages.filter(msg => !msg.isStreaming)
        }))
      },

      // Session actions
      setSessionId: (id) => set({ sessionId: id }),
      setConversationMode: (enabled) => set({ conversationMode: enabled }),
    }),
    {
      name: 'conversation-store',
      partialize: (state) => ({
        conversationMode: state.conversationMode
      })
    }
  )
)

// Optimized selectors
export const useMessages = () => useConversationStore((state) => state.messages)
export const useSessionId = () => useConversationStore((state) => state.sessionId)
export const useIsStreaming = () => useConversationStore((state) => state.isStreaming)
export const useStreamingContent = () => useConversationStore((state) => state.streamingContent)
export const useConversationMode = () => useConversationStore((state) => state.conversationMode)
export const useLastComparison = () => useConversationStore((state) => state.lastComparison)
