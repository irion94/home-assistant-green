import { useMemo } from 'react'
import { useHomeAssistant } from './useHomeAssistant'
import type { EntityState, EntityDomain } from '../types/entity'
import { getDomain } from '../types/entity'

export function useEntities(entityIds: string[]): Map<string, EntityState | undefined> {
  const { getState } = useHomeAssistant()

  return useMemo(() => {
    const result = new Map<string, EntityState | undefined>()
    entityIds.forEach(id => {
      result.set(id, getState(id))
    })
    return result
  }, [entityIds, getState])
}

export function useEntitiesByDomain(domain: EntityDomain): EntityState[] {
  const { states } = useHomeAssistant()

  return useMemo(() => {
    const result: EntityState[] = []
    states.forEach((state, entityId) => {
      if (getDomain(entityId) === domain) {
        result.push(state)
      }
    })
    return result.sort((a, b) => {
      const nameA = a.attributes.friendly_name ?? a.entity_id
      const nameB = b.attributes.friendly_name ?? b.entity_id
      return nameA.localeCompare(nameB)
    })
  }, [states, domain])
}

export function useLights(): EntityState[] {
  return useEntitiesByDomain('light')
}

export function useSensors(): EntityState[] {
  return useEntitiesByDomain('sensor')
}

export function useClimates(): EntityState[] {
  return useEntitiesByDomain('climate')
}

export function useSwitches(): EntityState[] {
  return useEntitiesByDomain('switch')
}

export default useEntities
