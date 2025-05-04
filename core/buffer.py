from typing import Union


class Buffer:
    __slots__ = ('_mv', '_pos')

    def __init__(self, data: Union[bytes, bytes, memoryview]):
        self._mv = memoryview(data)
        self._pos = 0

    def read(self, n: int) -> memoryview:
        if self._pos + n > len(self._mv):
            raise EOFError("Buffer overflow")
        out = self._mv[self._pos:self._pos + n]
        self._pos += n
        return out

    def peek(self, n: int) -> memoryview:
        if self._pos + n > len(self._mv):
            raise EOFError("Buffer overflow")
        return self._mv[self._pos:self._pos + n]

    def tell(self) -> int:
        return self._pos

    def seek(self, pos: int) -> None:
        self._pos = pos



