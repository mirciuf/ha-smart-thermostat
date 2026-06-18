"""Climate platform for Smart Thermostat."""
from __future__ import annotations

import logging
import json
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    NAME,
    VERSION,
    CONF_THERMOSTAT_NAME,
    CONF_TEMP_SENSOR,
    CONF_HEAT_SWITCH,
    CONF_COOL_SWITCH,
    CONF_WINDOW_SENSOR,
    CONF_WINDOW_SENSOR_2,
    CONF_OUTDOOR_SENSOR,
    CONF_TARGET_TEMP,
    CONF_HYSTERESIS,
    CONF_OUTDOOR_TEMP_THRESHOLD,
    CONF_MIN_TEMP,
    CONF_MAX_TEMP,
    CONF_PRESETS,
    CONF_AC_SCENE_COOL_ON,
    CONF_TEMP_STEP,
    DEFAULT_TEMP_STEP,
    CONF_AC_SCENE_COOL_OFF,
    DEFAULT_TARGET_TEMP,
    DEFAULT_HYSTERESIS,
    DEFAULT_OUTDOOR_THRESHOLD,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    ATTR_HYSTERESIS,
    ATTR_OUTDOOR_THRESHOLD,
    ATTR_WINDOW_OPEN,
    ATTR_OUTDOOR_TEMP,
    ATTR_HEAT_SWITCH,
    ATTR_COOL_SWITCH,
    ATTR_TEMP_SENSOR,
    ATTR_PRESETS,
    ATTR_AC_SCENE_COOL_ON,
    ATTR_AC_SCENE_COOL_OFF,
    PRESET_NONE,
    CONF_COOL_TYPE,
    COOL_TYPE_NONE,
    COOL_TYPE_SWITCH,
    COOL_TYPE_SCENE,
    COOL_TYPE_CLIMATE,
    CONF_AC_CLIMATE_ENTITY,
    CONF_AC_CLIMATE_COOL_TEMP,
    CONF_AC_CLIMATE_MIN_RUNTIME,
    DEFAULT_AC_CLIMATE_COOL_TEMP,
    DEFAULT_AC_CLIMATE_MIN_RUNTIME,
    ATTR_COOL_TYPE,
    ATTR_AC_CLIMATE_ENTITY,
    ATTR_AC_CLIMATE_COOL_TEMP,
    ATTR_AC_CLIMATE_MIN_RUNTIME,
    resolve_cool_type,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config = {**entry.data, **entry.options}

    presets_raw = config.get(CONF_PRESETS, "{}")
    try:
        presets = json.loads(presets_raw) if isinstance(presets_raw, str) else presets_raw
    except (json.JSONDecodeError, TypeError):
        presets = {}

    cool_type = resolve_cool_type(config)

    thermostat = SmartThermostat(
        hass=hass,
        entry_id=entry.entry_id,
        name=config.get(CONF_THERMOSTAT_NAME, "Smart Thermostat"),
        temp_sensor=config[CONF_TEMP_SENSOR],
        heat_switch=config[CONF_HEAT_SWITCH],
        cool_type=cool_type,
        cool_switch=config.get(CONF_COOL_SWITCH),
        window_sensor=config.get(CONF_WINDOW_SENSOR),
        window_sensor_2=config.get(CONF_WINDOW_SENSOR_2),
        outdoor_sensor=config.get(CONF_OUTDOOR_SENSOR),
        target_temp=float(config.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP)),
        hysteresis=float(config.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)),
        outdoor_threshold=float(config.get(CONF_OUTDOOR_TEMP_THRESHOLD, DEFAULT_OUTDOOR_THRESHOLD)),
        min_temp=float(config.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)),
        max_temp=float(config.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)),
        presets=presets,
        ac_scene_cool_on=config.get(CONF_AC_SCENE_COOL_ON),
        ac_scene_cool_off=config.get(CONF_AC_SCENE_COOL_OFF),
        ac_climate_entity=config.get(CONF_AC_CLIMATE_ENTITY),
        ac_climate_cool_temp=float(config.get(CONF_AC_CLIMATE_COOL_TEMP, DEFAULT_AC_CLIMATE_COOL_TEMP)),
        ac_climate_min_runtime=int(config.get(CONF_AC_CLIMATE_MIN_RUNTIME, DEFAULT_AC_CLIMATE_MIN_RUNTIME)),
        temp_step=float(config.get(CONF_TEMP_STEP, DEFAULT_TEMP_STEP)),
    )

    async_add_entities([thermostat], True)


class SmartThermostat(RestoreEntity, ClimateEntity):

    _attr_should_poll = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        temp_sensor: str,
        heat_switch: str,
        cool_type: str,
        cool_switch: str | None,
        window_sensor: str | None,
        window_sensor_2: str | None,
        outdoor_sensor: str | None,
        target_temp: float,
        hysteresis: float,
        outdoor_threshold: float,
        min_temp: float,
        max_temp: float,
        presets: dict[str, float],
        ac_scene_cool_on: str | None,
        ac_scene_cool_off: str | None,
        ac_climate_entity: str | None,
        ac_climate_cool_temp: float,
        ac_climate_min_runtime: int,
        temp_step: float = 0.5,
    ) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=name,
            manufacturer="TopTech Labs",
            model="Smart Thermostat v" + VERSION,
            sw_version=VERSION,
        )

        # Config
        self._temp_sensor = temp_sensor
        self._heat_switch = heat_switch
        self._cool_type = cool_type
        self._cool_switch = cool_switch
        self._window_sensor = window_sensor
        self._window_sensor_2 = window_sensor_2
        self._outdoor_sensor = outdoor_sensor
        self._hysteresis = hysteresis
        self._outdoor_threshold = outdoor_threshold
        self._attr_min_temp = min_temp
        self._attr_max_temp = max_temp
        self._ac_scene_cool_on = ac_scene_cool_on
        self._ac_scene_cool_off = ac_scene_cool_off
        self._ac_climate_entity = ac_climate_entity
        self._ac_climate_cool_temp = ac_climate_cool_temp
        self._ac_climate_min_runtime = ac_climate_min_runtime
        self._attr_target_temperature_step = temp_step

        # Determine if cool mode is available, based on the selected cool_type
        self._has_cool = bool(
            (cool_type == COOL_TYPE_SWITCH and cool_switch)
            or (cool_type == COOL_TYPE_SCENE and ac_scene_cool_on and ac_scene_cool_off)
            or (cool_type == COOL_TYPE_CLIMATE and ac_climate_entity)
        )

        # Presets
        self._presets = presets
        self._attr_preset_mode = PRESET_NONE

        # State
        self._attr_target_temperature = target_temp
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_current_temperature = None
        self._window_open = False
        self._outdoor_temp = None

        # HVAC modes
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        if self._has_cool:
            self._attr_hvac_modes.append(HVACMode.COOL)

        # Preset modes
        self._attr_preset_modes = [PRESET_NONE] + list(presets.keys())

        # Supported features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        if presets:
            self._attr_supported_features |= ClimateEntityFeature.PRESET_MODE

    # ------------------------------------------------------------------ #
    #  Properties
    # ------------------------------------------------------------------ #

    @property
    def hvac_action(self) -> HVACAction:
        if self._attr_hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self._window_open:
            return HVACAction.IDLE
        if self._is_switch_on(self._heat_switch):
            return HVACAction.HEATING
        if self._cool_type == COOL_TYPE_SWITCH and self._is_switch_on(self._cool_switch):
            return HVACAction.COOLING
        # For scene- or climate-based cool — check if cool mode is active
        if self._cool_type in (COOL_TYPE_SCENE, COOL_TYPE_CLIMATE) and self._attr_hvac_mode == HVACMode.COOL:
            return HVACAction.COOLING
        return HVACAction.IDLE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            ATTR_HYSTERESIS: self._hysteresis,
            ATTR_OUTDOOR_THRESHOLD: self._outdoor_threshold,
            ATTR_WINDOW_OPEN: self._window_open,
            ATTR_OUTDOOR_TEMP: self._outdoor_temp,
            ATTR_TEMP_SENSOR: self._temp_sensor,
            ATTR_HEAT_SWITCH: self._heat_switch,
            ATTR_COOL_TYPE: self._cool_type,
            ATTR_COOL_SWITCH: self._cool_switch,
            ATTR_AC_SCENE_COOL_ON: self._ac_scene_cool_on,
            ATTR_AC_SCENE_COOL_OFF: self._ac_scene_cool_off,
            ATTR_AC_CLIMATE_ENTITY: self._ac_climate_entity,
            ATTR_AC_CLIMATE_COOL_TEMP: self._ac_climate_cool_temp,
            ATTR_AC_CLIMATE_MIN_RUNTIME: self._ac_climate_min_runtime,
            ATTR_PRESETS: self._presets,
        }

    # ------------------------------------------------------------------ #
    #  Setup & restore
    # ------------------------------------------------------------------ #

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                # Restore HVAC mode and preset from last state
                mode = last_state.state
                if mode in [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]:
                    self._attr_hvac_mode = mode
                target = last_state.attributes.get(ATTR_TEMPERATURE)
                if target is not None:
                    self._attr_target_temperature = float(target)
                preset = last_state.attributes.get("preset_mode", PRESET_NONE)
                if preset in self._attr_preset_modes:
                    self._attr_preset_mode = preset
                # NOTE: hysteresis and outdoor_threshold are NOT restored from
                # last_state — they come from config/options which are already
                # set in __init__ and always reflect the latest saved values.
            except (ValueError, TypeError) as err:
                _LOGGER.warning("Could not restore state for %s: %s", self._attr_name, err)

        self._update_current_temp()
        self._update_window_state()
        self._update_outdoor_temp()

        # Register this instance so other thermostats sharing the same
        # AC climate entity can check whether it's still needed before
        # turning it off (see _other_thermostat_needs_climate_cool).
        self.hass.data.setdefault(DOMAIN, {}).setdefault("entities", {})[self._entry_id] = self

        self.async_on_remove(
            self.hass.bus.async_listen("state_changed", self._handle_state_change)
        )

        await self._async_control()

    async def async_will_remove_from_hass(self) -> None:
        entities = self.hass.data.get(DOMAIN, {}).get("entities", {})
        entities.pop(self._entry_id, None)
        await super().async_will_remove_from_hass()

    # ------------------------------------------------------------------ #
    #  State change handler
    # ------------------------------------------------------------------ #

    @callback
    def _handle_state_change(self, event: Event) -> None:
        entity_id = event.data.get("entity_id")
        changed = False

        if entity_id == self._temp_sensor:
            self._update_current_temp()
            changed = True
        if self._window_sensor and entity_id == self._window_sensor:
            self._update_window_state()
            changed = True
        if self._window_sensor_2 and entity_id == self._window_sensor_2:
            self._update_window_state()
            changed = True
        if self._outdoor_sensor and entity_id == self._outdoor_sensor:
            self._update_outdoor_temp()
            changed = True
        if entity_id in (self._heat_switch, self._cool_switch):
            changed = True
        if self._ac_climate_entity and entity_id == self._ac_climate_entity:
            changed = True

        if changed:
            self.hass.async_create_task(self._async_control())

    # ------------------------------------------------------------------ #
    #  Sensor readers
    # ------------------------------------------------------------------ #

    def _update_current_temp(self) -> None:
        state = self.hass.states.get(self._temp_sensor)
        if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                self._attr_current_temperature = float(state.state)
            except ValueError:
                self._attr_current_temperature = None

    def _update_window_state(self) -> None:
        """Window open if ANY available sensor reports open.
        Unavailable/unknown sensors are ignored — treated as if not configured.
        A persistent notification is fired when a sensor goes unavailable.
        """
        ACTIVE = {STATE_ON, STATE_OPEN, "on", "open"}
        UNAVAILABLE = {STATE_UNAVAILABLE, STATE_UNKNOWN, "unavailable", "unknown"}
        open1 = False
        open2 = False

        if self._window_sensor:
            state = self.hass.states.get(self._window_sensor)
            if state is None or state.state in UNAVAILABLE:
                self._notify_sensor_offline(self._window_sensor)
            else:
                # Sensor back online — clear flag and dismiss notification
                self._clear_sensor_notification(self._window_sensor)
                open1 = state.state in ACTIVE

        if self._window_sensor_2:
            state = self.hass.states.get(self._window_sensor_2)
            if state is None or state.state in UNAVAILABLE:
                self._notify_sensor_offline(self._window_sensor_2)
            else:
                self._clear_sensor_notification(self._window_sensor_2)
                open2 = state.state in ACTIVE

        self._window_open = open1 or open2

    def _clear_sensor_notification(self, sensor_id: str) -> None:
        """Clear notification flag and dismiss HA notification when sensor comes back."""
        notif_key = f"notified_{sensor_id}"
        if not self.hass.data.get(DOMAIN, {}).get(notif_key):
            return
        self.hass.data[DOMAIN][notif_key] = False
        notification_id = f"smart_thermostat_sensor_{sensor_id.replace('.', '_')}"
        self.hass.async_create_task(
            self.hass.services.async_call(
                "persistent_notification", "dismiss", {
                    "notification_id": notification_id,
                }
            )
        )
        _LOGGER.info(
            "%s: Senzorul '%s' a revenit online — notificare ștearsă.",
            self._attr_name, sensor_id
        )

    def _notify_sensor_offline(self, sensor_id: str) -> None:
        """Fire a persistent notification when a window sensor goes offline."""
        notification_id = f"smart_thermostat_sensor_{sensor_id.replace('.', '_')}"
        # Only notify once — check if already notified
        notif_key = f"notified_{sensor_id}"
        if self.hass.data.get(DOMAIN, {}).get(notif_key):
            return
        self.hass.data.setdefault(DOMAIN, {})[notif_key] = True
        _LOGGER.warning(
            "%s: Senzorul de geam '%s' este offline (unavailable/unknown) — ignorat.",
            self._attr_name, sensor_id
        )
        self.hass.async_create_task(
            self.hass.services.async_call(
                "persistent_notification", "create", {
                    "title": f"⚠️ {self._attr_name} — Senzor offline",
                    "message": (
                        f"Senzorul **{sensor_id}** este offline (unavailable/unknown).\n\n"
                        f"Termostatul **{self._attr_name}** funcționează normal ignorând acest senzor.\n"
                        f"Verifică bateriile sau conexiunea senzorului!"
                    ),
                    "notification_id": notification_id,
                }
            )
        )

    def _update_outdoor_temp(self) -> None:
        if not self._outdoor_sensor:
            self._outdoor_temp = None
            return
        state = self.hass.states.get(self._outdoor_sensor)
        if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                self._outdoor_temp = float(state.state)
            except ValueError:
                self._outdoor_temp = None

    def _is_switch_on(self, switch_id: str | None) -> bool:
        if not switch_id:
            return False
        state = self.hass.states.get(switch_id)
        return state is not None and state.state == STATE_ON

    # ------------------------------------------------------------------ #
    #  Control logic
    # ------------------------------------------------------------------ #

    async def _async_control(self) -> None:
        current = self._attr_current_temperature
        target = self._attr_target_temperature
        mode = self._attr_hvac_mode

        if mode == HVACMode.OFF:
            await self._async_turn_off_all()
            self.async_write_ha_state()
            return

        if self._window_open:
            _LOGGER.debug("%s: Window open — turning off", self._attr_name)
            await self._async_turn_off_all()
            self.async_write_ha_state()
            return

        if current is None:
            _LOGGER.warning("%s: No temperature reading — skipping control", self._attr_name)
            return

        if mode == HVACMode.HEAT:
            if self._outdoor_temp is not None and self._outdoor_temp > self._outdoor_threshold:
                _LOGGER.debug("%s: Outdoor %.1f > threshold %.1f — heat blocked",
                    self._attr_name, self._outdoor_temp, self._outdoor_threshold)
                await self._async_turn_off_switch(self._heat_switch)
                self.async_write_ha_state()
                return

            heat_on = self._is_switch_on(self._heat_switch)
            if heat_on:
                if current >= target + self._hysteresis:
                    await self._async_turn_off_switch(self._heat_switch)
            else:
                if current <= target - self._hysteresis:
                    await self._async_turn_on_switch(self._heat_switch)

        elif mode == HVACMode.COOL:
            if self._cool_type == COOL_TYPE_SWITCH and self._cool_switch:
                # Switch-based cool
                cool_on = self._is_switch_on(self._cool_switch)
                if cool_on:
                    if current <= target - self._hysteresis:
                        await self._async_turn_off_switch(self._cool_switch)
                else:
                    if current >= target + self._hysteresis:
                        await self._async_turn_on_switch(self._cool_switch)
            elif self._cool_type == COOL_TYPE_SCENE and self._ac_scene_cool_on and self._ac_scene_cool_off:
                # Scene-based cool
                if current <= target - self._hysteresis:
                    _LOGGER.debug("%s: COOL OFF via scene (checking shared AC)", self._attr_name)
                    await self._async_turn_off_cool_scene_if_safe()
                elif current >= target + self._hysteresis:
                    _LOGGER.debug("%s: COOL ON via scene", self._attr_name)
                    await self._async_activate_scene(self._ac_scene_cool_on)
            elif self._cool_type == COOL_TYPE_CLIMATE and self._ac_climate_entity:
                # Climate-entity-based cool (e.g. Tuya Smart IR AC)
                if current <= target - self._hysteresis:
                    _LOGGER.debug("%s: COOL OFF via climate entity (checking shared AC + min runtime)", self._attr_name)
                    await self._async_turn_off_climate_if_safe()
                elif current >= target + self._hysteresis:
                    _LOGGER.debug("%s: COOL ON via climate entity", self._attr_name)
                    await self._async_set_climate_cool()

        self.async_write_ha_state()

    # ------------------------------------------------------------------ #
    #  Switch & scene helpers
    # ------------------------------------------------------------------ #

    async def _async_turn_on_switch(self, switch_id: str | None) -> None:
        if not switch_id:
            return
        await self.hass.services.async_call(
            "switch", "turn_on", {"entity_id": switch_id}, blocking=True
        )

    async def _async_turn_off_switch(self, switch_id: str | None) -> None:
        if not switch_id:
            return
        await self.hass.services.async_call(
            "switch", "turn_off", {"entity_id": switch_id}, blocking=True
        )

    async def _async_activate_scene(self, scene_id: str | None) -> None:
        if not scene_id:
            return
        await self.hass.services.async_call(
            "scene", "turn_on", {"entity_id": scene_id}, blocking=True
        )

    async def _async_turn_off_all(self) -> None:
        await self._async_turn_off_switch(self._heat_switch)
        if self._cool_type == COOL_TYPE_SWITCH:
            await self._async_turn_off_switch(self._cool_switch)
        elif self._cool_type == COOL_TYPE_SCENE:
            await self._async_turn_off_cool_scene_if_safe()
        elif self._cool_type == COOL_TYPE_CLIMATE:
            await self._async_turn_off_climate_if_safe()

    async def _async_turn_off_cool_scene_if_safe(self) -> None:
        """Execute ac_scene_cool_off ONLY if no other thermostat
        with the same ac_scene_cool_on is still requesting cooling.
        """
        if not self._ac_scene_cool_off:
            return

        # Find all other SmartThermostat entities sharing the same cool scene
        for entry_id, data in self.hass.data.get(DOMAIN, {}).items():
            if entry_id == self._entry_id:
                continue
            if not isinstance(data, dict):
                continue
            # Check if another thermostat shares the same ac_scene_cool_on
            other_scene = data.get("ac_scene_cool_on")
            if other_scene != self._ac_scene_cool_on:
                continue
            # Check if that thermostat is actively cooling
            other_entity_id = f"climate.{data.get('thermostat_name', '').lower().replace(' ', '_').replace('-', '_')}"
            other_state = self.hass.states.get(other_entity_id)
            if other_state and other_state.state == "cool":
                _LOGGER.debug(
                    "%s: AC scene OFF skipped — '%s' is still cooling",
                    self._attr_name, other_entity_id
                )
                return  # Another thermostat still needs AC — don't turn off

        # Safe to turn off
        _LOGGER.debug("%s: AC scene OFF — no other thermostat needs cooling", self._attr_name)
        await self._async_activate_scene(self._ac_scene_cool_off)

    # ------------------------------------------------------------------ #
    #  AC climate entity helpers (cool_type == "climate")
    # ------------------------------------------------------------------ #

    def _other_thermostat_needs_climate_cool(self, entity_id: str) -> bool:
        """True if another SmartThermostat instance is sharing the same AC
        climate entity and is still actively requesting COOL from it."""
        entities = self.hass.data.get(DOMAIN, {}).get("entities", {})
        for entry_id, other in entities.items():
            if entry_id == self._entry_id:
                continue
            if getattr(other, "_cool_type", None) != COOL_TYPE_CLIMATE:
                continue
            if getattr(other, "_ac_climate_entity", None) != entity_id:
                continue
            if other._attr_hvac_mode == HVACMode.COOL and not other._window_open:
                return True
        return False

    def _climate_runtime_remaining(self, entity_id: str) -> float:
        """Seconds remaining before the AC may be safely turned off, based on
        how long it has been running (min_runtime protection for the compressor).
        Uses the climate entity's own last_changed timestamp — it changes
        precisely when the AC's hvac_mode last switched, so it doubles as a
        reliable 'running since' marker without needing extra bookkeeping.
        """
        if self._ac_climate_min_runtime <= 0:
            return 0
        state = self.hass.states.get(entity_id)
        if state is None or state.state != HVACMode.COOL:
            return 0  # Already off (or unknown) — nothing to protect
        elapsed = (dt_util.utcnow() - state.last_changed).total_seconds()
        remaining = (self._ac_climate_min_runtime * 60) - elapsed
        return max(0.0, remaining)

    def _cancel_pending_climate_off(self, entity_id: str) -> None:
        pending = self.hass.data.get(DOMAIN, {}).get("ac_climate_pending_off", {})
        cancel = pending.pop(entity_id, None)
        if cancel:
            cancel()

    def _schedule_climate_off(self, entity_id: str, delay_seconds: float) -> None:
        pending = self.hass.data.setdefault(DOMAIN, {}).setdefault("ac_climate_pending_off", {})
        if entity_id in pending:
            return  # A timer is already scheduled for this AC entity

        @callback
        def _fire(_now) -> None:
            pending.pop(entity_id, None)
            self.hass.async_create_task(self._async_recheck_and_turn_off_climate(entity_id))

        pending[entity_id] = async_call_later(self.hass, delay_seconds, _fire)

    async def _async_recheck_and_turn_off_climate(self, entity_id: str) -> None:
        """Called when a delayed OFF timer fires — re-checks conditions are
        still valid (another thermostat may now need cooling) before acting."""
        if self._other_thermostat_needs_climate_cool(entity_id):
            _LOGGER.debug(
                "%s: AC climate delayed OFF skipped — another thermostat now needs cooling",
                self._attr_name,
            )
            return
        remaining = self._climate_runtime_remaining(entity_id)
        if remaining > 0:
            self._schedule_climate_off(entity_id, remaining)
            return
        await self._async_execute_climate_off(entity_id)

    async def _async_execute_climate_off(self, entity_id: str) -> None:
        _LOGGER.debug("%s: AC climate OFF — %s", self._attr_name, entity_id)
        await self.hass.services.async_call(
            "climate", "set_hvac_mode",
            {"entity_id": entity_id, "hvac_mode": HVACMode.OFF},
            blocking=True,
        )

    async def _async_turn_off_climate_if_safe(self) -> None:
        """Turn the AC climate entity OFF, unless:
        - another thermostat sharing it still needs cooling, or
        - it hasn't been running for the configured minimum runtime yet
          (in which case OFF is scheduled for when that time is up).
        """
        entity_id = self._ac_climate_entity
        if not entity_id:
            return

        if self._other_thermostat_needs_climate_cool(entity_id):
            _LOGGER.debug(
                "%s: AC climate OFF skipped — another thermostat is still cooling",
                self._attr_name,
            )
            return

        remaining = self._climate_runtime_remaining(entity_id)
        if remaining <= 0:
            self._cancel_pending_climate_off(entity_id)
            await self._async_execute_climate_off(entity_id)
        else:
            _LOGGER.debug(
                "%s: AC climate min runtime protection — delaying OFF by %.0fs",
                self._attr_name, remaining,
            )
            self._schedule_climate_off(entity_id, remaining)

    async def _async_set_climate_cool(self) -> None:
        """Turn the AC climate entity ON for cooling at the configured fixed temperature."""
        entity_id = self._ac_climate_entity
        if not entity_id:
            return

        # We need it on now — cancel any pending delayed OFF for this AC
        self._cancel_pending_climate_off(entity_id)

        state = self.hass.states.get(entity_id)
        if state is None or state.state != HVACMode.COOL:
            await self.hass.services.async_call(
                "climate", "set_hvac_mode",
                {"entity_id": entity_id, "hvac_mode": HVACMode.COOL},
                blocking=True,
            )
        await self.hass.services.async_call(
            "climate", "set_temperature",
            {"entity_id": entity_id, "temperature": self._ac_climate_cool_temp},
            blocking=True,
        )

    # ------------------------------------------------------------------ #
    #  Service handlers
    # ------------------------------------------------------------------ #

    async def async_turn_on(self) -> None:
        if HVACMode.HEAT in self._attr_hvac_modes:
            await self.async_set_hvac_mode(HVACMode.HEAT)
        elif len(self._attr_hvac_modes) > 1:
            await self.async_set_hvac_mode(self._attr_hvac_modes[1])

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode not in self._attr_hvac_modes:
            return
        if hvac_mode == HVACMode.HEAT:
            if self._cool_type == COOL_TYPE_SWITCH:
                await self._async_turn_off_switch(self._cool_switch)
            elif self._cool_type == COOL_TYPE_SCENE:
                await self._async_turn_off_cool_scene_if_safe()
            elif self._cool_type == COOL_TYPE_CLIMATE:
                await self._async_turn_off_climate_if_safe()
        elif hvac_mode == HVACMode.COOL:
            await self._async_turn_off_switch(self._heat_switch)
        self._attr_hvac_mode = hvac_mode
        await self._async_control()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        self._attr_target_temperature = float(temp)
        self._attr_preset_mode = PRESET_NONE
        await self._async_control()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in self._attr_preset_modes:
            return
        self._attr_preset_mode = preset_mode
        if preset_mode != PRESET_NONE and preset_mode in self._presets:
            self._attr_target_temperature = float(self._presets[preset_mode])
        await self._async_control()
