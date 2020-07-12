# TODO: Use proper equivalency for ValuePattern

import collections.abc as cabc
import itertools
import sys
from typing import Dict, List, Mapping, Optional, Set, Type

__all__ = [
    "Pattern",
    "CapturePattern",
    "ClassPattern",
    "MappingPattern",
    "OrPattern",
    "SequencePattern",
    "ValuePattern",
    "WalrusPattern",
    "WildcardPattern",
]


class Pattern:
    """A pattern to be matched.

    Various subclasses exist for different pattern matching concepts
    (e.g. sequence pattern, class pattern, value pattern).

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

    However for capturing values there are variable bindings to be
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
    """

    def match(self, x: object) -> Optional[Dict[str, object]]:
        raise NotImplementedError

    def translate(self, target: str) -> str:
        """target is a string representing a variable.

        The argument can be e.g. 'foo' or 'foo.bar' or 'foo.bar[0]'.

        Returns an expression that checks whether the target matches
        the pattern, e.g.  for ValuePattern(42), it could return
        '(foo == 42)'.
        """
        raise NotImplementedError

    def bindings(self, strict: bool = True) -> Set[str]:
        """Compute set of variables bound by a pattern.

        The variable `_` is excluded from the result.

        If strict=True (default), raise for certain errors:
        - Inconsistent bindings in arms of alternatives
        - Multiple bindings to the same variable
        """
        raise NotImplementedError


def _is_instance(x: object, t: type) -> bool:
    """Like instance() but pretend int subclasses float.

    TODO: Also pretend float subclasses complex.
    """
    return isinstance(x, t) or (t is float and isinstance(x, int))


class ValuePattern(Pattern):
    """A pattern that matches a given value.

    NOTE: This covers literal patterns and constant value patterns in PEP 622.
    """

    def __init__(self, constant: object):
        self.constant = constant

    def match(self, x: object) -> Optional[Dict[str, object]]:
        if x == self.constant:
            return {}
        return None

    def translate(self, target: str) -> str:
        return f"({target} == {self.constant!r})"

    def bindings(self, strict: bool = True) -> Set[str]:
        return set()


class OrPattern(Pattern):
    """A pattern consisting of several alternatives.

    This is a sequence of patterns separated by bars (``|``).

    The first matching pattern is selected.
    """

    def __init__(self, patterns: List[Pattern]):
        self.patterns = patterns

    def match(self, x: object) -> Optional[Dict[str, object]]:
        for p in self.patterns:
            match = p.match(x)
            if match is not None:
                return match
        return None

    def translate(self, target: str) -> str:
        return f"({' or '.join(p.translate(target) for p in self.patterns)})"

    def bindings(self, strict: bool = True) -> Set[str]:
        if not self.patterns:
            return set()
        result = self.patterns[0].bindings(strict)
        for i, p in enumerate(self.patterns[1:], 1):
            b = p.bindings()
            if strict and b != result:
                raise TypeError(
                    f"Alternatives 0 and {i} bind inconsistent sets of variables: "
                    + f"{sorted(result)} vs. {sorted(b)} "
                    + f"(difference: {sorted(b ^ result)})"
                )
            result |= b
        return result


class CapturePattern(Pattern):
    """A pattern that captures a value into a variable.

    This is an 'irrefutable' pattern (meaning that it always matches)
    that produces a new name binding.

    NOTE: For '_' use WildcardPattern.
    """

    def __init__(self, name: str):
        assert name != "_"
        self.name = name

    def match(self, x: object) -> Dict[str, object]:
        return {self.name: x}

    def translate(self, target: str) -> str:
        return f"({self.name} := {target},)"  # Always true, sets self.name.

    def bindings(self, strict: bool = True) -> Set[str]:
        return {self.name}


class WildcardPattern(Pattern):
    """A pattern that always matches and captures nothing."""

    def __init__(self) -> None:
        pass

    def match(self, x: object) -> Dict[str, object]:
        return {}

    def translate(self, target: str) -> str:
        return f"True"

    def bindings(self, strict: bool = True) -> Set[str]:
        return set()


def _full_class_name(cls: type) -> str:
    # TODO: import shenanigans to make this actually work
    if cls.__module__ == "builtins":
        return cls.__qualname__
    else:
        return f"{cls.__module__}.{cls.__qualname__}"


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

    def translate(self, target: str) -> str:
        # TODO: arrange to import Sequence; exclude str/bytes
        per_item = (p.translate(f"{target}[{i}]") for i, p in enumerate(self.patterns))
        return f"(isinstance({target}, Sequence) and len({target}) == {len(self.patterns)} and {' and '.join(per_item)})"

    def bindings(self, strict: bool = True) -> Set[str]:
        result: Set[str] = set()
        for p in self.patterns:
            b = p.bindings(strict)
            if strict and b & result:
                raise TypeError(
                    f"Duplicate bindings in sequence pattern: {sorted(b & result)}"
                )
            result |= b
        return result


class MappingPattern(Pattern):
    """A pattern for a mapping.

    This uses constants for keys but patterns for values.
    Extra key/value pairs are ignored.
    """

    def __init__(self, patterns: Mapping[object, Pattern]):
        self.patterns = patterns

    def match(self, x: object) -> Optional[Dict[str, object]]:
        if not isinstance(x, Mapping):
            return None
        matches = {}
        for key, pattern in self.patterns.items():
            try:
                value = x[key]
            except KeyError:
                return None
            match = pattern.match(value)
            if match is None:
                return None
            matches.update(match)
        return matches

    def translate(self, target: str) -> str:
        # TODO: arrange to import Mapping
        per_item = (
            f"({key!r} in {target} and " + pat.translate(f"{target}[{key!r}]") + ")"
            for key, pat in self.patterns.items()
        )
        return f"(isinstance({target}, Mapping) and {' and '.join(per_item)})"

    def bindings(self, strict: bool = True) -> Set[str]:
        result: Set[str] = set()
        for key, p in self.patterns.items():
            b = p.bindings(strict)
            if strict and b & result:
                raise TypeError(
                    f"Duplicate bindings in mapping pattern: {sorted(b & result)}"
                )
            result |= b
        return result


def _get_stack_depth() -> int:
    """Hack used to generate unique names depending on nesting."""
    i = 0
    while True:
        try:
            sys._getframe(i)
        except ValueError:
            return i
        i += 1


class ClassPattern(Pattern):
    """A pattern that matches a class instance.

    For example, ``MyClass(x, flag=y)``.  This extracts variables
    ``x`` and ``y``.
    """

    def __init__(
        self, cls: Type, posargs: List[Pattern], kwargs: Mapping[str, Pattern]
    ):
        self.cls = cls
        self.posargs = posargs
        self.kwargs = kwargs
        self.fields = getattr(self.cls, "__match_args__", ())
        if not isinstance(self.fields, (list, tuple)):
            raise TypeError("__match_args__ should be a list or tuple")
        if len(self.posargs) > len(self.fields):
            raise TypeError("more positional args than __match_args__ supports")
        for i, field in enumerate(self.fields[:len(self.posargs)]):
            if field in self.kwargs:
                raise TypeError(f"posargs[{i}] conflicts with kwargs[{field!r}]")

    def match(self, x: object) -> Optional[Dict[str, object]]:
        if not _is_instance(x, self.cls):
            return None

        missing = object()
        matches = {}

        for field, pattern in zip(self.fields, self.posargs):
            value = getattr(x, field, missing)
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

    def translate(self, target: str) -> str:
        # TODO: arrange to import Sequence and _Nope
        depth = _get_stack_depth()
        daclass = f"_c{depth}"
        tmpvar = f"_t{depth}"
        item = f"_i{depth}"
        conditions = []
        conditions.append(f"({tmpvar} := {target},)")
        conditions.append(f"({daclass} := {_full_class_name(self.cls)},)")
        conditions.append(f"isinstance({tmpvar}, {daclass})")
        npos = len(self.posargs)
        if npos > 0:
            for pat, field in zip(self.posargs, self.fields, strict=False):
                conditions.append(
                    f"({item} := getattr({tmpvar}, {field!r}, _Nope)) is not _Nope"
                )
                conditions.append(pat.translate(item))
        for kw, pat in self.kwargs.items():
            conditions.append(
                f"({item} := getattr({tmpvar}, {kw!r}, _Nope)) is not _Nope"
            )
            conditions.append(pat.translate(item))

        ## print("\nXXX ========>")
        ## for cond in conditions:
        ##     print("XXX ", cond)
        ##     compile(cond, "XXX", "eval")
        ## print("XXX <========")

        joined = " and ".join(conditions)
        return f"({joined})"

    def bindings(self, strict: bool = True) -> Set[str]:
        result: Set[str] = set()
        for p in itertools.chain(self.posargs, self.kwargs.values()):
            b = p.bindings(strict)
            if strict and b & result:
                raise TypeError(
                    f"Duplicate bindings in instance pattern: {sorted(b & result)}"
                )
            result |= b
        return result


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

    def translate(self, target: str) -> str:
        return f"(({self.name} := {target},) if {self.pattern.translate(target)} else False)"

    def bindings(self, strict: bool = True) -> Set[str]:
        result = self.pattern.bindings(strict)
        if self.name != "_":
            if strict and self.name in result:
                raise TypeError("Duplicate bindings in walrus pattern")
            result |= {self.name}
        return result
