"""Request/response base classes for the high-level SFS app layer.

``SystemRequest`` / ``SystemResponse`` correspond to controller=SYSTEM
messages (``SysAction.LOGIN`` etc). ``ExtensionRequest`` /
``ExtensionResponse`` correspond to controller=EXTENSION extension calls
keyed by a command string.

Response classes additionally inherit from ``_RaisableMixin`` (a tiny
``Exception`` subclass) so handlers can write ``raise PussyResponse(...)``
and the dispatcher catches it and sends the reply. ``Reply(model)`` is
the more explicit wrapper for non-Response models.
"""

from __future__ import annotations

from typing import ClassVar

from sfs2x.app.models import SFSModel
from sfs2x.core import SFSObject
from sfs2x.protocol import ControllerID, Message


class Reply(Exception):
    """Wrap an SFSModel into an exception so handlers can ``raise`` it."""

    def __init__(self, model: SFSModel) -> None:
        self.model = model
        super().__init__(repr(model))


class _RaisableMixin(Exception):
    """Mixin so ``raise SomeResponse(...)`` works inside handlers."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        Exception.__init__(self)


class SystemRequest(SFSModel):
    """Base for outbound/inbound system messages (HANDSHAKE/LOGIN/...)."""

    __action__: ClassVar[int]

    def to_message(self) -> Message:
        return Message(ControllerID.SYSTEM, self.__action__, self.to_sfs_object())


class SystemResponse(SFSModel, _RaisableMixin):
    """Base for system replies — raisable so ``raise LoginResponse(...)`` works."""

    __action__: ClassVar[int]

    def to_message(self) -> Message:
        return Message(ControllerID.SYSTEM, self.__action__, self.to_sfs_object())


class ExtensionRequest(SFSModel):
    """Base for outbound/inbound extension commands."""

    __command__: ClassVar[str]

    def to_message(self, request_id: int = -1) -> Message:
        params: SFSObject = self.to_sfs_object()
        return Message.extension(self.__command__, params, request_id=request_id)


class ExtensionResponse(SFSModel, _RaisableMixin):
    """Base for extension replies — also raisable."""

    __command__: ClassVar[str]

    def to_message(self, request_id: int = -1) -> Message:
        params: SFSObject = self.to_sfs_object()
        return Message.extension(self.__command__, params, request_id=request_id)
