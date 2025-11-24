import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { HomeAssistantProvider } from './hooks/useHomeAssistant'
import KioskLayout from './components/layout/KioskLayout'
import Overview from './pages/Overview'
import Lights from './pages/Lights'
import Climate from './pages/Climate'
import Sensors from './pages/Sensors'
import VoiceAssistant from './pages/VoiceAssistant'
import KioskHome from './pages/KioskHome'

function App() {
  return (
    <HomeAssistantProvider>
      <BrowserRouter>
        <Routes>
          {/* New horizontal kiosk layout */}
          <Route path="/kiosk" element={<KioskHome />} />

          {/* Original layout with navigation */}
          <Route element={<KioskLayout />}>
            <Route path="/" element={<Overview />} />
            <Route path="/lights" element={<Lights />} />
            <Route path="/climate" element={<Climate />} />
            <Route path="/sensors" element={<Sensors />} />
            <Route path="/voice" element={<VoiceAssistant />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </HomeAssistantProvider>
  )
}

export default App
