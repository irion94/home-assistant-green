import { Tv, Speaker, Play, Pause, VolumeX, Volume2 } from 'lucide-react'
import { useEntity } from '../../../hooks/useEntity'
import { useHomeAssistant } from '../../../hooks/useHomeAssistant'
import { MEDIA } from '../../../config/entities'
import { classNames } from '../../../utils/formatters'

interface MediaCardProps {
  entityId: string
  name: string
  icon: 'tv' | 'speaker'
}

function MediaCard({ entityId, name, icon }: MediaCardProps) {
  const { entity, state, isAvailable } = useEntity(entityId)
  const { callService } = useHomeAssistant()

  const isPlaying = state === 'playing'
  const isIdle = state === 'idle' || state === 'off'

  const Icon = icon === 'tv' ? Tv : Speaker

  const handlePlayPause = async () => {
    if (isPlaying) {
      await callService('media_player', 'media_pause', { entity_id: entityId })
    } else {
      await callService('media_player', 'media_play', { entity_id: entityId })
    }
  }

  const handleMute = async () => {
    await callService('media_player', 'volume_mute', {
      entity_id: entityId,
      is_volume_muted: !entity?.attributes.is_volume_muted,
    })
  }

  if (!isAvailable) {
    return (
      <div className="p-4 bg-surface-light rounded-xl opacity-50">
        <div className="flex items-center gap-3">
          <Icon className="w-6 h-6 text-text-secondary" />
          <span className="font-medium">{name}</span>
        </div>
        <p className="text-sm text-text-secondary mt-2">Unavailable</p>
      </div>
    )
  }

  return (
    <div
      className={classNames(
        'p-4 bg-surface-light rounded-xl transition-all',
        isPlaying && 'bg-primary/20 border border-primary/30'
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <Icon className={classNames('w-6 h-6', isPlaying ? 'text-primary' : 'text-text-secondary')} />
          <div>
            <p className="font-medium">{name}</p>
            <p className="text-xs text-text-secondary capitalize">{state}</p>
          </div>
        </div>
      </div>

      {/* Media info */}
      {entity?.attributes.media_title && (
        <p className="text-sm text-text-secondary mb-3 truncate">
          {entity.attributes.media_title}
        </p>
      )}

      {/* Controls */}
      {!isIdle && (
        <div className="flex items-center gap-2">
          <button
            onClick={handlePlayPause}
            className="p-2 bg-background rounded-lg hover:bg-surface transition-colors"
          >
            {isPlaying ? (
              <Pause className="w-5 h-5" />
            ) : (
              <Play className="w-5 h-5" />
            )}
          </button>

          <button
            onClick={handleMute}
            className="p-2 bg-background rounded-lg hover:bg-surface transition-colors"
          >
            {entity?.attributes.is_volume_muted ? (
              <VolumeX className="w-5 h-5 text-error" />
            ) : (
              <Volume2 className="w-5 h-5" />
            )}
          </button>
        </div>
      )}
    </div>
  )
}

export default function MediaPanel() {
  return (
    <div className="h-full flex flex-col bg-surface rounded-2xl p-6">
      {/* Header */}
      <h2 className="text-kiosk-xl font-bold mb-6">Media</h2>

      {/* Media Players */}
      <div className="flex-1 space-y-4">
        <MediaCard
          entityId={MEDIA.nestHub.entity_id}
          name={MEDIA.nestHub.name}
          icon="speaker"
        />
        <MediaCard
          entityId={MEDIA.tvSalon.entity_id}
          name={MEDIA.tvSalon.name}
          icon="tv"
        />
        <MediaCard
          entityId={MEDIA.tvSypialnia.entity_id}
          name={MEDIA.tvSypialnia.name}
          icon="tv"
        />
      </div>

      {/* Footer */}
      <div className="mt-4 pt-4 border-t border-surface-light">
        <p className="text-sm text-text-secondary text-center">
          Media & Entertainment
        </p>
      </div>
    </div>
  )
}
