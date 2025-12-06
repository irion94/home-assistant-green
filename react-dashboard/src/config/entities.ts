export const LIGHTS = {
  salon: {
    name: 'Salon',
    entity_id: 'light.yeelight_color_0x80156a9',
    icon: 'sofa',
  },
  kuchnia: {
    name: 'Kuchnia',
    entity_id: 'light.yeelight_color_0x49c27e1',
    icon: 'utensils',
  },
  sypialnia: {
    name: 'Sypialnia',
    entity_id: 'light.yeelight_color_0x80147dd',
    icon: 'bed',
  },
  biurko: {
    name: 'Biurko',
    entity_id: 'light.yeelight_lamp15_0x1b37d19d',
    icon: 'lamp-desk',
  },
  biurkoAmbient: {
    name: 'Biurko Ambient',
    entity_id: 'light.yeelight_lamp15_0x1b37d19d_ambilight',
    icon: 'lamp',
  },
  lampa1: {
    name: 'Lampa 1',
    entity_id: 'light.yeelight_color_0x801498b',
    icon: 'lightbulb',
  },
  lampa2: {
    name: 'Lampa 2',
    entity_id: 'light.yeelight_color_0x8015154',
    icon: 'lightbulb',
  },
} as const

export const CLIMATE = {
  // No climate entities found - add here when available
  // heatPump: {
  //   name: 'Pompa Ciepła',
  //   entity_id: 'climate.pompa_ciepla_room_temperature',
  // },
} as const

export const SENSORS = {
  weather: 'weather.forecast_dom',
  cpuTemp: 'sensor.rpi_cpu_temperature',
  downloadSpeed: 'sensor.orange_funbox_3_download_speed',
  uploadSpeed: 'sensor.orange_funbox_3_upload_speed',
  voiceStatus: 'sensor.voice_assistant_status',
  voiceText: 'sensor.voice_assistant_text',
  // Add solar/temperature sensors when available:
  // solarPower: 'sensor.inverter_pv_power',
  // indoorTemp: 'sensor.temperature_indoor',
} as const

export const MEDIA = {
  nestHub: {
    name: 'Nest Hub',
    entity_id: 'media_player.living_room_display',
  },
  tvSalon: {
    name: 'TV Salon',
    entity_id: 'media_player.telewizor_w_salonie',
  },
  tvSypialnia: {
    name: 'TV Sypialnia',
    entity_id: 'media_player.telewizor_w_sypialni',
  },
} as const

export type LightKey = keyof typeof LIGHTS
export type ClimateKey = keyof typeof CLIMATE
export type SensorKey = keyof typeof SENSORS
export type MediaKey = keyof typeof MEDIA

// Helper to get all light entity IDs
export function getAllLightIds(): string[] {
  return Object.values(LIGHTS).map(l => l.entity_id)
}

// Helper to get entity config by ID
export function getLightByEntityId(entityId: string) {
  return Object.values(LIGHTS).find(l => l.entity_id === entityId)
}
