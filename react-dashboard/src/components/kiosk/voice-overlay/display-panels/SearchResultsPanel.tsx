import { Search, ExternalLink, X } from 'lucide-react'
import { motion } from 'framer-motion'
import { DisplayPanelProps, SearchResultsData } from '../types'

export default function SearchResultsPanel({ action, onClose }: DisplayPanelProps) {
  const data = action.data as SearchResultsData
  const { query, results } = data

  if (!results || results.length === 0) {
    return (
      <div className="p-4 bg-black/20 backdrop-blur-md border-b border-white/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Search className="w-5 h-5 text-primary" />
            <h3 className="text-lg font-semibold">No results found for "{query}"</h3>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 rounded-full bg-white/5 hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 bg-black/20 backdrop-blur-md border-b border-white/10 max-h-[50vh] overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 sticky top-0 bg-black/20 backdrop-blur-md pb-2 border-b border-white/10">
        <div className="flex items-center gap-3">
          <Search className="w-5 h-5 text-primary" />
          <div>
            <h3 className="text-lg font-semibold">Search Results</h3>
            <p className="text-sm text-text-secondary">"{query}"</p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-2 rounded-full bg-white/5 hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Results list */}
      <div className="space-y-3">
        {results.map((result, idx) => (
          <motion.a
            key={idx}
            href={result.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-3 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 hover:border-primary/30 transition-all cursor-pointer group"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
              delay: idx * 0.05,
              type: "spring",
              stiffness: 300,
              damping: 25
            }}
          >
            <div className="flex justify-between gap-3">
              <div className="flex-1 min-w-0">
                <h4 className="text-base font-medium text-primary group-hover:text-primary-dark line-clamp-1">
                  {result.title}
                </h4>
                <p className="text-sm text-text-secondary line-clamp-2 mt-1">
                  {result.snippet}
                </p>
                <p className="text-xs text-text-secondary/60 mt-2 truncate">
                  {new URL(result.url).hostname}
                </p>
              </div>
              <ExternalLink className="w-4 h-4 text-text-secondary flex-shrink-0 group-hover:text-primary transition-colors" />
            </div>
          </motion.a>
        ))}
      </div>
    </div>
  )
}
