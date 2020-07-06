# Using match to simplify the implementation of overloaded functions.
#
# PEP 484 overloaded functions must be followed by a single implementation.
# Those implementations traditionally use `isinstance()` and other hacks.
# Using `match` we can make the implementation much cleaner.

from dataclasses import dataclass
from typing import overload


# First example: overload add() to support scalars and lists.

@overload
def add(a: int, b: int) -> int:
    pass
@overload
def add(a: list[int], b: list[int]) -> list[int]:
    pass
def add(a, b):
    match a, b:
        case list(), list():
            return [ai + bi for ai, bi in zip(a, b, strict=True)]
        case int(), int():
            return a + b
        case _:
            raise TypeError("incompatible arguments")

print(add(1, 2))
print(add([1, 2], [3, 4]))


# Second example: create a 3D point from various inputs.

@dataclass
class Point2d:
    x: int
    y: int

@dataclass
class Point3d:
    x: int
    y: int
    z: int

@overload
def point(p: Point2d) -> Point3d:
    pass
@overload
def point(p: Point3d) -> Point3d:
    pass
@overload
def point(x: int, y: int) -> Point3d:
    pass
@overload
def point(x: int, y: int, z: int) -> Point3d:
    pass
def point(*args):
    match args:
        case [Point2d(x, y)]:
            return Point3d(x, y, 0)
        case [p := Point3d()]:
            return p
        case [x := int(), y := int()]:
            return Point3d(x, y, 0)
        case [x := int(), y := int(), z := int()]:
            return Point3d(x, y, z)
        case _:
            raise TypeError("Huh?")

print(point(1, 2))
print(point(1, 2, 3))
print(point(Point2d(1, 2)))
print(point(Point3d(1, 2, 3)))
