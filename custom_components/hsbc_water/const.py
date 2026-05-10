"""鹤山北控水务 HA 集成常量定义"""

from homeassistant.const import Platform

DOMAIN = "hsbc_water"
PLATFORM_NAME = "鹤山北控水务"
PLATFORMS = [Platform.SENSOR, Platform.BUTTON]

# API 配置
BASE_URL = "http://59.36.246.10:8016"

# API 端点
API_GET_TOKEN = "/wechat/get_token"
API_GET_OPENID = "/wechat/getopenid"      # 未直接使用，因为需要微信 code
API_GET_USER_INFO = "/GetUserInfo"
API_GET_USER_BIND = "/GetUserBind"
API_GET_FEE_DETAIL = "/GetFeeDetail"      # 需要 fee_id，暂未使用

# 配置键
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_OPEN_ID = "open_id"
CONF_TOKEN = "token"
CONF_TOKEN_EXPIRED = "token_expired"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SCAN_INTERVAL_UNIT = "scan_interval_unit"

SCAN_INTERVAL_UNITS = {
    "hour": "小时（每 N 小时）",
    "day": "天（每天 X 点）",
    "week": "周（每周 X，1=周一）",
    "month": "月（每月 X 号）",
}

# 传感器类型定义
SENSOR_TYPES = {
    # 核心数据
    "client_name": {
        "name": "用户名",
        "icon": "mdi:account",
    },
    "mobile_phone": {
        "name": "手机号",
        "icon": "mdi:phone",
    },
    "meter_address": {
        "name": "用水地址",
        "icon": "mdi:home-map-marker",
    },
    "meter_detail_address": {
        "name": "详细地址",
        "icon": "mdi:home-city",
    },
    "meter_feekind": {
        "name": "用水类型",
        "icon": "mdi:water",
    },
    "meter_status": {
        "name": "水表状态",
        "icon": "mdi:water-pump",
    },
    # 读数与用水量
    "pre_meter_read_date": {
        "name": "上次抄表时间",
        "icon": "mdi:calendar-arrow-left",
    },
    "pre_meter_read": {
        "name": "上次抄表读数",
        "unit": "m³",
        "icon": "mdi:counter",
    },
    "now_meter_read_date": {
        "name": "本次抄表时间",
        "icon": "mdi:calendar-arrow-right",
    },
    "now_meter_read": {
        "name": "本次抄表读数",
        "unit": "m³",
        "icon": "mdi:counter",
    },
    "actual_calc_qty": {
        "name": "本期用水量",
        "unit": "m³",
        "icon": "mdi:water",
    },
    # 费用相关
    "should_pay_amount": {
        "name": "应缴金额",
        "unit": "¥",
        "icon": "mdi:cash",
    },
    "balance": {
        "name": "账户余额",
        "unit": "¥",
        "icon": "mdi:wallet",
    },
    # 阶梯水费明细（从 fee_detail_list 聚合）
    "fee_step1_amount": {
        "name": "一阶梯水费",
        "unit": "¥",
        "icon": "mdi:stairs-up",
    },
    "fee_step1_price": {
        "name": "一阶梯水价",
        "unit": "¥/m³",
        "icon": "mdi:currency-cny",
    },
    "fee_sewage_amount": {
        "name": "污水处理费",
        "unit": "¥",
        "icon": "mdi:dump-truck",
    },
    "fee_garbage_amount": {
        "name": "垃圾处理费",
        "unit": "¥",
        "icon": "mdi:trash-can",
    },
    # 附加信息
    "meter_no": {
        "name": "水表编号",
        "icon": "mdi:identifier",
    },
    "client_no": {
        "name": "客户编号",
        "icon": "mdi:card-account-details",
    },
    "is_fee_closing": {
        "name": "系统暂停状态",
        "icon": "mdi:alert-circle",
    },
    # 集成状态
    "integration_status": {
        "name": "集成状态",
        "icon": "mdi:checkbox-marked-circle",
    },
}

# Token 管理
from datetime import timedelta

TOKEN_REFRESH_INTERVAL = timedelta(hours=1)
TOKEN_EXPIRE_THRESHOLD = timedelta(minutes=5)
DEFAULT_SCAN_INTERVAL = timedelta(hours=1)