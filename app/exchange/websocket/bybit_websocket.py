import logging
import asyncio
import json
from uuid import uuid4
import aiohttp


from .utils import *


logger=logging.getLogger('websocket')

SUBDOMAIN_TESTNET = "stream-testnet"
SUBDOMAIN_MAINNET = "stream"
DOMAIN_MAIN = "bybit"
TLD_MAIN = "com"



class AsyncWebSocketManager:
    def __init__(
            self,
            callback_function,
            testnet=False,
            api_key=None,
            api_secret=None,
            ping_interval=20,
    ):
        self.testnet = testnet
        self.api_key = api_key
        self.api_secret = api_secret
        self.callback = callback_function
        self.ping_interval = ping_interval
        self.ws = None
        self.session = None
        self.ping_task = None
        self.subscriptions = {}
        self.callback_directory = {}
        self.data = {}
        self.running = False
        self.is_closing = False


    async def connect(self, base_url="wss://{SUBDOMAIN}.{DOMAIN}.{TLD}/v5/public/linear"):
        subdomain = SUBDOMAIN_TESTNET if self.testnet else SUBDOMAIN_MAINNET
        url = base_url.format(SUBDOMAIN=subdomain, DOMAIN=DOMAIN_MAIN, TLD=TLD_MAIN)

        try:
            self.session = aiohttp.ClientSession()
            self.ws = await self.session.ws_connect(url)
            logger.info(f"WebSocket connected to {url}")

            if self.api_key and self.api_secret:
                await self._authenticate()

            self.ping_task = asyncio.create_task(self._ping_loop())


            self.running = True
            asyncio.create_task(self._message_loop())


            await self._resubscribe()

            return True
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            if self.ws:
                await self.ws.close()
            if self.session:
                await self.session.close()
            self.ws = None
            self.session = None
            return False

    async def subscribe(self, topic, callback, symbol=None):
        if symbol:
            if isinstance(symbol, str):
                symbol = [symbol]
            topics = [topic.format(symbol=s) for s in symbol]
        else:
            topics = [topic]

        req_id = str(uuid4())
        subscription_message = json.dumps({
            "op": "subscribe",
            "req_id": req_id,
            "args": topics
        })

        if self.ws and not self.ws.closed:
            await self.ws.send_str(subscription_message)
            self.subscriptions[req_id] = subscription_message

            for t in topics:
                self.callback_directory[t] = callback
        else:
            logger.warning("WebSocket not connected. Saving subscription for later.")
            self.subscriptions[req_id] = subscription_message
            for t in topics:
                self.callback_directory[t] = callback

    async def _authenticate(self):
        expires = generate_timestamp() + 1000  # 1 second expiration
        param_str = f"GET/realtime{expires}"
        signature = generate_signature(self.api_secret, param_str)

        auth_message = json.dumps({
            "op": "auth",
            "args": [self.api_key, expires, signature]
        })

        await self.ws.send_str(auth_message)
        logger.info("Authentication request sent")

    async def _ping_loop(self):
        while self.ws and not self.ws.closed:
            try:
                await asyncio.sleep(self.ping_interval)
                if self.ws and not self.ws.closed:
                    await self.ws.send_str(json.dumps({"op": "ping"}))
            except Exception as e:
                logger.error(f"Error in ping loop: {e}")
                if not self.ws or self.ws.closed:
                    break

    async def _message_loop(self):
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    if data.get("ret_msg") == "pong" or data.get("op") == "pong":
                        continue

                    elif data.get("op") == "auth":
                        if data.get("success"):
                            logger.info("Authentication successful")
                        else:
                            logger.error(f"Authentication failed: {data}")

                    elif data.get("op") == "subscribe":
                        if data.get("success"):
                            logger.info(f"Subscription successful: {data}")
                        else:
                            logger.error(f"Subscription failed: {data}")


                    elif data.get("op") == "unsubscribe":
                        if data.get("success"):
                            logger.info(f"Unsubscription successful: {data}")
                        else:
                            logger.error(f"Unsubscription failed: {data}")
                    else:
                        await self._process_message(data)

                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.info("WebSocket connection closed by server")
                    break

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket connection error: {msg.data}")
                    break
        except Exception as e:
            logger.error(f"Error in message loop: {e}")
        finally:
            self.running = False
            if self.ws and not self.ws.closed:
                await self.ws.close()

            if not self.is_closing:
                asyncio.create_task(self._reconnect())
            else:
                logger.info("Connection closed permanently - not reconnecting")

    async def _process_message(self, message):
        if not message.get("topic"):
            await self._execute_callback(self.callback, message)
            return

        topic = message["topic"]
        if topic in self.callback_directory:
            callback = self.callback_directory[topic]

            if "orderbook" in topic:
                self._process_orderbook_update(message, topic)
                message_copy = copy.deepcopy(message)
                message_copy["type"] = "snapshot"
                message_copy["data"] = self.data.get(topic, {})
                await self._execute_callback(callback, message_copy)
            elif "tickers" in topic:
                self._process_ticker_update(message, topic)
                message_copy = copy.deepcopy(message)
                message_copy["type"] = "snapshot"
                message_copy["data"] = self.data.get(topic, {})
                await self._execute_callback(callback, message_copy)
            else:
                await self._execute_callback(callback, message)
        else:
            await self._execute_callback(self.callback, message)

    async def _execute_callback(self, callback, data):
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as e:
            logger.error(f"Error in callback: {e}")

    def _process_orderbook_update(self, message, topic):
        if topic not in self.data:
            self.data[topic] = {}

        if "snapshot" in message["type"]:
            self.data[topic] = message["data"]
            return

        if "delta" in message["type"]:
            book_sides = {"b": message["data"]["b"], "a": message["data"]["a"]}
            self.data[topic]["u"] = message["data"]["u"]
            self.data[topic]["seq"] = message["data"]["seq"]

            for side, entries in book_sides.items():
                for entry in entries:
                    # Delete price level
                    if float(entry[1]) == 0:
                        if side in self.data[topic]:
                            self.data[topic][side] = [
                                level for level in self.data[topic][side]
                                if level[0] != entry[0]
                            ]
                        continue

                    if side not in self.data[topic]:
                        self.data[topic][side] = []

                    levels = self.data[topic][side]
                    for i, level in enumerate(levels):
                        if level[0] == entry[0]:
                            # Update existing level
                            self.data[topic][side][i] = entry
                            break
                    else:
                        self.data[topic][side].append(entry)

    def _process_ticker_update(self, message, topic):
        if topic not in self.data:
            self.data[topic] = {}

        if "snapshot" in message["type"]:
            self.data[topic] = message["data"]
            return

        if "delta" in message["type"]:
            for key, value in message["data"].items():
                self.data[topic][key] = value

    async def _resubscribe(self):
        for req_id, sub_message in self.subscriptions.items():
            if self.ws and not self.ws.closed:
                await self.ws.send_str(sub_message)
                logger.info(f"Resubscribed: {sub_message}")

    async def _reconnect(self):
        if self.is_closing:
            logger.info("No reconnection attempted - client was deliberately closed")
            return

        if self.running:
            return

        logger.info("Attempting to reconnect...")
        await asyncio.sleep(1)
        if self.ws and not self.ws.closed:
            await self.ws.close()
        if self.session and not self.session.closed:
            await self.session.close()

        self.ws = None
        self.session = None

        if self.ping_task:
            self.ping_task.cancel()

        await self.connect()

    async def unsubscribe(self, topic, symbol=None):
        if symbol:
            if isinstance(symbol, str):
                symbol = [symbol]
            topics = [topic.format(symbol=s) for s in symbol]
        else:
            topics = [topic]

        req_id = str(uuid4())
        unsubscription_message = json.dumps({
            "op": "unsubscribe",
            "req_id": req_id,
            "args": topics
        })

        if self.ws and not self.ws.closed:
            await self.ws.send_str(unsubscription_message)
            logger.info(f"Unsubscribed from topics: {topics}")

            for t in topics:
                if t in self.callback_directory:
                    del self.callback_directory[t]
                if t in self.data:
                    del self.data[t]


            subscriptions_to_remove = []
            for sub_req_id, sub_message in self.subscriptions.items():
                message_data = json.loads(sub_message)
                if "args" in message_data and any(arg in message_data["args"] for arg in topics):
                    subscriptions_to_remove.append(sub_req_id)

            for sub_req_id in subscriptions_to_remove:
                del self.subscriptions[sub_req_id]

            return True
        else:
            logger.warning("WebSocket not connected. Cannot unsubscribe.")
            return False


    async def close(self):
        self.is_closing = True
        self.running = False

        if self.ping_task and not self.ping_task.done():
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                pass

        if self.ws:
            try:
                if not self.ws.closed:
                    await self.ws.close()
                if hasattr(self.ws, 'close_task') and self.ws.close_task:
                    await self.ws.close_task
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")

        if self.session:
            try:
                if not self.session.closed:
                    await self.session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")

        self.ws = None
        self.session = None
        self.ping_task = None

        logger.info("WebSocket connection has been permanently closed")
        return True


class AsyncV5WebSocketClient(AsyncWebSocketManager):
    def __init__(self, testnet=False, api_key=None, api_secret=None):
        super().__init__(self._default_callback, testnet, api_key, api_secret)

    async def _default_callback(self, message):
        logger.debug(f"Received message: {message}")

    async def subscribe_orderbook(self, symbol, depth=100, callback=None):
        topic = f"orderbook.{depth}.{{symbol}}"
        await self.subscribe(topic, callback or self._default_callback, symbol)

    async def subscribe_tickers(self, symbol, callback=None):
        topic = "tickers.{symbol}"
        await self.subscribe(topic, callback or self._default_callback, symbol)


    async def subscribe_klines(self, symbol, interval, callback=None):
        topic = f"kline.{interval}.{{symbol}}"
        await self.subscribe(topic, callback or self._default_callback, symbol)


    async def unsubscribe_orderbook(self, symbol, depth=100):
        topic = f"orderbook.{depth}.{{symbol}}"
        await self.unsubscribe(topic, symbol)

    async def unsubscribe_tickers(self, symbol):
        topic = "tickers.{symbol}"
        await self.unsubscribe(topic, symbol)


    async def unsubscribe_klines(self, symbol, interval):
        topic = f"kline.{interval}.{{symbol}}"
        await self.unsubscribe(topic, symbol)

