"""Built-in models for the standard SFS2X system actions.

Field keys mirror the SFS2X SDK conventions (``zn`` = zone, ``un`` =
username, etc.). Optional fields are declared as ``T | None`` so a
missing key parses as ``None`` instead of raising.
"""

from __future__ import annotations

from sfs2x.app.models import field
from sfs2x.app.responses import (
    SystemRequest,
    SystemResponse,
)
from sfs2x.core import (
    Bool,
    Int,
    Short,
    SFSObject,
    UtfString,
    UtfStringArray,
)
from sfs2x.protocol import SysAction


class HandshakeRequest(SystemRequest, action=SysAction.HANDSHAKE):
    api: UtfString = field("api", default="1.7.3")
    cl: UtfString = field("cl", default="Python/ZewSFS")
    bin: Bool = field("bin", default=True)


class HandshakeResponse(SystemResponse, action=SysAction.HANDSHAKE):
    token: UtfString | None = field("tk", default=None)
    compression_threshold: Int | None = field("ct", default=None)
    max_message_size: Int | None = field("ms", default=None)


class LoginRequest(SystemRequest, action=SysAction.LOGIN):
    zone: UtfString = field("zn")
    username: UtfString = field("un", default="")
    password: UtfString = field("pw", default="")
    params: SFSObject = field("p", default_factory=SFSObject)


class LoginResponse(SystemResponse, action=SysAction.LOGIN):
    zone: UtfString | None = field("zn", default=None)
    username: UtfString | None = field("un", default=None)
    user_id: Int | None = field("id", default=None)
    privilege_id: Int = field("pi", default=0)
    params: SFSObject | None = field("p", default=None)


class LoginErrorResponse(SystemResponse, action=SysAction.LOGIN):
    error_code: Short = field("ec")
    error_message: UtfString | None = field("em", default=None)
    error_params: UtfStringArray | None = field("epr", default=None)


class LogoutRequest(SystemRequest, action=SysAction.LOGOUT):
    pass


class LogoutResponse(SystemResponse, action=SysAction.LOGOUT):
    zone: UtfString | None = field("zn", default=None)


class PingPongRequest(SystemRequest, action=SysAction.PING_PONG):
    pass


class PingPongResponse(SystemResponse, action=SysAction.PING_PONG):
    pass
