from dataclasses import dataclass
from os import urandom
from typing import Protocol, runtime_checkable

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

_KEY_LENGTH: int = 16


@runtime_checkable
class Cipher(Protocol):
    """Minimal symetric cipher protocol."""

    def encrypt(self, data: bytes) -> bytes: ...

    def decrypt(self, data: bytes) -> bytes: ...


@dataclass(slots=True)
class AESCipher(Cipher):
    """AES-128-CBC with PKCS#7 and padding (16-bit)."""

    key: bytes  # 16 signs only

    def __post_init__(self) -> None:
        """Check key length."""
        if len(self.key) != _KEY_LENGTH:
            msg = "key must be 16 bytes long"
            raise ValueError(msg)

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data, using AES-128-CBC."""
        iv = urandom(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return iv + cipher.encrypt(pad(data, 16))

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt data, using AES-128-CBC."""
        iv = data[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(data[16:]), 16)
