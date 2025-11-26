// Display panel registry - maps action types to components

import { ComponentType } from 'react'
import { DisplayPanelProps } from '../types'
import DefaultDisplayPanel from './DefaultDisplayPanel'
import LightControlPanel from './LightControlPanel'
import SearchResultsPanel from './SearchResultsPanel'

// WebViewPanel deferred to future enhancement
const WebViewPanel = ({ action }: DisplayPanelProps) => (
  <div className="p-4 bg-black/20 backdrop-blur-md border-b border-white/10">
    <p className="text-text-secondary">WebView (coming soon)</p>
    <p className="text-sm text-text-secondary/70 mt-2">
      URL: {action.data.url}
    </p>
  </div>
)

// Panel registry mapping action type to component
const DISPLAY_PANELS: Record<string, ComponentType<DisplayPanelProps>> = {
  default: DefaultDisplayPanel,
  web_view: WebViewPanel,
  light_control: LightControlPanel,
  search_results: SearchResultsPanel,
}

/**
 * Get the appropriate display panel component for an action type
 * Falls back to default panel if type is not found
 */
export function getDisplayPanel(actionType: string): ComponentType<DisplayPanelProps> {
  return DISPLAY_PANELS[actionType] || DISPLAY_PANELS.default
}

export { DefaultDisplayPanel, LightControlPanel, SearchResultsPanel, WebViewPanel }
