// Display panel registry - maps action types to components

import { ComponentType } from 'react'
import { DisplayPanelProps } from '../types'
import DefaultDisplayPanel from './DefaultDisplayPanel'
import LightControlPanel from './LightControlPanel'
import LightControlDetailedPanel from './LightControlDetailedPanel'
import MediaControlPanel from './MediaControlPanel'
import SearchResultsPanel from './SearchResultsPanel'
import WebViewPanel from './WebViewPanel'
import TimeDisplayPanel from './TimeDisplayPanel'
import HomeDataPanel from './HomeDataPanel'
import EntityDetailPanel from './EntityDetailPanel'
import ResearchResultsPanel from './ResearchResultsPanel'

// Panel registry mapping action type to component
const DISPLAY_PANELS: Record<string, ComponentType<DisplayPanelProps>> = {
  default: DefaultDisplayPanel,
  web_view: WebViewPanel,
  light_control: LightControlPanel,
  light_control_detailed: LightControlDetailedPanel,
  media_control: MediaControlPanel,
  search_results: SearchResultsPanel,
  get_time: TimeDisplayPanel,
  get_home_data: HomeDataPanel,
  get_entity: EntityDetailPanel,
  research_results: ResearchResultsPanel,
}

/**
 * Get the appropriate display panel component for an action type
 * Falls back to default panel if type is not found
 */
export function getDisplayPanel(actionType: string): ComponentType<DisplayPanelProps> {
  return DISPLAY_PANELS[actionType] || DISPLAY_PANELS.default
}

export {
  DefaultDisplayPanel,
  LightControlPanel,
  LightControlDetailedPanel,
  MediaControlPanel,
  SearchResultsPanel,
  WebViewPanel,
  TimeDisplayPanel,
  HomeDataPanel,
  EntityDetailPanel,
  ResearchResultsPanel,
}
