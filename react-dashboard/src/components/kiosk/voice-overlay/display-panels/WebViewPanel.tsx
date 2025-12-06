import { Globe, ExternalLink, X } from 'lucide-react'
import { DisplayPanelProps } from '../types'

interface WebViewData {
  url: string
  title?: string
}

export default function WebViewPanel({ action, onClose }: DisplayPanelProps) {
  const data = action.data as WebViewData

  return (
    <div className="flex flex-col h-full bg-black/20 backdrop-blur-md">
      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-black/30 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Globe className="w-5 h-5 text-primary" />
          <span className="font-medium text-text-primary">
            {data.title || 'Web View'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={data.url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 hover:bg-white/10 rounded transition-colors"
            title="Open in new tab"
          >
            <ExternalLink className="w-4 h-4 text-text-secondary hover:text-text-primary" />
          </a>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded transition-colors"
              title="Close"
            >
              <X className="w-5 h-5 text-text-secondary hover:text-text-primary" />
            </button>
          )}
        </div>
      </div>

      {/* Iframe Container */}
      <div className="flex-1 relative">
        <iframe
          src={data.url}
          className="absolute inset-0 w-full h-full border-0"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          title={data.title || 'Web View'}
          loading="lazy"
        />
      </div>
    </div>
  )
}
