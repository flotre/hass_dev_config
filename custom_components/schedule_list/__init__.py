"""Support to manage a schedule list."""
import asyncio
import logging
import uuid

import voluptuous as vol

from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.util.json import load_json, save_json
from homeassistant.components import websocket_api

ATTR_NAME = "name"

DOMAIN = "schedule_list"
_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({DOMAIN: {}}, extra=vol.ALLOW_EXTRA)
ITEM_UPDATE_SCHEMA = vol.Schema({"enable": bool, ATTR_NAME: str})
PERSISTENCE = ".schedule_list.json"


WS_TYPE_SCHEDULE_LIST_FETCH = "schedule_list/fetch"
WS_TYPE_SCHEDULE_LIST_UPDATE = "schedule_list/update"

SCHEMA_WEBSOCKET_FETCH = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {   vol.Required("type"): WS_TYPE_SCHEDULE_LIST_FETCH,
        vol.Required("schedule_id"): str,
    }
)

SCHEMA_WEBSOCKET_UPDATE = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {
        vol.Required("type"): WS_TYPE_SCHEDULE_LIST_UPDATE,
        vol.Required("schedule_id"): str,
        vol.Required("data"): {vol.Required("schedule"): [[{'cval': str, 'nval': str}]], vol.Required("entities"): [str]},
    }
)


@asyncio.coroutine
def async_setup(hass, config):
    """Initialize the schedule list."""

    data = hass.data[DOMAIN] = ScheduleData(hass)
    yield from data.async_load()


    hass.components.websocket_api.async_register_command(
        WS_TYPE_SCHEDULE_LIST_FETCH,
        websocket_handle_fetch,
        SCHEMA_WEBSOCKET_FETCH
    )

    hass.components.websocket_api.async_register_command(
        WS_TYPE_SCHEDULE_LIST_UPDATE,
        websocket_handle_update,
        SCHEMA_WEBSOCKET_UPDATE,
    )

    return True


class ScheduleData:
    """Class to hold schedule list data."""

    def __init__(self, hass):
        """Initialize the schedule list."""
        self.hass = hass
        self.data = {}


    @callback
    def async_update(self, sid, data):
        """Update schedule list."""
        _LOGGER.debug("update schedule %s", sid)
        self.data[sid] = data
        self.hass.async_add_job(self.save)

    @asyncio.coroutine
    def async_load(self):
        """Load items."""

        def load():
            """Load the items synchronously."""
            _LOGGER.debug("load schedule")
            return load_json(self.hass.config.path(PERSISTENCE), default={})

        self.data = yield from self.hass.async_add_job(load)

    def save(self):
        """Save the items."""
        _LOGGER.debug("save schedule")
        save_json(self.hass.config.path(PERSISTENCE), self.data)




@callback
def websocket_handle_fetch(hass, connection, msg):
    """Handle fetch schedule_list."""
    sid = msg.pop("schedule_id")
    _LOGGER.debug("handle fetch for %s", sid)
    try:
        data = hass.data[DOMAIN].data.get(sid, {'schedule':None, 'entities':None})
    except:
        _LOGGER.debug("Exception in handle fetch %s", sid)
        data = {'schedule':None, 'entities':None}
    connection.send_message(
        websocket_api.result_message(msg["id"], data)
    )
    _LOGGER.debug("end handle fetch for %s, %r", sid, data["entities"])



@websocket_api.async_response
async def websocket_handle_update(hass, connection, msg):
    """Handle update schedule_list item."""
    sid = msg.pop("schedule_id")
    data = msg.pop("data")

    try:
        hass.data[DOMAIN].async_update(sid, data)
        connection.send_message(websocket_api.result_message(msg["id"]))
    except KeyError:
        connection.send_message(
            websocket_api.error_message(msg["id"], "item_not_found", "Item not found")
        )

