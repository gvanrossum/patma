from patma import *
import dataclasses


@dataclasses.dataclass
class MyClass:
    x: int
    y: str


def test_literal_pattern():
    # case 42:
    pat = LiteralPattern(42)
    assert pat.match(42) == {}
    assert pat.match(0) is None
    assert pat.match('42') is None


def test_alternatives_pattern():
    # case 1|2|3:
    pat = AlternativesPattern([LiteralPattern(i) for i in [1, 2, 3]])
    assert pat.match(1) == {}
    assert pat.match(2) == {}
    assert pat.match(3) == {}
    assert pat.match(0) is None
    assert pat.match(4) is None
    assert pat.match('1') is None


def test_instance_pattern():
    # case MyClass(xx: int, y='hello'):
    vxx = AnnotatedPattern(VariablePattern('xx'), int)
    hello = LiteralPattern('hello')
    pat = InstancePattern(MyClass, [vxx], {'y': hello})
    match = pat.match(MyClass(42, "hello"))
    assert match == {'xx': 42}
