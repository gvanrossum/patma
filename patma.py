import collections.abc as cabc
import dataclasses
import itertools
import sys
from typing import Dict, List, Mapping, Optional, Set, Type

__all__ = [
    "Pattern",
    "AlternativesPattern",
    "ConstantPattern",
    "VariablePattern",
    "AnnotatedPattern",
    "SequencePattern",
    "MappingPattern",
    "InstancePattern",
    "WalrusPattern",
    "BindingsError",
    "InconsistentBindings",
    "DuplicateBindings",
]


class BindingsError(Exception):
    """Invalid bindings detected.

    A subclass of this is raised for cases like these:

    - case [] | [x]: ...
    - case [x, x]: ...
    """


class InconsistentBindings(BindingsError):
    """Not all alternatives bind the same set of variables."""


class DuplicateBindings(BindingsError):
    """Variable bound more than once."""


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
        raise NotImplementedError

    def translate(self, target: str) -> str:
        """target is a string representing a variable.

        The argument can be e.g. 'foo' or 'foo.bar' or 'foo.bar[0]'.

        Returns an expression that checks whether the target matches
        the pattern, e.g.  for ConstantPattern(42), it could return
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

    def translate(self, target: str) -> str:
        if isinstance(self.constant, int):
            return f"({target} == {self.constant!r} and isinstance({target}, int))"
        if isinstance(self.constant, float):
            return f"({target} == {self.constant!r} and isinstance({target}, (int, float)))"
        # TODO: complex
        return f"({target} == {self.constant!r})"

    def bindings(self, strict: bool = True) -> Set[str]:
        return set()


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

    def translate(self, target: str) -> str:
        return f"({' or '.join(p.translate(target) for p in self.patterns)})"

    def bindings(self, strict: bool = True) -> Set[str]:
        if not self.patterns:
            return set()
        result = self.patterns[0].bindings(strict)
        for i, p in enumerate(self.patterns[1:], 1):
            b = p.bindings()
            if strict and b != result:
                raise InconsistentBindings(
                    f"Alternatives 0 and {i} bind inconsistent sets of variables: "
                    + f"{sorted(result)} vs. {sorted(b)} "
                    + f"(difference: {sorted(b ^ result)})"
                )
            result |= b
        return result


class VariablePattern(Pattern):
    """A value extraction pattern.

    This is an 'irrefutable' pattern (meaning that it always matches)
    that produces a new name binding.
    """

    def __init__(self, name: str):
        self.name = name

    def match(self, x: object) -> Dict[str, object]:
        return {self.name: x}

    def translate(self, target: str) -> str:
        return f"({self.name} := {target},)"

    def bindings(self, strict: bool = True) -> Set[str]:
        if self.name == "_":
            return set()
        else:
            return {self.name}


def _full_class_name(cls: type) -> str:
    # TODO: import shenanigans to make this actually work
    if cls.__module__ == "builtins":
        return cls.__qualname__
    else:
        return f"{cls.__module__}.{cls.__qualname__}"


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

    def translate(self, target: str) -> str:
        # TODO: numeric tower
        return f"(isinstance({target}, {_full_class_name(self.cls)}) and {self.pattern.translate(target)})"

    def bindings(self, strict: bool = True) -> Set[str]:
        return self.pattern.bindings(strict)


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
                raise DuplicateBindings(
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
                raise DuplicateBindings(
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

    def translate(self, target: str) -> str:
        depth = _get_stack_depth()
        tmpvar = f"_t{depth}"
        fields = f"_f{depth}"
        item = f"_i{depth}"
        conditions = []
        conditions.append(
            f"({tmpvar} := {_full_class_name(self.cls)}.__match__({target})) is not None"
        )
        npos = len(self.posargs)
        if npos > 0:
            conditions.append(
                f"({fields} := getattr({tmpvar}, '__match_args__', None)) is not None"
            )
            conditions.append(f"isinstance({fields}, Sequence)")
            conditions.append(f"len({fields}) >= {npos}")
            for i in range(npos):
                conditions.append(
                    f"({item} := getattr({tmpvar}, {fields}[{i}], _Nope)) is not _Nope"
                )
                conditions.append(self.posargs[i].translate(item))
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
                raise DuplicateBindings(
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
                raise DuplicateBindings("Duplicate bindings in walrus pattern")
            result |= {self.name}
        return result
