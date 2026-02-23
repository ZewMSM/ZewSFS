from dataclasses import dataclass

from sfs2x.core import Bool, Byte, Int, SFSObject, Short, UtfString
from sfs2x.protocol import ControllerID, SysAction


@dataclass(slots=True)
class Message:
    """High-level representation of SFS-Packet."""

    controller: int
    action: int
    payload: SFSObject

    def __init__(self, controller: int, action: int, payload: SFSObject | dict) -> None:
        """Initialize message."""
        self.controller = controller
        self.action = action
        self.payload = payload if type(payload) is SFSObject else SFSObject(payload)

    def to_sfs_object(self) -> SFSObject:
        """Pack message to SFS-Object."""
        return SFSObject({
            "c": Byte(self.controller),
            "a": Short(self.action),
            "p": self.payload
        })

    @classmethod
    def handshake(cls, api: str = "1.0.3", client_type: str = "UnityPlayer::") -> "Message":
        """Build the SFS2X handshake request (first message after TCP connect)."""
        return cls(
            controller=ControllerID.SYSTEM,
            action=SysAction.HANDSHAKE,
            payload=SFSObject({
                "api": UtfString(api),
                "cl": UtfString(client_type),
                "bin": Bool(True),
            }),
        )

    @classmethod
    def login(cls, zone: str, username: str, password: str,
              params: SFSObject | dict | None = None) -> "Message":
        """Build the SFS2X login request."""
        return cls(
            controller=ControllerID.SYSTEM,
            action=SysAction.LOGIN,
            payload=SFSObject({
                "zn": UtfString(zone),
                "un": UtfString(username),
                "pw": UtfString(password),
                "p": params if isinstance(params, SFSObject) else SFSObject(params or {}),
            }),
        )

    @classmethod
    def extension(cls, cmd: str, params: SFSObject | dict, *, request_id: int = -1) -> "Message":
        """Build an extension request (client -> server, action=12)."""
        ext = SFSObject({
            "c": UtfString(cmd),
            "r": Int(request_id),
            "p": params,
        })
        return cls(controller=ControllerID.EXTENSION, action=12, payload=ext)

    @property
    def is_extension_response(self) -> bool:
        """True if this is a server extension response/push (action=13)."""
        return self.controller == ControllerID.EXTENSION and self.action == SysAction.CALL_EXTENSION

    @property
    def extension_cmd(self) -> str | None:
        """Extract the command name from an extension response, or None."""
        if not self.is_extension_response:
            return None
        return self.payload.get("c")

    @property
    def extension_params(self) -> SFSObject:
        """Extract the inner params from an extension response."""
        p = self.payload.get("p")
        return p if isinstance(p, SFSObject) else self.payload

    def __repr__(self) -> str:
        """Return represented message."""
        cname = ControllerID(self.controller).name \
            if self.controller in ControllerID \
            else self.controller
        aname = SysAction(self.action).name \
            if cname == ControllerID.SYSTEM.name and self.action in SysAction \
            else self.action
        return (f"<Message {cname}/{aname} "
                f"payload={self.payload!r}>")
