/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_HA_URL: string
  readonly VITE_HA_TOKEN: string
  readonly VITE_GATEWAY_URL: string
  readonly VITE_KIOSK_MODE: string
  readonly VITE_SCREEN_TIMEOUT: string
  readonly VITE_LANGUAGE: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
