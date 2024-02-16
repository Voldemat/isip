import asyncio
import logging

from .client import SIPClient
from .parser import SIPRegisterRequest, SIPRequest, SIPResponse
from .utils import gen_call_id


class SIPHolder:
    task: asyncio.Task[None] | None

    def __init__(
        self,
        client: SIPClient,
        username: str,
        password: str,
        registration_expires_s: int = 30,
        logger: logging.Logger = logging.getLogger(__name__),
    ) -> None:
        self.logger = logger
        self.client = client
        self.registration_count = 1
        self.should_stop = False
        self.task = None
        self.username = username
        self.password = password
        self.call_id = gen_call_id()
        self.registration_expires_s = registration_expires_s

    async def start(self) -> None:
        self.task = asyncio.create_task(self.task_main())

    async def task_main(self) -> None:
        while not self.should_stop:
            await self.register()
            self.logger.debug(f"Sleeping for {self.registration_expires_s}s")
            await asyncio.sleep(self.registration_expires_s)

    async def register(self) -> None:
        self.logger.debug("Starting register routine")
        local_host, local_port = self.client.get_local_addr()
        self.logger.debug(f"Local addr: {local_host}:{local_port}")
        request = SIPRegisterRequest.build_new(
            username=self.username,
            host=self.client.host,
            port=self.client.port,
            local_host=local_host,
            local_port=local_port,
            call_id=self.call_id,
            cseq=self.registration_count,
            expires_s=self.registration_expires_s,
        )
        self.logger.debug(
            f"Builded new register request: \n {request.serialize().decode()}"
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
        self.registration_count += 1

    async def send_and_receive(
        self, request: SIPRequest
    ) -> SIPResponse | None:
        self.client.clear_queue()
        for _ in range(0, 3):
            await self.client.send_message(request)
            try:
                message = await asyncio.wait_for(
                    self.client.wait_for_message(), timeout=10
                )
                self.logger.debug(f"Received message: {message}")
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
