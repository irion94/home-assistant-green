import { useEffect, useState, useMemo, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Mic } from 'lucide-react'
import HorizontalScroller from '../components/kiosk/HorizontalScroller'
import KioskPanel from '../components/kiosk/KioskPanel'
import MenuPanel from '../components/kiosk/panels/MenuPanel'
import HomePanel from '../components/kiosk/panels/HomePanel'
import LightsGridPanel from '../components/kiosk/panels/LightsGridPanel'
import SensorsPanel from '../components/kiosk/panels/SensorsPanel'
import VoicePanel from '../components/kiosk/panels/VoicePanel'
import MediaPanel from '../components/kiosk/panels/MediaPanel'
import VoiceOverlay from '../components/kiosk/VoiceOverlay'
import { mqttService, VoiceState } from '../services/mqttService'

// Panel width configurations (in viewport width units)
const PANEL_WIDTHS = {
  menu: 80,       // 80vw
  home: 50,       // 50vw - half screen for Time/Weather
  lights: 80,     // 80vw - grid with all lights
  sensors: 80,    // 80vw
  voice: 80,      // 80vw
  media: 80,      // 80vw
}

export default function KioskHome() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [initialOffset, setInitialOffset] = useState(0)
  const [voiceOverlayOpen, setVoiceOverlayOpen] = useState(false)
  const [startSessionOnOpen, setStartSessionOnOpen] = useState(false)
  const [triggerState, setTriggerState] = useState<VoiceState>('idle')

  // Ref to track overlay state for callbacks (avoids stale closure)
  const voiceOverlayOpenRef = useRef(voiceOverlayOpen)
  voiceOverlayOpenRef.current = voiceOverlayOpen

  // Get room ID from URL param, env var, or localStorage (priority order)
  const roomId = useMemo(() => {
    // 1. URL parameter (?room=living_room)
    const urlRoom = searchParams.get('room')
    if (urlRoom) {
      localStorage.setItem('roomId', urlRoom)
      return urlRoom
    }
    // 2. Environment variable
    const envRoom = import.meta.env.VITE_ROOM_ID
    if (envRoom) return envRoom
    // 3. localStorage (persisted from previous URL param)
    const storedRoom = localStorage.getItem('roomId')
    if (storedRoom) return storedRoom
    // 4. Default to 'salon' (matches wake-word service ROOM_ID)
    return 'salon'
  }, [searchParams])

  // Calculate initial offset to position at Home panel (index 1, after Menu)
  useEffect(() => {
    // Menu is at index 0, Home is at index 1
    // Initial offset = width of Menu panel
    const menuWidthPx = (PANEL_WIDTHS.menu / 100) * window.innerWidth
    setInitialOffset(menuWidthPx)
  }, [])

  // Listen for wake-word detection via MQTT (stable connection, doesn't reconnect on overlay state)
  useEffect(() => {
    const mqttHost = import.meta.env.VITE_MQTT_URL || `ws://${window.location.hostname}:9001`

    // Set room ID before connecting
    mqttService.setRoomId(roomId)

    // Connect to MQTT broker
    mqttService.connect(mqttHost)

    // Set initial callback to auto-open overlay when wake-word detected
    // Note: VoiceOverlay will override this when open, but that's OK
    mqttService.setCallbacks({
      onStateChange: (state: VoiceState, _sessionId: string | null) => {
        // Open overlay when wake-word detected or listening starts
        // This works for both single-command and multi-turn modes
        // Use ref to get current overlay state (avoid stale closure)
        if ((state === 'wake_detected' || state === 'listening' || state === 'waiting') && !voiceOverlayOpenRef.current) {
          console.log(`[KioskHome] Voice activity detected (${state}), opening voice overlay`)
          setTriggerState(state)  // Pass the triggering state to overlay
          setStartSessionOnOpen(false)  // Don't start session - wake-word already did
          setVoiceOverlayOpen(true)
        }
      },
      onSessionEnd: (_sessionId: string) => {
        // Close overlay when session ends (e.g., "koniec" detected)
        console.log(`[KioskHome] Session ended, closing overlay`)
        setVoiceOverlayOpen(false)
        setTriggerState('idle')
      }
    })

    return () => {
      // Disconnect on unmount
      mqttService.disconnect()
    }
  }, [roomId])  // Only reconnect if room changes, NOT on overlay state change

  const handleNavigate = (path: string) => {
    navigate(path)
  }

  return (
    <div className="h-screen w-screen bg-background">
      <HorizontalScroller
        initialOffset={initialOffset}
        resetTimeout={15000}
      >
        {/* Panel 0: Menu (hidden to left by default) */}
        <KioskPanel width={`${PANEL_WIDTHS.menu}vw`}>
          <MenuPanel onNavigate={handleNavigate} />
        </KioskPanel>

        {/* Panel 1: Home (Time + Weather) - Initial position */}
        <KioskPanel width={`${PANEL_WIDTHS.home}vw`}>
          <HomePanel />
        </KioskPanel>

        {/* Panel 2: Lights Grid */}
        <KioskPanel width={`${PANEL_WIDTHS.lights}vw`}>
          <LightsGridPanel />
        </KioskPanel>

        {/* Panel 3: Sensors */}
        <KioskPanel width={`${PANEL_WIDTHS.sensors}vw`}>
          <SensorsPanel />
        </KioskPanel>

        {/* Panel 10: Voice */}
        <KioskPanel width={`${PANEL_WIDTHS.voice}vw`}>
          <VoicePanel />
        </KioskPanel>

        {/* Panel 11: Media */}
        <KioskPanel width={`${PANEL_WIDTHS.media}vw`}>
          <MediaPanel />
        </KioskPanel>
      </HorizontalScroller>

      {/* Floating Voice Button */}
      <button
        onClick={() => {
          setStartSessionOnOpen(true)  // Start session via MQTT when button clicked
          setVoiceOverlayOpen(true)
        }}
        className="fixed bottom-6 right-6 w-16 h-16 rounded-full bg-primary shadow-lg shadow-primary/30 flex items-center justify-center hover:bg-primary-dark transition-colors z-50"
      >
        <Mic className="w-7 h-7 text-white" />
      </button>

      {/* Voice Overlay */}
      <VoiceOverlay
        isOpen={voiceOverlayOpen}
        onClose={() => {
          setVoiceOverlayOpen(false)
          setStartSessionOnOpen(false)
          setTriggerState('idle')
        }}
        roomId={roomId}
        startOnOpen={startSessionOnOpen}
        initialState={triggerState}
      />
    </div>
  )
}
