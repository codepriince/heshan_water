"""鹤山北控水务 按钮平台"""

import logging
from typing import Optional

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    buttons = [
        RefreshDataButton(hass, config_entry),
        # FetchHistoryButton 因 API 限制暂不实现，可后续扩展
    ]
    async_add_entities(buttons)
    _LOGGER.info("鹤山北控水务按钮已注册")


class RefreshDataButton(ButtonEntity):
    """手动刷新数据按钮"""

    _attr_has_entity_name = True
    _attr_name = "刷新数据"
    _attr_icon = "mdi:refresh"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        self.hass = hass
        self.config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_refresh_data"

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "鹤山北控水务",
            "manufacturer": "北控水务",
            "model": "智慧水务",
        }

    async def async_press(self) -> None:
        _LOGGER.info("用户触发手动刷新数据")
        coordinator = self.hass.data.get(DOMAIN, {}).get(f"{self.config_entry.entry_id}_coordinator")
        if coordinator:
            await coordinator.async_request_refresh()
        else:
            _LOGGER.error("Coordinator 未初始化，无法刷新")