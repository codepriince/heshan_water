"""鹤山北控水务 Home Assistant 集成"""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .api import HeshanWaterApi, SessionTimeoutError
from .const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_OPEN_ID,
    CONF_TOKEN,
    CONF_TOKEN_EXPIRED,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
    TOKEN_EXPIRE_THRESHOLD,
    TOKEN_REFRESH_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info(f"设置鹤山北控水务集成: {entry.title}")
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = dict(entry.data)

    # 获取配置参数
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    open_id = entry.data.get(CONF_OPEN_ID)
    token = entry.data.get(CONF_TOKEN, "")
    token_expired = entry.data.get(CONF_TOKEN_EXPIRED, "")

    # Token 刷新回调（持久化新 Token）
    async def on_token_refresh(new_token: str, new_expired: str):
        _LOGGER.info("保存新 Token 到 config_entry")
        new_data = {**entry.data}
        new_data[CONF_TOKEN] = new_token
        new_data[CONF_TOKEN_EXPIRED] = new_expired
        hass.config_entries.async_update_entry(entry, data=new_data)

    session = async_get_clientsession(hass)
    api = HeshanWaterApi(
        username=username,
        password=password,
        open_id=open_id,
        token=token,
        token_expired=token_expired,
        on_token_refresh=on_token_refresh,
        session=session,
    )

    hass.data[DOMAIN][f"{entry.entry_id}_api"] = api

    # ========== 独立 Token 刷新定时器 ==========
    async def _async_refresh_token_hourly(now=None):
        """每小时整点刷新 Token"""
        try:
            remaining = api.get_token_remaining_seconds()
            _LOGGER.info(f"定时器[整点]: 当前 Token 剩余 {remaining} 秒，开始刷新...")
            await api.async_refresh_token()
            _LOGGER.info("定时器[整点]: Token 刷新成功")
        except SessionTimeoutError:
            _LOGGER.error("定时器[整点]: Token 刷新失败（认证失效），请检查用户名密码或 open_id")
        except Exception as e:
            _LOGGER.error(f"定时器[整点]: Token 刷新异常: {e}")

    async def _async_refresh_token_urgent(now=None):
        """紧急刷新：剩余时间不足阈值时刷新"""
        try:
            remaining = api.get_token_remaining_seconds()
            if remaining is None or remaining >= TOKEN_EXPIRE_THRESHOLD.total_seconds():
                return
            _LOGGER.info(f"定时器[紧急]: Token 剩余 {remaining} 秒（<{TOKEN_EXPIRE_THRESHOLD}秒），立即刷新")
            await api.async_refresh_token()
            _LOGGER.info("定时器[紧急]: Token 刷新成功")
        except SessionTimeoutError:
            _LOGGER.error("定时器[紧急]: Token 刷新失败（认证失效）")
        except Exception as e:
            _LOGGER.error(f"定时器[紧急]: Token 刷新异常: {e}")

    cancel_hourly = async_track_time_interval(
        hass, _async_refresh_token_hourly, TOKEN_REFRESH_INTERVAL
    )
    cancel_urgent = async_track_time_interval(
        hass, _async_refresh_token_urgent, timedelta(minutes=1)
    )
    hass.data[DOMAIN][f"{entry.entry_id}_token_timer_cancel"] = cancel_hourly
    hass.data[DOMAIN][f"{entry.entry_id}_token_timer_urgent_cancel"] = cancel_urgent
    _LOGGER.info(f"独立 Token 刷新定时器已启动（整点间隔 {TOKEN_REFRESH_INTERVAL}，紧急检查 1分钟）")

    # 启动后立即执行一次刷新
    hass.async_create_task(_async_refresh_token_hourly())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info(f"卸载鹤山北控水务集成: {entry.title}")

    # 取消定时器
    cancel_hourly = hass.data[DOMAIN].pop(f"{entry.entry_id}_token_timer_cancel", None)
    if cancel_hourly:
        cancel_hourly()
    cancel_urgent = hass.data[DOMAIN].pop(f"{entry.entry_id}_token_timer_urgent_cancel", None)
    if cancel_urgent:
        cancel_urgent()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.data[DOMAIN].pop(f"{entry.entry_id}_coordinator", None)
        hass.data[DOMAIN].pop(f"{entry.entry_id}_api", None)
    return unload_ok