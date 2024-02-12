import asyncio

import pytest
from isip.client import SIPClient
from isip.holder import SIPHolder


@pytest.mark.asyncio
async def test_holder(client: SIPClient) -> None:
    holder = SIPHolder(client=client, username="alice", password="alice")
    try:
        await holder.start()
        await asyncio.sleep(100000000)
    finally:
        await holder.stop()
