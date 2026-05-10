"""鹤山北控水务 配置流程"""

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_OPEN_ID,
    CONF_TOKEN,
    CONF_TOKEN_EXPIRED,
    CONF_SCAN_INTERVAL,
    CONF_SCAN_INTERVAL_UNIT,
    DOMAIN,
    SCAN_INTERVAL_UNITS,
    BASE_URL,
    API_GET_TOKEN,
    API_GET_USER_INFO,
)

_LOGGER = logging.getLogger(__name__)

def _validate_interval(value, unit):
    if unit == "hour":
        if not 1 <= value <= 24:
            return "间隔小时数请输入 1-24"
    elif unit == "day":
        if not 0 <= value <= 23:
            return "日模式请输入 0-23（每天几点更新）"
    elif unit == "week":
        if not 1 <= value <= 7:
            return "周模式请输入 1-7（1=周一）"
    elif unit == "month":
        if not 1 <= value <= 31:
            return "月模式请输入 1-31"
    return None

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            open_id = user_input[CONF_OPEN_ID]

            interval_val = user_input.get(CONF_SCAN_INTERVAL, 1)
            interval_unit = user_input.get(CONF_SCAN_INTERVAL_UNIT, "hour")
            interval_err = _validate_interval(interval_val, interval_unit)
            if interval_err:
                errors[CONF_SCAN_INTERVAL] = interval_err
            else:
                try:
                    session = async_get_clientsession(self.hass)
                    token_data = await self._async_get_token(session, username, password)
                    token = token_data["token"]
                    token_expired = token_data["expired"]

                    user_info = await self._async_get_user_info(session, token, open_id)
                    if not user_info:
                        errors["base"] = "no_binding"
                    else:
                        data = {
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                            CONF_OPEN_ID: open_id,
                            CONF_TOKEN: token,
                            CONF_TOKEN_EXPIRED: token_expired,
                            CONF_SCAN_INTERVAL: interval_val,
                            CONF_SCAN_INTERVAL_UNIT: interval_unit,
                        }
                        title = f"鹤山北控水务 ({user_info.get('client_name', open_id)})"
                        return self.async_create_entry(title=title, data=data)
                except Exception as e:
                    _LOGGER.exception("验证失败")
                    errors["base"] = "auth_failed"

        schema = vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Required(CONF_OPEN_ID): str,
            vol.Required(CONF_SCAN_INTERVAL, default=1): vol.All(vol.Coerce(int)),
            vol.Required(CONF_SCAN_INTERVAL_UNIT, default="hour"): vol.In(SCAN_INTERVAL_UNITS),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _async_get_token(self, session, username, password):
        url = f"{BASE_URL}{API_GET_TOKEN}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"username": username, "password": password}
        async with session.post(url, headers=headers, data=data, timeout=30) as resp:
            if resp.status != 200:
                raise Exception("HTTP error")
            # 关键修复：服务器返回 Content-Type: text/html，但实际是 JSON
            result = await resp.json(content_type=None)
            if result.get("return_code") != 0:
                raise Exception(result.get("return_msg", "登录失败"))
            return result["return_data"]

    async def _async_get_user_info(self, session, token, open_id):
        url = f"{BASE_URL}{API_GET_USER_INFO}?token={token}"
        headers = {"Content-Type": "application/json"}
        json_data = {"open_id": open_id}
        async with session.post(url, headers=headers, json=json_data, timeout=30) as resp:
            if resp.status != 200:
                return None
            # 同样修复 Content-Type 问题
            data = await resp.json(content_type=None)
            if "result" in data:
                data = data["result"]
            if data.get("return_code") in (0, "0", "1"):
                return data.get("return_data", {}).get("user_info", {})
            return None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            interval_val = user_input.get(CONF_SCAN_INTERVAL, 1)
            interval_unit = user_input.get(CONF_SCAN_INTERVAL_UNIT, "hour")
            error = _validate_interval(interval_val, interval_unit)
            if error:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._build_schema(),
                    errors={CONF_SCAN_INTERVAL: error},
                )
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=self._build_schema())

    def _build_schema(self):
        current_val = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, 1)
        )
        current_unit = self.config_entry.options.get(
            CONF_SCAN_INTERVAL_UNIT,
            self.config_entry.data.get(CONF_SCAN_INTERVAL_UNIT, "hour")
        )
        return vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL, default=current_val): vol.All(vol.Coerce(int)),
            vol.Required(CONF_SCAN_INTERVAL_UNIT, default=current_unit): vol.In(SCAN_INTERVAL_UNITS),
        })