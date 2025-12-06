import { motion } from 'framer-motion'
import { MapPin, ExternalLink } from 'lucide-react'
import { DisplayPanelProps } from '../types'

interface ResearchResult {
  title: string
  url: string
  description: string
}

export default function ResearchResultsPanel({ action }: DisplayPanelProps) {
  const data = action.data as {
    query: string
    location?: string | null
    results: ResearchResult[]
    map_url: string
  }
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="p-6 space-y-4 h-full flex flex-col"
    >
      <div className="flex items-center gap-3">
        <MapPin className="w-8 h-8 text-blue-400" />
        <div className="flex-1 min-w-0">
          <h3 className="text-xl font-semibold truncate">{data.query}</h3>
          {data.location && (
            <p className="text-sm text-gray-400 truncate">{data.location}</p>
          )}
        </div>
      </div>

      {/* Google Maps link */}
      <a
        href={data.map_url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 px-4 py-3 bg-blue-500/20 hover:bg-blue-500/30 rounded-lg transition-colors group"
      >
        <MapPin className="w-5 h-5 text-blue-400" />
        <span className="flex-1">Otwórz w Google Maps</span>
        <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" />
      </a>

      {/* Results list */}
      <div className="flex-1 overflow-y-auto space-y-3 scrollbar-hide">
        {data.results && data.results.length > 0 ? (
          data.results.map((result, idx) => (
            <motion.a
              key={idx}
              href={result.url}
              target="_blank"
              rel="noopener noreferrer"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="block p-4 bg-white/5 hover:bg-white/10 rounded-lg transition-colors group"
            >
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold mb-1 group-hover:text-blue-400 transition-colors">
                    {result.title}
                  </h4>
                  <p className="text-sm text-gray-400 line-clamp-2">
                    {result.description}
                  </p>
                  <div className="text-xs text-gray-500 mt-2 truncate">
                    {new URL(result.url).hostname}
                  </div>
                </div>
                <ExternalLink className="w-4 h-4 text-gray-400 flex-shrink-0 mt-1 group-hover:text-blue-400 transition-colors" />
              </div>
            </motion.a>
          ))
        ) : (
          <div className="text-center text-gray-400 py-8">
            Nie znaleziono wyników
          </div>
        )}
      </div>

      {/* Results count */}
      {data.results && data.results.length > 0 && (
        <div className="text-xs text-gray-500 text-center">
          Znaleziono {data.results.length} wynik{data.results.length === 1 ? '' : 'ów'}
        </div>
      )}
    </motion.div>
  )
}
