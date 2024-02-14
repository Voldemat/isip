from __future__ import annotations

import asyncio
import socket
import logging
from collections import deque
from typing import Any, AsyncGenerator

from .parser import SIPMessage, SIPParser, SIPRequest


class SIPProtocol(asyncio.DatagramProtocol):
    def __init__(self, client: SIPClient) -> None:
        self.client = client

    def datagram_received(self, data: bytes, _: tuple[str | Any, int]) -> None:
        self.client._on_datagram(data)

    def connection_lost(self, exc: Exception | None) -> None:
        self.client._close_connection(exc)


class SIPClient(AsyncGenerator[SIPMessage, None]):
    transport: asyncio.DatagramTransport | None
    closed_event: asyncio.Event
    queue: deque[SIPMessage]
    logger: logging.Logger

    def __init__(
        self,
        host: str,
        port: int,
        parser: SIPParser,
        local_host: str = "0.0.0.0",
        local_port: int = 5060,
        logger: logging.Logger = logging.getLogger(__name__),
    ) -> None:
        self.logger = logger
        self.port = port
        self.host = host
        self.local_host = local_host
        self.local_port = local_port
        self.parser = parser
        self.queue = deque()
        self.transport = None
        self.new_msg_event = asyncio.Event()
        self.closed_event = asyncio.Event()

    async def send_message(self, msg: SIPRequest) -> None:
        assert self.transport is not None, "Client is not connected"
        content = msg.serialize()
        self.logger.debug(
            f"(send_message) Sending content: {content.decode()}"
        )
        self.transport.sendto(data=content)

    async def connect(self, loop: asyncio.AbstractEventLoop) -> None:
        if self.transport is not None:
            self.logger.debug("(connect) Already connected...")
            return
        self.logger.debug(
            "(connect) Creating datagram endpoint to "
            f"{self.host}:{self.port}"
        )
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: SIPProtocol(self),
            local_addr=(self.local_host, self.local_port),
            remote_addr=(self.host, self.port),
            family=socket.AF_INET,
        )
        self.logger.info(
            f"(connect) Created datagram endpoint to {self.host}:{self.port}"
        )
        self.closed_event.clear()

    def get_message(self) -> SIPMessage | None:
        if len(self.queue) == 0:
            return None
        return self.queue.popleft()

    async def wait_for_message(self) -> SIPMessage | None:
        msg = self.get_message()
        if msg is not None:
            self.logger.debug(f"(wait_for_message) returning msg: {msg}")
            return msg
        self.logger.debug("(wait_for_message) blocking on event...")
        await self.new_msg_event.wait()
        self.new_msg_event.clear()
        return self.get_message()

    def __aiter__(self) -> SIPClient:
        return self

    async def asend(self, _: None) -> SIPMessage:
        msg = await self.wait_for_message()
        if msg is None:
            raise StopAsyncIteration()
        return msg

    async def athrow(self, *args: Any, **kwargs: Any) -> SIPMessage:
        return await super().athrow(*args, **kwargs)

    async def disconnect(self) -> None:
        if self.transport is None:
            self.logger.debug("(disconnect) Not connected, skipping...")
            return
        if not self.transport.is_closing():
            self.transport.close()
        self.logger.info(
            f"(disconnect) Disconnected from {self.host}:{self.port}"
        )
        await self.closed_event.wait()
        self.closed_event.clear()

    def clear_queue(self) -> None:
        self.queue.clear()

    def _on_datagram(self, buffer: bytes) -> None:
        self.logger.debug(f"Received datagram: \n{buffer.decode()}")
        try:
            msg = self.parser.parse(buffer.decode())
            if isinstance(msg, Exception):
                raise msg
            self.queue.append(msg)
            self.new_msg_event.set()
        except BaseException:
            self.logger.exception("Parsing error: ")
            raise

    def _close_connection(self, exc: Exception | None) -> None:
        if exc is not None:
            self.logger.error(f"Error on close_connection: {exc}")
        self.closed_event.set()
        self.new_msg_event.set()

    def get_local_addr(self) -> tuple[str, int]:
        return self.local_host, self.local_port
