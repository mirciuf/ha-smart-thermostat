"""Climate platform for Smart Thermostat."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
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

from .const import (
    DOMAIN,
    CONF_THERMOSTAT_NAME,
    CONF_TEMP_SENSOR,
    CONF_HEAT_SWITCH,
    CONF_COOL_SWITCH,
    CONF_WINDOW_SENSOR,
    CONF_OUTDOOR_SENSOR,
    CONF_TARGET_TEMP,
    CONF_HYSTERESIS,
    CONF_OUTDOOR_TEMP_THRESHOLD,
    CONF_MIN_TEMP,
    CONF_MAX_TEMP,
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
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart Thermostat climate entity."""
    config = {**entry.data, **entry.options}

    thermostat = SmartThermostat(
        hass=hass,
        entry_id=entry.entry_id,
        name=config.get(CONF_THERMOSTAT_NAME, "Smart Thermostat"),
        temp_sensor=config[CONF_TEMP_SENSOR],
        heat_switch=config[CONF_HEAT_SWITCH],
        cool_switch=config.get(CONF_COOL_SWITCH),
        window_sensor=config.get(CONF_WINDOW_SENSOR),
        outdoor_sensor=config.get(CONF_OUTDOOR_SENSOR),
        target_temp=float(config.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP)),
        hysteresis=float(config.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)),
        outdoor_threshold=float(config.get(CONF_OUTDOOR_TEMP_THRESHOLD, DEFAULT_OUTDOOR_THRESHOLD)),
        min_temp=float(config.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)),
        max_temp=float(config.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)),
    )

    async_add_entities([thermostat], True)


class SmartThermostat(RestoreEntity, ClimateEntity):
    """Smart Thermostat climate entity."""

    _attr_should_poll = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        temp_sensor: str,
        heat_switch: str,
        cool_switch: str | None,
        window_sensor: str | None,
        outdoor_sensor: str | None,
        target_temp: float,
        hysteresis: float,
        outdoor_threshold: float,
        min_temp: float,
        max_temp: float,
    ) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{entry_id}"

        # Config
        self._temp_sensor = temp_sensor
        self._heat_switch = heat_switch
        self._cool_switch = cool_switch
        self._window_sensor = window_sensor
        self._outdoor_sensor = outdoor_sensor
        self._hysteresis = hysteresis
        self._outdoor_threshold = outdoor_threshold
        self._attr_min_temp = min_temp
        self._attr_max_temp = max_temp

        # State
        self._attr_target_temperature = target_temp
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_current_temperature = None
        self._window_open = False
        self._outdoor_temp = None

        # HVAC modes available depend on whether cool_switch is configured
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        if cool_switch:
            self._attr_hvac_modes.append(HVACMode.COOL)

        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )

    # ------------------------------------------------------------------ #
    #  Properties
    # ------------------------------------------------------------------ #

    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action."""
        if self._attr_hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self._window_open:
            return HVACAction.IDLE

        heat_on = self._is_switch_on(self._heat_switch)
        cool_on = self._cool_switch and self._is_switch_on(self._cool_switch)

        if heat_on:
            return HVACAction.HEATING
        if cool_on:
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
            ATTR_COOL_SWITCH: self._cool_switch,
        }

    # ------------------------------------------------------------------ #
    #  Setup & restore
    # ------------------------------------------------------------------ #

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to events."""
        await super().async_added_to_hass()

        # Restore previous state
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                mode = last_state.state
                if mode in [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]:
                    self._attr_hvac_mode = mode

                target = last_state.attributes.get(ATTR_TEMPERATURE)
                if target is not None:
                    self._attr_target_temperature = float(target)

                self._hysteresis = float(
                    last_state.attributes.get(ATTR_HYSTERESIS, self._hysteresis)
                )
                self._outdoor_threshold = float(
                    last_state.attributes.get(ATTR_OUTDOOR_THRESHOLD, self._outdoor_threshold)
                )
                _LOGGER.debug("Restored %s: mode=%s target=%.1f", self._attr_name, mode, self._attr_target_temperature)
            except (ValueError, TypeError) as err:
                _LOGGER.warning("Could not restore state for %s: %s", self._attr_name, err)

        # Read current sensor states
        self._update_current_temp()
        self._update_window_state()
        self._update_outdoor_temp()

        # Subscribe to state changes
        self.async_on_remove(
            self.hass.bus.async_listen("state_changed", self._handle_state_change)
        )

        # Initial control cycle
        await self._async_control()

    # ------------------------------------------------------------------ #
    #  State change handler
    # ------------------------------------------------------------------ #

    @callback
    def _handle_state_change(self, event: Event) -> None:
        """Handle state changes from sensors and switches."""
        entity_id = event.data.get("entity_id")

        changed = False

        if entity_id == self._temp_sensor:
            self._update_current_temp()
            changed = True

        if self._window_sensor and entity_id == self._window_sensor:
            self._update_window_state()
            changed = True

        if self._outdoor_sensor and entity_id == self._outdoor_sensor:
            self._update_outdoor_temp()
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
        if not self._window_sensor:
            self._window_open = False
            return
        state = self.hass.states.get(self._window_sensor)
        if state:
            self._window_open = state.state in (STATE_ON, STATE_OPEN, "on", "open")

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
        """Main control loop — decides what to turn on/off."""
        current = self._attr_current_temperature
        target = self._attr_target_temperature
        mode = self._attr_hvac_mode

        # Always turn off both if mode is OFF
        if mode == HVACMode.OFF:
            await self._async_turn_off_all()
            self.async_write_ha_state()
            return

        # Window open → turn off everything
        if self._window_open:
            _LOGGER.debug("%s: Window open — turning off", self._attr_name)
            await self._async_turn_off_all()
            self.async_write_ha_state()
            return

        if current is None:
            _LOGGER.warning("%s: No temperature reading — skipping control", self._attr_name)
            return

        if mode == HVACMode.HEAT:
            # Check outdoor temperature threshold
            if self._outdoor_temp is not None and self._outdoor_temp > self._outdoor_threshold:
                _LOGGER.debug(
                    "%s: Outdoor temp %.1f > threshold %.1f — heat blocked",
                    self._attr_name, self._outdoor_temp, self._outdoor_threshold
                )
                await self._async_turn_off_switch(self._heat_switch)
                self.async_write_ha_state()
                return

            heat_on = self._is_switch_on(self._heat_switch)

            if heat_on:
                # Turn off heat when temp reaches target + hysteresis
                if current >= target + self._hysteresis:
                    _LOGGER.debug("%s: HEAT OFF — %.1f >= %.1f", self._attr_name, current, target + self._hysteresis)
                    await self._async_turn_off_switch(self._heat_switch)
            else:
                # Turn on heat when temp drops below target - hysteresis
                if current <= target - self._hysteresis:
                    _LOGGER.debug("%s: HEAT ON — %.1f <= %.1f", self._attr_name, current, target - self._hysteresis)
                    await self._async_turn_on_switch(self._heat_switch)

        elif mode == HVACMode.COOL and self._cool_switch:
            cool_on = self._is_switch_on(self._cool_switch)

            if cool_on:
                # Turn off cool when temp drops to target - hysteresis
                if current <= target - self._hysteresis:
                    _LOGGER.debug("%s: COOL OFF — %.1f <= %.1f", self._attr_name, current, target - self._hysteresis)
                    await self._async_turn_off_switch(self._cool_switch)
            else:
                # Turn on cool when temp rises above target + hysteresis
                if current >= target + self._hysteresis:
                    _LOGGER.debug("%s: COOL ON — %.1f >= %.1f", self._attr_name, current, target + self._hysteresis)
                    await self._async_turn_on_switch(self._cool_switch)

        self.async_write_ha_state()

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

    async def _async_turn_off_all(self) -> None:
        """Turn off both heat and cool switches."""
        await self._async_turn_off_switch(self._heat_switch)
        if self._cool_switch:
            await self._async_turn_off_switch(self._cool_switch)

    # ------------------------------------------------------------------ #
    #  Service handlers
    # ------------------------------------------------------------------ #

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode not in self._attr_hvac_modes:
            _LOGGER.warning("%s: Unsupported mode %s", self._attr_name, hvac_mode)
            return

        # Turn off the other switch when switching modes
        if hvac_mode == HVACMode.HEAT and self._cool_switch:
            await self._async_turn_off_switch(self._cool_switch)
        elif hvac_mode == HVACMode.COOL:
            await self._async_turn_off_switch(self._heat_switch)

        self._attr_hvac_mode = hvac_mode
        await self._async_control()

    async def async_turn_on(self) -> None:
        """Turn on — default to HEAT mode."""
        if HVACMode.HEAT in self._attr_hvac_modes:
            await self.async_set_hvac_mode(HVACMode.HEAT)
        elif len(self._attr_hvac_modes) > 1:
            await self.async_set_hvac_mode(self._attr_hvac_modes[1])

    async def async_turn_off(self) -> None:
        """Turn off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        self._attr_target_temperature = float(temp)
        await self._async_control()
