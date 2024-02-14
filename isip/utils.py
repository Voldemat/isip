import hashlib
import uuid


def build_request_uri(username: str, host: str, port: int) -> str:
    return f"sip:{username}@{host}:{port}"


def gen_branch() -> str:
    return "z9hG4bK." + uuid.uuid4().hex[:24]


def build_contact(username: str, host: str, port: int) -> str:
    return f"<sip:{username}@{host}:{port}>"


def get_host_and_username_from_contact(contact: str) -> tuple[str, str]:
    username, host = contact[1:-1].split(":", 1)[1].split("@")
    return username, host


def build_via(host: str, port: int) -> str:
    return f"SIP/2.0/UDP {host}:{port};" f"branch={gen_branch()};alias"


def build_from(username: str, contact: str) -> str:
    return f'"{username}" {contact}'


def build_to(username: str, contact: str) -> str:
    return f'"{username}" {contact}'


def build_digest(
    method: str,
    host: str,
    realm: str,
    nonce: str,
    username: str,
    password: str,
) -> str:
    part1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
    part2 = hashlib.md5(f"{method}:{host}".encode()).hexdigest()
    return hashlib.md5(f"{part1}:{nonce}:{part2}".encode()).hexdigest()


def build_digest_response(
    method: str,
    host: str,
    realm: str,
    nonce: str,
    username: str,
    password: str,
    opaque: str,
) -> str:
    hash = build_digest(
        method=method,
        host=host,
        realm=realm,
        nonce=nonce,
        username=username,
        password=password,
    )
    return (
        f'Digest username="{username}", realm="{realm}", '
        f'nonce="{nonce}", uri="{host}", algorithm=MD5, '
        f'opaque="{opaque}", response="{hash}"'
    )


def gen_call_id() -> str:
    return str(uuid.uuid4())
