/**
 * PanelError - Error fallback for panel rendering failures
 *
 * Displayed when ErrorBoundary catches an error in panel components.
 */

export const PanelError = () => (
  <div className="flex items-center justify-center h-full p-4">
    <div className="text-center">
      <div className="text-red-400 text-lg mb-2">⚠️ Panel Error</div>
      <div className="text-gray-400 text-sm">Failed to load panel content</div>
    </div>
  </div>
)
