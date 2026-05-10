"""鹤山北控水务 传感器平台"""

import logging
from datetime import timedelta, datetime
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from homeassistant.components.sensor import SensorEntity

from .api import HeshanWaterApi, SessionTimeoutError
from .const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_OPEN_ID,
    CONF_TOKEN,
    CONF_TOKEN_EXPIRED,
    CONF_SCAN_INTERVAL,
    CONF_SCAN_INTERVAL_UNIT,
    DOMAIN,
    SENSOR_TYPES,
    TOKEN_EXPIRE_THRESHOLD,
)

_LOGGER = logging.getLogger(__name__)


class HeshanWaterSensor(SensorEntity):
    """传感器基类"""

    def __init__(self, coordinator: DataUpdateCoordinator, sensor_type: str):
        self.coordinator = coordinator
        self.sensor_type = sensor_type
        self._attr_unique_id = f"{DOMAIN}_{sensor_type}"
        self._attr_name = SENSOR_TYPES[sensor_type]["name"]
        self._attr_icon = SENSOR_TYPES[sensor_type].get("icon")
        self._attr_native_unit_of_measurement = SENSOR_TYPES[sensor_type].get("unit")

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": "鹤山北控水务",
            "manufacturer": "北控水务",
            "model": "智慧水务平台",
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
        if self.coordinator.data is not None:
            self.async_write_ha_state()

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None

        # 直接映射
        if self.sensor_type in data:
            val = data[self.sensor_type]
            if self.sensor_type in ("should_pay_amount", "balance"):
                # 去除 "元" 后缀，转为 float
                if isinstance(val, str):
                    val = val.replace("元", "").strip()
                    try:
                        return float(val)
                    except:
                        return val
            return val

        # 特殊处理: 阶梯水费明细
        if self.sensor_type == "fee_step1_amount":
            return data.get("_fee_step1_amount", 0.0)
        if self.sensor_type == "fee_step1_price":
            return data.get("_fee_step1_price", 0.0)
        if self.sensor_type == "fee_sewage_amount":
            return data.get("_fee_sewage_amount", 0.0)
        if self.sensor_type == "fee_garbage_amount":
            return data.get("_fee_garbage_amount", 0.0)
        if self.sensor_type == "actual_calc_qty":
            # 从读数差计算
            pre = data.get("pre_meter_read")
            now = data.get("now_meter_read")
            if pre is not None and now is not None:
                try:
                    return float(now) - float(pre)
                except:
                    pass
            return data.get("_actual_calc_qty", 0.0)
        if self.sensor_type == "integration_status":
            return data.get("integration_status", "unknown")

        return None


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """设置传感器"""
    # 获取共享 API 实例
    api = hass.data[DOMAIN].get(f"{config_entry.entry_id}_api")
    if api is None:
        _LOGGER.warning("未找到共享 API 实例，创建新的（Token 可能不同步）")
        username = config_entry.data[CONF_USERNAME]
        password = config_entry.data[CONF_PASSWORD]
        open_id = config_entry.data[CONF_OPEN_ID]
        token = config_entry.data.get(CONF_TOKEN, "")
        token_expired = config_entry.data.get(CONF_TOKEN_EXPIRED, "")

        async def on_token_refresh(new_token, new_expired):
            new_data = {**config_entry.data}
            new_data[CONF_TOKEN] = new_token
            new_data[CONF_TOKEN_EXPIRED] = new_expired
            hass.config_entries.async_update_entry(config_entry, data=new_data)

        session = async_get_clientsession(hass)
        api = HeshanWaterApi(username, password, open_id, token, token_expired, on_token_refresh, session)

    # 扫描间隔
    interval_val = config_entry.options.get(CONF_SCAN_INTERVAL, config_entry.data.get(CONF_SCAN_INTERVAL, 1))
    interval_unit = config_entry.options.get(CONF_SCAN_INTERVAL_UNIT, config_entry.data.get(CONF_SCAN_INTERVAL_UNIT, "hour"))
    if interval_unit == "hour":
        scan_interval = timedelta(hours=interval_val)
    else:
        scan_interval = timedelta(hours=1)  # 其他模式暂按1小时，后续可增强
    _LOGGER.info(f"数据更新间隔: {interval_val} {interval_unit} (实际 {scan_interval})")

    async def async_update_data():
        """更新数据"""
        result = {
            "integration_status": "normal",
            "client_name": "未知",
            "mobile_phone": "未知",
            "meter_address": "未知",
            "meter_detail_address": "未知",
            "meter_feekind": "未知",
            "meter_status": "未知",
            "pre_meter_read_date": "未知",
            "pre_meter_read": 0.0,
            "now_meter_read_date": "未知",
            "now_meter_read": 0.0,
            "should_pay_amount": 0.0,
            "balance": 0.0,
            "meter_no": "未知",
            "client_no": "未知",
            "is_fee_closing": False,
            "meter_calibre": "未知",
            "payment_people": "未知",
            # 阶梯费用相关
            "_fee_step1_amount": 0.0,
            "_fee_step1_price": 0.0,
            "_fee_sewage_amount": 0.0,
            "_fee_garbage_amount": 0.0,
            "_actual_calc_qty": 0.0,
        }

        # 检查 token 是否即将过期
        if api.is_token_expiring_soon(threshold_seconds=TOKEN_EXPIRE_THRESHOLD.total_seconds()):
            _LOGGER.warning("Token 即将过期，强制刷新")
            try:
                await api.async_refresh_token()
            except Exception as e:
                _LOGGER.error(f"强制刷新 Token 失败: {e}")
                result["integration_status"] = "token_expired"

        try:
            user_info = await api.async_get_user_info()
            if not user_info:
                result["integration_status"] = "api_error"
                _LOGGER.error("获取用户信息为空")
                return result

            # 提取基础字段
            for key in ["client_name", "mobile_phone", "meter_address", "meter_detail_address",
                        "meter_feekind", "meter_status", "pre_meter_read_date", "now_meter_read_date",
                        "meter_no", "client_no", "payment_people", "meter_calibre"]:
                if key in user_info:
                    result[key] = user_info[key]

            # 数值转换
            try:
                result["pre_meter_read"] = float(user_info.get("pre_meter_read", 0))
                result["now_meter_read"] = float(user_info.get("now_meter_read", 0))
            except:
                pass

            # 费用字段: 可能是 "-27.41元" 或 "0.0元"
            should_pay = user_info.get("should_pay_amount", "0元")
            balance = user_info.get("balance", "0元")
            if isinstance(should_pay, str):
                should_pay = should_pay.replace("元", "").strip()
            if isinstance(balance, str):
                balance = balance.replace("元", "").strip()
            try:
                result["should_pay_amount"] = float(should_pay)
                result["balance"] = float(balance)
            except:
                pass

            # 本期用水量（优先使用 actual_calc_qty，否则计算读数差）
            actual_qty = user_info.get("actual_calc_qty")
            if actual_qty is not None:
                try:
                    result["_actual_calc_qty"] = float(actual_qty)
                except:
                    pass
            else:
                result["_actual_calc_qty"] = max(0, result["now_meter_read"] - result["pre_meter_read"])

            result["is_fee_closing"] = user_info.get("is_fee_closing", False)

            # 尝试获取费用明细（需要 fee_id，这里暂时无法获取，留空）
            # 注意：完整实现需要先获取 fee_id，但抓包未提供列表接口，故暂不实现

            result["integration_status"] = "normal"
            _LOGGER.debug(f"用户信息更新成功: {result['client_name']}, 用水量 {result['_actual_calc_qty']} m³")

        except SessionTimeoutError as e:
            _LOGGER.error(f"会话超时，Token 失效: {e}")
            result["integration_status"] = "token_expired"
        except Exception as e:
            _LOGGER.error(f"更新数据失败: {e}")
            result["integration_status"] = "api_error"

        return result

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=scan_interval,
    )

    # 存储 coordinator 供按钮使用
    hass.data[DOMAIN][f"{config_entry.entry_id}_coordinator"] = coordinator

    # 创建传感器
    entities = [HeshanWaterSensor(coordinator, stype) for stype in SENSOR_TYPES]
    async_add_entities(entities)

    # 执行首次刷新
    await coordinator.async_config_entry_first_refresh()