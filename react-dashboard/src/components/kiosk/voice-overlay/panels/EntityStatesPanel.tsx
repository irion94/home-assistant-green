/**
 * EntityStatesPanel - Real-time entity states grouped by domain
 *
 * Displays Home Assistant entities with live updates via WebSocket.
 * Groups entities by domain (lights, sensors, climate, etc.)
 */

import { useLightEntities, useSensorEntities, useClimateEntities, useSwitchEntities } from '../../../../stores/entityStore';
import { Lightbulb, Thermometer, Wind, Power } from 'lucide-react';
import type { NormalizedEntity } from '../../../../stores/entityStore';

interface EntityStatesPanelProps {
  roomId?: string;
}

export default function EntityStatesPanel({ roomId }: EntityStatesPanelProps) {
  const lights = useLightEntities();
  const sensors = useSensorEntities();
  const climate = useClimateEntities();
  const switches = useSwitchEntities();

  // Filter by room if specified
  const filterByRoom = (entities: NormalizedEntity[]) => {
    if (!roomId) return entities;
    return entities.filter(e => e.room === roomId || !e.room); // Show unassigned too
  };

  const filteredLights = filterByRoom(lights);
  const filteredSensors = filterByRoom(sensors);
  const filteredClimate = filterByRoom(climate);
  const filteredSwitches = filterByRoom(switches);

  // Show message if no entities
  const hasEntities =
    filteredLights.length > 0 ||
    filteredSensors.length > 0 ||
    filteredClimate.length > 0 ||
    filteredSwitches.length > 0;

  if (!hasEntities) {
    return (
      <div className="flex items-center justify-center h-32 text-white/50 text-sm">
        {roomId ? `No entities found for room: ${roomId}` : 'No entities available'}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {filteredLights.length > 0 && (
        <EntityGroup title="Lights" entities={filteredLights} icon={<Lightbulb className="w-4 h-4" />} />
      )}
      {filteredSensors.length > 0 && (
        <EntityGroup title="Sensors" entities={filteredSensors} icon={<Thermometer className="w-4 h-4" />} />
      )}
      {filteredClimate.length > 0 && (
        <EntityGroup title="Climate" entities={filteredClimate} icon={<Wind className="w-4 h-4" />} />
      )}
      {filteredSwitches.length > 0 && (
        <EntityGroup title="Switches" entities={filteredSwitches} icon={<Power className="w-4 h-4" />} />
      )}
    </div>
  );
}

function EntityGroup({
  title,
  entities,
  icon,
}: {
  title: string;
  entities: NormalizedEntity[];
  icon: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-xs font-medium text-white/70 mb-2 flex items-center gap-2">
        {icon}
        {title} ({entities.length})
      </h3>
      <div className="space-y-1">
        {entities.slice(0, 10).map(entity => (
          <EntityRow key={entity.entity_id} entity={entity} />
        ))}
        {entities.length > 10 && (
          <p className="text-xs text-white/40 pl-2 pt-1">
            ... and {entities.length - 10} more
          </p>
        )}
      </div>
    </div>
  );
}

function EntityRow({ entity }: { entity: NormalizedEntity }) {
  const isOn = entity.isOn;
  const isAvailable = entity.isAvailable;

  // Format state text
  let stateText = entity.state;
  if (entity.domain === 'sensor') {
    const unit = entity.attributes.unit_of_measurement || '';
    stateText = `${entity.state}${unit}`;
  } else if (entity.domain === 'light' && isOn && entity.attributes.brightness) {
    const brightnessPct = Math.round((entity.attributes.brightness / 255) * 100);
    stateText = `on (${brightnessPct}%)`;
  }

  return (
    <div className="flex items-center justify-between p-2 rounded bg-white/5 hover:bg-white/10 transition-colors">
      <div className="flex-1 min-w-0">
        <p className="text-sm text-white truncate">{entity.displayName}</p>
        <p className="text-xs text-white/50 truncate">{entity.entity_id}</p>
      </div>
      <div
        className={`
          px-2 py-1 rounded text-xs font-medium ml-2 whitespace-nowrap
          ${
            !isAvailable
              ? 'bg-gray-500/20 text-gray-400'
              : isOn
              ? 'bg-green-500/20 text-green-400'
              : 'bg-gray-500/20 text-gray-300'
          }
        `}
      >
        {stateText}
      </div>
    </div>
  );
}
