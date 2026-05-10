"""鹤山北控水务 API 封装 - 基于 aiohttp"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional, Callable, Awaitable

import aiohttp
from .const import (
    API_GET_TOKEN,
    API_GET_USER_INFO,
    API_GET_USER_BIND,
    BASE_URL,
)

_LOGGER = logging.getLogger(__name__)


class SessionTimeoutError(Exception):
    """认证失效/Token 无效异常"""
    pass


class HeshanWaterApi:
    """鹤山北控水务 API 客户端"""

    def __init__(
        self,
        username: str,
        password: str,
        open_id: str,
        token: str = "",
        token_expired: str = "",
        on_token_refresh: Optional[Callable[[str, str], Awaitable[None]]] = None,
        session: aiohttp.ClientSession = None,
    ):
        self.username = username
        self.password = password
        self.open_id = open_id
        self.token = token
        self.token_expired = token_expired
        self._on_token_refresh = on_token_refresh
        self._session = session

    def get_token_remaining_seconds(self) -> Optional[int]:
        """获取 Token 剩余有效时间（秒）"""
        if not self.token_expired:
            return None
        try:
            expire_dt = datetime.strptime(self.token_expired, "%Y-%m-%d %H:%M:%S")
            remaining = (expire_dt - datetime.now()).total_seconds()
            return max(0, int(remaining))
        except Exception as e:
            _LOGGER.warning(f"解析 Token 过期时间失败: {e}")
            return None

    def is_token_expiring_soon(self, threshold_seconds: int = 300) -> bool:
        remaining = self.get_token_remaining_seconds()
        if remaining is None:
            return True
        return remaining < threshold_seconds

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict = None,
        json_data: dict = None,
        use_token: bool = True,
    ) -> Dict[str, Any]:
        """通用请求方法"""
        url = f"{BASE_URL}{endpoint}"
        if use_token and self.token:
            params = params or {}
            params["token"] = self.token

        headers = {
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 "
                "Safari/537.36 MicroMessenger/7.0.20.1781"
            ),
        }

        _LOGGER.debug(f"请求: {method} {url} params={params} json={json_data}")

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    _LOGGER.error(f"HTTP {resp.status}: {text[:200]}")
                    raise Exception(f"HTTP {resp.status}: {text[:100]}")

                # 关键修改：允许非标准 Content-Type
                data = await resp.json(content_type=None)

                # 检测业务错误
                if "return_code" in data:
                    if data["return_code"] != 0 and data["return_code"] != "0":
                        err_msg = data.get("return_msg", "未知错误")
                        _LOGGER.warning(f"API 业务错误: return_code={data['return_code']} msg={err_msg}")
                        if "token" in err_msg.lower() or "登录" in err_msg:
                            raise SessionTimeoutError(err_msg)
                        raise Exception(err_msg)

                if "result" in data and isinstance(data["result"], dict):
                    inner = data["result"]
                    if inner.get("return_code") not in (0, "0", "1", None):
                        err_msg = inner.get("return_msg", "未知错误")
                        if "token" in err_msg.lower() or "登录" in err_msg:
                            raise SessionTimeoutError(err_msg)
                        raise Exception(err_msg)
                    return inner
                return data

        except aiohttp.ClientError as e:
            _LOGGER.error(f"网络请求异常: {e}")
            raise Exception(f"网络错误: {e}")
        except SessionTimeoutError:
            raise
        except Exception as e:
            _LOGGER.error(f"请求异常: {e}")
            raise

    async def async_get_token(self, retry: int = 3) -> Dict[str, Any]:
        """登录获取 Token，支持重试"""
        url = f"{BASE_URL}{API_GET_TOKEN}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/132.0.0.0 MicroMessenger/7.0.20"
            ),
        }
        data = {"username": self.username, "password": self.password}

        for attempt in range(retry):
            try:
                async with self._session.post(
                    url, headers=headers, data=data, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise Exception(f"登录失败 HTTP {resp.status}: {text[:100]}")
                    # 关键修改：允许 text/html Content-Type
                    result = await resp.json(content_type=None)
                    if result.get("return_code") != 0:
                        raise Exception(result.get("return_msg", "登录失败"))
                    return result["return_data"]
            except aiohttp.ContentTypeError as e:
                _LOGGER.warning(f"Content-Type 错误 (尝试 {attempt+1}/{retry}): {e}")
                if attempt == retry - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # 指数退避
            except Exception as e:
                _LOGGER.warning(f"获取 Token 异常 (尝试 {attempt+1}/{retry}): {e}")
                if attempt == retry - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        raise Exception("获取 Token 失败: 超过重试次数")

    async def async_refresh_token(self) -> bool:
        """刷新 Token（重新登录获取新 Token）"""
        _LOGGER.info("开始刷新 Token...")
        try:
            token_data = await self.async_get_token(retry=3)
            new_token = token_data["token"]
            new_expired = token_data["expired"]

            self.token = new_token
            self.token_expired = new_expired

            if self._on_token_refresh:
                await self._on_token_refresh(new_token, new_expired)

            _LOGGER.info("Token 刷新成功，新过期时间: %s", new_expired)
            return True
        except Exception as e:
            _LOGGER.error(f"Token 刷新失败: {e}")
            raise SessionTimeoutError(f"刷新 Token 失败: {e}")

    async def async_get_user_info(self) -> Dict[str, Any]:
        """获取用户用水信息"""
        json_data = {"open_id": self.open_id}
        result = await self._request("POST", API_GET_USER_INFO, json_data=json_data)
        return_data = result.get("return_data", {})
        user_info = return_data.get("user_info", {})
        return user_info

    async def async_get_user_bind(self) -> Dict[str, Any]:
        """获取绑定水表信息"""
        json_data = {"open_id": self.open_id}
        result = await self._request("POST", API_GET_USER_BIND, json_data=json_data)
        return_data = result.get("return_data", {})
        return return_data