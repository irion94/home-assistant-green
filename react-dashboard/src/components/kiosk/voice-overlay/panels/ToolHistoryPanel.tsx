/**
 * ToolHistoryPanel - Tool execution history
 *
 * Displays recent tool executions with timestamps and results.
 * Shows tool name, arguments, and execution status.
 */

import { Clock, CheckCircle, XCircle } from 'lucide-react';
import { useVoiceStore } from '../../../../stores/voiceStore';

interface ToolExecution {
  id: string;
  toolName: string;
  arguments: Record<string, any>;
  result: string;
  success: boolean;
  timestamp: number;
}

export default function ToolHistoryPanel() {
  // For Phase 4, we'll show conversation messages as a proxy for tool history
  // In Phase 5, this could be enhanced with actual tool execution tracking
  const messages = useVoiceStore(state => state.messages);

  // Extract tool-like messages (assistant responses that indicate actions)
  const toolMessages = messages
    .filter(m => m.type === 'assistant' && m.text)
    .slice(-10) // Last 10 messages
    .reverse(); // Most recent first

  if (toolMessages.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-white/50 text-sm">
        No tool executions yet
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {toolMessages.map((message, index) => (
        <ToolHistoryItem
          key={message.timestamp}
          execution={{
            id: `${message.timestamp}-${index}`,
            toolName: 'conversation',
            arguments: {},
            result: message.text,
            success: !message.text.toLowerCase().includes('error'),
            timestamp: message.timestamp,
          }}
        />
      ))}
    </div>
  );
}

function ToolHistoryItem({ execution }: { execution: ToolExecution }) {
  const timeAgo = getTimeAgo(execution.timestamp);

  return (
    <div className="p-3 rounded-lg bg-white/5 border border-white/10">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {execution.success ? (
            <CheckCircle className="w-4 h-4 text-green-400" />
          ) : (
            <XCircle className="w-4 h-4 text-red-400" />
          )}
          <span className="text-sm font-medium text-white">
            {execution.toolName}
          </span>
        </div>
        <div className="flex items-center gap-1 text-xs text-white/50">
          <Clock className="w-3 h-3" />
          <span>{timeAgo}</span>
        </div>
      </div>

      {/* Result */}
      <p className="text-sm text-white/70 line-clamp-2">{execution.result}</p>
    </div>
  );
}

function getTimeAgo(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);

  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
