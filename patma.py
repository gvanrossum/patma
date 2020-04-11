import collections.abc as cabc
import dataclasses
from typing import Dict, List, Optional, Type, Mapping

__all__ = [
    "Pattern",
    "AlternativesPattern",
    "ConstantPattern",
    "VariablePattern",
    "AnnotatedPattern",
    "SequencePattern",
    "InstancePattern",
    "WalrusPattern",
]


class Pattern:
    """A pattern to be matched.

    Various subclasses exist for different pattern matching concepts
    (e.g. sequence unpack, object unpack, value extraction).

    The translation of a match statement produces one Pattern per case.

    For example, this input::

        match x:
            case pattern1 if guard1:
                block1
            case pattern2 if guard2:
                block2
            ...

    translates roughly into this::

        if pattern1.match(x) is not None and guard1:
            block1
        elif pattern2.match(x) is not None and guard2:
            block2
        ...

    However for value extractions there are variable bindings to be
    created.  We leave those up to the compiler; the
    ``Pattern.match()`` method just returns a dict mapping variable
    names to values.

    For example, for this input::

        match x:
            case [a, b] if a == b:
                block

    where ``x`` has the value ``(4, 2)``, the ``pattern.match(x)``
    call returns ``{'a': 4, 'b': 2}``.  If a pattern extracts no
    values it returns ``{}``.

    Note that, while any ``Pattern`` can be nested inside any other
    ``Pattern`` (provided it can contain nested patterns at all), the
    syntax may restrict nesting.  For example, a type annotation
    pattern (e.g. ``a: int``) uses a ``Pattern`` to represent the
    variable, but the syntax constrains what appears to the left of
    the colon and where the ``a: int`` pattern can occur.
    """

    def match(self, x: object) -> Optional[Dict[str, object]]:
        return None


def _is_instance(x: object, t: type) -> bool:
    return isinstance(x, t) or (t is float and isinstance(x, int))


class ConstantPattern(Pattern):
    """A pattern that matches a given value.

    The matched value's type must be a subtype of the constant's type.
    """

    def __init__(self, constant: object):
        self.constant = constant

    def match(self, x: object) -> Optional[Dict[str, object]]:
        if _is_instance(x, type(self.constant)) and x == self.constant:
            return {}
        return None


class AlternativesPattern(Pattern):
    """A pattern consisting of several alternatives.

    This is a sequence of patterns separated by bars (``|``).
    """

    def __init__(self, patterns: List[Pattern]):
        self.patterns = patterns

    def match(self, x: object) -> Optional[Dict[str, object]]:
        for p in self.patterns:
            match = p.match(x)
            if match is not None:
                return match
        return None


class VariablePattern(Pattern):
    """A value extraction pattern.

    This is an 'irrefutable' pattern (meaning that it always matches)
    that produces a new name binding.
    """

    def __init__(self, name: str):
        self.name = name

    def match(self, x: object) -> Dict[str, object]:
        return {self.name: x}


class AnnotatedPattern(Pattern):
    """A pattern involving a type annotation.

    For example, ``(x: int)``.

    TODO: This requires instantiating the Pattern object
          each time a match statement is executed.
          We should instead somehow pass the name lookup
          context to the match() call.
    """

    def __init__(self, pattern: Pattern, cls: Type):
        self.pattern = pattern
        self.cls = cls

    def match(self, x: object) -> Optional[Dict[str, object]]:
        if _is_instance(x, self.cls):
            return self.pattern.match(x)
        return None


class SequencePattern(Pattern):
    """A pattern for a (fixed) sequence of subpatterns.

    This is similar to list or tuple unpacking, but it doesn't match
    strings (neither str nor bytes, but it does match bytestring and
    memoryview).
    """

    def __init__(self, patterns: List[Pattern]):
        self.patterns = patterns

    def match(self, x: object) -> Optional[Dict[str, object]]:
        if (
            isinstance(x, cabc.Sequence)
            and not isinstance(x, (str, bytes))
            and len(x) == len(self.patterns)
        ):
            matches = {}
            for pattern, item in zip(self.patterns, x):
                match = pattern.match(item)
                if match is None:
                    return None
                matches.update(match)
            return matches
        return None


class InstancePattern(Pattern):
    """A pattern that matches a class instance.

    For example, ``MyClass(x, flag=y)``.  This extracts variables
    ``x`` and ``y``.

    TODO: Same problem for the class name as AnnotatedPattern.
    """

    def __init__(
        self, cls: Type, posargs: List[Pattern], kwargs: Mapping[str, Pattern]
    ):
        self.cls = cls
        self.posargs = posargs
        self.kwargs = kwargs

    def match(self, x: object) -> Optional[Dict[str, object]]:
        if not _is_instance(x, self.cls):
            return None

        try:
            fields = dataclasses.fields(x)
        except RuntimeError:
            fields = ()

        if len(self.posargs) > len(fields):
            return None  # Can't match: more positional patterns than fields.

        missing = object()
        matches = {}

        for field, pattern in zip(fields, self.posargs):
            value = getattr(x, field.name, missing)
            if value is missing:
                return None  # Can't match: attribute not set.
            match = pattern.match(value)
            if match is None:
                return None
            matches.update(match)

        for name, pattern in self.kwargs.items():
            value = getattr(x, name, missing)
            if value is missing:
                return None  # Can't match: attribute not set.
            match = pattern.match(value)
            if match is None:
                return None
            matches.update(match)

        return matches


class WalrusPattern(Pattern):
    """A pattern using a walrus operator.

    For example, ``a := (p, q)``.  This matches a pair, whose elements
    are extracted into ``p`` and ``q``, while the entire pair is
    extracted into ``a``.
    """

    def __init__(self, name: str, pattern: Pattern):
        self.name = name
        self.pattern = pattern

    def match(self, x: object) -> Optional[Dict[str, object]]:
        match = self.pattern.match(x)
        if match is not None:
            match[self.name] = x
        return match
