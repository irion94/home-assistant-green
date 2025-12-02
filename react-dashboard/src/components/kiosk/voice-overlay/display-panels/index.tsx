/**
 * Display panel registry - auto-registers panels with configuration.
 *
 * Phase 3: Eliminates switch statements by using PanelRegistry pattern.
 */

import { ComponentType, lazy } from 'react'
import { DisplayPanelProps } from '../types'
import { panelRegistry } from './registry'

// Import default panel and DataDisplayPanel eagerly (frequently used)
import DefaultDisplayPanel from './DefaultDisplayPanel'
import DataDisplayPanel from './DataDisplayPanel'

// Lazy load all other panels for code splitting
const LightControlPanel = lazy(() => import('./LightControlPanel'))
const LightControlDetailedPanel = lazy(() => import('./LightControlDetailedPanel'))
const MediaControlPanel = lazy(() => import('./MediaControlPanel'))
const SearchResultsPanel = lazy(() => import('./SearchResultsPanel'))
const WebViewPanel = lazy(() => import('./WebViewPanel'))
const TimeDisplayPanel = lazy(() => import('./TimeDisplayPanel'))
const HomeDataPanel = lazy(() => import('./HomeDataPanel'))
const EntityDetailPanel = lazy(() => import('./EntityDetailPanel'))
const ResearchResultsPanel = lazy(() => import('./ResearchResultsPanel'))

// Register all panels with auto-close timeouts
// This runs at module load time
panelRegistry.register({
  type: 'default',
  component: DefaultDisplayPanel,
  autoCloseTimeout: null,
  title: 'Voice Assistant',
  description: 'Default voice interaction panel'
})

panelRegistry.register({
  type: 'web_view',
  component: WebViewPanel,
  autoCloseTimeout: null, // Never auto-close (user interaction)
  title: 'Web View',
  description: 'Display websites in iframe'
})

panelRegistry.register({
  type: 'light_control',
  component: LightControlPanel,
  autoCloseTimeout: 10000, // 10s
  title: 'Light Control',
  description: 'Basic light controls'
})

panelRegistry.register({
  type: 'light_control_detailed',
  component: LightControlDetailedPanel,
  autoCloseTimeout: 10000, // 10s
  title: 'Light Control (Detailed)',
  description: 'Control lights with sliders and color'
})

panelRegistry.register({
  type: 'media_control',
  component: MediaControlPanel,
  autoCloseTimeout: null, // Never auto-close (user interaction)
  title: 'Media Control',
  description: 'Control media playback'
})

panelRegistry.register({
  type: 'search_results',
  component: SearchResultsPanel,
  autoCloseTimeout: 15000, // 15s
  title: 'Search Results',
  description: 'Web search results'
})

// Phase 4: Old panels kept for backward compatibility but not registered
// Backend now sends 'data_display' type instead of 'get_time', 'get_home_data', 'get_entity'
// Uncomment these registrations if you need to rollback to old format:
/*
panelRegistry.register({
  type: 'get_time',
  component: TimeDisplayPanel,
  autoCloseTimeout: 10000, // 10s
  title: 'Time',
  description: 'Display current time'
})

panelRegistry.register({
  type: 'get_home_data',
  component: HomeDataPanel,
  autoCloseTimeout: 10000, // 10s
  title: 'Home Data',
  description: 'Display home sensor status'
})

panelRegistry.register({
  type: 'get_entity',
  component: EntityDetailPanel,
  autoCloseTimeout: 10000, // 10s
  title: 'Entity Details',
  description: 'Display entity state'
})
*/

panelRegistry.register({
  type: 'research_results',
  component: ResearchResultsPanel,
  autoCloseTimeout: null, // Never auto-close (map link interaction)
  title: 'Local Search',
  description: 'Nearby places and businesses'
})

panelRegistry.register({
  type: 'data_display',
  component: DataDisplayPanel,
  autoCloseTimeout: 10000, // 10s
  title: 'Data Display',
  description: 'Display time, home status, or entity details (Phase 4)'
})

/**
 * Get the appropriate display panel component for an action type.
 * Uses PanelRegistry instead of switch statement.
 *
 * @param actionType Display action type identifier
 * @returns Panel component or default if not found
 */
export function getDisplayPanel(actionType: string): ComponentType<DisplayPanelProps> {
  const config = panelRegistry.get(actionType)
  if (!config) {
    console.warn(`[DisplayPanels] Panel '${actionType}' not registered, using default`)
    return DefaultDisplayPanel
  }
  return config.component
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
  DataDisplayPanel,
}
