import { Play, Pause, SkipForward, SkipBack, Volume2, X } from 'lucide-react'
import { motion } from 'framer-motion'
import { DisplayPanelProps, MediaControlData } from '../types'

export default function MediaControlPanel({ action, onClose }: DisplayPanelProps) {
  const data = action.data as MediaControlData

  const isPlaying = data.state === 'playing'
  const volume = data.volume_level !== undefined ? Math.round(data.volume_level * 100) : 50

  // Format duration/position to MM:SS
  const formatTime = (seconds?: number) => {
    if (seconds === undefined || seconds === null) return '--:--'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const progress = data.media_duration && data.media_position
    ? (data.media_position / data.media_duration) * 100
    : 0

  return (
    <div className="flex flex-col h-full bg-black/20 backdrop-blur-md">
      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-black/30 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Volume2 className="w-5 h-5 text-primary" />
          <span className="font-medium text-text-primary">Media Player</span>
        </div>
        {onClose && (
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded transition-colors" title="Close">
            <X className="w-5 h-5 text-text-secondary hover:text-text-primary" />
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 p-6 flex flex-col items-center justify-center space-y-6">
        {/* Artwork */}
        {data.artwork_url ? (
          <motion.img
            src={data.artwork_url}
            alt="Album artwork"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="w-48 h-48 rounded-lg shadow-2xl object-cover"
          />
        ) : (
          <div className="w-48 h-48 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
            <Volume2 className="w-24 h-24 text-primary/30" />
          </div>
        )}

        {/* Now Playing Info */}
        <div className="text-center space-y-1 max-w-md">
          {data.media_title && (
            <motion.h3
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="text-xl font-bold text-text-primary truncate"
            >
              {data.media_title}
            </motion.h3>
          )}
          {data.media_artist && (
            <motion.p
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="text-sm text-text-secondary truncate"
            >
              {data.media_artist}
            </motion.p>
          )}
          {data.media_album && (
            <motion.p
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="text-xs text-text-secondary/70 truncate"
            >
              {data.media_album}
            </motion.p>
          )}
        </div>

        {/* Progress Bar */}
        {data.media_duration !== undefined && data.media_duration > 0 && (
          <div className="w-full max-w-md space-y-1">
            <div className="h-1 bg-gray-700 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-primary"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
            <div className="flex justify-between text-xs text-text-secondary">
              <span>{formatTime(data.media_position)}</span>
              <span>{formatTime(data.media_duration)}</span>
            </div>
          </div>
        )}

        {/* Playback Controls */}
        <div className="flex items-center gap-4">
          <button
            className="p-3 hover:bg-white/10 rounded-full transition-colors"
            title="Previous"
            disabled
          >
            <SkipBack className="w-5 h-5 text-text-secondary" />
          </button>

          <button
            className="p-4 bg-primary hover:bg-primary/80 rounded-full transition-colors"
            title={isPlaying ? 'Pause' : 'Play'}
            disabled
          >
            {isPlaying ? (
              <Pause className="w-6 h-6 text-white fill-white" />
            ) : (
              <Play className="w-6 h-6 text-white fill-white" />
            )}
          </button>

          <button
            className="p-3 hover:bg-white/10 rounded-full transition-colors"
            title="Next"
            disabled
          >
            <SkipForward className="w-5 h-5 text-text-secondary" />
          </button>
        </div>

        {/* Volume Control */}
        <div className="w-full max-w-md space-y-2">
          <div className="flex items-center justify-between text-xs text-text-secondary">
            <span>Volume</span>
            <span className="font-mono">{volume}%</span>
          </div>
          <div className="flex items-center gap-3">
            <Volume2 className="w-4 h-4 text-text-secondary" />
            <input
              type="range"
              min="0"
              max="100"
              value={volume}
              disabled
              className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
            />
          </div>
        </div>
      </div>

      {/* Footer Status */}
      <div className="p-3 bg-black/30 border-t border-white/10">
        <div className="flex items-center justify-between text-xs text-text-secondary">
          <span>State: {data.state}</span>
          <span className="truncate ml-2">{data.entity_id}</span>
        </div>
      </div>

      <style>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: #3b82f6;
          cursor: pointer;
        }

        .slider::-moz-range-thumb {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: #3b82f6;
          cursor: pointer;
          border: none;
        }
      `}</style>
    </div>
  )
}
