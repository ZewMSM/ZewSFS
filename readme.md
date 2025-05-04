# ZewSFS Documentation

ZewSFS is a Python implementation of the SmartFoxServer2X protocol, providing both client and server-side functionality. The library is modular, allowing flexible integration into various projects.

## Modules

- **core**: Contains foundational components, including data types and serialization logic.
- **client**: Handles client-side protocol implementation (in development).
- **server**: Manages server-side protocol implementation (in development).
- **orm**: Provides ORM-style interaction with protocol packets (in development).

## Core Module Documentation

The `core` module defines the essential data types and serialization mechanisms for the SmartFoxServer2X protocol.

### Supported Data Types

The following data types are implemented in the `core` module:

- `NULL` (0): Represents a null value.
- `BOOL` (1): A boolean value (`True` or `False`).
- `BYTE` (2): An 8-bit integer.
- `SHORT` (3): A 16-bit integer.
- `INT` (4): A 32-bit integer.
- `LONG` (5): A 64-bit integer.
- `FLOAT` (6): A 32-bit floating-point number.
- `DOUBLE` (7): A 64-bit floating-point number.
- `UTF_STRING` (8): A UTF-8 encoded string.
- `BOOL_ARRAY` (9): An array of boolean values.
- `BYTE_ARRAY` (10): An array of 8-bit integers.
- `SHORT_ARRAY` (11): An array of 16-bit integers.
- `INT_ARRAY` (12): An array of 32-bit integers.
- `LONG_ARRAY` (13): An array of 64-bit integers.
- `FLOAT_ARRAY` (14): An array of 32-bit floating-point numbers.
- `DOUBLE_ARRAY` (15): An array of 64-bit floating-point numbers.
- `UTF_STRING_ARRAY` (16): An array of UTF-8 encoded strings.
- `SFS_ARRAY` (17): A container for nested arrays.
- `SFS_OBJECT` (18): A container for key-value pairs.
- `CLASS` (19): Not implemented.
- `TEXT` (20): A text string.

### Usage Examples

#### Imperative Usage

The `SFSObject` and `SFSArray` classes provide a flexible, method-chaining API for building protocol-compliant data structures.

```python
from sfs2x.core.types.containers import SFSObject, SFSArray

# Create an SFSObject
object = SFSObject()

# Add a single integer
object.put_int('number', 12)

# Chain multiple additions
object.put_double_array('doubles', [3.14, -4.5]) \
    .put_bool("flag", True)

# Dictionary-like assignment with nested SFSArray
object['array'] = SFSArray().add_long(99999999999).add_bool(False)
```

#### Declarative Usage

For a more concise approach, you can define `SFSObject` and `SFSArray` structures using Python dictionaries and lists, leveraging specific type wrappers.

```python
from sfs2x.core import UtfString, UtfStringArray, Long
from sfs2x.core.types.containers import SFSObject, SFSArray

# Create a nested SFSObject declaratively
object = SFSObject({
    'nickname': UtfString('Zewsic'),
    'tags': UtfStringArray(['pro', 'player', 'admin']),
    'friends': SFSArray([
        SFSObject({
            'id': Long(101),
            'nickname': UtfString('Cotulars'),
        }),
        SFSObject({
            'id': Long(102),
            'nickname': UtfString('Tyrant'),
        }),
    ])
})
```

#### ORM Usage

ORM-style interaction is currently in development and will provide a higher-level abstraction for working with protocol packets.

### Serialization

#### Serializing to Bytes

Convert an `SFSObject` to its binary representation for transmission or storage.

```python
packed_object = object.to_bytes()
```

#### Deserializing from Bytes

Decode a byte string into an `SFSObject` using the `decode` function.

```python
from sfs2x.core import decode
object: SFSObject = decode(b'\x12\x00\x03\x00\x03num\x04\x00\x00\x00\x0c\x00\x03str\x08\x00\x05Hello')
```

## Notes

- The `client`, `server`, and `orm` modules are under active development and will be documented as they mature.
- The `CLASS` data type (19) is not implemented in the current version.

For further details or contributions, refer to the project's Git repository.
