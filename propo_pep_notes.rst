PEP: 9999
Title: Pattern matching
Version: $Revision$
Last-Modified: $Date$
Author: ..., ..., Ivan Levkivskyi <levkivskyi@gmail.com>
BDFL-Delegate:
Discussions-To: Python-Dev <python-dev@python.org>
Status: Draft
Type: Standards Track
Content-Type: text/x-rst
Created: 2020-05-04
Python version: 3.10
Resolution:

Abstract
========

This PEP proposes to add pattern matching statements [1]_ to Python. This will
allow more readable and reliable code when dealing with structured
heterogeneous data. The PEP takes a holistic approach and contains syntax
specification, runtime specification, and recommended specification for static
type checkers.

Previously PEP 275 and PEP 3103 that proposed similar constructs were
rejected. Here we choose a different approach and focus on generalizing
iterable and dictionary unpacking instead of syntax-sugaring and optimizing
``if ... elif ... else`` statement. Also, recently implemented PEP 617
that introduced a new PEG parser for Python now allows more flexible syntactic
options.


Rationale and Goals
===================

Let us start from some anecdotal evidence: ``isinstance()`` is one of the most
called functions in large scale Python code-bases (by static call count).
In particular, when analyzing some multi-million line production code base,
it was discovered that ``isinstance()`` is the second mast called builtin
function (after ``len()``). Even taking into account builtin classes, it is
still in the top ten. Most of such calls are followed by specific attribute
access.

There are two possible conclusions that can be made from this information:

* Handling of heterogeneous data (i.e. situations where a variable can take
  values of multiple types) is common in real world code.

* Python doesn't have expressive ways of destructuring data (i.e. separating
  the content of an object into multiple variables).

This is in contrast with the opposite sides of both aspects:

* Its success in the numeric world indicates that Python is good when
  working with homogeneous data. It also has builtin support for homogeneous
  data structures such as e.g. lists and arrays, and semantic constructs such
  as iterators and generators.

* Python is expressive and flexible at constructing object. It has syntactic
  support for collection literals and comprehensions. Custom objects can be
  created using positional and keyword calls that are customized by special
  ``__init__()`` method.

This PEP aims at improving the support for destructuring heterogeneous data
by adding a dedicated syntactic support for it in the form of pattern matching.
On very high level it is similar to regular expressions, but instead of
matching string, it will be possible to match arbitrary Python objects.

We believe this will improve both readability and reliability of relevant code.
To illustrate the readability improvement, let us consider an actual example
from the Python standard library::

  def is_tuple(node):
      if isinstance(node, Node) and node.children == [LParen(), RParen()]:
          return True
      return (isinstance(node, Node)
              and len(node.children) == 3
              and isinstance(node.children[0], Leaf)
              and isinstance(node.children[1], Node)
              and isinstance(node.children[2], Leaf)
              and node.children[0].value == "("
              and node.children[2].value == ")")

With the syntax proposed in this PEP it can be rewritten as below. Note that
the proposed code will work without any modifications to the definition of
``Node`` and other classes here::

  def is_tuple(node: Node) -> bool:
      match node:
      as Node(children=[LParen(), RParen()]):
      as Node(children=[Leaf(value="("), Node(...), Leaf(value=")")]):
          return True
      else:
          return False

See the `syntax`_ sections below for a more detailed specification. From
the reliability perspective, experience shows that missing a case when dealing
with a set of possible data values leads to hard to debug issues, thus forcing
people to add safety asserts like this::

  def get_first(data: Union[int, list[int]]) -> int:
      if isinstance(data, list) and data:
          return data[0]
      elif isinstance(data, int):
          return data
      else:
          assert False, "should never get here"

With the proposed pattern matching such exhaustiveness checks will be added
automatically.

Similarly to how constructing objects can be customized by a user-defined
``__init__()`` method, we propose that destructuring objects can be customized
by a new special ``__match__()`` method. As part of this PEP we specify the
builtin implementation for ``object.__match__()``, match behavior for builtin
collections such as ``tuple``, ``list``, and ``dict``, and for auto-generated
flexible ``__match__()`` method for PEP 557 dataclasses. See `runtime`_
section below.

Finally, we aim to provide a comprehensive support for static type checkers
and similar tools. For this purpose we propose to introduce a
``@typing.sealed`` class decorator that will be idempotent at runtime, but
will indicate to static tools that all subclasses of this class must be defined
in the same module. This will allow effective static exhaustiveness checks,
and together with dataclasses, will provide a nice support for algebraic data
types [2]_. See `static checkers`_ section for more details.

In general, we believe that pattern matching proved to be a useful and
expressive tool in various modern languages. In particular, many aspects of
this PEP were inspired by how pattern matching works in Rust [3]_ and
Scala [4]_.


.. _syntax:

Syntax and Semantics
====================

Match arms
----------

A simplified pseudo-grammar for the proposed syntax is::

    Match = "match" Expression ":" (("as" Pattern ":")+ Suite)+ ["else:" Suite]

We propose the match syntax to be a statement, not expression. Although in
many languages it is an expression, being a statement better suites the general
logic of Python syntax. See `rejected ideas`_ for more discussion. The list of
allowed patterns is specified below in the `patterns`_ subsection.

The ``match`` word is proposed to be a soft keyword, so that it is recognized
as a keyword at the beginning of match statement, but is allowed to be used in
other positions as a variable or argument name.

Note that there can be more than one match arm per match suite. The proposed
indentation structure is as following::

    match some_expression:
    as pattern_1a:
    as pattern_1b:
        ...
    as pattern_2:
        ...
    else:
        ...

Such layout saves an indentation level and matches a common indentation scheme
for ``switch`` statement in C language. Although this may be tricky for some
simple-minded editors, it should be not hard to support in principle, one just
needs to not add indentation level after a colon if the previous line starts
with ``match``.


Match semantics
---------------

The proposed large scale semantics for choosing the match is to choose first
matching pattern and execute the corresponding suite. The remaining patterns
are not tried. If there are no matching pattens, the ``else`` clause is
executed. If the latter is absent, an instance of ``UnmatchedValue`` (proposed
to be a subclass of ``ValueError``) is raised.

Essentially this is equivalent to a chain of ``if ... elif ... else`` except
the default ``else`` clause is to raise an exception. Note that unlike for
``switch`` statement, the pre-computed dispatch dictionary semantics does not
apply here.

Name bindings made during successful pattern match outlive the executed suite
and can be used after the match statement. This follows the logic of other
Python statements that can bind names, such as ``for`` loop and ``with``
statement. For example::

  match shape:
  as Point(x, y):
      ...
  as Rectangle(x, y, _x, _y):
      ...
  print(x, y)  # This works


.. _patterns:

Allowed patterns
----------------

We introduce the proposed syntax gradually. Here we start from the main
building blocks. The following patterns are supported:

* **Literal pattern**, i.e. a simple literal like a string, a number, boolean,
  or ``None``::

    match number:
    as 1:
        print("Just one")
    as 2:
        print("A couple")
    else:
        print("Many")

  Literal pattern uses equality with literal on the right hand side, so that
  in the above example ``number == 1`` and then possibly ``number == 2`` will
  be evaluated.

* **Name pattern**, that serves as an assignment target for the matched
  expression::

    match greeting:
    as None:
        print("Hello!")
    as name:
        print(f"Hi {name}!")

  Note that name pattern always succeeds. No special meaning is attached to
  names that start with underscores. A name pattern appearing in a scope
  makes the name local to that scope. For example, using ``name`` after
  the above snippet may raise ``UnboundLocalError`` rather than ``NameError``,
  if the ``None`` match arm was taken.

* **Display pattern** is a generalization of iterable unpacking and supports
  builtin collections: tuples, lists, and dictionaries. Each element
  can be an arbitrary pattern plus there may be at most one ``*name`` or
  ``**name`` pattern to catch all remaining items::

    match collection:
    as (1, x, *other):
        print("Got tuple")
    as [1, [x, *other]]:
        print("Got nested list")
    as {1: x, **other}:
        print("Got dictionary")
    else:
        print("Probably a set")

  For dictionaries the order of items is ignored, so e.g. the result of
  matching ``{1: 2, 3: 4}`` against ``{k1: v1, k2: v2}`` is unpredictable, but
  the latter will only match a dictionary with two items. Only name pattern
  and literal pattern are allowed in the key position, and the ``**other`` item
  must always be last, see details in the `runtime`_ section.

* **Unstructured class pattern** is a synonym for an ``isinstance()`` check, it is
  mostly useful in nested positions, when the content of the object is not
  important and it serves just as a marker. For example::

    match shapes:
    as [Point(...), second, third, *other]:
        print(f"The first one is some point, then {second} and {third}")

* **Structured class pattern** supports two possible ways of matching: by position
  like ``Point(x, y)``, and by name like ``User(id=id, name=name)``. These two
  can be combined, but positional match cannot follow a match by name. Each
  item in a class match can be an arbitrary pattern, plus at most one ``*name``
  or ``**name`` pattern can be present (the former may be not last). Semantics
  of the class pattern is an ``isinstance()`` call plus a ``__match__()`` call
  on the class if the former returns ``True``. For example::

    match shape:
    as Point(x, y):
        ...
    as Rectangle(*coordinates, painted=True):
        ...

  This PEP only fully specifies the behavior of ``__match__()`` for ``object``
  and dataclasses, custom classes are only required to follow the protocol
  specified in `runtime`_ section. After all, the authors of a class know best
  how to "revert" the logic of the ``__init__()`` they wrote. The runtime will
  then chain these calls to allow matching against arbitrarily nested
  patterns.


Guards
------

Each *top-level* pattern can be followed by a guard of the form
``if expression``. A match arm succeeds if the pattern matches and
the guard evaluates to true value. For example::

  match shape:
  as Point(x, y, color) if color == BLACK:
      print("Black point")
  else:
      print("Something else")

Note that having guards is important since names always have store semantics,
i.e. serve as assignment targets. Static languages can easily special case
constants and enums to be used similar to literals, but this is not possible
in Python. An early version of this PEP proposed to support constant patterns
via special syntax or complicated implicit rules, see `rejected ideas`_.

Note that guards are also useful in a much wider range of scenarios, for
example::

  match input:
  as (x, y) if x > MAX_INT and y > MAX_INT:
      print("Got a pair of large numbers")
  as x if x > MAX_INT:
      print("Got a large number")
  else:
      print("Not an outstanding input")

If evaluating a guard raises an exception, it is propagated onwards rather
than fail the match arm. Although name patterns always succeed, all names that
appear in a pattern are bound after the guard succeeds. So this will raise
a ``NameError``::

  values = [0]

  match value:
  as [x] if x:
      ...
  else:
      ...
  x  # NameError here


Coinciding names
----------------

If patterns in match arm contain name patterns with coinciding names, then
all the matched objects must compare equal for the match arm to succeed::

  match sorted(deck):
  as [x, x, y, y, y]:
  as [x, x, x, y, y]:
      print("Got a full house")

When matching against such patterns, all matched values are compared by
a chained (not pairwise) equality for every group, and the lexicographically
left-most value in each group is bound to the name. For example this match::

   match nested:
   as [x, [x, [x, y, y]]]:
       ...

is essentially equivalent to the following expansion with intermediate names
and a guard::

  match nested:
  as [_1, [_2, [_3, _4, _5]]] if _1 == _2 == _3 and _4 == _5:
      x = _1
      y = _4
      ...

Note that this case diverges from the semantics of iterable unpacking, because
the latter simply sequentially assigns values to the same variable, but we
believe that checking for the values to be same it is what people would
typically expect.


Named sub-patterns
------------------

It is often useful to match a sub-pattern *and* to bind the corresponding
value to a name. For example, it can be useful to ensure some sub-patterns
are equal, to write more efficient matches, or simply to avoid repetition.
To simplify such cases, a name pattern can be combined with arbitrary other
pattern using named sub-patterns of the form ``name := pattern``.
For example::

  match get_shape():
  as Line(point := Point(x, y), point):
      print(f"Zero length line at {x}, {y}")

Note that the name pattern used in the named sub-pattern can be used in
the match suite, or after the match statement. Another example::

  match group_shapes():
  as [], [point := Point(x, y), *other]:
      print(f"Got {point} in the second group")
      ...

Technically, most such examples can be rewritten using guards and/or nested
match statements, but this will be less readable and/or will produce less
efficient code. Essentially, most of the arguments in PEP 572 apply here
equally.


One-off matches
---------------

While inspecting some code-bases that may benefit the most from the proposed
syntax, it was found that single arm matches would be used relatively often,
mostly for various special-casing. In other languages this is supported in
the form of one-off matches. We propose to support such one-off matches too::

  if match value as pattern [and guard]:
      ...

as equivalent to the following expansion::

  match value:
  as pattern [if guard]:
      ...
  else:
      pass  # Note: not raising UnmatchedValue exception here

There will be no ``elif match`` statements allowed. One-off match is special
case of ``match`` statement, not a special case of an ``if`` statement.
Similarly, ``if not match`` is not allowed, since ``match ... as ...`` is not
an expression.

To illustrate how this will benefit readability, consider this (slightly
simplified) snippet from real code::

  if isinstance(node, CallExpr):
      if (isinstance(node.callee, NameExpr) and len(node.args) == 1 and
              isinstance(node.args[0], NameExpr)):
          call = node.callee.name
          arg = node.args[0].name
          ...  # Continue special-casing 'call' and 'arg'
  ...  # Follow with common code

This can be rewritten in a more straightforward way as::

  if match node as CallExpr(callee=NameExpr(name=call), args=[NameExpr(name=arg)]):
      ...  # Continue special-casing 'call' and 'arg'
  ...  # Follow with common code


.. _runtime:

Runtime specification
=====================

The ``__match__()`` protocol
----------------------------

Here we specify how structured class patterns work using the ``__match__()``
special method. This method is implicitly a class method, and has the following
signature::

  PosData = tuple[object, ...]
  NamedData = dict[str, object]
  MathData = tuple[PosData, NamedData, Optional[PosData], Optional[NamedData]]

  def __match__(
      cls,
      value: object,
      pos: PosData,
      named: NamedData,
      star_position: int = -1,
      star_named_present: bool = False,
  ) -> Union[NotImplemented, MatchData]:
      ...

When an interpreter tries to match a value again a structured class pattern,
it first calls ``isinstance(value, Class)``. If the call returns ``True``, it
then makes the following call::

  Class.__match__(
      value,
      pos_vales,
      named_values,
      star_position,
      star_named_present,
  )

In ``pos_values`` every sub-pattern is represented by an ``Ellipsis`` object,
while literals are included as is. We pass literals instead of later comparing
the matched value to allow user classes to implement efficient matches by
failing soon. The same logic applies to ``named_values`` where the dictionary
keys are strings used as names in for the named match. Last two arguments
indicate whether ``*`` or ``**`` patterns are present. For example, this
match arm will trigger the following call::

  match shape:
  as Point3D(0, y, z, painted=True, visible=visible, **flags):
      ...

  Point3D.__match__(
      shape,
      (0, ..., ...),
      {"painted": True, "visible": ...},
      -1,
      True,
  )

The method is then expected to either return ``NotImplemented`` which means
the match failed or return a value for every ellipsis placeholder. The
initial literal values passed in should not be included in the return, only
the missing values. If star patterns were present it is expected to return
corresponding values packed as a tuple and/or a dictionary, and to return
``None`` otherwise.

Thus in the example above a valid return would look like this::

  (1, 2), {"visible": False}, None, {"fast_render": False}

Any violation in the expected return object will trigger ``RuntimeError``, in
particular:

* Returned length mismatches the expected one.
* Returned values contain ``Ellipsis`` among them.
* Unexpected star data where none expected or vice versa.

If all the matched patterns were name patterns, then interpreter performs
the corresponding assignments, otherwise it tries to match the returned values
against sub-patterns. For example the following code will trigger the following
(simplified) sequence of calls::

  match shape:
  as Line(Point(x1, 1), Point(x2, 2)):
      ...

  isinstance(shape, Line)
  (_1, _2), *_ = Line.__match__(shape, (..., ...), {})
  isinstance(_1, Point)
  (x1,), *_ = Point.__match__(_1, (..., 1), {})
  isinstance(_2, Point)
  (x2,), *_ = Point.__match__(_2, (..., 2), {})

The order between stepping into sub-patterns, checking guards, and checking
any coinciding names is unspecified. The interpreter is free to choose
the fast path and skip nested matches if it can already infer the match fails.

Note that we always pass a plain ellipsis for every pattern except literal,
one could imagine faster and/or more flexible ``__match__()`` implementations
with more context, but there are various downsides to this, see
`rejected ideas`_.


Impossible matches
-------------------

Implementers of custom classes that implement a ``__match__()`` method are
encouraged to "revert" the logic in the ``__init__()`` method rather than
use the internal representation of the object state to fill the structured
class pattern. This way, the match statements with such classes will have
a uniform look with instantiation calls. For example, if there is a class::

  class Point3D:
      def __init__(self, coordinates: List[int]) -> None:
          self.x, self.y, self.z = coordinates

then the corresponding match method should expect a single list, rather than
three integers::

  match shape:
  as Point3D([0, y, z]):  # Recommended
      ...
  as Point3D(coordinates=[0, y, z]):  # Recommended
      ...
  as Point3D(0, y, z):  # Not recommended
      ...
  as Point3D(x=0, y=y, z=z):  # Not recommended
      ...

The implementers of custom classes are *strongly* encouraged to raise
a special builtin exception ``ImpossibleMatchError`` (proposed to be
a subclass of ``TypeError``) instead of returning ``NotImplemented`` if
the expected match is impossible in principle. This way subtle bugs will be
caught sooner. For example, with the above class definition::

  match shape:
  as Point3D(x, y):  # Strongly recommended to raise here
      ...

Although these recommendations are in no way enforced by Python runtime,
builtins and standard library classes will follow these recommendations.


Default ``object.__match__()``
------------------------------

The default implementation is aimed at providing basic useful (but still safe)
experience with pattern matching out of the box. For this purpose the match
method follows this logic:

* ``isinstance()`` will be automatically ensured by runtime, so no need to
  do this.

* Only either positional or named patterns may be present, mixing them will
  cause ``ImpossibleMatchError``.

* For positional match, if the class defines ``__slots__``, try unpacking
  them, if there is no star item and there is a length mismatch, raise
  ``ImpossibleMatchError``. If some literals provided and don't match actual
  values, then return ``NotImplemented``.

* For positional match if class has a ``__dict__``, try using ``__iter__()``
  and ``__getitem__()`` to perform iterable unpacking (while comparing to any
  expected literals). If the class doesn't have these methods, raise
  ``ImpossibleMatchError``.

* For named match use ``getattr()`` for every name provided. To accommodate
  typical use cases, match succeeds even if only some attributes were
  requested and there is no star item. If the instance doesn't have a given
  attribute, transform ``AttributeError`` into ``ImpossibleMatchError``.

* As an exception to the above, empty match succeeds only if instance
  dictionary is empty and there are no slots or empty slots.

* If a class defines ``__getstate__()`` use it as an override to perform the
  match by name.


Builtin classes
---------------

Builtin collections will be special-cased instead of using ``__match__()`` to
use efficient code and avoid excessive method calls. Every match will use
(recursive) iteration or indexing over the corresponding collection.
Effectively, pattern matching for lists and tuples will be not different from
iterable unpacking plus matching all sub-patterns.

Dictionaries are treated specially depending on whether a given key in
the display pattern is a literal or a name (other are not allowed). If it is
a literal (not necessary a string), then the corresponding key will be taken
from object using ``__getitem__()``, if the latter raises ``KeyError``, then
the match fails. If the key is not a literal, an arbitrary item is pulled from
the dictionary iterator. If there is a length mismatch and no star item,
the dictionary match always fails.

As an additional safety restriction, if key pattern is a name, the value
pattern must also be a name. To illustrate the rules, consider an example::

  config = {"name": "default", "ttl": 3600}

  match config:
  as {"foo": x}:  # Doesn't match
      ...
  as {"name": x}:  # Doesn't match
      ...
  as {"name": x, y: z} if y in ("ttl", "time"):  # Matches
      ...
  as {"name": x, **rest}:  # Matches
      ...
  as {"name": x, y1: z1, y2: z2}:  # Doesn't match
      ...
  as {x: 3600, y: "default"}:  # Invalid pattern
      ...

Note that sets and frozen sets are not supported because supporting them will
be either ambiguous or tricky, see `rejected ideas`_.

Specification for standard library classes are not included in this PEP.
Support for them can be added incrementally when necessary (i.e. if the
default ``object.__match__()`` implementation doesn't provide reasonable
support). Possible first candidate for a better ``__match__()`` method are
named tuples.

An attempt to use builtin classes in structured class patterns will cause
a ``TypeError`` with a suggestion to use a corresponding collection display.
For example, one must use ``(x, y, z)`` instead of ``tuple(x, y, z)`` or
``tuple([x, y, z])``, and ``{"foo": x, "bar": y}`` instead of
``dict(foo=x, bar=y)`` or ``dict([("foo", x), ("bar", y)])``.


Dataclasses
-----------

Dataclasses are special with respect to this PEP because they have a flexible
auto-generated ``__init__()`` method. Therefore, we can generate a
corresponding flexible ``__match__()`` method. It will provide the following
improvements over the default ``object.__match__()``:

* Positional match can be used even if ``__iter__()`` and ``__getitem__()``
  are not defined in the class. We just pull the fields in the order they
  are defined in the class (and superclasses) to match ``__init__()``.

* Positional and named matches can be combined. However, a positional and
  a named match must not target the same dataclass field. This will trigger
  ``ImpossibleMatchError``.

* All fields that don't have a default value or a default factory (see [5]_),
  must be matched, so all of ``Point3D(x, y)``, ``Point3D(x=x, y=y)``, and
  ``Point3D(x, y=y)`` will raise ``ImpossibleMatchError``.

* To get a (less safe) partial match by name mimicking that in
  ``object.__match__()``  one can still use star items, e.g.
  ``Point3D(0, *other)``, and ``Point3D(x=0, **other)`` work.

* Fields with ``init=False`` (see [5]_) cannot be matched by position, but can
  still be matched by name. This deviates from the general logic that pattern
  should resemble instantiation call, but this is were practicality beats
  purity.


.. _static checkers:

Static checkers specification
=============================

Exhaustiveness checks
---------------------

PEP 484 specifies that static type checkers should support exhaustiveness in
conditional checks with respect to enum values. PEP 586 later generalized this
requirement to literal types. This PEP further generalizes this requirement to
arbitrary patterns. A typical situation where this applies is matching an
expression with a union type::

  def classify(val: Union[int, Tuple[int, int], List[int]]) -> str:
      match val:
      as [x, *other]:
          return f"A list starting with {x}"
      as (x, y) if x > 0 and y > 0:
          return f"A pair of {x} and {y}"
      as int(...):
          return f"Some integer"
      # Type-checking error: some cases unhandled.

The exhaustiveness checks should also apply where both pattern matching
and enum values are combined::

  from enum import Enum
  from typing import Union

  class Level(Enum):
      BASIC = 1
      ADVANCED = 2
      PRO = 3

  class User:
      name: str
      level: Level

  class Admin:
      name: str

  account: Union[User, Admin]

  match account:
  as Admin(name=name):
  as User(name=name, level=level) if level == Level.PRO
      ...
  as User(level=level) if level == Level.ADVANCED:
      ...
  # Type-checking error: basic user unhandled

Obviously, no ``Matchable`` protocol (in terms of PEP 544) is needed, since
every class is matchable and therefore is subject to the checks specified
above.


Sealed classes as ADTs
----------------------

Quite often it is desirable to apply exhaustiveness to a set of classes without
defining ad-hoc union types, which is itself fragile if a class is missing in
the union definition. A design pattern where a group of record-like classes is
combined into a union is popular in other languages that support pattern
matching and is known under a name of algebraic data types [2]_ or ADTs.

We propose to add a special decorator class ``@sealed`` to the ``typing``
module [6]_, that will have no effect at runtime, but will indicate to static
type checkers that all subclasses (direct and indirect) of this class should
be defined in the same module as the base class.

The idea is that since all subclasses are known, the type checker can treat
the sealed base class as a union of all its subclasses. Together with
dataclasses this allows a clean and safe support of ADTs in Python. Consider
this example::

  from dataclasses import dataclass
  from typing import sealed

  @sealed
  class Node:
      ...

  class Expression(Node):
      ...

  class Statement(Node):
      ...

  @dataclass
  class Name(Expression):
      name: str

  @dataclass
  class Operation(Expression):
      left: Expression
      op: str
      right: Expression

  @dataclass
  class Assignment(Statement):
      target: str
      value: Expression

  @dataclasses
  class Print(Statement):
      value: Expression

With such definition, a type checker can safely treat ``Node`` as
``Union[Name, Operation, Assignment, Print]``, and also safely treat e.g.
``Expression`` as ``Union[Name, Operation]``. So this will result in a type
checking error in the below snippet, because ``Name`` is not handled (and type
checker can give a useful error message)::

  def dump(node: Node) -> str:
      match node:
      as Assignment(target, value):
          return f"{target} = {dump(value)}"
      as Print(value):
          return f"print({dump(value)})"
      as Operation(left, op, right):
          return f"({dump(left)} {op} {dump(right)})"


Type erasure
------------

The unstructured class patterns are subject to runtime type erasure. Namely,
although one can define a type alias``IntQueue = Queue[int]`` so that
a pattern like ``IntQueue(...)`` is syntactically valid, type checkers should
rejected such unstructured match::

  queue: Union[Queue[int], Queue[str]]
  match queue as IntQueue(...):  # Type-checking error here.
      ...

Note that the above snippet actually fails at runtime with the current
implementation of generic classes in ``typing`` module, and builtin generic
classes in recently accepted and PEP 585.

To clarify, generic classes are not prohibited in general from participating
in pattern matching, just that their type parameters can't be explicitly
specified. It is still fine if sub-patterns or literals bind the type
variables. For example::

  from typing import Generic, TypeVar, Union

  T = TypeVar('T')

  class Result(Generic[T]):
      first: T
      other: list[T]

  result: Union[Result[int], Result[str]]

  match result:
  as Result(first=int(...)):
      ...  # Type of result is Result[int] here
  as Result(other=["foo", "bar", *rest]):
      ...  # Type of result is Result[str] here


Note about constants
--------------------

The fact that name pattern is always an assignment target may create unwanted
consequences when a user by mistake tries to "match" a value against
a constant. As a result, at runtime such match will always succeed and
moreover override the value of the constant. It is important therefore that
static type checkers warn about such situations. For example::

  from typing import Final

  MAX_INT: Final = 2 ** 64

  value = 0

  match value:
  as MAX_INT:  # Type-checking error here: cannot assign to final name
      print("Got big number")
  as _:
      print("Something else")


Precise type checking of star matches
-------------------------------------

Type checkers should perform precise type checking of star items in pattern
matching giving them either a heterogeneous `tuple[X, Y, Z]` type, or
a ``TypedDict`` type as specified by PEP 589. For example::

  from dataclasses import dataclass

  class Expession:
      ...

  class Statement:
      ...

  @dataclass
  class AssignmentExpression(Expression):
      target: str
      value: Expression
      line: int = -1
      column: int = -1

  @dataclass
  class AssignmentStatement(Statement):
      target: str
      value: Expression
      line: int = -1
      column: int = -1

  def transform(expr: Expression) -> Statement:
      match expr:
      as AssignmentExpression(target, value, **position):
          # Here position is TypedDict({"line": int, "column": int})
          # so the below call is safe
          return AssignmentStatement(f"{target}_tr", value, **position)
      as AssignmentExpression(target, *rest):
          # Here rest is tuple[Expression, int, int]
          # so the below call is a type-checking error
          return AssignmentStatement(*rest)


Backwards Compatibility
=======================

This PEP is fully backwards compatible.


Reference Implementation
========================

None yet. If there will be a general positive attitude towards the PEP, we
will start working on implementation soon to iron out possible corner cases
before acceptance.


.. _rejected ideas:

Rejected Ideas
==============

This general idea was floating around for pretty long time, and many
back and forth decisions were made. Here we summarize many alternative
paths that were taken, but abandoned after all.

Don't do this, patter matching is hard to learn
-----------------------------------------------

In our opinion, the proposed pattern matching is not more difficult than
adding ``isinstance()`` and ``getattr()`` to iterable unpacking. Also, we
believe the proposed syntax significantly improves readability for a wide
range of code patterns, by allowing to express *what* one wants to do, rather
than *how* to do it. We hope few real code snippets we included in the PEP
above illustrate this comparison well enough.

Here are some other snippets from CPython repository that may potentially
benefit from pattern matching::

  # Doc/tools/extensions/pyspecific.py
  if node.children and isinstance(node[0], nodes.paragraph) and node[0].rawsource:
      ...

  # Lib/_pydecimal.py
  if equality_op and isinstance(other, _numbers.Complex) and other.imag == 0:
      ...

  # Lib/logging/__init__.py
  if (args and len(args) == 1 and isinstance(args[0], collections.abc.Mapping)
      and args[0]):
      args = args[0]

  # Tools/clinic/clinic.py
  if isinstance(expr, ast.Name) and expr.id == 'NULL':
      ...
  elif (isinstance(expr, ast.BinOp) or
      (isinstance(expr, ast.UnaryOp) and
       not (isinstance(expr.operand, ast.Num) or
            (hasattr(ast, 'Constant') and
             isinstance(expr.operand, ast.Constant) and
             type(expr.operand.value) in (int, float, complex)))
      )):
      ...
  elif isinstance(expr, ast.Attribute):
      ...
  else:
      ...

  # Tools/parser/unparse.py
  if isinstance(t.value, ast.Constant) and isinstance(t.value.value, int):
      ...

Notably, there is a tendency that such code patterns most often appear in
various parsing/compiling contexts. We don't think however that this
application-domain tendency should stop us.


Split dataclasses and typing parts into separate PEPs
-----------------------------------------------------

There was an option to make three separate PEPs: one for the syntax, one for
the dataclasses improvements, and one for static typing. We propose to have
one larger PEP instead of three separate, because this is a major change to
Python and such changes should apply coherently to various aspects of
the language.

In particular, the specification for default ``object.__match__()`` and
generated match for dataclasses affect the decision on support for structured
class patterns. And the support for sealed classes in ``typing`` module depends
on good support for pattern matching of dataclasses.


Allow a more flexible assignment targets instead
------------------------------------------------

There was an idea to instead just generalize the iterable unpacking to much
more general assignment targets, instead of adding a new kind of statement.
This concept is known in some other languages as "irrefutable matches". We
decided not to do this because inspection of real-life potential use cases
showed that in vast majority of cases destructuring is related to an ``if``
condition. Also many of those are grouped in a series of exclusive choices.

Note however that single ``if`` condition still appears relatively often, this
is why we propose to allow one-off matches.


Make it an expression
---------------------

In most other languages pattern matching is represented by an expression, not
statement. But making it an expression would be inconsistent with other
syntactic choices in Python. All decision making logic is expressed almost
exclusively in statements, so we decided to not deviate from this.


Use a hard keyword
------------------

There were options to make ``match`` a hard keyword, or choose a different
keyword. Although using a hard keyword would simplify life for simple-minded
syntax highlighters, we decided not to use hard keyword for several reasons:

* Most importantly, the new parser doesn't require us to do this. Unlike with
  ``async`` that caused hardships with being a soft keyword for few releases,
  here we can make ``match`` a permanent soft keyword.

* ``match`` is so commonly used in existing code, that it would break almost
  every existing program and will put a burned to fix code on many people who
  may not even benefit from the new syntax.

* It is hard to find an alternative keyword that would not be commonly used
  in existing programs as an identifier, and would still clearly reflect the
  meaning of the statement.


Use ``case`` instead of ``as`` for match arms
---------------------------------------------

There are three arguments in favour of using ``as`` as a keyword to start each
match arm:

* It is a bit shorter so will save some keystrokes and horizontal space, which
  may be important since this keyword will be repeated many times.

* Use of ``case`` is often associated with ``switch``, while using ``as`` is
  closer to plain English formulation of the concept.

* It is already a hard keyword, so we would need only one soft keyword instead
  of two.


Use a nested indentation scheme
-------------------------------

There was an idea to use an alternative indentation scheme, for example where
every match arm would be indented with respect to the initial ``match`` part::

  match expression:
      as patter_1:
          ...
      as pattern_2:
          ...
      else:
          ...

This idea was rejected because having nested match statements would waste too
much horizontal space. There are few more possible indentation schemes
summarized in PEP 3103, and the scheme proposed in this PEP seems the most
optimal.


Use ``|`` and ``!`` to combine patterns
---------------------------------------

It may be convenient to have alternative matches and negative matches (similar
to string regular expressions). For example one could write::

  match expr:
  as BinaryOp(left=!IntExpr(value=0)):
      ...
  as UnaryOp(operand=IntExpr(value=0) | NameExpr(name="False")):
      ...

Although some real code shows this can indeed be useful, we decided not to
include these in the present PEP for several reasons:

* This will significantly complicate the specification and implementation. In
  particular interaction with name patterns may be non-trivial.

* Top-level alternative matches would be often split over multiple lines
  anyway. So this would look essentially not different from having multiple
  arms.

* Nested alternative matches and negative matches will be likely not needed
  often, and may be added in future if requested by users.

* This can be sometimes expressed using guards and/or nested match statements.


Support constant pattern
------------------------

This is probably the trickiest item. Matching against some pre-defined
constants is very common, but also dynamic nature of Python makes it ambiguous
with name patterns. Four other alternatives were considered:

* Use some implicit rules. For example if a name was defined in the global
  scope, then it refers to a constant, rather than represents a name pattern::

    FOO = 1
    value = 0

    match value:
    as FOO:  # This would not be matched
        ...
    as BAR:
        ...  # This would be matched

  This however can cause surprises and action at a distance if someone
  defines an unrelated coinciding name before the match statement.

* Use extra parentheses to indicate lookup semantics for a given name. For
  example::

    FOO = 1
    value = 0

    match value:
    as (FOO):  # This would not be matched
        ...
    as BAR:
        ...  # This would be matched

  This may be a viable option, but it can create some visual noise if used
  often. Also honestly it looks pretty unusual, especially in nested contexts.

* Introduce a special symbol, for example ``$`` to indicate that given name is
  a constant to be matched against, not to be assigned to::

    FOO = 1
    value = 0

    match value:
    as $FOO:  # This would not be matched
        ...
    as BAR:
        ...  # This would be matched

  The problem with this approach is that introducing a new syntax for such
  narrow use-case is probably an overkill.

* There was also on idea to make lookup semantics the default, and require
  ``$`` to be used in name patterns::

    FOO = 1
    value = 0

    match value:
    as FOO:  # This would not be matched
        ...
    as $BAR:
        ...  # This would be matched

  But the name patterns are more common in typical code, so having special
  syntax for common case would be weird.

After all, these alternatives were rejected because of mentioned drawbacks.
Note that many use cases for constant matches can be remedied with guards. For
example::

  FOO = 1
  value = 0

  match value:
  as some if some == FOO:  # This would not be matched
      ...
  as BAR:
      ...  # This would be matched

Finally, possible performance implications for using guards instead of
constant patterns can be remedied by a compiler optimization that will detect
trivial equality guards and transforming them into looked up values.


Use dispatch dict semantics for matches
---------------------------------------

Implementations for classic ``switch`` statement sometimes use a pre-computed
hash table instead of a chained equality comparisons to gain some performance.
In the context of ``match`` statement this is technically also possible for
matches against literal patterns. However, having subtly different semantics
for different kinds of patterns would be too surprising for potentially
modest performance win.

We can still experiment with possible performance optimizations in this
direction if they will not cause semantic differences.


Allow fall through without a match
----------------------------------

There was an alternative to allow falling through all match arms without
a match. It was decided not to allow this, and by default raise an
``UnmatchedValue`` exception. There are few reasons:

* This can cause subtle bugs. In view of this it is preferable that the safer
  option is the default one.

* It is always easy to add an ``else`` match arm.

* For ad-hoc special casing where adding a dummy ``else`` clause would be
  tedious, one cause one-off matches.


Allow ``elif match`` and other one-offs
---------------------------------------

There was an idea to allow multi-branch one-off matches of the following
form::

  if match value_1 as patter_1 [and guard_1]:
      ...
  elif match value_2 as pattern_2 [and guard_2]:
      ...
  elif match value_3 as pattern_3 [and guard_3]:
      ...
  else:
      ...

It was decided not to this. Mainly because these defeats the purpose of
one-off matches as a complement to exhaustive full matches. Similarly, we
don't propose ``while match`` construct present in some languages with pattern
matching, since although it may be handy, it will likely be used rarely.
Finally, ``while match`` is easy to add later.


Send full patterns to the ``__match__()`` method
------------------------------------------------

The current specification for ``__match__()`` protocol prescribes that we
always send just a plain ``...`` as placeholder for a pattern. There was
an idea to send custom pattern objects that will provide the full context.
For example the below match would generate the following call::

  match expr:
  as BinaryOp(left=Number(value=x), op=op, right=Number(value=y)):
      ...

  from types import PatternObject

  BinaryOp.__match__(
      (),
      {
          "left": PatternObject(Number, (), {"value": ...}, -1, False),
          "op": ...,
          "right": PatternObject(Number, (), {"value": ...}, -1, False),
      },
      -1,
      False,
  )

This would allow faster ``__match__()`` implementations and will give better
support for customization in user-defined classes. There is however a big
downside to this: it will make basic implementation of this method quite
tedious. Also, there will be actual performance penalty if user does not treat
pattern object properly.


Support matches for ``set`` and ``frozenset``
---------------------------------------------

There was an idea to add support for set literal patterns, and ``frozenset``
patterns (mostly for completeness). We don't do this because there are two
complications that arise:

* First of all, sets are unordered, so it is hard do define any useful
  deterministic semantics.

* Second, supporting ``frozenset`` is even more ambiguous and will be used
  very rarely. Namely, in addition to the general ordering issue, there are
  three possible forms to support it: ``frozenset([x, y, z])`` vs
  ``frozenset({x, y, z})`` vs ``frozenset(x, y, z)``.

We can reconsider this later if people will actually ask about supporting
set patterns.


References
==========

.. [1]
   https://en.wikipedia.org/wiki/Pattern_matching

.. [2]
   https://en.wikipedia.org/wiki/Algebraic_data_type

.. [3]
   https://doc.rust-lang.org/reference/patterns.html

.. [4]
   https://docs.scala-lang.org/tour/pattern-matching.html

.. [5]
   https://docs.python.org/3/library/dataclasses.html

.. [6]
   https://docs.python.org/3/library/typing.html


Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.



..
   Local Variables:
   mode: indented-text
   indent-tabs-mode: nil
   sentence-end-double-space: t
   fill-column: 70
   coding: utf-8
   End:

