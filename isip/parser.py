from __future__ import annotations
import logging

import re
from dataclasses import dataclass

from .utils import (
    build_contact,
    build_digest_response,
    build_from,
    build_request_uri,
    build_to,
    build_via,
    gen_branch,
    get_host_and_username_from_contact,
)

digest_regex = re.compile(r'(\w+)[:=][\s"]?([^",]+)"?')


@dataclass
class SIPBaseMessage:
    version: str
    body: str | None
    headers: dict[str, str]


@dataclass
class SIPRequest(SIPBaseMessage):
    method: str
    request_uri: str

    def __post_init__(self) -> None:
        self.headers["Content-Length"] = str(len(self.body or ""))

    def serialize(self) -> bytes:
        buffer = f"{self.method} {self.request_uri} {self.version}\r\n"
        headers = self.headers
        for key, value in headers.items():
            buffer += f"{key}: {value}\r\n"
        buffer += "\r\n"
        if self.body is not None:
            buffer += self.body
        return buffer.encode()


@dataclass
class SIPRegisterRequest(SIPRequest):
    @classmethod
    def build_new(
        cls,
        username: str,
        local_host: str,
        local_port: int,
        host: str,
        port: int,
        call_id: str,
        expires_s: int,
        cseq: int = 1,
    ) -> SIPRegisterRequest:
        local_contact = build_contact(username, local_host, local_port)
        remote_contact = build_contact(username, host, port)
        headers = {
            "Contact": local_contact,
            "Via": build_via(local_host, local_port),
            "CSeq": f"{cseq} REGISTER",
            "Call-ID": call_id,
            "From": build_from(username, remote_contact),
            "To": build_to(username, remote_contact),
            "Max-Forwards": "70",
        }
        if expires_s is not None:
            headers["Expires"] = str(expires_s)
        return SIPRegisterRequest(
            method="REGISTER",
            request_uri=build_request_uri(username, host, port),
            version="SIP/2.0",
            headers=headers,
            body=None,
        )

    @classmethod
    def build_from_response(
        cls, request: SIPRegisterRequest, response: SIPResponse, password: str
    ) -> SIPRegisterRequest:
        username, host = get_host_and_username_from_contact(
            request.headers["Contact"]
        )
        authenticate = response.headers["WWW-Authenticate"]
        options = dict(digest_regex.findall(authenticate))
        auth_response = build_digest_response(
            realm=options["realm"],
            method=request.method,
            host=host,
            username=username,
            password=password,
            nonce=options["nonce"],
            opaque=options["opaque"],
        )
        return SIPRegisterRequest(
            method="REGISTER",
            request_uri=request.request_uri,
            version="SIP/2.0",
            headers={
                "Contact": request.headers["Contact"],
                "Via": response.headers["Via"].split(";")[0]
                + f";branch={gen_branch()};alias",
                "CSeq": request.headers["CSeq"],
                "Call-ID": request.headers["Call-ID"],
                "From": request.headers["From"],
                "To": request.headers["To"],
                "Authorization": auth_response,
            },
            body=None,
        )


@dataclass
class SIPResponse(SIPBaseMessage):
    status: int
    reason: str


SIPMessage = SIPRequest | SIPResponse


class SIPParser:
    def __init__(
        self, logger: logging.Logger = logging.getLogger(__name__)
    ) -> None:
        self.logger = logger

    def parse_request(self, message: str) -> SIPRequest | Exception:
        self.logger.debug(f"(parse_request) message: {message}")
        lines = message.split("\r\n")
        self.logger.debug(f"(parse_request) lines: {lines}")
        start_line = lines.pop(0)
        self.logger.debug(f"(parse_request) start_line: {start_line}")
        method, request_uri, version = start_line.split(" ")
        result = self.parse_headers_and_body(lines)
        if isinstance(result, ValueError):
            return result
        headers, body = result
        return SIPRequest(
            body=body,
            method=method,
            version=version,
            headers=headers,
            request_uri=request_uri,
        )

    def parse_headers_and_body(
        self, lines: list[str]
    ) -> tuple[dict[str, str], str | None] | ValueError:
        headers: dict[str, str] = {}
        line_break_index: int | None = None
        for index, line in enumerate(lines):
            if line == "":
                line_break_index = index
                break
            self.logger.debug(
                f"(parse_headers_and_body) line before split: {line}"
            )
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
        body: str | None = None
        if line_break_index is not None and len(lines) > line_break_index + 1:
            body = "\r\n".join(lines[line_break_index + 1 :])
        return headers, body

    def parse_response(self, message: str) -> SIPResponse | Exception:
        try:
            lines = message.split("\r\n")
            status_line = lines.pop(0)
            version, status, reason = status_line.split(" ")
            result = self.parse_headers_and_body(lines)
            if isinstance(result, ValueError):
                return result
            headers, body = result
            return SIPResponse(
                body=body,
                reason=reason,
                version=version,
                headers=headers,
                status=int(status),
            )
        except Exception as exc:
            return exc

    def parse(self, buffer: str) -> SIPMessage | Exception:
        result: SIPMessage | Exception
        result = self.parse_response(buffer)
        if isinstance(result, SIPResponse):
            return result
        result = self.parse_request(buffer)
        return result
