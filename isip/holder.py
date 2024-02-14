import asyncio
import uuid
from isip.client import SIPClient
from isip.parser import SIPRegisterRequest, SIPRequest, SIPResponse


class SIPHolder:
    task: asyncio.Task[None] | None

    def __init__(
        self, client: SIPClient, username: str, password: str
    ) -> None:
        self.client = client
        self.should_stop = False
        self.task = None
        self.username = username
        self.password = password

    async def start(self) -> None:
        self.task = asyncio.create_task(self.task_main())

    async def task_main(self) -> None:
        call_id = str(uuid.uuid4())
        while not self.should_stop:
            await self.register(call_id)
            await asyncio.sleep(30)

    async def register(self, call_id: str) -> None:
        local_host, local_port = self.client.get_local_addr()
        request = SIPRegisterRequest.build_new(
            username=self.username,
            host=self.client.host,
            port=self.client.port,
            local_host=local_host,
            local_port=local_port,
            call_id=call_id,
        )
        response: SIPResponse | None = await self.send_and_receive(request)
        if response is None:
            raise RuntimeError(
                f"Cannot register number {self.username} "
                f"on host {self.client.host}:{self.client.port}"
            )
        assert response.status == 401, "Response status not 401"
        request_with_auth = SIPRegisterRequest.build_from_response(
            request=request, response=response, password=self.password
        )
        response = await self.send_and_receive(request_with_auth)
        if response is None or response.status != 200:
            raise RuntimeError(
                f"Cannot register number {self.username} "
                f"on host {self.client.host}:{self.client.port}"
            )

    async def send_and_receive(
        self, request: SIPRequest
    ) -> SIPResponse | None:
        self.client.clear_queue()
        for _ in range(0, 3):
            print("sending: ", request)
            await self.client.send_message(request)
            try:
                message = await asyncio.wait_for(
                    self.client.wait_for_message(), timeout=10
                )
                assert message is not None, "Message is None"
                assert isinstance(
                    message, SIPResponse
                ), "Message is not response"
                return message
            except asyncio.TimeoutError:
                continue

        return None

    async def stop(self) -> None:
        self.should_stop = True
        if self.task is not None:
            self.task.cancel()
