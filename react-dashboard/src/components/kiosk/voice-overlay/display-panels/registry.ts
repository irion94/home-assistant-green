/**
 * Panel Registry for managing display panel components.
 *
 * Eliminates switch statements by providing a centralized registration system
 * for panel components with their configuration.
 *
 * Phase 3: Tool Testing & Registry implementation.
 */

import { ComponentType } from 'react'
import { DisplayAction } from '../types'

/**
 * Configuration for a display panel.
 */
export interface PanelConfig {
  /** Panel type identifier (matches DisplayAction.type) */
  type: string

  /** React component to render for this panel */
  component: ComponentType<{ action: DisplayAction; onClose?: () => void }>

  /** Auto-close timeout in milliseconds, or null to never auto-close */
  autoCloseTimeout: number | null

  /** Human-readable panel title */
  title: string

  /** Optional panel description */
  description?: string
}

/**
 * Registry for managing display panels.
 *
 * Provides centralized configuration for:
 * - Panel component mapping
 * - Auto-close timeouts
 * - Panel metadata
 *
 * Usage:
 * ```typescript
 * import { panelRegistry } from './registry'
 *
 * // Register a panel
 * panelRegistry.register({
 *   type: 'web_view',
 *   component: WebViewPanel,
 *   autoCloseTimeout: null,
 *   title: 'Web View'
 * })
 *
 * // Get panel config
 * const config = panelRegistry.get('web_view')
 * ```
 */
class PanelRegistry {
  private panels = new Map<string, PanelConfig>()

  /**
   * Register a panel with configuration.
   *
   * @param config Panel configuration
   */
  register(config: PanelConfig): void {
    if (this.panels.has(config.type)) {
      console.warn(
        `[PanelRegistry] Panel '${config.type}' already registered, overwriting`
      )
    }
    this.panels.set(config.type, config)
    console.debug(`[PanelRegistry] Registered panel: ${config.type}`)
  }

  /**
   * Get panel configuration by type.
   *
   * @param type Panel type identifier
   * @returns Panel config or undefined if not found
   */
  get(type: string): PanelConfig | undefined {
    return this.panels.get(type)
  }

  /**
   * Get auto-close timeout for a panel type.
   *
   * @param type Panel type identifier
   * @returns Timeout in ms, null for no auto-close, or 10000ms default
   */
  getAutoCloseTimeout(type: string): number | null {
    const panel = this.panels.get(type)
    if (!panel) {
      // Default timeout for unregistered panels
      return 10000
    }
    return panel.autoCloseTimeout
  }

  /**
   * Check if a panel type is registered.
   *
   * @param type Panel type identifier
   * @returns True if panel is registered
   */
  has(type: string): boolean {
    return this.panels.has(type)
  }

  /**
   * List all registered panels.
   *
   * @returns Array of all panel configurations
   */
  listPanels(): PanelConfig[] {
    return Array.from(this.panels.values())
  }

  /**
   * Clear all registered panels (primarily for testing).
   */
  clear(): void {
    this.panels.clear()
    console.debug('[PanelRegistry] Cleared all panels')
  }

  /**
   * Get count of registered panels.
   *
   * @returns Number of registered panels
   */
  size(): number {
    return this.panels.size
  }
}

/**
 * Global panel registry instance.
 *
 * Import this in panel index files to register panels at module load time.
 */
export const panelRegistry = new PanelRegistry()
