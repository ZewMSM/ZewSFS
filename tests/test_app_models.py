import pytest

from sfs2x.app import (
    ExtensionRequest,
    ExtensionResponse,
    Int,
    Long,
    ParseError,
    SFSArray,
    SFSModel,
    SFSObject,
    SystemRequest,
    SystemResponse,
    UtfString,
    UtfStringArray,
    field,
)
from sfs2x.protocol import ControllerID, SysAction


def test_declaration_uses_sfs_annotations():
    class M(SFSModel):
        name: UtfString = field("n")
        score: Int = field("s")

    m = M(name="alice", score=42)
    assert m.name == "alice"
    assert m.score == 42


def test_to_and_from_sfs_object_roundtrip():
    class M(SFSModel):
        name: UtfString = field("n")
        score: Int = field("s")

    m = M(name="alice", score=42)
    obj = m.to_sfs_object()
    assert obj.value["n"].value == "alice"
    assert obj.value["s"].value == 42
    back = M.from_sfs_object(obj)
    assert back == m


def test_long_vs_int_annotation_distinguished_on_wire():
    class A(SFSModel):
        x: Int = field("x")

    class B(SFSModel):
        x: Long = field("x")

    a_obj = A(x=1).to_sfs_object()
    b_obj = B(x=1).to_sfs_object()
    assert type(a_obj.value["x"]).__name__ == "Int"
    assert type(b_obj.value["x"]).__name__ == "Long"


def test_missing_required_raises():
    class M(SFSModel):
        name: UtfString = field("n")

    with pytest.raises(TypeError):
        M()
    with pytest.raises(ParseError):
        M.from_sfs_object(SFSObject())


def test_optional_field_defaults_to_none():
    class M(SFSModel):
        name: UtfString | None = field("n", default=None)

    m = M()
    assert m.name is None
    obj = m.to_sfs_object()
    assert "n" not in obj.value
    back = M.from_sfs_object(SFSObject())
    assert back.name is None


def test_default_factory():
    class M(SFSModel):
        params: SFSObject = field("p", default_factory=SFSObject)

    m1 = M()
    m2 = M()
    assert m1.params is not m2.params
    assert isinstance(m1.params, SFSObject)


def test_nested_model_roundtrip():
    class Inner(SFSModel):
        v: Int = field("v")

    class Outer(SFSModel):
        inner: Inner = field("in")

    o = Outer(inner=Inner(v=7))
    obj = o.to_sfs_object()
    inner_obj = obj.value["in"]
    assert isinstance(inner_obj, SFSObject)
    assert inner_obj.value["v"].value == 7

    back = Outer.from_sfs_object(obj)
    assert isinstance(back.inner, Inner)
    assert back.inner.v == 7


def test_sfs_object_passthrough():
    class M(SFSModel):
        data: SFSObject = field("d")

    inner = SFSObject({"x": Int(1)})
    m = M(data=inner)
    obj = m.to_sfs_object()
    assert obj.value["d"] is inner
    back = M.from_sfs_object(obj)
    assert isinstance(back.data, SFSObject)
    assert back.data.value["x"].value == 1


def test_sfs_array_passthrough():
    class M(SFSModel):
        items: SFSArray = field("i")

    arr = SFSArray([Int(1), Int(2)])
    m = M(items=arr)
    obj = m.to_sfs_object()
    back = M.from_sfs_object(obj)
    assert isinstance(back.items, SFSArray)


def test_try_from_sfs_object_returns_none_on_mismatch():
    class M(SFSModel):
        required: Int = field("r")

    assert M.try_from_sfs_object(SFSObject()) is None


def test_try_from_sfs_object_returns_instance_on_match():
    class M(SFSModel):
        v: Int = field("v")

    parsed = M.try_from_sfs_object(SFSObject({"v": Int(3)}))
    assert parsed == M(v=3)


def test_system_request_to_message():
    class MyReq(SystemRequest, action=SysAction.LOGIN):
        zone: UtfString = field("zn")

    msg = MyReq(zone="x").to_message()
    assert msg.controller == ControllerID.SYSTEM
    assert msg.action == SysAction.LOGIN
    assert msg.payload.value["zn"].value == "x"


def test_extension_request_to_message_with_request_id():
    class MyExt(ExtensionRequest, command="ping"):
        v: Int = field("v")

    msg = MyExt(v=9).to_message(request_id=42)
    assert msg.controller == ControllerID.EXTENSION
    assert msg.payload.value["c"].value == "ping"
    assert msg.payload.value["r"].value == 42
    assert msg.payload.value["p"].value["v"].value == 9


def test_response_is_raisable():
    class R(ExtensionResponse, command="x"):
        n: Int = field("n")

    with pytest.raises(R) as ei:
        raise R(n=5)
    assert ei.value.n == 5


def test_repr_and_eq():
    class M(SFSModel):
        a: Int = field("a")
        b: UtfString = field("b")

    m1 = M(a=1, b="x")
    m2 = M(a=1, b="x")
    m3 = M(a=2, b="x")
    assert m1 == m2
    assert m1 != m3
    assert "a=1" in repr(m1)


def test_unsupported_annotation_rejected():
    with pytest.raises(TypeError):
        class Bad(SFSModel):
            x: int = field("x")  # python type, not SFS type — should fail


def test_inheritance_preserves_fields():
    class Base(SFSModel):
        a: Int = field("a")

    class Child(Base):
        b: UtfString = field("b")

    c = Child(a=1, b="x")
    assert c.a == 1
    assert c.b == "x"
    obj = c.to_sfs_object()
    assert "a" in obj.value
    assert "b" in obj.value


def test_array_types():
    class M(SFSModel):
        names: UtfStringArray = field("ns")

    m = M(names=["alice", "bob"])
    obj = m.to_sfs_object()
    assert obj.value["ns"].value == ["alice", "bob"]
    back = M.from_sfs_object(obj)
    assert back.names == ["alice", "bob"]
