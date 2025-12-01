/**
 * QuickActionsPanel - One-click command buttons
 *
 * Provides quick access to common commands without voice input.
 * Sends text commands to AI Gateway via voiceStore.
 */

import { Lightbulb, LightbulbOff, Cloud, Moon, Coffee, Clock, Home, MapPin } from 'lucide-react';
import { useVoiceStore } from '../../../../stores/voiceStore';

interface QuickActionsPanelProps {
  roomId?: string;
}

interface QuickAction {
  label: string;
  command: string;
  icon: React.ReactNode;
  description?: string;
}

const GLOBAL_ACTIONS: QuickAction[] = [
  {
    label: 'Current Time',
    command: 'Która godzina?',
    icon: <Clock className="w-5 h-5" />,
    description: 'Test get_time tool',
  },
  {
    label: 'Home Status',
    command: 'Pokaż stan domu',
    icon: <Home className="w-5 h-5" />,
    description: 'Test get_home_data tool',
  },
  {
    label: 'Living Room',
    command: 'Włącz światła w salonie',
    icon: <Lightbulb className="w-5 h-5" />,
    description: 'Test light_control_detailed tool',
  },
  {
    label: 'Nearby Bars',
    command: 'Sprawdź najbliższe bary',
    icon: <MapPin className="w-5 h-5" />,
    description: 'Test research_local tool',
  },
  {
    label: 'Weather',
    command: "What's the weather?",
    icon: <Cloud className="w-5 h-5" />,
    description: 'Test web_search tool',
  },
  {
    label: 'All Lights Off',
    command: 'Turn off all lights',
    icon: <LightbulbOff className="w-5 h-5" />,
    description: 'Turn off all lights',
  },
  {
    label: 'Good Night',
    command: 'Good night routine',
    icon: <Moon className="w-5 h-5" />,
    description: 'Activate night mode',
  },
  {
    label: 'Good Morning',
    command: 'Good morning routine',
    icon: <Coffee className="w-5 h-5" />,
    description: 'Activate morning routine',
  },
];

export default function QuickActionsPanel({ roomId }: QuickActionsPanelProps) {
  const addMessage = useVoiceStore((state) => state.addMessage);
  const sessionId = useVoiceStore((state) => state.sessionId);
  const setSessionId = useVoiceStore((state) => state.setSessionId);

  const handleAction = async (action: QuickAction) => {
    try {
      // Generate or use existing session ID
      const effectiveSessionId = sessionId || `quick-${Date.now()}`;
      const effectiveRoomId = roomId || 'salon';

      // Set session ID if not already set (for display actions)
      if (!sessionId) {
        setSessionId(effectiveSessionId);
      }

      // Add user message
      addMessage({
        id: `user-${Date.now()}`,
        type: 'user',
        text: action.command,
        timestamp: Date.now(),
      });

      console.log(`[QuickActions] Sending command to /conversation (session=${effectiveSessionId}, room=${effectiveRoomId})`);

      // Send command to AI Gateway
      const response = await fetch(`${import.meta.env.VITE_GATEWAY_URL}/conversation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: action.command,
          session_id: effectiveSessionId,
          room_id: effectiveRoomId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log(`[QuickActions] Response received:`, data);

      // Add assistant response
      addMessage({
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        text: data.text || 'Done',  // Backend returns 'text' field, not 'response'
        timestamp: Date.now(),
      });
    } catch (error) {
      console.error('[QuickActions] Error:', error);
      addMessage({
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        text: 'Sorry, I could not complete that action.',
        timestamp: Date.now(),
      });
    }
  };

  return (
    <div className="grid grid-cols-2 gap-2">
      {GLOBAL_ACTIONS.map(action => (
        <button
          key={action.label}
          onClick={() => handleAction(action)}
          className="
            flex flex-col items-center gap-2 p-4 rounded-lg
            bg-white/5 hover:bg-white/10
            border border-white/10 hover:border-white/20
            transition-all duration-200
            group
          "
          title={action.description}
        >
          <div className="text-primary group-hover:scale-110 transition-transform">
            {action.icon}
          </div>
          <span className="text-sm text-white text-center">{action.label}</span>
        </button>
      ))}
    </div>
  );
}
