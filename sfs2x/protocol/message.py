from dataclasses import dataclass

from sfs2x.core import Byte, Int, SFSObject, Short, UtfString
from sfs2x.protocol import ControllerID, SysAction


@dataclass(slots=True)
class Message:
    """High-level representation of SFS-Packet."""

    controller: int
    action: int
    payload: SFSObject

    def to_sfs_object(self) -> SFSObject:
        """Pack message to SFS-Object."""
        return SFSObject({
            "c": Byte(self.controller),
            "a": Short(self.action),
            "p": self.payload
        })

    @classmethod
    def extension(cls, cmd: str, params: SFSObject, *, request_id: int = -1) -> "Message":
        ext = SFSObject({
            "c": UtfString(cmd),
            "r": Int(request_id),
            "p": params,
        })
        return cls(controller=ControllerID.EXTENSION, action=12, payload=ext)

    def __repr__(self) -> str:
        """Return represented message."""
        cname = ControllerID(self.controller).name \
            if self.controller in ControllerID \
            else self.controller
        aname = SysAction(self.action).name \
            if cname == ControllerID.SYSTEM.name and self.action in SysAction \
            else self.action
        return (f"f<Message {cname}/{aname} "
                f"payload={self.payload!r}>")
