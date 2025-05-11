

class Buffer:
    """Represents a binary buffer with some useful methods."""

    __slots__ = ("_mv", "_pos")

    def __init__(self, data: bytes | memoryview) -> None:
        self._mv = memoryview(data)
        self._pos = 0

    def read(self, n: int) -> memoryview:
        if self._pos + n > len(self._mv):
            msg = "Buffer overflow"
            raise EOFError(msg)
        out = self._mv[self._pos:self._pos + n]
        self._pos += n
        return out

    def peek(self, n: int) -> memoryview:
        if self._pos + n > len(self._mv):
            msg = "Buffer overflow"
            raise EOFError(msg)
        return self._mv[self._pos:self._pos + n]

    def tell(self) -> int:
        return self._pos

    def seek(self, pos: int) -> None:
        self._pos = pos



