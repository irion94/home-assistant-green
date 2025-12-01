/**
 * Device Store - MQTT and Display Action State
 *
 * Phase 6: Split from monolithic voiceStore for better performance.
 * Handles MQTT connection state, room configuration, and display actions.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { DisplayAction } from '../components/kiosk/voice-overlay/types'

interface DeviceState {
  // Connection state
  mqttConnected: boolean
  roomId: string

  // Display action state
  displayAction: DisplayAction | null

  // Actions
  setMqttConnected: (connected: boolean) => void
  setRoomId: (roomId: string) => void
  setDisplayAction: (action: DisplayAction | null) => void
  clearDisplayAction: () => void
}

export const useDeviceStore = create<DeviceState>()(
  persist(
    (set) => ({
      // Initial state
      mqttConnected: false,
      roomId: 'salon',
      displayAction: null,

      // Actions
      setMqttConnected: (connected) => set({ mqttConnected: connected }),

      setRoomId: (roomId) => {
        localStorage.setItem('roomId', roomId)
        set({ roomId })
      },

      setDisplayAction: (action) => {
        // Import uiStore to log and manage left panel
        const uiStore = require('./uiStore').useUIStore.getState()
        uiStore.addDebugLog('MQTT', `display_action: ${action?.type ?? 'null'}`)

        // Show left panel when display action is received
        if (action && action.type !== 'default') {
          const currentTimer = uiStore.autoCloseTimerId
          if (currentTimer) clearTimeout(currentTimer)

          set({ displayAction: action })
          uiStore.showLeftPanel(action.type)
        } else {
          set({ displayAction: action })
        }
      },

      clearDisplayAction: () => set({ displayAction: null }),
    }),
    {
      name: 'device-store',
      partialize: (state) => ({
        roomId: state.roomId
      })
    }
  )
)

// Optimized selectors
export const useMqttConnected = () => useDeviceStore((state) => state.mqttConnected)
export const useRoomId = () => useDeviceStore((state) => state.roomId)
export const useDisplayAction = () => useDeviceStore((state) => state.displayAction)
