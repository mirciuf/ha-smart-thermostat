"""Config flow for Smart Thermostat integration."""
from __future__ import annotations

import json
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er

from .const import (
    DOMAIN,
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
    resolve_cool_type,
)

_LOGGER = logging.getLogger(__name__)


def _get_temp_sensors(hass):
    result = {}
    for state in hass.states.async_all("sensor"):
        eid = state.entity_id
        device_class = state.attributes.get("device_class", "")
        unit = state.attributes.get("unit_of_measurement", "")
        if device_class == "temperature" or unit in ["°C", "°F", "K"]:
            name = state.attributes.get("friendly_name", eid)
            result[eid] = f"{name} ({eid})"
    return dict(sorted(result.items(), key=lambda x: x[1]))


def _get_switches(hass):
    result = {}
    for state in hass.states.async_all("switch"):
        eid = state.entity_id
        name = state.attributes.get("friendly_name", eid)
        result[eid] = f"{name} ({eid})"
    return dict(sorted(result.items(), key=lambda x: x[1]))


def _get_window_sensors(hass):
    result = {}
    WINDOW_CLASSES = {"door", "window", "opening", "garage_door"}
    for state in hass.states.async_all("binary_sensor"):
        eid = state.entity_id
        device_class = state.attributes.get("device_class", "")
        if device_class in WINDOW_CLASSES:
            name = state.attributes.get("friendly_name", eid)
            result[eid] = f"{name} ({eid})"
    return dict(sorted(result.items(), key=lambda x: x[1]))


def _get_scenes(hass):
    result = {}
    for state in hass.states.async_all("scene"):
        eid = state.entity_id
        name = state.attributes.get("friendly_name", eid)
        result[eid] = f"{name} ({eid})"
    return dict(sorted(result.items(), key=lambda x: x[1]))


def _get_climates(hass):
    """Return climate entities, excluding the ones created by this integration itself."""
    result = {}
    registry = er.async_get(hass)
    for state in hass.states.async_all("climate"):
        eid = state.entity_id
        entry = registry.async_get(eid)
        if entry and entry.platform == DOMAIN:
            continue  # Don't allow picking one of our own smart thermostats
        name = state.attributes.get("friendly_name", eid)
        result[eid] = f"{name} ({eid})"
    return dict(sorted(result.items(), key=lambda x: x[1]))


COOL_TYPE_OPTIONS = {
    COOL_TYPE_NONE: "— Fără răcire —",
    COOL_TYPE_SWITCH: "Switch",
    COOL_TYPE_SCENE: "Scenă (pornire/oprire)",
    COOL_TYPE_CLIMATE: "Climate Entity (AC / IR)",
}


def _validate_cool_fields(user_input: dict, errors: dict) -> None:
    """Validate the fields relevant to the selected cool_type."""
    cool_type = user_input.get(CONF_COOL_TYPE, COOL_TYPE_NONE)

    if cool_type == COOL_TYPE_SWITCH:
        if user_input.get(CONF_COOL_SWITCH, "none") == "none":
            errors[CONF_COOL_SWITCH] = "cool_field_required"
    elif cool_type == COOL_TYPE_SCENE:
        if user_input.get(CONF_AC_SCENE_COOL_ON, "none") == "none":
            errors[CONF_AC_SCENE_COOL_ON] = "cool_field_required"
        if user_input.get(CONF_AC_SCENE_COOL_OFF, "none") == "none":
            errors[CONF_AC_SCENE_COOL_OFF] = "cool_field_required"
    elif cool_type == COOL_TYPE_CLIMATE:
        if user_input.get(CONF_AC_CLIMATE_ENTITY, "none") == "none":
            errors[CONF_AC_CLIMATE_ENTITY] = "cool_field_required"


def _clean_cool_fields(data: dict) -> None:
    """Null out cool-related fields that don't belong to the selected cool_type,
    so stale leftovers from a previous selection don't linger in storage."""
    cool_type = data.get(CONF_COOL_TYPE, COOL_TYPE_NONE)

    if cool_type != COOL_TYPE_SWITCH:
        data[CONF_COOL_SWITCH] = None
    if cool_type != COOL_TYPE_SCENE:
        data[CONF_AC_SCENE_COOL_ON] = None
        data[CONF_AC_SCENE_COOL_OFF] = None
    if cool_type != COOL_TYPE_CLIMATE:
        data[CONF_AC_CLIMATE_ENTITY] = None

    for key in (CONF_COOL_SWITCH, CONF_AC_SCENE_COOL_ON, CONF_AC_SCENE_COOL_OFF, CONF_AC_CLIMATE_ENTITY):
        if data.get(key) == "none":
            data[key] = None


class SmartThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        temp_sensors = _get_temp_sensors(self.hass)
        switches = _get_switches(self.hass)
        window_sensors = _get_window_sensors(self.hass)
        scenes = _get_scenes(self.hass)
        climates = _get_climates(self.hass)

        if not temp_sensors:
            return self.async_abort(reason="no_temp_sensors")
        if not switches:
            return self.async_abort(reason="no_switches")

        opt_window = {"none": "— Fără senzor —", **window_sensors}
        opt_temp = {"none": "— Fără senzor exterior —", **temp_sensors}
        opt_switch_cool = {"none": "— Fără switch AC —", **switches}
        opt_scene = {"none": "— Fără scenă —", **scenes}
        opt_climate = {"none": "— Fără climate entity —", **climates}

        if user_input is not None:
            name = user_input.get(CONF_THERMOSTAT_NAME, "").strip()
            if not name:
                errors[CONF_THERMOSTAT_NAME] = "name_required"
            elif not user_input.get(CONF_TEMP_SENSOR):
                errors[CONF_TEMP_SENSOR] = "entity_required"
            elif not user_input.get(CONF_HEAT_SWITCH):
                errors[CONF_HEAT_SWITCH] = "entity_required"
            elif float(user_input.get(CONF_MIN_TEMP, 0)) >= float(user_input.get(CONF_MAX_TEMP, 0)):
                errors[CONF_MIN_TEMP] = "invalid_range"
            else:
                _validate_cool_fields(user_input, errors)

            if not errors:
                data = dict(user_input)
                for key in [CONF_WINDOW_SENSOR, CONF_WINDOW_SENSOR_2, CONF_OUTDOOR_SENSOR]:
                    if data.get(key) == "none":
                        data[key] = None
                _clean_cool_fields(data)
                data[CONF_PRESETS] = "{}"
                await self.async_set_unique_id(f"{DOMAIN}_{name}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=name, data=data)

        schema = vol.Schema({
            vol.Required(CONF_THERMOSTAT_NAME, default="Termostat Camera"): str,
            vol.Required(CONF_TEMP_SENSOR): vol.In(temp_sensors),
            vol.Required(CONF_HEAT_SWITCH): vol.In(switches),
            # Cool — tip + câmpuri pentru toate tipurile (doar cele relevante tipului ales sunt folosite)
            vol.Required(CONF_COOL_TYPE, default=COOL_TYPE_NONE): vol.In(COOL_TYPE_OPTIONS),
            vol.Optional(CONF_COOL_SWITCH, default="none"): vol.In(opt_switch_cool),
            vol.Optional(CONF_AC_SCENE_COOL_ON, default="none"): vol.In(opt_scene),
            vol.Optional(CONF_AC_SCENE_COOL_OFF, default="none"): vol.In(opt_scene),
            vol.Optional(CONF_AC_CLIMATE_ENTITY, default="none"): vol.In(opt_climate),
            vol.Optional(CONF_AC_CLIMATE_COOL_TEMP, default=DEFAULT_AC_CLIMATE_COOL_TEMP): vol.All(vol.Coerce(float), vol.Range(min=16, max=30)),
            vol.Optional(CONF_AC_CLIMATE_MIN_RUNTIME, default=DEFAULT_AC_CLIMATE_MIN_RUNTIME): vol.All(vol.Coerce(int), vol.Range(min=0, max=120)),
            # Window sensors
            vol.Optional(CONF_WINDOW_SENSOR, default="none"): vol.In(opt_window),
            vol.Optional(CONF_WINDOW_SENSOR_2, default="none"): vol.In(opt_window),
            # Outdoor
            vol.Optional(CONF_OUTDOOR_SENSOR, default="none"): vol.In(opt_temp),
            # Params
            vol.Required(CONF_TARGET_TEMP, default=DEFAULT_TARGET_TEMP): vol.All(vol.Coerce(float), vol.Range(min=5, max=35)),
            vol.Required(CONF_HYSTERESIS, default=DEFAULT_HYSTERESIS): vol.All(vol.Coerce(float), vol.Range(min=0, max=2)),
            vol.Required(CONF_OUTDOOR_TEMP_THRESHOLD, default=DEFAULT_OUTDOOR_THRESHOLD): vol.All(vol.Coerce(float), vol.Range(min=0, max=40)),
            vol.Required(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.All(vol.Coerce(float), vol.Range(min=5, max=30)),
            vol.Required(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.All(vol.Coerce(float), vol.Range(min=10, max=35)),
            vol.Required(CONF_TEMP_STEP, default=DEFAULT_TEMP_STEP): vol.In({
                0.1: "0.1°C",
                0.2: "0.2°C",
                0.5: "0.5°C",
                1.0: "1.0°C",
            }),
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SmartThermostatOptionsFlow()


class SmartThermostatOptionsFlow(config_entries.OptionsFlow):

    def _current(self):
        return {**self.config_entry.data, **self.config_entry.options}

    def _get_presets(self) -> dict:
        current = self._current()
        raw = current.get(CONF_PRESETS, "{}")
        try:
            return json.loads(raw) if isinstance(raw, str) else (raw or {})
        except (json.JSONDecodeError, TypeError):
            return {}

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            action = user_input.get("action")
            if action == "edit_config":
                return await self.async_step_edit_config()
            if action == "edit_params":
                return await self.async_step_edit_params()
            if action == "manage_presets":
                return await self.async_step_manage_presets()

        schema = vol.Schema({
            vol.Required("action"): vol.In({
                "edit_config":    "Modifica senzori si switch-uri",
                "edit_params":    "Modifica parametrii (temperatura, histereza, prag exterior)",
                "manage_presets": "Gestioneaza preseturi",
            }),
        })
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_edit_config(self, user_input=None):
        errors = {}
        current = self._current()

        temp_sensors = _get_temp_sensors(self.hass)
        switches = _get_switches(self.hass)
        window_sensors = _get_window_sensors(self.hass)
        scenes = _get_scenes(self.hass)
        climates = _get_climates(self.hass)

        opt_window = {"none": "— Fără senzor —", **window_sensors}
        opt_temp = {"none": "— Fără senzor exterior —", **temp_sensors}
        opt_switch_cool = {"none": "— Fără switch AC —", **switches}
        opt_scene = {"none": "— Fără scenă —", **scenes}
        opt_climate = {"none": "— Fără climate entity —", **climates}

        current_cool_type = resolve_cool_type(current)

        if user_input is not None:
            if not user_input.get(CONF_TEMP_SENSOR):
                errors[CONF_TEMP_SENSOR] = "entity_required"
            elif not user_input.get(CONF_HEAT_SWITCH):
                errors[CONF_HEAT_SWITCH] = "entity_required"
            else:
                _validate_cool_fields(user_input, errors)

            if not errors:
                data = dict(user_input)
                for key in [CONF_WINDOW_SENSOR, CONF_WINDOW_SENSOR_2, CONF_OUTDOOR_SENSOR]:
                    if data.get(key) == "none":
                        data[key] = None
                _clean_cool_fields(data)
                return self.async_create_entry(title="", data={**self.config_entry.options, **data})

        schema = vol.Schema({
            vol.Required(CONF_TEMP_SENSOR, default=current.get(CONF_TEMP_SENSOR)): vol.In(temp_sensors),
            vol.Required(CONF_HEAT_SWITCH, default=current.get(CONF_HEAT_SWITCH)): vol.In(switches),
            vol.Required(CONF_COOL_TYPE, default=current_cool_type): vol.In(COOL_TYPE_OPTIONS),
            vol.Optional(CONF_COOL_SWITCH, default=current.get(CONF_COOL_SWITCH) or "none"): vol.In(opt_switch_cool),
            vol.Optional(CONF_AC_SCENE_COOL_ON, default=current.get(CONF_AC_SCENE_COOL_ON) or "none"): vol.In(opt_scene),
            vol.Optional(CONF_AC_SCENE_COOL_OFF, default=current.get(CONF_AC_SCENE_COOL_OFF) or "none"): vol.In(opt_scene),
            vol.Optional(CONF_AC_CLIMATE_ENTITY, default=current.get(CONF_AC_CLIMATE_ENTITY) or "none"): vol.In(opt_climate),
            vol.Optional(CONF_AC_CLIMATE_COOL_TEMP, default=float(current.get(CONF_AC_CLIMATE_COOL_TEMP, DEFAULT_AC_CLIMATE_COOL_TEMP))): vol.All(vol.Coerce(float), vol.Range(min=16, max=30)),
            vol.Optional(CONF_AC_CLIMATE_MIN_RUNTIME, default=int(current.get(CONF_AC_CLIMATE_MIN_RUNTIME, DEFAULT_AC_CLIMATE_MIN_RUNTIME))): vol.All(vol.Coerce(int), vol.Range(min=0, max=120)),
            vol.Optional(CONF_WINDOW_SENSOR, default=current.get(CONF_WINDOW_SENSOR) or "none"): vol.In(opt_window),
            vol.Optional(CONF_WINDOW_SENSOR_2, default=current.get(CONF_WINDOW_SENSOR_2) or "none"): vol.In(opt_window),
            vol.Optional(CONF_OUTDOOR_SENSOR, default=current.get(CONF_OUTDOOR_SENSOR) or "none"): vol.In(opt_temp),
        })
        return self.async_show_form(step_id="edit_config", data_schema=schema, errors=errors)

    async def async_step_edit_params(self, user_input=None):
        errors = {}
        current = self._current()

        if user_input is not None:
            if float(user_input.get(CONF_MIN_TEMP, 0)) >= float(user_input.get(CONF_MAX_TEMP, 0)):
                errors[CONF_MIN_TEMP] = "invalid_range"
            else:
                return self.async_create_entry(title="", data={**self.config_entry.options, **user_input})

        schema = vol.Schema({
            vol.Required(CONF_TARGET_TEMP, default=float(current.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP))): vol.All(vol.Coerce(float), vol.Range(min=5, max=35)),
            vol.Required(CONF_HYSTERESIS, default=float(current.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS))): vol.All(vol.Coerce(float), vol.Range(min=0, max=2)),
            vol.Required(CONF_OUTDOOR_TEMP_THRESHOLD, default=float(current.get(CONF_OUTDOOR_TEMP_THRESHOLD, DEFAULT_OUTDOOR_THRESHOLD))): vol.All(vol.Coerce(float), vol.Range(min=0, max=40)),
            vol.Required(CONF_MIN_TEMP, default=float(current.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP))): vol.All(vol.Coerce(float), vol.Range(min=5, max=30)),
            vol.Required(CONF_MAX_TEMP, default=float(current.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP))): vol.All(vol.Coerce(float), vol.Range(min=10, max=35)),
            vol.Required(CONF_TEMP_STEP, default=float(current.get(CONF_TEMP_STEP, DEFAULT_TEMP_STEP))): vol.In({
                0.1: "0.1°C",
                0.2: "0.2°C",
                0.5: "0.5°C",
                1.0: "1.0°C",
            }),
        })
        return self.async_show_form(step_id="edit_params", data_schema=schema, errors=errors)

    async def async_step_manage_presets(self, user_input=None):
        presets = self._get_presets()

        if user_input is not None:
            action = user_input.get("preset_action")
            if action == "add":
                return await self.async_step_add_preset()
            if action == "delete" and presets:
                return await self.async_step_delete_preset()

        options = {"add": "➕ Adauga preset nou"}
        if presets:
            options["delete"] = "🗑️ Sterge un preset"

        preset_list = "\n".join([f"• {name}: {temp}°C" for name, temp in presets.items()])

        schema = vol.Schema({
            vol.Required("preset_action"): vol.In(options),
        })
        return self.async_show_form(
            step_id="manage_presets",
            data_schema=schema,
            description_placeholders={
                "preset_list": preset_list if preset_list else "Nu există preseturi configurate.",
            },
        )

    async def async_step_add_preset(self, user_input=None):
        errors = {}
        presets = self._get_presets()
        current = self._current()

        if user_input is not None:
            name = user_input.get("preset_name", "").strip()
            temp = user_input.get("preset_temp")
            if not name:
                errors["preset_name"] = "name_required"
            elif temp is None:
                errors["preset_temp"] = "invalid_value"
            else:
                presets[name] = float(temp)
                new_options = {**self.config_entry.options, CONF_PRESETS: json.dumps(presets)}
                return self.async_create_entry(title="", data=new_options)

        schema = vol.Schema({
            vol.Required("preset_name"): str,
            vol.Required("preset_temp", default=float(current.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP))): vol.All(vol.Coerce(float), vol.Range(min=5, max=35)),
        })
        return self.async_show_form(step_id="add_preset", data_schema=schema, errors=errors)

    async def async_step_delete_preset(self, user_input=None):
        errors = {}
        presets = self._get_presets()

        if not presets:
            return await self.async_step_manage_presets()

        if user_input is not None:
            name = user_input.get("preset_to_delete")
            if name and name in presets:
                del presets[name]
                new_options = {**self.config_entry.options, CONF_PRESETS: json.dumps(presets)}
                return self.async_create_entry(title="", data=new_options)

        schema = vol.Schema({
            vol.Required("preset_to_delete"): vol.In(
                {name: f"{name} ({temp}°C)" for name, temp in presets.items()}
            ),
        })
        return self.async_show_form(step_id="delete_preset", data_schema=schema, errors=errors)
