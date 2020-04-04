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


def test_variable_pattern():
    # case x:
    pat = VariablePattern('x')
    assert pat.match(42) == {'x': 42}
    assert pat.match((1, 2)) == {'x': (1, 2)}
    assert pat.match(None) == {'x': None}


def test_annotated_pattern():
    # case (x: int):
    pat = AnnotatedPattern(VariablePattern('x'), int)
    assert pat.match(42) == {'x': 42}
    assert pat.match('hello') is None


def test_sequence_pattern():
    # case (x, y, z):
    pat = SequencePattern([VariablePattern(s) for s in 'xyz'])
    assert pat.match((1, 2, 3)) == {'x': 1, 'y': 2, 'z': 3}
    assert pat.match((1, 2)) is None
    assert pat.match((1, 2, 3, 4)) is None
    assert pat.match(123) is None
    assert pat.match('abc') is None


def test_instance_pattern():
    # case MyClass(xx: int, y='hello'):
    vxx = AnnotatedPattern(VariablePattern('xx'), int)
    hello = LiteralPattern('hello')
    pat = InstancePattern(MyClass, [vxx], {'y': hello})
    match = pat.match(MyClass(42, "hello"))
    assert match == {'xx': 42}
