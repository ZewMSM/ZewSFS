class ProtocolError(RuntimeError):
    """Exception appears when packet structure is invalid."""

class UnsupportedFlagError(ProtocolError):
    """Exception appears when trying to use ENCRYPTED or COMPRESSED flags."""
