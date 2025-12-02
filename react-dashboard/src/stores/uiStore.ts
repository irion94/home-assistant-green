/**
 * UI Store - Voice State and Panel Management
 *
 * Phase 6: Split from monolithic voiceStore for better performance.
 * Handles voice state, overlay visibility, left panel state, and debug features.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { VoiceState } from '../services/mqttService'
import { useConversationStore } from './conversationStore'

export type DebugLogType = 'STATE' | 'MQTT' | 'TIMING' | 'ERROR'

export interface DebugLogEntry {
  id: string
  timestamp: Date
  type: DebugLogType
  message: string
}

const MAX_DEBUG_LOGS = 100

interface UIState {
  // Voice state
  state: VoiceState
  overlayOpen: boolean
  startSessionOnOpen: boolean
  triggerState: VoiceState

  // Left panel state
  leftPanelVisible: boolean
  activeTool: string | null
  autoCloseTimerId: NodeJS.Timeout | null

  // Debug state
  debugEnabled: boolean
  debugLogs: DebugLogEntry[]

  // Hybrid STT state
  hybridSTTEnabled: boolean
  browserSTTAvailable: boolean

  // Voice state actions
  setVoiceState: (state: VoiceState) => void

  // Overlay actions
  openOverlay: (startSession: boolean, initialState?: VoiceState) => void
  closeOverlay: () => void
  endSession: () => void

  // Left panel actions
  showLeftPanel: (toolType: string) => void
  hideLeftPanel: () => void
  setAutoCloseTimer: (timerId: NodeJS.Timeout | null) => void

  // Debug actions
  addDebugLog: (type: DebugLogType, message: string) => void
  clearDebugLogs: () => void
  toggleDebug: () => void

  // Hybrid STT actions
  setHybridSTTEnabled: (enabled: boolean) => void
  setBrowserSTTAvailable: (available: boolean) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      // Initial state
      state: 'idle',
      overlayOpen: false,
      startSessionOnOpen: false,
      triggerState: 'idle',
      leftPanelVisible: false,
      activeTool: null,
      autoCloseTimerId: null,
      debugEnabled: false,
      debugLogs: [],
      hybridSTTEnabled: true,
      browserSTTAvailable: false,

      // Voice state actions
      setVoiceState: (state) => {
        // Import from conversationStore to avoid circular dependency
        const conversationStore = useConversationStore.getState()
        const { messages, conversationMode, isStreaming } = conversationStore
        const { overlayOpen, closeOverlay } = get()

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

      // Overlay actions
      openOverlay: (startSession, initialState = 'idle') => {
        set({
          overlayOpen: true,
          startSessionOnOpen: startSession,
          triggerState: initialState,
          leftPanelVisible: true,
          activeTool: 'default',
          ...(startSession ? { state: 'idle' } : {})
        })

        // Clear messages if starting new session
        if (startSession) {
          const conversationStore = useConversationStore.getState()
          conversationStore.clearMessages()
          conversationStore.setLastComparison(null)
        }
      },

      closeOverlay: () => {
        const currentTimer = get().autoCloseTimerId
        if (currentTimer) clearTimeout(currentTimer)

        set({
          overlayOpen: false,
          startSessionOnOpen: false,
          triggerState: 'idle',
          leftPanelVisible: false,
          activeTool: null,
          autoCloseTimerId: null
        })
      },

      endSession: () => {
        const { overlayOpen } = get()

        // Close overlay after short delay when session ends
        if (overlayOpen) {
          setTimeout(() => {
            const conversationStore = useConversationStore.getState()
            conversationStore.setSessionId(null)

            set({
              overlayOpen: false,
              startSessionOnOpen: false,
              triggerState: 'idle',
              state: 'idle'
            })
          }, 1500)
        } else {
          const conversationStore = useConversationStore.getState()
          conversationStore.setSessionId(null)
          set({ state: 'idle' })
        }
      },

      // Left panel actions
      showLeftPanel: (toolType) => {
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

      // Debug actions
      addDebugLog: (type, message) => set((state) => {
        const newLog: DebugLogEntry = {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
          timestamp: new Date(),
          type,
          message
        }
        const logs = [...state.debugLogs, newLog].slice(-MAX_DEBUG_LOGS)
        return { debugLogs: logs }
      }),

      clearDebugLogs: () => set({ debugLogs: [] }),

      toggleDebug: () => set((state) => ({ debugEnabled: !state.debugEnabled })),

      // Hybrid STT actions
      setHybridSTTEnabled: (enabled) => set({ hybridSTTEnabled: enabled }),
      setBrowserSTTAvailable: (available) => set({ browserSTTAvailable: available })
    }),
    {
      name: 'ui-store',
      partialize: (state) => ({
        debugEnabled: state.debugEnabled
      })
    }
  )
)

// Optimized selectors
export const useVoiceState = () => useUIStore((state) => state.state)
export const useOverlayOpen = () => useUIStore((state) => state.overlayOpen)
export const useLeftPanelVisible = () => useUIStore((state) => state.leftPanelVisible)
export const useActiveTool = () => useUIStore((state) => state.activeTool)
export const useDebugEnabled = () => useUIStore((state) => state.debugEnabled)
export const useDebugLogs = () => useUIStore((state) => state.debugLogs)
export const useStartSessionOnOpen = () => useUIStore((state) => state.startSessionOnOpen)
export const useTriggerState = () => useUIStore((state) => state.triggerState)
