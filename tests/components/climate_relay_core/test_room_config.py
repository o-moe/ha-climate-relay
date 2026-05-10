"""Room configuration normalization tests."""

from __future__ import annotations

from unittest import TestCase

from custom_components.climate_relay_core.const import (
    CONF_AWAY_TARGET_TEMPERATURE,
    CONF_AWAY_TARGET_TYPE,
    CONF_HOME_TARGET_TEMPERATURE,
    CONF_PRIMARY_CLIMATE_ENTITY_ID,
    CONF_ROOMS,
    CONF_SCHEDULE,
    CONF_SCHEDULE_HOME_END,
    CONF_SCHEDULE_HOME_START,
    CONF_WINDOW_ACTION_TYPE,
    CONF_WINDOW_OPEN_DELAY_SECONDS,
    DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
)
from custom_components.climate_relay_core.room_config import (
    InvalidScheduleTimeError,
    ScheduleWindowRequiredError,
    normalize_daily_schedule_window,
    normalize_non_negative_int,
    normalize_optional_float,
    normalize_room_options,
    normalize_rooms,
    validate_room_schedule_window,
)


class RoomConfigTest(TestCase):
    """Test room/profile configuration helpers."""

    def test_normalize_room_options_keeps_existing_persisted_shape(self) -> None:
        normalized = normalize_room_options(
            {
                CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                CONF_HOME_TARGET_TEMPERATURE: "21.5",
                CONF_AWAY_TARGET_TYPE: "absolute",
                CONF_AWAY_TARGET_TEMPERATURE: "18.0",
                CONF_WINDOW_ACTION_TYPE: "off",
                CONF_WINDOW_OPEN_DELAY_SECONDS: "30",
                CONF_SCHEDULE_HOME_START: "07:00:00",
                CONF_SCHEDULE_HOME_END: "22:00:00",
            }
        )

        self.assertEqual("climate.living_room", normalized[CONF_PRIMARY_CLIMATE_ENTITY_ID])
        self.assertEqual(21.5, normalized[CONF_HOME_TARGET_TEMPERATURE])
        self.assertEqual(18.0, normalized[CONF_AWAY_TARGET_TEMPERATURE])
        self.assertEqual(30, normalized[CONF_WINDOW_OPEN_DELAY_SECONDS])
        self.assertEqual("07:00:00", normalized[CONF_SCHEDULE_HOME_START])
        self.assertEqual("22:00:00", normalized[CONF_SCHEDULE_HOME_END])

    def test_normalize_rooms_filters_non_dict_entries(self) -> None:
        normalized = normalize_rooms(
            {
                CONF_ROOMS: [
                    {
                        CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.office",
                        CONF_HOME_TARGET_TEMPERATURE: 21.0,
                    },
                    "invalid",
                ]
            }
        )

        self.assertEqual(1, len(normalized))
        self.assertEqual("climate.office", normalized[0][CONF_PRIMARY_CLIMATE_ENTITY_ID])

    def test_normalize_room_options_rejects_invalid_away_target_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported away target type"):
            normalize_room_options({CONF_AWAY_TARGET_TYPE: "unsupported"})

    def test_normalize_room_options_rejects_invalid_window_action_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported window action type"):
            normalize_room_options({CONF_WINDOW_ACTION_TYPE: "unsupported"})

    def test_optional_float_accepts_strings_with_comma_and_dot(self) -> None:
        self.assertEqual(19.5, normalize_optional_float("19,5"))
        self.assertEqual(19.5, normalize_optional_float("19.5"))
        self.assertIsNone(normalize_optional_float(""))

    def test_non_negative_integer_defaults_on_empty_or_negative_value(self) -> None:
        self.assertEqual(
            DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
            normalize_non_negative_int("", default=DEFAULT_WINDOW_OPEN_DELAY_SECONDS),
        )
        self.assertEqual(
            DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
            normalize_non_negative_int("-1", default=DEFAULT_WINDOW_OPEN_DELAY_SECONDS),
        )

    def test_schedule_values_can_be_read_from_nested_shape(self) -> None:
        normalized = normalize_room_options(
            {
                CONF_SCHEDULE: {
                    CONF_SCHEDULE_HOME_START: "08:00:00",
                    CONF_SCHEDULE_HOME_END: "20:00:00",
                }
            }
        )

        self.assertEqual("08:00:00", normalized[CONF_SCHEDULE_HOME_START])
        self.assertEqual("20:00:00", normalized[CONF_SCHEDULE_HOME_END])

    def test_schedule_window_validation_rejects_identical_values(self) -> None:
        self.assertFalse(validate_room_schedule_window("08:00:00", "08:00:00"))
        self.assertTrue(validate_room_schedule_window("08:00:00", "20:00:00"))

    def test_daily_schedule_validation_accepts_valid_window(self) -> None:
        self.assertEqual(
            {
                CONF_SCHEDULE_HOME_START: "06:30:00",
                CONF_SCHEDULE_HOME_END: "22:00:00",
            },
            normalize_daily_schedule_window("06:30", "22:00:00"),
        )

    def test_daily_schedule_validation_rejects_identical_start_and_end(self) -> None:
        with self.assertRaises(ScheduleWindowRequiredError):
            normalize_daily_schedule_window("08:00", "08:00:00")

    def test_daily_schedule_validation_rejects_invalid_time_values(self) -> None:
        with self.assertRaises(InvalidScheduleTimeError):
            normalize_daily_schedule_window("25:00", "22:00")

    def test_daily_schedule_validation_rejects_missing_window_endpoint(self) -> None:
        with self.assertRaises(ScheduleWindowRequiredError):
            normalize_daily_schedule_window(None, "22:00")
