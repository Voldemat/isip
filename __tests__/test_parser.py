from isip.parser import SIPParser


NOTIFY_REQUEST = """NOTIFY sip:150@10.135.0.12;line=16172 SIP/2.0
Via: SIP/2.0/UDP 10.135.0.1;\
branch=z9hG4bK1308.a003bf56000000000000000000000000.0
To: <sip:150@10.135.0.1>;tag=l0hih
From: <sip:vmaccess*150@10.135.0.1>;\
tag=a6a1c5f60faecf035a1ae5b6e96e979a-6277
CSeq: 1111 NOTIFY
Call-ID: fi6am90efehg8ku2c1p2uwrvy@10.135.0.1
Content-Length: 90
User-Agent: Wildix GW-4.2.5.35963
Max-Forwards: 70
Event: message-summary
Contact: <sip:vmaccess*150@mypbx.wildixin.com:5060;user=phone>
Subscription-State: active;expires=240
Content-Type: application/simple-message-summary

Messages-Waiting: yes
Message-Account: sip:vmaccess*150@wildix
Voice-Message: 1/0 (1/0)
"""

REGISTER_RESPONSE = """SIP/2.0 401 Unauthorized
Via: SIP/2.0/UDP 10.10.1.13:5060;branch=z9hG4bK78946131-99e1;\
received=10.10.1.13;rport=5060
From: <sip:13@10.10.1.99>;tag=d60e6131-99e1-de11-8845-080027608325
To: <sip:13@10.10.1.99>;tag=as5489aead
Call-ID: e4ec6031-99e1
CSeq: 1 REGISTER
User-Agent: My PBX
Allow: INVITE, ACK, CANCEL, OPTIONS, BYE, REFER, SUBSCRIBE, NOTIFY
Supported: replaces
WWW-Authenticate: Digest algorithm=MD5, realm="mypbx", nonce="343eb793"
Content-Length: 0
"""


def test_parse_request(parser: SIPParser) -> None:
    message = parser.parse_request(NOTIFY_REQUEST)
    if isinstance(message, Exception):
        raise message
    assert message.method == "NOTIFY"
    assert message.request_uri == "sip:150@10.135.0.12;line=16172"
    assert message.version == "SIP/2.0"
    assert message.headers.get("Via") == (
        "SIP/2.0/UDP 10.135.0.1;"
        "branch=z9hG4bK1308.a003bf56000000000000000000000000.0"
    )
    assert message.headers.get("To") == "<sip:150@10.135.0.1>;tag=l0hih"
    assert message.headers.get("From") == (
        "<sip:vmaccess*150@10.135.0.1>;"
        "tag=a6a1c5f60faecf035a1ae5b6e96e979a-6277"
    )
    assert message.headers.get("CSeq") == "1111 NOTIFY"
    assert message.headers.get("Call-ID") == (
        "fi6am90efehg8ku2c1p2uwrvy@10.135.0.1"
    )
    assert message.headers.get("Content-Length") == "90"
    assert message.headers.get("User-Agent") == "Wildix GW-4.2.5.35963"
    assert message.headers.get("Max-Forwards") == "70"
    assert message.headers.get("Event") == "message-summary"
    assert message.headers.get("Contact") == (
        "<sip:vmaccess*150@mypbx.wildixin.com:5060;user=phone>"
    )
    assert message.headers.get("Subscription-State") == "active;expires=240"
    assert message.headers.get("Content-Type") == (
        "application/simple-message-summary"
    )
    assert message.body == (
        "Messages-Waiting: yes\n"
        "Message-Account: sip:vmaccess*150@wildix\n"
        "Voice-Message: 1/0 (1/0)\n"
    )


def test_parse_response(parser: SIPParser) -> None:
    response = parser.parse_response(REGISTER_RESPONSE)
    if isinstance(response, Exception):
        raise response
    assert response.status == 401
    assert response.reason == "Unauthorized"
    assert response.version == "SIP/2.0"
    assert response.body is None
    assert response.headers.get("Via") == (
        "SIP/2.0/UDP 10.10.1.13:5060;branch=z9hG4bK78946131-99e1;"
        "received=10.10.1.13;rport=5060"
    )
    assert response.headers.get("From") == (
        "<sip:13@10.10.1.99>;tag=d60e6131-99e1-de11-8845-080027608325"
    )
    assert response.headers.get("To") == "<sip:13@10.10.1.99>;tag=as5489aead"
    assert response.headers.get("Call-ID") == "e4ec6031-99e1"
    assert response.headers.get("CSeq") == "1 REGISTER"
    assert response.headers.get("User-Agent") == "My PBX"
    assert response.headers.get("Allow") == (
        "INVITE, ACK, CANCEL, OPTIONS, BYE, REFER, SUBSCRIBE, NOTIFY"
    )
    assert response.headers.get("Supported") == "replaces"
    assert response.headers.get("WWW-Authenticate") == (
        'Digest algorithm=MD5, realm="mypbx", nonce="343eb793"'
    )
    assert response.headers.get("Content-Length") == "0"
