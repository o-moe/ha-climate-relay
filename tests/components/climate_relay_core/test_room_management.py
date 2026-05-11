"""Room management operation tests."""

from __future__ import annotations

from unittest import TestCase

from custom_components.climate_relay_core.const import (
    CONF_AWAY_TARGET_TEMPERATURE,
    CONF_AWAY_TARGET_TYPE,
    CONF_HOME_TARGET_TEMPERATURE,
    CONF_HUMIDITY_ENTITY_ID,
    CONF_PRIMARY_CLIMATE_ENTITY_ID,
    CONF_SCHEDULE,
    CONF_SCHEDULE_HOME_END,
    CONF_SCHEDULE_HOME_START,
    CONF_WINDOW_ACTION_TYPE,
    CONF_WINDOW_CUSTOM_TEMPERATURE,
    CONF_WINDOW_ENTITY_ID,
    CONF_WINDOW_OPEN_DELAY_SECONDS,
    DEFAULT_WINDOW_ACTION_TYPE,
    DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
)
from custom_components.climate_relay_core.room_management import (
    DuplicatePrimaryClimateError,
    MissingPrimaryClimateError,
    UnknownRoomReferenceError,
    activate_room,
    disable_room,
    update_room,
    update_room_schedule,
)


def _room(
    primary_climate_entity_id: str,
    *,
    home_target_temperature: float = 21.0,
    schedule_home_start: str = "06:00:00",
    schedule_home_end: str = "22:00:00",
) -> dict[str, object]:
    return {
        CONF_PRIMARY_CLIMATE_ENTITY_ID: primary_climate_entity_id,
        CONF_HUMIDITY_ENTITY_ID: f"sensor.{primary_climate_entity_id.split('.')[1]}_humidity",
        CONF_WINDOW_ENTITY_ID: f"binary_sensor.{primary_climate_entity_id.split('.')[1]}_window",
        CONF_WINDOW_ACTION_TYPE: DEFAULT_WINDOW_ACTION_TYPE,
        CONF_WINDOW_CUSTOM_TEMPERATURE: None,
        CONF_WINDOW_OPEN_DELAY_SECONDS: DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
        CONF_HOME_TARGET_TEMPERATURE: home_target_temperature,
        CONF_AWAY_TARGET_TYPE: "absolute",
        CONF_AWAY_TARGET_TEMPERATURE: 17.0,
        CONF_SCHEDULE_HOME_START: schedule_home_start,
        CONF_SCHEDULE_HOME_END: schedule_home_end,
    }


class RoomManagementTest(TestCase):
    """Test backend-owned room management operations."""

    def test_activate_room_appends_one_normalized_room(self) -> None:
        existing_rooms = [_room("climate.office")]
        result = activate_room(
            existing_rooms,
            {
                CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                CONF_HOME_TARGET_TEMPERATURE: "20.5",
                CONF_AWAY_TARGET_TYPE: "relative",
                CONF_AWAY_TARGET_TEMPERATURE: "-2.0",
                CONF_SCHEDULE: {
                    CONF_SCHEDULE_HOME_START: "07:00:00",
                    CONF_SCHEDULE_HOME_END: "21:00:00",
                },
            },
        )

        self.assertEqual(2, len(result))
        self.assertEqual(existing_rooms[0], result[0])
        self.assertEqual("climate.living_room", result[1][CONF_PRIMARY_CLIMATE_ENTITY_ID])
        self.assertEqual(20.5, result[1][CONF_HOME_TARGET_TEMPERATURE])
        self.assertEqual("relative", result[1][CONF_AWAY_TARGET_TYPE])
        self.assertEqual(-2.0, result[1][CONF_AWAY_TARGET_TEMPERATURE])
        self.assertEqual("07:00:00", result[1][CONF_SCHEDULE_HOME_START])
        self.assertEqual("21:00:00", result[1][CONF_SCHEDULE_HOME_END])
        self.assertNotIn(CONF_SCHEDULE, result[1])

    def test_activate_room_rejects_missing_primary_climate(self) -> None:
        with self.assertRaises(MissingPrimaryClimateError):
            activate_room([], {CONF_HOME_TARGET_TEMPERATURE: 21.0})

    def test_activate_room_rejects_duplicate_primary_climate(self) -> None:
        with self.assertRaises(DuplicatePrimaryClimateError):
            activate_room(
                [_room("climate.office")],
                _room("climate.office", home_target_temperature=20.0),
            )

    def test_update_room_replaces_exactly_one_room(self) -> None:
        existing_rooms = [_room("climate.office"), _room("climate.bedroom")]

        result = update_room(
            existing_rooms,
            "climate.office",
            _room("climate.living_room", home_target_temperature=22.0),
        )

        self.assertEqual("climate.living_room", result[0][CONF_PRIMARY_CLIMATE_ENTITY_ID])
        self.assertEqual(22.0, result[0][CONF_HOME_TARGET_TEMPERATURE])
        self.assertEqual(existing_rooms[1], result[1])
        self.assertEqual("climate.office", existing_rooms[0][CONF_PRIMARY_CLIMATE_ENTITY_ID])

    def test_update_room_preserves_unrelated_rooms(self) -> None:
        bedroom = _room("climate.bedroom", home_target_temperature=19.0)

        result = update_room(
            [_room("climate.office"), bedroom],
            "climate.office",
            _room("climate.office", home_target_temperature=20.0),
        )

        self.assertEqual(bedroom, result[1])
        self.assertIsNot(bedroom, result[1])

    def test_update_room_rejects_unknown_room_reference(self) -> None:
        with self.assertRaises(UnknownRoomReferenceError):
            update_room(
                [_room("climate.office")],
                "climate.unknown",
                _room("climate.unknown"),
            )

    def test_update_room_rejects_duplicate_primary_climate_against_another_room(self) -> None:
        with self.assertRaises(DuplicatePrimaryClimateError):
            update_room(
                [_room("climate.office"), _room("climate.bedroom")],
                "climate.office",
                _room("climate.bedroom"),
            )

    def test_update_room_allows_keeping_same_primary_climate(self) -> None:
        result = update_room(
            [_room("climate.office"), _room("climate.bedroom")],
            "climate.office",
            _room("climate.office", home_target_temperature=20.0),
        )

        self.assertEqual("climate.office", result[0][CONF_PRIMARY_CLIMATE_ENTITY_ID])
        self.assertEqual(20.0, result[0][CONF_HOME_TARGET_TEMPERATURE])

    def test_disable_room_removes_exactly_one_room(self) -> None:
        result = disable_room(
            [_room("climate.office"), _room("climate.bedroom")],
            "climate.office",
        )

        self.assertEqual([_room("climate.bedroom")], result)

    def test_disable_room_preserves_unrelated_rooms(self) -> None:
        bedroom = _room("climate.bedroom")

        result = disable_room([_room("climate.office"), bedroom], "climate.office")

        self.assertEqual(bedroom, result[0])
        self.assertIsNot(bedroom, result[0])

    def test_disable_room_rejects_unknown_room_reference(self) -> None:
        with self.assertRaises(UnknownRoomReferenceError):
            disable_room([_room("climate.office")], "climate.unknown")

    def test_existing_rooms_list_is_not_mutated_in_place(self) -> None:
        existing_rooms = [_room("climate.office")]
        original = [dict(room) for room in existing_rooms]

        result = activate_room(existing_rooms, _room("climate.bedroom"))

        self.assertEqual(original, existing_rooms)
        self.assertIsNot(existing_rooms, result)
        self.assertIsNot(existing_rooms[0], result[0])

    def test_normalized_output_keeps_existing_flat_room_item_shape(self) -> None:
        result = activate_room([], _room("climate.office"))

        self.assertEqual(
            {
                CONF_PRIMARY_CLIMATE_ENTITY_ID,
                CONF_HUMIDITY_ENTITY_ID,
                CONF_WINDOW_ENTITY_ID,
                CONF_WINDOW_ACTION_TYPE,
                CONF_WINDOW_CUSTOM_TEMPERATURE,
                CONF_WINDOW_OPEN_DELAY_SECONDS,
                CONF_HOME_TARGET_TEMPERATURE,
                CONF_AWAY_TARGET_TYPE,
                CONF_AWAY_TARGET_TEMPERATURE,
                CONF_SCHEDULE_HOME_START,
                CONF_SCHEDULE_HOME_END,
            },
            set(result[0]),
        )

    def test_no_schedule_expansion_beyond_existing_start_and_end_fields(self) -> None:
        result = activate_room(
            [],
            {
                **_room("climate.office"),
                CONF_SCHEDULE: {
                    CONF_SCHEDULE_HOME_START: "08:00:00",
                    CONF_SCHEDULE_HOME_END: "18:00:00",
                },
            },
        )

        self.assertEqual("08:00:00", result[0][CONF_SCHEDULE_HOME_START])
        self.assertEqual("18:00:00", result[0][CONF_SCHEDULE_HOME_END])
        self.assertNotIn(CONF_SCHEDULE, result[0])

    def test_update_room_schedule_updates_exactly_one_room(self) -> None:
        office = {**_room("climate.office"), "custom_field": "keep"}
        bedroom = _room("climate.bedroom", schedule_home_start="07:00:00")

        result = update_room_schedule(
            [office, bedroom],
            "climate.office",
            schedule_home_start="08:30",
            schedule_home_end="20:45",
        )

        self.assertEqual("08:30:00", result[0][CONF_SCHEDULE_HOME_START])
        self.assertEqual("20:45:00", result[0][CONF_SCHEDULE_HOME_END])
        self.assertEqual("keep", result[0]["custom_field"])
        self.assertEqual(bedroom, result[1])
        self.assertEqual("06:00:00", office[CONF_SCHEDULE_HOME_START])

    def test_update_room_schedule_rejects_unknown_room(self) -> None:
        with self.assertRaises(UnknownRoomReferenceError):
            update_room_schedule(
                [_room("climate.office")],
                "climate.unknown",
                schedule_home_start="08:00",
                schedule_home_end="20:00",
            )
