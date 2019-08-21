"""Support to manage a schedule list."""
import asyncio
import logging
import uuid

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.helpers import intent
import homeassistant.helpers.config_validation as cv
from homeassistant.util.json import load_json, save_json
from homeassistant.components import websocket_api

ATTR_NAME = "name"

DOMAIN = "schedule_list"
_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({DOMAIN: {}}, extra=vol.ALLOW_EXTRA)
EVENT = "schedule_list_updated"
INTENT_ADD_ITEM = "HassScheduleListAddItem"
INTENT_LAST_ITEMS = "HassScheduleListLastItems"
ITEM_UPDATE_SCHEMA = vol.Schema({"enable": bool, ATTR_NAME: str})
PERSISTENCE = ".schedule_list.json"

SERVICE_ADD_ITEM = "add_item"
SERVICE_ENABLE_ITEM = "enable_item"

SERVICE_ITEM_SCHEMA = vol.Schema({vol.Required(ATTR_NAME): vol.Any(None, cv.string)})

WS_TYPE_SCHEDULE_LIST_ITEMS = "schedule_list/items"
WS_TYPE_SCHEDULE_LIST_ADD_ITEM = "schedule_list/items/add"
WS_TYPE_SCHEDULE_LIST_UPDATE_ITEM = "schedule_list/items/update"
WS_TYPE_SCHEDULE_LIST_CLEAR_ITEMS = "schedule_list/items/clear"

SCHEMA_WEBSOCKET_ITEMS = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {vol.Required("type"): WS_TYPE_SCHEDULE_LIST_ITEMS}
)

SCHEMA_WEBSOCKET_ADD_ITEM = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {vol.Required("type"): WS_TYPE_SCHEDULE_LIST_ADD_ITEM, vol.Required("name"): str}
)

SCHEMA_WEBSOCKET_UPDATE_ITEM = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {
        vol.Required("type"): WS_TYPE_SCHEDULE_LIST_UPDATE_ITEM,
        vol.Required("item_id"): str,
        vol.Optional("name"): str,
        vol.Optional("enable"): bool,
    }
)

SCHEMA_WEBSOCKET_CLEAR_ITEMS = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {vol.Required("type"): WS_TYPE_SCHEDULE_LIST_CLEAR_ITEMS}
)


@asyncio.coroutine
def async_setup(hass, config):
    """Initialize the schedule list."""

    @asyncio.coroutine
    def add_item_service(call):
        """Add an item with `name`."""
        data = hass.data[DOMAIN]
        name = call.data.get(ATTR_NAME)
        if name is not None:
            data.async_add(name)

    @asyncio.coroutine
    def enable_item_service(call):
        """Mark the item provided via `name` as enabled."""
        data = hass.data[DOMAIN]
        name = call.data.get(ATTR_NAME)
        if name is None:
            return
        try:
            item = [item for item in data.items if item["name"] == name][0]
        except IndexError:
            _LOGGER.error("Removing of item failed: %s cannot be found", name)
        else:
            data.async_update(item["id"], {"name": name, "enable": True})

    data = hass.data[DOMAIN] = ScheduleData(hass)
    yield from data.async_load()

    intent.async_register(hass, AddItemIntent())
    intent.async_register(hass, ListTopItemsIntent())

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_ITEM, add_item_service, schema=SERVICE_ITEM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ENABLE_ITEM, enable_item_service, schema=SERVICE_ITEM_SCHEMA
    )

    hass.components.conversation.async_register(
        INTENT_ADD_ITEM, ["Add [the] [a] [an] {item} to my schedule list"]
    )
    hass.components.conversation.async_register(
        INTENT_LAST_ITEMS, ["What is on my schedule list"]
    )

    hass.components.websocket_api.async_register_command(
        WS_TYPE_SCHEDULE_LIST_ITEMS, websocket_handle_items, SCHEMA_WEBSOCKET_ITEMS
    )
    hass.components.websocket_api.async_register_command(
        WS_TYPE_SCHEDULE_LIST_ADD_ITEM, websocket_handle_add, SCHEMA_WEBSOCKET_ADD_ITEM
    )
    hass.components.websocket_api.async_register_command(
        WS_TYPE_SCHEDULE_LIST_UPDATE_ITEM,
        websocket_handle_update,
        SCHEMA_WEBSOCKET_UPDATE_ITEM,
    )
    hass.components.websocket_api.async_register_command(
        WS_TYPE_SCHEDULE_LIST_CLEAR_ITEMS,
        websocket_handle_clear,
        SCHEMA_WEBSOCKET_CLEAR_ITEMS,
    )

    return True


class ScheduleData:
    """Class to hold schedule list data."""

    def __init__(self, hass):
        """Initialize the schedule list."""
        self.hass = hass
        self.items = []

    @callback
    def async_add(self, name):
        """Add a schedule list item."""
        item = {"name": name, "id": uuid.uuid4().hex, "enable": False}
        self.items.append(item)
        self.hass.async_add_job(self.save)
        return item

    @callback
    def async_update(self, item_id, info):
        """Update a schedule list item."""
        item = next((itm for itm in self.items if itm["id"] == item_id), None)

        if item is None:
            raise KeyError

        info = ITEM_UPDATE_SCHEMA(info)
        item.update(info)
        self.hass.async_add_job(self.save)
        return item

    @callback
    def async_clear_enabled(self):
        """Clear enabled items."""
        self.items = [itm for itm in self.items if not itm["enable"]]
        self.hass.async_add_job(self.save)

    @asyncio.coroutine
    def async_load(self):
        """Load items."""

        def load():
            """Load the items synchronously."""
            return load_json(self.hass.config.path(PERSISTENCE), default=[])

        self.items = yield from self.hass.async_add_job(load)

    def save(self):
        """Save the items."""
        save_json(self.hass.config.path(PERSISTENCE), self.items)


class AddItemIntent(intent.IntentHandler):
    """Handle AddItem intents."""

    intent_type = INTENT_ADD_ITEM
    slot_schema = {"item": cv.string}

    @asyncio.coroutine
    def async_handle(self, intent_obj):
        """Handle the intent."""
        slots = self.async_validate_slots(intent_obj.slots)
        item = slots["item"]["value"]
        intent_obj.hass.data[DOMAIN].async_add(item)

        response = intent_obj.create_response()
        response.async_set_speech("I've added {} to your schedule list".format(item))
        intent_obj.hass.bus.async_fire(EVENT)
        return response


class ListTopItemsIntent(intent.IntentHandler):
    """Handle AddItem intents."""

    intent_type = INTENT_LAST_ITEMS
    slot_schema = {"item": cv.string}

    @asyncio.coroutine
    def async_handle(self, intent_obj):
        """Handle the intent."""
        items = intent_obj.hass.data[DOMAIN].items[-5:]
        response = intent_obj.create_response()

        if not items:
            response.async_set_speech("There are no items on your schedule list")
        else:
            response.async_set_speech(
                "These are the top {} items on your schedule list: {}".format(
                    min(len(items), 5),
                    ", ".join(itm["name"] for itm in reversed(items)),
                )
            )
        return response



@callback
def websocket_handle_items(hass, connection, msg):
    """Handle get schedule_list items."""
    connection.send_message(
        websocket_api.result_message(msg["id"], hass.data[DOMAIN].items)
    )


@callback
def websocket_handle_add(hass, connection, msg):
    """Handle add item to schedule_list."""
    item = hass.data[DOMAIN].async_add(msg["name"])
    hass.bus.async_fire(EVENT)
    connection.send_message(websocket_api.result_message(msg["id"], item))


@websocket_api.async_response
async def websocket_handle_update(hass, connection, msg):
    """Handle update schedule_list item."""
    msg_id = msg.pop("id")
    item_id = msg.pop("item_id")
    msg.pop("type")
    data = msg

    try:
        item = hass.data[DOMAIN].async_update(item_id, data)
        hass.bus.async_fire(EVENT)
        connection.send_message(websocket_api.result_message(msg_id, item))
    except KeyError:
        connection.send_message(
            websocket_api.error_message(msg_id, "item_not_found", "Item not found")
        )


@callback
def websocket_handle_clear(hass, connection, msg):
    """Handle clearing schedule_list items."""
    hass.data[DOMAIN].async_clear_enabled()
    hass.bus.async_fire(EVENT)
    connection.send_message(websocket_api.result_message(msg["id"]))
