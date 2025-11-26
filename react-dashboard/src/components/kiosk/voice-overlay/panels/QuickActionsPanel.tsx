/**
 * QuickActionsPanel - One-click command buttons
 *
 * Provides quick access to common commands without voice input.
 * Sends text commands to AI Gateway via voiceStore.
 */

import { Lightbulb, LightbulbOff, Cloud, Thermometer, Moon, Coffee } from 'lucide-react';
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
    label: 'All Lights On',
    command: 'Turn on all lights',
    icon: <Lightbulb className="w-5 h-5" />,
    description: 'Turn on all lights in the house',
  },
  {
    label: 'All Lights Off',
    command: 'Turn off all lights',
    icon: <LightbulbOff className="w-5 h-5" />,
    description: 'Turn off all lights',
  },
  {
    label: 'Weather',
    command: "What's the weather?",
    icon: <Cloud className="w-5 h-5" />,
    description: 'Get current weather conditions',
  },
  {
    label: 'Temperature',
    command: "What's the temperature?",
    icon: <Thermometer className="w-5 h-5" />,
    description: 'Get indoor/outdoor temperature',
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
  const addMessage = useVoiceStore(state => state.addMessage);
  const sessionId = useVoiceStore(state => state.sessionId);

  const handleAction = async (action: QuickAction) => {
    try {
      // Add user message
      addMessage({
        id: `user-${Date.now()}`,
        type: 'user',
        text: action.command,
        timestamp: Date.now(),
      });

      // Send command to AI Gateway
      const response = await fetch(`${import.meta.env.VITE_GATEWAY_URL}/conversation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: action.command,
          session_id: sessionId || 'quick-action',
          room_id: roomId || 'salon',
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      // Add assistant response
      addMessage({
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        text: data.response || 'Done',
        timestamp: Date.now(),
      });
    } catch (error) {
      console.error('Quick action error:', error);
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
