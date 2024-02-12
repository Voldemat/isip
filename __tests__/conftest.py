import asyncio
from typing import AsyncGenerator
import pytest
from isip.client import SIPClient

from isip.parser import SIPParser


@pytest.fixture
def parser() -> SIPParser:
    return SIPParser()


@pytest.fixture
async def client(parser: SIPParser) -> AsyncGenerator[SIPClient, None]:
    c = SIPClient(host="localhost", port=5060, parser=parser)
    await c.connect(loop=asyncio.get_running_loop())
    try:
        yield c
    finally:
        await c.disconnect()
