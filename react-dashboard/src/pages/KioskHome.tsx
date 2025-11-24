import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import HorizontalScroller from '../components/kiosk/HorizontalScroller'
import KioskPanel from '../components/kiosk/KioskPanel'
import MenuPanel from '../components/kiosk/panels/MenuPanel'
import HomePanel from '../components/kiosk/panels/HomePanel'
import LightPanel from '../components/kiosk/panels/LightPanel'
import SensorsPanel from '../components/kiosk/panels/SensorsPanel'
import VoicePanel from '../components/kiosk/panels/VoicePanel'
import MediaPanel from '../components/kiosk/panels/MediaPanel'
import { LIGHTS } from '../config/entities'

// Panel width configurations (in viewport width units)
const PANEL_WIDTHS = {
  menu: 80,      // 80vw
  home: 50,      // 50vw - half screen for Time/Weather
  light: 40,     // 40vw per light
  sensors: 80,   // 80vw
  voice: 80,     // 80vw
  media: 80,     // 80vw
}

export default function KioskHome() {
  const navigate = useNavigate()
  const [initialOffset, setInitialOffset] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)

  // Get all light entities
  const lights = Object.entries(LIGHTS)

  // Calculate initial offset to position at Home panel (index 1, after Menu)
  useEffect(() => {
    // Menu is at index 0, Home is at index 1
    // Initial offset = width of Menu panel
    const menuWidthPx = (PANEL_WIDTHS.menu / 100) * window.innerWidth
    setInitialOffset(menuWidthPx)
  }, [])

  const handleNavigate = (path: string) => {
    navigate(path)
  }

  return (
    <div ref={containerRef} className="h-screen w-screen bg-background">
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

        {/* Panels 2-8: Lights */}
        {lights.map(([key, light]) => (
          <KioskPanel key={key} width={`${PANEL_WIDTHS.light}vw`}>
            <LightPanel
              entityId={light.entity_id}
              name={light.name}
            />
          </KioskPanel>
        ))}

        {/* Panel 9: Sensors */}
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
    </div>
  )
}
