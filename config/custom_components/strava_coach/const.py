"""Constants for the Strava Coach integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

# Domain
DOMAIN: Final = "strava_coach"

# Integration metadata
NAME: Final = "Strava Coach"
VERSION: Final = "0.1.0"

# Configuration
CONF_CLIENT_ID: Final = "client_id"
CONF_CLIENT_SECRET: Final = "client_secret"
CONF_SYNC_TIME: Final = "sync_time"
CONF_HISTORY_WINDOW: Final = "history_window_days"
CONF_LLM_ENABLED: Final = "llm_enabled"
CONF_LLM_PROVIDER: Final = "llm_provider"
CONF_LLM_API_KEY: Final = "llm_api_key"
CONF_LLM_MODEL: Final = "llm_model"
CONF_AGGREGATES_ONLY: Final = "aggregates_only"

# Defaults
DEFAULT_SYNC_TIME: Final = "07:00"
DEFAULT_HISTORY_WINDOW: Final = 42
DEFAULT_ATL_DAYS: Final = 7
DEFAULT_CTL_DAYS: Final = 42
DEFAULT_LLM_ENABLED: Final = False
DEFAULT_LLM_PROVIDER: Final = "openai"
DEFAULT_LLM_MODEL: Final = "gpt-4-turbo-preview"
DEFAULT_AGGREGATES_ONLY: Final = True

# Update intervals
UPDATE_INTERVAL: Final = timedelta(hours=1)
SYNC_COOLDOWN: Final = timedelta(minutes=15)

# Strava API
STRAVA_API_BASE: Final = "https://www.strava.com/api/v3"
STRAVA_AUTH_URL: Final = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL: Final = "https://www.strava.com/oauth/token"
STRAVA_RATE_LIMIT_15MIN: Final = 100  # requests per 15 minutes
STRAVA_RATE_LIMIT_DAILY: Final = 1000  # requests per day

# OAuth
OAUTH2_SCOPES: Final = ["read", "activity:read_all"]
OAUTH2_AUTHORIZE: Final = "authorize"
OAUTH2_TOKEN: Final = "token"

# Database
DB_FILENAME: Final = "strava_coach.db"

# Entity attributes
ATTR_ATL: Final = "atl"
ATTR_CTL: Final = "ctl"
ATTR_TSB: Final = "tsb"
ATTR_MONOTONY: Final = "monotony"
ATTR_WINDOW_DAYS: Final = "window_days"
ATTR_RATIONALE: Final = "rationale_short"
ATTR_COMMAND: Final = "command"
ATTR_PARAMS: Final = "params"
ATTR_LAST_SYNC: Final = "last_sync"
ATTR_NEXT_SYNC: Final = "next_sync"

# Sensor names
SENSOR_READINESS: Final = "readiness"
SENSOR_FITNESS: Final = "fitness"
SENSOR_FATIGUE: Final = "fatigue"
SENSOR_FORM: Final = "form"
SENSOR_SUGGESTION: Final = "today_suggestion"

# Services
SERVICE_SYNC_NOW: Final = "sync_now"
SERVICE_GENERATE_SUGGESTION: Final = "generate_suggestion"

# Service parameters
ATTR_DATE: Final = "date"
ATTR_WINDOW_DAYS_PARAM: Final = "window_days"
ATTR_USE_LLM: Final = "use_llm"

# Training commands vocabulary
COMMAND_REST_DAY: Final = "REST_DAY"
COMMAND_Z2_RIDE: Final = "Z2_RIDE"
COMMAND_TEMPO_RIDE: Final = "TEMPO_RIDE"
COMMAND_SWEETSPOT_3X12: Final = "SWEETSPOT_3x12"
COMMAND_VO2MAX_5X3: Final = "VO2MAX_5x3"
COMMAND_ENDURO_TECH_SKILLS: Final = "ENDURO_TECH_SKILLS"
COMMAND_STRENGTH_FULL_BODY: Final = "STRENGTH_FULL_BODY"
COMMAND_MOBILITY_20MIN: Final = "MOBILITY_20MIN"

VALID_COMMANDS: Final = [
    COMMAND_REST_DAY,
    COMMAND_Z2_RIDE,
    COMMAND_TEMPO_RIDE,
    COMMAND_SWEETSPOT_3X12,
    COMMAND_VO2MAX_5X3,
    COMMAND_ENDURO_TECH_SKILLS,
    COMMAND_STRENGTH_FULL_BODY,
    COMMAND_MOBILITY_20MIN,
]

# Readiness thresholds
READINESS_VERY_LOW: Final = 20
READINESS_LOW: Final = 40
READINESS_MODERATE: Final = 60
READINESS_HIGH: Final = 80

# Logging
LOGGER_NAME: Final = f"custom_components.{DOMAIN}"
