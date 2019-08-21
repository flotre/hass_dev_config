"""Adds support for generic smart thermostat units."""
import asyncio
import logging
import json
from datetime import datetime, timedelta
import voluptuous as vol

from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateDevice
from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    HVAC_MODE_AUTO,
    PRESET_AWAY,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    PRESET_NONE,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_HOME
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_NAME,
    EVENT_HOMEASSISTANT_START,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNKNOWN,
)
from homeassistant.core import DOMAIN as HA_DOMAIN, callback
from homeassistant.helpers import condition
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

DEFAULT_TOLERANCE = 0.3
DEFAULT_NAME = 'Generic Smart Thermostat'
DEFAULT_AWAY_TEMP = 15.0
DEFAULT_CONFORT_TEMP = 19.0
DEFAULT_ECO_TEMP = 17.0
DEFAULT_MIN_POWER = 5
DEFAULT_CALCULATE_PERIOD = 30

CONF_HEATER = 'heater'
CONF_SENSOR_IN = 'in_temp_sensor'
CONF_SENSOR_OUT = 'out_temp_sensor'
CONF_MIN_TEMP = 'min_temp'
CONF_MAX_TEMP = 'max_temp'
CONF_TARGET_TEMP = 'target_temp'
CONF_AC_MODE = 'ac_mode'
CONF_MIN_POWER = 'min_cycle_power'
CONF_COLD_TOLERANCE = 'cold_tolerance'
CONF_HOT_TOLERANCE = 'hot_tolerance'
CONF_INITIAL_HVAC_MODE = "initial_hvac_mode"
CONF_AWAY_TEMP = 'away_temp'
CONF_PRECISION = 'precision'
CONF_SCHEDULE = 'schedule'
CONF_PREHEAT = "preheat"
CONF_CONFORT_TEMP = 'confort_temp'
CONF_ECO_TEMP = 'eco_temp'
CONF_CALCULATE_PERIOD = 'calculate_period'
SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE )

PRESET_MODES = [PRESET_NONE, PRESET_AWAY, PRESET_ECO, PRESET_COMFORT]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HEATER): cv.entity_id,
        vol.Required(CONF_SENSOR_IN): cv.entity_id,
        vol.Required(CONF_SENSOR_OUT): cv.entity_id,
        vol.Optional(CONF_AC_MODE): cv.boolean,
        vol.Optional(CONF_MAX_TEMP): vol.Coerce(float),
        vol.Optional(CONF_MIN_POWER, default=DEFAULT_MIN_POWER): vol.All(int, vol.Range(min=5, max=100)),
        vol.Optional(CONF_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_COLD_TOLERANCE, default=DEFAULT_TOLERANCE): vol.Coerce(float),
        vol.Optional(CONF_HOT_TOLERANCE, default=DEFAULT_TOLERANCE): vol.Coerce(float),
        vol.Optional(CONF_TARGET_TEMP): vol.Coerce(float),
        vol.Optional(CONF_INITIAL_HVAC_MODE): vol.In(
                [HVAC_MODE_COOL, HVAC_MODE_HEAT, HVAC_MODE_OFF]
            ),
        vol.Optional(CONF_AWAY_TEMP, default=DEFAULT_AWAY_TEMP): vol.Coerce(float),
        vol.Optional(CONF_PRECISION): vol.In(
            [PRECISION_TENTHS, PRECISION_HALVES, PRECISION_WHOLE]
        ),
        vol.Optional(CONF_CONFORT_TEMP, default=DEFAULT_CONFORT_TEMP): vol.Coerce(float),
        vol.Optional(CONF_ECO_TEMP, default=DEFAULT_ECO_TEMP): vol.Coerce(float),
        vol.Optional(CONF_CALCULATE_PERIOD, default=DEFAULT_CALCULATE_PERIOD): vol.All(int, vol.Range(min=1)),
        vol.Optional(CONF_SCHEDULE, default=[]):
            vol.All(cv.ensure_list, [{vol.Required('mode'):vol.Any(vol.In(PRESET_MODES), vol.Coerce(float)),
                                      vol.Required('days'):cv.string,
                                      vol.Required('start'):cv.time
                                      }
                                    ]
            ),
        vol.Optional(CONF_PREHEAT, default=False): cv.boolean
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the generic thermostat platform."""
    name = config.get(CONF_NAME)
    heater_entity_id = config.get(CONF_HEATER)
    in_temp_sensor_entity_id = config.get(CONF_SENSOR_IN)
    out_temp_sensor_entity_id = config.get(CONF_SENSOR_OUT)
    min_temp = config.get(CONF_MIN_TEMP)
    max_temp = config.get(CONF_MAX_TEMP)
    target_temp = config.get(CONF_TARGET_TEMP)
    ac_mode = config.get(CONF_AC_MODE)
    min_cycle_power = config.get(CONF_MIN_POWER)
    cold_tolerance = config.get(CONF_COLD_TOLERANCE)
    hot_tolerance = config.get(CONF_HOT_TOLERANCE)
    initial_hvac_mode = config.get(CONF_INITIAL_HVAC_MODE)
    away_temp = config.get(CONF_AWAY_TEMP)
    eco_temp = config.get(CONF_ECO_TEMP)
    comfort_temp = config.get(CONF_CONFORT_TEMP)
    precision = config.get(CONF_PRECISION)
    calculate_period = config.get(CONF_CALCULATE_PERIOD)
    unit = hass.config.units.temperature_unit
    schedule = config.get(CONF_SCHEDULE)
    preheat = config.get(CONF_PREHEAT)

    async_add_entities(
        [
            GenericSmartThermostat(
                name,
                heater_entity_id,
                in_temp_sensor_entity_id,
                out_temp_sensor_entity_id,
                min_temp,
                max_temp,
                target_temp,
                ac_mode,
                min_cycle_power,
                cold_tolerance,
                hot_tolerance,
                initial_hvac_mode,
                away_temp,
                eco_temp,
                comfort_temp,
                precision,
                unit,
                calculate_period,
                schedule,
                preheat
            )
        ]
    )



class GenericSmartThermostat(ClimateDevice, RestoreEntity):
    """Representation of a Generic Thermostat device."""

    def __init__(
        self,
        name,
        heater_entity_id,
        in_temp_sensor_entity_id,
        out_temp_sensor_entity_id,
        min_temp,
        max_temp,
        target_temp,
        ac_mode,
        min_cycle_power,
        cold_tolerance,
        hot_tolerance,
        initial_hvac_mode,
        away_temp,
        eco_temp,
        comfort_temp,
        precision,
        unit,
        calculate_period,
        schedule,
        preheat
    ):
        """Initialize the thermostat."""
        _LOGGER.debug("debug init")
        self._name = name
        self.heater_entity_id = heater_entity_id
        self.in_temp_sensor_entity_id = in_temp_sensor_entity_id
        self.out_temp_sensor_entity_id = out_temp_sensor_entity_id
        self.InternalsDefaults = {
            'ConstC': float(60),  # inside heating coeff, depends on room size & power of your heater (60 by default)
            'ConstT': float(1),  # external heating coeff,depends on the insulation relative to the outside (1 by default)
            'nbCC': 0,  # number of learnings for ConstC
            'nbCT': 0,  # number of learnings for ConstT
            'LastPwr': 0,  # % power from last calculation
            'LastInT': float(0),  # inside temperature at last calculation
            'LastOutT': float(0),  # outside temprature at last calculation
            'LastSetPoint': float(20),  # setpoint at time of last calculation
            'ALStatus': 0}  # AutoLearning status (0 = uninitialized, 1 = initialized, 2 = disabled)
        self.Internals = self.InternalsDefaults.copy()
        self.ac_mode = ac_mode
        self.min_cycle_power = min_cycle_power
        self._cold_tolerance = cold_tolerance
        self._hot_tolerance = hot_tolerance
        self._hvac_mode = initial_hvac_mode
        self._saved_target_temp = target_temp
        self._temp_precision = precision
        if self.ac_mode:
            self._hvac_list = [HVAC_MODE_COOL, HVAC_MODE_OFF]
        else:
            self._hvac_list = [HVAC_MODE_HEAT, HVAC_MODE_OFF, HVAC_MODE_AUTO]
        self._in_temp = None
        self._out_temp = None
        self._temp_lock = asyncio.Lock()
        self._min_temp = min_temp
        self._max_temp = max_temp
        self._target_temp = target_temp
        self._unit = unit
        self._support_flags = SUPPORT_FLAGS
        self._away_temp = away_temp
        self._learn = True
        self._calculate_period = calculate_period # in minutes
        self.endheat = datetime.now()
        self.nextcalc = self.endheat
        self.lastcalc = self.endheat
        self.nextupdate = self.endheat
        self.nexttemps = self.endheat
        self.forced = False
        self.forcedduration = 60  # time in minutes for the forced mode
        self.heat = False
        # pause
        self.pauseondelay = 2  # time between pause sensor actuation and actual pause
        self.pauseoffdelay = 1  # time between end of pause sensor actuation and end of actual pause
        self.pause = False
        self.pauserequested = False
        self.pauserequestchangedtime = datetime.now()
        # modes
        self._preset_mode = PRESET_NONE
        self._preset_mode_temp = {PRESET_NONE:None, PRESET_AWAY:away_temp, PRESET_ECO:eco_temp, PRESET_COMFORT:comfort_temp}

        # pre-heat
        self._preheat = preheat

        # schedule : list of start date by day
        self._last_do_schedule = datetime.now()
        self.schedule = [{} for i in range(7)]
        self._parse_schedule(schedule)
        _LOGGER.debug("schedule: %s", self.schedule)

        _LOGGER.debug("fin init")
        

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        # Add listener
        async_track_state_change(
            self.hass, self.in_temp_sensor_entity_id, self._async_in_temp_changed
        )
        async_track_state_change(
            self.hass, self.out_temp_sensor_entity_id, self._async_out_temp_changed
        )
        async_track_state_change(
            self.hass, self.heater_entity_id, self._async_switch_changed
        )

        @callback
        def _async_startup(event):
            """Init on startup."""
            # get in temperature
            sensor_state = self.hass.states.get(self.in_temp_sensor_entity_id)
            if sensor_state and sensor_state.state != STATE_UNKNOWN:
                self._async_update_in_temp(sensor_state)
            # get out temperature
            sensor_state = self.hass.states.get(self.out_temp_sensor_entity_id)
            if sensor_state and sensor_state.state != STATE_UNKNOWN:
                self._async_update_out_temp(sensor_state)

        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _async_startup)

        # Check If we have an old state
        old_state = await self.async_get_last_state()
        if old_state is not None:
            # If we have no initial temperature, restore
            if self._target_temp is None:
                # If we have a previously saved temperature
                if old_state.attributes.get(ATTR_TEMPERATURE) is None:
                    if self.ac_mode:
                        self._target_temp = self.max_temp
                    else:
                        self._target_temp = self.min_temp
                    _LOGGER.warning(
                        "Undefined target temperature," "falling back to %s",
                        self._target_temp,
                    )
                else:
                    self._target_temp = float(old_state.attributes[ATTR_TEMPERATURE])

            self._preset_mode = old_state.attributes.get(ATTR_PRESET_MODE)

            if not self._hvac_mode and old_state.state:
                self._hvac_mode = old_state.state

            # Internals
            for k in self.Internals:
                self.Internals[k] = old_state.attributes.get(k)

        else:
            # No previous state, try and restore defaults
            if self._target_temp is None:
                if self.ac_mode:
                    self._target_temp = self.max_temp
                else:
                    self._target_temp = self.min_temp
            _LOGGER.warning(
                "No previously saved temperature, setting to %s", self._target_temp
            )
        # Set default state to off
        if not self._hvac_mode:
            self._hvac_mode = HVAC_MODE_OFF
                            
        # add heatbeat
        async_track_time_interval(self.hass, self._async_control_heating, timedelta(seconds=10))

        # schedule
        async_track_time_interval(self.hass, self._async_do_schedule, timedelta(seconds=10))
        
    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def precision(self):
        """Return the precision of the system."""
        if self._temp_precision is not None:
            return self._temp_precision
        return super().precision

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def current_temperature(self):
        """Return the sensor temperature."""
        return self._in_temp

    @property
    def hvac_mode(self):
        """Return current operation."""
        return self._hvac_mode

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        if self._hvac_mode == HVAC_MODE_OFF:
            return CURRENT_HVAC_OFF
        if not self._is_device_active:
            return CURRENT_HVAC_IDLE
        if self.ac_mode:
            return CURRENT_HVAC_COOL
        return CURRENT_HVAC_HEAT

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temp

    @property
    def hvac_modes(self):
        """List of available operation modes."""
        return self._hvac_list

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp."""
        return self._preset_mode

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        return PRESET_MODES

    @property
    def state_attributes(self):
        """Return device specific state attributes."""
        attr = super().state_attributes
        attr.update(self.Internals)
        return attr

    async def async_set_hvac_mode(self, hvac_mode):
        """Set hvac mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            self._hvac_mode = HVAC_MODE_HEAT
            _LOGGER.debug("set hvac mode to HEAT")
            await self._async_control_heating(force=True)
        elif hvac_mode == HVAC_MODE_COOL:
            self._hvac_mode = HVAC_MODE_COOL
            await self._async_control_heating(force=True)
        elif hvac_mode == HVAC_MODE_AUTO:
            self._hvac_mode = HVAC_MODE_AUTO
            await self._async_control_heating(force=True)
        elif hvac_mode == HVAC_MODE_OFF:
            self._hvac_mode = HVAC_MODE_OFF
            _LOGGER.debug("set hvac mode to OFF")
            if self._is_device_active:
                await self._async_heater_turn_off()
        else:
            _LOGGER.error("Unrecognized hvac mode: %s", hvac_mode)
            return
        # Ensure we update the current operation after changing the mode
        self.schedule_update_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._target_temp = temperature
        await self._async_control_heating(force=True)
        await self.async_update_ha_state()

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        if self._min_temp:
            return self._min_temp

        # get default temp from super class
        return super().min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        if self._max_temp:
            return self._max_temp

        # Get default temp from super class
        return super().max_temp

    async def _async_in_temp_changed(self, entity_id, old_state, new_state):
        """Handle temperature changes."""
        if new_state is None:
            return

        self._async_update_in_temp(new_state)
        await self._async_control_heating()
        await self.async_update_ha_state()

    async def _async_out_temp_changed(self, entity_id, old_state, new_state):
        """Handle temperature changes."""
        if new_state is None:
            return

        self._async_update_out_temp(new_state)
        await self._async_control_heating()
        await self.async_update_ha_state()

    @callback
    def _async_switch_changed(self, entity_id, old_state, new_state):
        """Handle heater switch state changes."""
        if new_state is None:
            return
        self.async_schedule_update_ha_state()

    @callback
    def _async_update_in_temp(self, state):
        """Update thermostat with latest indoor temperature."""
        try:
            self._in_temp = float(state.state)
        except ValueError as ex:
            _LOGGER.error("Unable to update from sensor: %s", ex)
    
    @callback
    def _async_update_out_temp(self, state):
        """Update thermostat with latest outdoor temperature."""
        try:
            self._out_temp = float(state.state)
        except ValueError as ex:
            _LOGGER.error("Unable to update from sensor: %s", ex)

    async def _async_control_heating(self, time=None, force=False):
        async with self._temp_lock:
            now = datetime.now()

            if None in (self._in_temp, self._out_temp, self._target_temp):
                _LOGGER.info(
                    "in, out or target temperature is None "
                    "Thermostat not active. %s, %s, %s",
                    self._in_temp,
                    self._out_temp,
                    self._target_temp,
                )
                return
            # Thermostat is off
            if self._hvac_mode == HVAC_MODE_OFF:
                _LOGGER.debug("Thermostat is off")
                if self.forced or self.heat:  # thermostat setting was just changed so we kill the heating
                    self.forced = False
                    self.endheat = now
                    _LOGGER.debug("Switching heat Off !")
                    await self._async_heater_turn_off()
            # Thermostat is in forced mode
            elif self._hvac_mode == HVAC_MODE_HEAT:
                _LOGGER.debug("Thermostat is forced mode")
                if self.forced:
                    if self.endheat <= now:
                        self.forced = False
                        self.endheat = now
                        _LOGGER.debug("Forced mode Off !")
                        await self.async_set_hvac_mode(HVAC_MODE_AUTO)
                        await self._async_heater_turn_off()
                else:
                    self.forced = True
                    self.endheat = now + timedelta(minutes=self.forcedduration)
                    _LOGGER.debug("Forced mode On !")
                    await self._async_heater_turn_on()
            # Thermostat is in mode auto
            elif self._hvac_mode == HVAC_MODE_AUTO:
                _LOGGER.debug("Thermostat is mode auto")
                # thermostat setting was just changed from "forced" so we kill the forced mode
                if self.forced:
                    self.forced = False
                    self.endheat = now
                    self.nextcalc = now   # this will force a recalculation on next heartbeat
                    _LOGGER.debug("Forced mode Off !")
                    await self._async_heater_turn_off()
                # heat cycle is over
                elif (self.endheat <= now or self.pause) and self.heat:
                    self.endheat = now
                    self.heat = False
                    if self.Internals['LastPwr'] < 100:
                        await self._async_heater_turn_off()
                    # if power was 100(i.e. a full cycle), then we let the next calculation (at next heartbeat) decide
                    # to switch off in order to avoid potentially damaging quick off/on cycles to the heater(s)
                # we are in pause and the pause switch is now off
                elif self.pause and not self.pauserequested:
                    if self.pauserequestchangedtime + timedelta(minutes=self.pauseoffdelay) <= now:
                        _LOGGER.info("Pause is now Off")
                        self.pause = False
                # we are not in pause and the pause switch is now on
                elif not self.pause and self.pauserequested:
                    if self.pauserequestchangedtime + timedelta(minutes=self.pauseondelay) <= now:
                        _LOGGER.info("Pause is now On")
                        self.pause = True
                        await self._async_heater_turn_off()
                # we start a new calculation
                elif ((self.nextcalc <= now) and not self.pause) or force:
                    self.nextcalc = now + timedelta(minutes=self._calculate_period)
                    _LOGGER.debug("Next calculation time will be : " + str(self.nextcalc))

                    # do the thermostat work
                    await self.auto_mode()
            else:
                _LOGGER.error("unrecognized hvac mode:", self._hvac_mode)


    @property
    def _is_device_active(self):
        """If the toggleable device is currently active."""
        return self.hass.states.is_state(self.heater_entity_id, STATE_ON)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    async def _async_heater_turn_on(self):
        """Turn heater toggleable device on."""
        data = {ATTR_ENTITY_ID: self.heater_entity_id}
        await self.hass.services.async_call(HA_DOMAIN, SERVICE_TURN_ON, data)

    async def _async_heater_turn_off(self):
        """Turn heater toggleable device off."""
        data = {ATTR_ENTITY_ID: self.heater_entity_id}
        await self.hass.services.async_call(HA_DOMAIN, SERVICE_TURN_OFF, data)

    async def async_set_preset_mode(self, preset_mode: str):
        """Set new preset mode.

        This method must be run in the event loop and returns a coroutine.
        """
        if preset_mode in self._preset_mode_temp:
            if self._preset_mode != preset_mode:
                self._preset_mode = preset_mode
                if preset_mode == PRESET_NONE:
                    self._target_temp = self._saved_target_temp
                else:
                    self._saved_target_temp = self._target_temp
                    self._target_temp = self._preset_mode_temp[preset_mode]
                
                await self._async_control_heating(force=True)
        else:
            _LOGGER.error("preset mode not supported:", preset_mode)

        await self.async_update_ha_state()


    async def auto_mode(self):
        _LOGGER.debug("Temperatures: Inside = {} / Outside = {}".format(self._in_temp, self._out_temp))

        if self._in_temp > self._target_temp + self._hot_tolerance:
            _LOGGER.debug("Temperature exceeds _target_temp")
            overshoot = True
            power = 0
        else:
            overshoot = False
            if self._learn:
                self.auto_callib()
            else:
                self._learn = True
            power = self._power(self._target_temp, self._in_temp, self._out_temp)

        if power < 0:
            power = 0  # lower limit
        elif power > 100:
            power = 100  # upper limit

        # apply minimum power as required
        if power <= self.min_cycle_power and not overshoot:
            _LOGGER.debug(
                "Calculated power is {}, applying minimum power of {}".format(power, self.min_cycle_power))
            power = self.min_cycle_power

        heatduration = round(power * self._calculate_period / 100)
        _LOGGER.debug("Calculation: Power = {} -> heat duration = {} minutes".format(power, heatduration))

        if power == 0:
            await self._async_heater_turn_off()
            _LOGGER.debug("No heating requested !")
        else:
            self.endheat = datetime.now() + timedelta(minutes=heatduration)
            _LOGGER.debug("End Heat time = " + str(self.endheat))
            await self._async_heater_turn_on()
            if self.Internals["ALStatus"] < 2:
                self.Internals['LastPwr'] = power
                self.Internals['LastInT'] = self._in_temp
                self.Internals['LastOutT'] = self._out_temp
                self.Internals['LastSetPoint'] = self._target_temp
                self.Internals['ALStatus'] = 1
                # store values
                await self.async_update_ha_state()

        self.lastcalc = datetime.now()


    def auto_callib(self):

        now = datetime.now()
        if self.Internals['ALStatus'] != 1:  # not initalized... do nothing
            _LOGGER.debug("Fist pass at AutoCallib... no callibration")
            pass
        elif self.Internals['LastPwr'] == 0:  # heater was off last time, do nothing
            _LOGGER.debug("Last power was zero... no callibration")
            pass
        elif self.Internals['LastPwr'] == 100 and self._in_temp < self.Internals['LastSetPoint']:
            # heater was on max but setpoint was not reached... no learning
            _LOGGER.debug("Last power was 100% but setpoint not reached... no callibration")
            pass
        elif self._in_temp > self.Internals['LastInT'] and self.Internals['LastSetPoint'] > self.Internals['LastInT']:
            # learning ConstC
            ConstC = (self.Internals['ConstC'] * ((self.Internals['LastSetPoint'] - self.Internals['LastInT']) /
                                                  (self._in_temp - self.Internals['LastInT']) *
                                                  (timedelta.total_seconds(now - self.lastcalc) /
                                                   (self._calculate_period * 60))))
            _LOGGER.debug("New calc for ConstC = {}".format(ConstC))
            self.Internals['ConstC'] = round((self.Internals['ConstC'] * self.Internals['nbCC'] + ConstC) /
                                             (self.Internals['nbCC'] + 1), 1)
            self.Internals['nbCC'] = min(self.Internals['nbCC'] + 1, 50)
            _LOGGER.debug("ConstC updated to {}".format(self.Internals['ConstC']))
        elif self._out_temp is not None and self.Internals['LastSetPoint'] > self.Internals['LastOutT']:
            # learning ConstT
            ConstT = (self.Internals['ConstT'] + ((self.Internals['LastSetPoint'] - self._in_temp) /
                                                  (self.Internals['LastSetPoint'] - self.Internals['LastOutT']) *
                                                  self.Internals['ConstC'] *
                                                  (timedelta.total_seconds(now - self.lastcalc) /
                                                   (self._calculate_period * 60))))
            _LOGGER.debug("New calc for ConstT = {}".format(ConstT))
            self.Internals['ConstT'] = round((self.Internals['ConstT'] * self.Internals['nbCT'] + ConstT) /
                                             (self.Internals['nbCT'] + 1), 1)
            self.Internals['nbCT'] = min(self.Internals['nbCT'] + 1, 50)
            _LOGGER.debug("ConstT updated to {}".format(self.Internals['ConstT']))

    def _power(self, target_temp, in_temp, out_temp):
        if out_temp is None:
            power = round((target_temp - in_temp) * self.Internals["ConstC"], 1)
        else:
            power = round((target_temp - in_temp) * self.Internals["ConstC"] +
                            (target_temp - out_temp) * self.Internals["ConstT"], 1)
        return power

    def _parse_schedule(self, schedule):
        for s in schedule:
            days = s['days']
            start = s['start']
            mode = s['mode']
            if "-" in days:
                # range of days
                s, e = days.split("-")
                try: 
                    days = range(int(s), int(e)+1 )
                except ValueError:
                    _LOGGER.error("schedule format error for %s (ignored)", s['days'])
                    continue
            elif "," in days:
                # list of days
                days = days.split(',')
            else:
                # unique day
                days = [days]
            # store schedule
            for d in days:
                try:
                    intday = int(d)
                except ValueError:
                    _LOGGER.error("schedule format error for %s (ignored)", s['days'])
                    continue
                if intday >= 0 and intday <= 6:
                    self.schedule[intday][start] = mode
                else:
                    _LOGGER.error("schedule format error for %s (ignored)", s['days'])
                    continue
    
    def _schedule_get_next_start(self):
        now = datetime.now()
        weekday = now.weekday()
        for i in range(7):
            wd = (weekday + i) % 7
            dict_start = sorted(self.schedule[wd])
            for start in dict_start:
                dt_start = now.replace(day=now.day+i, hour=start.hour, minute=start.minute, second=0, microsecond=0)
                if dt_start >= now:
                    # turn mode on
                    _LOGGER.debug("Schedule: next start mode %s@%s", self.schedule[wd][start], dt_start)
                    return dt_start, self.schedule[wd][start]
        
        return None, None
    
    def _schedule_get_last_start(self):
        now = datetime.now()
        weekday = now.weekday()
        for i in range(7):
            wd = (weekday - i) % 7
            dict_start = reversed(sorted(self.schedule[wd]))
            for start in dict_start:
                dt_start = now.replace(day=now.day+i, hour=start.hour, minute=start.minute, second=0, microsecond=0)
                if dt_start <= now:
                    # turn mode on
                    _LOGGER.debug("Schedule: last start mode %s@%s", self.schedule[wd][start], dt_start)
                    return dt_start, self.schedule[wd][start]
        
        return None, None


    async def _async_do_schedule(self, time):
        if self._hvac_mode != HVAC_MODE_AUTO:
            return

        # get planning
        data = self.hass.data["schedule_list"]
        _LOGGER.debug("schedule schedule list: %s", data.items)
        # date
        now = datetime.now()
        # get last and next mode
        last_start, ls_mode = self._schedule_get_last_start()
        next_start, ns_mode = self._schedule_get_next_start()

        start_mode = None
        preheat_mode = None

        # check if mode changed
        if last_start and ls_mode:
            if self._last_do_schedule < last_start and last_start <= now:
                start_mode = ls_mode
        
        self._last_do_schedule = now

        # pre-heat mode
        if self._preheat:
            # TODO check if learning is done
            if next_start and ns_mode:
                # get next target temp
                next_target_temp = self._preset_mode_temp[ns_mode]
                # next temperature > current temperature
                if next_target_temp > self._target_temp:
                    # compute pre-heat duration
                    power = self._power(next_target_temp, self._in_temp, self._out_temp)
                    heatduration = round(0.9 * power * self._calculate_period / 100)
                    _LOGGER.debug("pre-heat: duration=%d", heatduration)
                    endheat = datetime.now() + timedelta(minutes=heatduration)
                    if endheat >= next_start:
                        # activated next mode
                        preheat_mode = ns_mode
        
        next_mode = None
        if preheat_mode:
            _LOGGER.debug("pre-heat: next mode to %s@%s",preheat_mode, next_start)
            next_mode = preheat_mode
        elif start_mode:
            next_mode = start_mode
            _LOGGER.debug("schedule: next mode to %s@%s",ls_mode, last_start)
        # apply new mode
        if next_mode and next_mode != self.preset_mode:
            _LOGGER.info("schedule: change mode to %s", next_mode)
            await self.async_set_preset_mode(next_mode)



