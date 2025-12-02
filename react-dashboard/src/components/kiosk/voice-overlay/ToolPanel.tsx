/**
 * ToolPanel - Main container for interactive tool dashboard (Phase 4)
 *
 * 4-tab interface:
 * - Quick Actions: One-click command buttons (default)
 * - Entities: Real-time entity states by domain
 * - History: Tool execution history
 * - Debug: Terminal-style debug logs
 */

import { useState } from 'react';
import EntityStatesPanel from './panels/EntityStatesPanel';
import QuickActionsPanel from './panels/QuickActionsPanel';
import ToolHistoryPanel from './panels/ToolHistoryPanel';
import { DebugLogPanel } from '../DebugLogPanel';

type TabType = 'actions' | 'entities' | 'history' | 'debug';

interface ToolPanelProps {
  roomId?: string;
  className?: string;
}

export default function ToolPanel({ roomId, className = '' }: ToolPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>('actions');

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Tab Switcher */}
      <div className="flex border-b border-white/10">
        <TabButton
          active={activeTab === 'actions'}
          onClick={() => setActiveTab('actions')}
        >
          Quick Actions
        </TabButton>
        <TabButton
          active={activeTab === 'entities'}
          onClick={() => setActiveTab('entities')}
        >
          Entities
        </TabButton>
        <TabButton
          active={activeTab === 'history'}
          onClick={() => setActiveTab('history')}
        >
          History
        </TabButton>
        <TabButton
          active={activeTab === 'debug'}
          onClick={() => setActiveTab('debug')}
        >
          Debug
        </TabButton>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto scrollbar-hide p-3">
        {activeTab === 'actions' && <QuickActionsPanel roomId={roomId} />}
        {activeTab === 'entities' && <EntityStatesPanel roomId={roomId} />}
        {activeTab === 'history' && <ToolHistoryPanel />}
        {activeTab === 'debug' && <DebugLogPanel />}
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        flex-1 px-4 py-2 text-sm font-medium transition-colors
        ${
          active
            ? 'text-white bg-white/10 border-b-2 border-primary'
            : 'text-white/60 hover:text-white/80 hover:bg-white/5'
        }
      `}
    >
      {children}
    </button>
  );
}
