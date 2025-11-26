import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { HomeAssistantProvider } from './hooks/useHomeAssistant'
import { ApiProvider } from './components/ApiProvider'
import KioskHome from './pages/KioskHome'

function App() {
  return (
    <ApiProvider>
      {/* Keep HomeAssistantProvider for backward compatibility during migration */}
      <HomeAssistantProvider>
        <BrowserRouter>
          <Routes>
            {/* Horizontal kiosk layout with panels */}
            <Route path="/kiosk" element={<KioskHome />} />
            <Route path="/" element={<KioskHome />} />
          </Routes>
        </BrowserRouter>
      </HomeAssistantProvider>
    </ApiProvider>
  )
}

export default App
