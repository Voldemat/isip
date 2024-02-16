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
            try:
                await self.register()
            except BaseException:
                self.logger.exception("Register exception: ")
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
        response = await self.send_and_receive(request)
        if isinstance(response, Exception):
            raise response
        request_with_auth = SIPRegisterRequest.build_from_response(
            request=request, response=response, password=self.password
        )
        response = await self.send_and_receive(request_with_auth)
        if isinstance(response, Exception):
            raise response
        self.registration_count += 1

    async def send_and_receive(
        self, request: SIPRequest
    ) -> SIPResponse | Exception:
        self.client.clear_queue()
        last_error: Exception | None = None
        for _ in range(0, 3):
            await self.client.send_message(request)
            try:
                message = await asyncio.wait_for(
                    self.client.wait_for_message(), timeout=10
                )
                self.logger.debug(f"Received message: {message}")
                if message is None:
                    last_error = RuntimeError(
                        "Returned None when expected response"
                    )
                elif isinstance(message, SIPRequest):
                    last_error = RuntimeError(
                        f"Received request: {message} when expected response"
                    )
                else:
                    return message
            except asyncio.TimeoutError:
                last_error = RuntimeError("Waiting for message timed out")
                continue
        assert last_error is not None
        return last_error

    async def stop(self) -> None:
        if self.task is None:
            return
        self.should_stop = True
        try:
            await asyncio.wait_for(self.task, timeout=3)
            return
        except asyncio.TimeoutError:
            pass
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass
