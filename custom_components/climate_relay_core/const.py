"""Constants for Climate Relay."""

DOMAIN = "climate_relay_core"
DEFAULT_NAME = "Climate Relay"

CONF_FALLBACK_TEMPERATURE = "fallback_temperature"
CONF_MANUAL_OVERRIDE_RESET_ENABLED = "manual_override_reset_enabled"
CONF_MANUAL_OVERRIDE_RESET_TIME = "manual_override_reset_time"
CONF_PERSON_ENTITY_IDS = "person_entity_ids"
CONF_SIMULATION_MODE = "simulation_mode"
CONF_UNKNOWN_STATE_HANDLING = "unknown_state_handling"
CONF_VERBOSE_LOGGING = "verbose_logging"

ATTR_EFFECTIVE_PRESENCE = "effective_presence"
ATTR_FALLBACK_TEMPERATURE = "fallback_temperature"
ATTR_MANUAL_OVERRIDE_RESET_TIME = "manual_override_reset_time"
ATTR_SIMULATION_MODE = "simulation_mode"
ATTR_UNKNOWN_STATE_HANDLING = "unknown_state_handling"

DEFAULT_FALLBACK_TEMPERATURE = 20.0
DEFAULT_UNKNOWN_STATE_HANDLING = "away"

SERVICE_SET_GLOBAL_MODE = "set_global_mode"
ENTITY_TRANSLATION_KEY_PRESENCE_CONTROL = "presence_control"
