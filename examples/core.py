#################### IMPERATIVE USAGE ####################
from sfs2x.core import UtfString, UtfStringArray, Long, decode
from sfs2x.core.types.containers import SFSObject, SFSArray

object = SFSObject()

# basic
object.put_int('number', 12)

# multi-put
object.put_double_array('doubles', [3.14, -4.5]) \
    .put_bool("flag", True)

# dict-like
object['array'] = SFSArray().add_long(99999999999).add_bool(False)

#################### DECLARATIVE USAGE ####################
from sfs2x.core import UtfString, UtfStringArray, Long, decode
from sfs2x.core.types.containers import SFSObject, SFSArray

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

#################### PACK TO BYTES ####################

packed_object = object.to_bytes()

#################### LOAD FROM BYTES ####################

object: SFSObject = decode(b'\x12\x00\x03\x00\x03num\x04\x00\x00\x00\x0c\x00\x03str\x08\x00\x05Hello')