import logging
import json
import aiohttp
import time
import hmac
import hashlib
import asyncio
from .utils import retrier_async, validate_response

logger = logging.getLogger('trading')

def dict_to_query_string(params: dict) -> str:
    return '&'.join([f'{key}={value}' for key, value in params.items()])

class BybitRequester:
    def __init__(self, api_key: str, api_secret: str, testnet: bool, session: aiohttp.ClientSession = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.recv_window = '5000'
        self.base_url = "https://api.bybit.com"
        self.base_url_testnet = 'https://api-testnet.bybit.com'
        self._session = session
        self._session_lock = asyncio.Lock()

    def _get_base_url(self) -> str:
        return self.base_url_testnet if self.testnet else self.base_url

    async def _ensure_session(self):
        """Ensure that the session is open and create a new one if needed."""
        async with self._session_lock:
            if self._session is None or self._session.closed:
                logger.info("Creating new aiohttp ClientSession")
                self._session = aiohttp.ClientSession()

    @property
    async def session(self):
        await self._ensure_session()
        return self._session

    async def close(self):
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.closed
                self._session = None

    @retrier_async
    async def send_public_request(self, endpoint: str, params: dict = None) -> dict:
        session = await self.session
        url = f"{self._get_base_url()}{endpoint}"
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                validate_response(data, endpoint, params)
                return data
        except aiohttp.ClientConnectionError as e:
            logger.error(f"Connection error in send_public_request: {e}")
            await self._handle_connection_error()
            raise  # Let the retrier handle this

    @retrier_async
    async def send_signed_request(self, method: str, endpoint: str, params: dict) -> dict:
        session = await self.session
        time_stamp = str(int(time.time() * 1000))
        signature = self._gen_signature(params, time_stamp, method)
        headers = {
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-SIGN': signature,
            'X-BAPI-SIGN-TYPE': '2',
            'X-BAPI-TIMESTAMP': time_stamp,
            'X-BAPI-RECV-WINDOW': self.recv_window,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        url = f"{self._get_base_url()}{endpoint}"

        try:
            if method.upper() == "POST":
                async with session.post(url, headers=headers, data=json.dumps(params)) as response:
                    response.raise_for_status()
                    data = await response.json()
            elif method.upper() == "GET":
                query = dict_to_query_string(params)
                full_url = f"{url}?{query}"
                async with session.get(full_url, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
            else:
                raise ValueError(f"Unsupported method: {method}")

            validate_response(data, endpoint, params)
            return data
        except (aiohttp.ClientConnectionError, aiohttp.ClientOSError) as e:
            logger.error(f"Connection error in send_signed_request: {e}")
            await self._handle_connection_error()
            raise  # Let the retrier handle this

    async def _handle_connection_error(self):
        """Handle connection errors by creating a new session."""
        logger.info("Handling connection error, recreating session")
        async with self._session_lock:
            if self._session and not self._session.closed:
                try:
                    await self._session.close()
                except Exception as e:
                    logger.warning(f"Error closing session: {e}")
            self._session = None  # Will be recreated on next request

    async def send_paginated_request(self, method: str, endpoint: str, params: dict = None):
        params = params or {}
        next_cursor = None
        result = []

        while True:
            if next_cursor:
                next_cursor = next_cursor.replace('%', ':')
                params['cursor'] = next_cursor
                params.pop('startTime', None)
                params.pop('endTime', None)

            response = await self.send_signed_request(method, endpoint, params)
            result.extend(response.get('result', {}).get('list', []))

            last_cursor = next_cursor
            next_cursor = response.get('result', {}).get('nextPageCursor')

            if not next_cursor or next_cursor == last_cursor:
                return result

    def _gen_signature(self, params: dict, time_stamp: str, method: str) -> str:
        if method.upper() == "POST":
            param_str = json.dumps(params)
        else:
            param_str = dict_to_query_string(params)

        base_str = f"{time_stamp}{self.api_key}{self.recv_window}{param_str}"
        return hmac.new(self.api_secret.encode(), base_str.encode(), hashlib.sha256).hexdigest()