"""Config flow for Smart Thermostat integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

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
)

_LOGGER = logging.getLogger(__name__)


def _get_entities(hass, domain):
    """Get all entities of a given domain."""
    result = {}
    for state in hass.states.async_all(domain):
        eid = state.entity_id
        name = state.attributes.get("friendly_name", eid)
        result[eid] = f"{name} ({eid})"
    return dict(sorted(result.items(), key=lambda x: x[1]))


def _get_temp_sensors(hass):
    """Get all temperature sensors."""
    result = {}
    for state in hass.states.async_all("sensor"):
        eid = state.entity_id
        device_class = state.attributes.get("device_class", "")
        unit = state.attributes.get("unit_of_measurement", "")
        if device_class == "temperature" or unit in ["°C", "°F", "K"]:
            name = state.attributes.get("friendly_name", eid)
            result[eid] = f"{name} ({eid})"
    return dict(sorted(result.items(), key=lambda x: x[1]))


def _get_window_sensors(hass):
    """Get door/window binary sensors."""
    result = {}
    WINDOW_CLASSES = {"door", "window", "opening", "garage_door"}
    for state in hass.states.async_all("binary_sensor"):
        eid = state.entity_id
        device_class = state.attributes.get("device_class", "")
        if device_class in WINDOW_CLASSES:
            name = state.attributes.get("friendly_name", eid)
            result[eid] = f"{name} ({eid})"
    return dict(sorted(result.items(), key=lambda x: x[1]))


class SmartThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Thermostat."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step — basic config."""
        errors = {}

        temp_sensors = _get_temp_sensors(self.hass)
        switches = _get_entities(self.hass, "switch")
        window_sensors = _get_window_sensors(self.hass)

        if not temp_sensors:
            return self.async_abort(reason="no_temp_sensors")
        if not switches:
            return self.async_abort(reason="no_switches")

        # Add "none" option for optional fields
        optional_sensors = {"none": "— Fără senzor —", **window_sensors}
        optional_temp = {"none": "— Fără senzor exterior —", **temp_sensors}
        optional_switch = {"none": "— Fără switch AC —", **switches}

        if user_input is not None:
            name = user_input.get(CONF_THERMOSTAT_NAME, "").strip()
            if not name:
                errors[CONF_THERMOSTAT_NAME] = "name_required"
            elif not user_input.get(CONF_TEMP_SENSOR):
                errors[CONF_TEMP_SENSOR] = "entity_required"
            elif not user_input.get(CONF_HEAT_SWITCH):
                errors[CONF_HEAT_SWITCH] = "entity_required"
            elif user_input.get(CONF_MIN_TEMP, 0) >= user_input.get(CONF_MAX_TEMP, 0):
                errors[CONF_MIN_TEMP] = "invalid_range"
            else:
                # Clean up "none" selections
                data = dict(user_input)
                for key in [CONF_COOL_SWITCH, CONF_WINDOW_SENSOR, CONF_OUTDOOR_SENSOR]:
                    if data.get(key) == "none":
                        data[key] = None

                await self.async_set_unique_id(f"{DOMAIN}_{name}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=name, data=data)

        schema = vol.Schema({
            vol.Required(CONF_THERMOSTAT_NAME, default="Termostat Camera"): str,
            vol.Required(CONF_TEMP_SENSOR): vol.In(temp_sensors),
            vol.Required(CONF_HEAT_SWITCH): vol.In(switches),
            vol.Optional(CONF_COOL_SWITCH, default="none"): vol.In(optional_switch),
            vol.Optional(CONF_WINDOW_SENSOR, default="none"): vol.In(optional_sensors),
            vol.Optional(CONF_OUTDOOR_SENSOR, default="none"): vol.In(optional_temp),
            vol.Required(CONF_TARGET_TEMP, default=DEFAULT_TARGET_TEMP): vol.All(
                vol.Coerce(float), vol.Range(min=5, max=35)
            ),
            vol.Required(CONF_HYSTERESIS, default=DEFAULT_HYSTERESIS): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=2)
            ),
            vol.Required(CONF_OUTDOOR_TEMP_THRESHOLD, default=DEFAULT_OUTDOOR_THRESHOLD): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=40)
            ),
            vol.Required(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.All(
                vol.Coerce(float), vol.Range(min=5, max=30)
            ),
            vol.Required(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.All(
                vol.Coerce(float), vol.Range(min=10, max=35)
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SmartThermostatOptionsFlow()


class SmartThermostatOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def _current(self):
        return {**self.config_entry.data, **self.config_entry.options}

    async def async_step_init(self, user_input=None):
        """Show options menu."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "edit_config":
                return await self.async_step_edit_config()
            if action == "edit_params":
                return await self.async_step_edit_params()

        schema = vol.Schema({
            vol.Required("action"): vol.In({
                "edit_config": "Modifica configuratia (senzori, switch-uri)",
                "edit_params": "Modifica parametrii (temperatura, histereza, prag exterior)",
            }),
        })
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_edit_config(self, user_input=None):
        """Edit sensors and switches."""
        errors = {}
        current = self._current()

        temp_sensors = _get_temp_sensors(self.hass)
        switches = _get_entities(self.hass, "switch")
        window_sensors = _get_window_sensors(self.hass)

        optional_sensors = {"none": "— Fără senzor —", **window_sensors}
        optional_temp = {"none": "— Fără senzor exterior —", **temp_sensors}
        optional_switch = {"none": "— Fără switch AC —", **switches}

        if user_input is not None:
            if not user_input.get(CONF_TEMP_SENSOR):
                errors[CONF_TEMP_SENSOR] = "entity_required"
            elif not user_input.get(CONF_HEAT_SWITCH):
                errors[CONF_HEAT_SWITCH] = "entity_required"
            else:
                data = dict(user_input)
                for key in [CONF_COOL_SWITCH, CONF_WINDOW_SENSOR, CONF_OUTDOOR_SENSOR]:
                    if data.get(key) == "none":
                        data[key] = None
                return self.async_create_entry(title="", data={**self.config_entry.options, **data})

        schema = vol.Schema({
            vol.Required(CONF_TEMP_SENSOR, default=current.get(CONF_TEMP_SENSOR)): vol.In(temp_sensors),
            vol.Required(CONF_HEAT_SWITCH, default=current.get(CONF_HEAT_SWITCH)): vol.In(switches),
            vol.Optional(CONF_COOL_SWITCH, default=current.get(CONF_COOL_SWITCH) or "none"): vol.In(optional_switch),
            vol.Optional(CONF_WINDOW_SENSOR, default=current.get(CONF_WINDOW_SENSOR) or "none"): vol.In(optional_sensors),
            vol.Optional(CONF_OUTDOOR_SENSOR, default=current.get(CONF_OUTDOOR_SENSOR) or "none"): vol.In(optional_temp),
        })

        return self.async_show_form(step_id="edit_config", data_schema=schema, errors=errors)

    async def async_step_edit_params(self, user_input=None):
        """Edit temperature parameters."""
        errors = {}
        current = self._current()

        if user_input is not None:
            if user_input.get(CONF_MIN_TEMP, 0) >= user_input.get(CONF_MAX_TEMP, 0):
                errors[CONF_MIN_TEMP] = "invalid_range"
            else:
                return self.async_create_entry(title="", data={**self.config_entry.options, **user_input})

        schema = vol.Schema({
            vol.Required(CONF_TARGET_TEMP, default=float(current.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP))): vol.All(
                vol.Coerce(float), vol.Range(min=5, max=35)
            ),
            vol.Required(CONF_HYSTERESIS, default=float(current.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS))): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=2)
            ),
            vol.Required(CONF_OUTDOOR_TEMP_THRESHOLD, default=float(current.get(CONF_OUTDOOR_TEMP_THRESHOLD, DEFAULT_OUTDOOR_THRESHOLD))): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=40)
            ),
            vol.Required(CONF_MIN_TEMP, default=float(current.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP))): vol.All(
                vol.Coerce(float), vol.Range(min=5, max=30)
            ),
            vol.Required(CONF_MAX_TEMP, default=float(current.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP))): vol.All(
                vol.Coerce(float), vol.Range(min=10, max=35)
            ),
        })

        return self.async_show_form(step_id="edit_params", data_schema=schema, errors=errors)
