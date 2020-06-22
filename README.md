# Pattern Matching

This repo contains a [draft PEP](pep-9999.rst) proposing a `match`
statement.

Origins
-------

The work has several origins:

- Many statically compiled languages (especially functional ones) have
  a `match` expression, for example
  [Scala](http://www.scala-lang.org/files/archive/spec/2.11/08-pattern-matching.html),
  [Rust](https://doc.rust-lang.org/reference/expressions/match-expr.html),
  [F#](https://docs.microsoft.com/en-us/dotnet/fsharp/language-reference/pattern-matching);
- Several extensive discussions on python-ideas, culminating in a
  summarizing
  [blog post](https://tobiaskohn.ch/index.php/2018/09/18/pattern-matching-syntax-in-python/)
  by Tobias Kohn;
- An independently developed [draft
  PEP](https://github.com/ilevkivskyi/peps/blob/pattern-matching/pep-9999.rst)
  by Ivan Levkivskyi.

Implementation
--------------

A full reference implementation written by Brandt Bucher is available
as a [fork]((https://github.com/brandtbucher/cpython/tree/patma)) of
the CPython repo.  This is readily converted to a [pull
request](https://github.com/brandtbucher/cpython/pull/2)).

Examples
--------

Some [example code](examples/) is available from this repo.

Tutorial
--------

A `match` statement takes an expression and compares it to successive
patterns given as one or more `case` blocks.  This is superficially
similar to a `switch` statement in C, Java or JavaScript (an many
other languages), but much more powerful.

The simplest form compares a target value against one or more literals:

```py
def http_error(status):
    match status:
        case 400:
            return "Bad request"
        case 401:
            return "Unauthorized"
        case 403:
            return "Forbidden"
        case 404:
            return "Not found"
        case 418:
            return "I'm a teapot"
        case _:
            return "Something else"
```

Note the last block: the "variable name" `_` acts as a *wildcard* and
never fails to match.

You can combine several literals in a single pattern using `|` ("or"):

```py
        case 401|403|404:
            return "Not allowed"
```

Patterns can look like unpacking assignments, and can be used to bind
variables:

```py
# The target is an (x, y) tuple
match point:
    case (0, 0):
        print("Origin")
    case (0, y):
        print(f"Y={y}")
    case (x, 0):
        print(f"X={x}")
    case (x, y):
        print(f"X={x}, Y={y}")
    case _:
        raise ValueError("Not a point")
```

Study that one carefully!  The first pattern has two literals, and can
be thought of as an extension of the literal pattern shown above.  But
the second two patterns combine a literal and a variable, and the
variable is *extracted* from the target value (`point`).  The fourth
pattern is a double extraction, which makes it conceptually similar to
the unpacking assignment `(x, y) = point`.

If you are using classes to structure your data (e.g. data classes)
you can use the class name followed by an argument list resembling a
constructor, but with the ability to extract variables:

```py
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

def whereis(point):
    match point:
        case Point(0, 0):
            print("Origin")
        case Point(0, y):
            print(f"Y={y}")
        case Point(x, 0):
            print(f"X={x}")
        case Point():
            print("Somewhere else")
        case _:
            print("Not a point")
```

We can use keyword parameters too.  The following patterns are all
equivalent (and all bind the `y` attribute to the `var` variable):

```py
Point(1, var)
Point(1, y=var)
Point(x=1, y=var)
Point(y=var, x=1)
```

Patterns can be arbitrarily nested.  For example, if we have a short
list of points, we could match it like this:

```py
match points:
    case []:
        print("No points")
    case [Point(0, 0)]:
        print("The origin")
    case [Point(x, y)]:
        print(f"Single point {x}, {y}")
    case [Point(0, y1), Point(0, y2)]:
        print(f"Two on the Y axis at {y1}, {y2}")
    case _:
        print("Something else")
```

We can add an `if` clause to a pattern, known as a "guard".  If the
guard is false, `match` goes on to try the next `case` block.  Note
that variable extraction happens before the guard is evaluated:

```py
match point:
    case Point(x, y) if x == y:
        print(f"Y=X at {x}")
    case Point(x, y):
        print(f"Not on the diagonal")
```

Several other key features:

- Like unpacking assignments, tuple and list patterns have exactly the
  same meaning and actually match arbitrary sequences.  An important
  exception is that they don't match iterators or strings.
  (Technically, the target must be an instance of
  `collections.abc.Sequence`.)

- Sequence patterns support wildcards: `[x, y, *rest]` and `(x, y,
  *rest)` work similar to wildcards in unpacking assignments.  The
  name after `*` may also be `_`, so `(x, y, *_)` matches a sequence
  of at least two items without binding the remaining items.

- Mapping patterns: `{"bandwidth": b, "latency": l}` extracts the
  `"bandwidth"` and `"latency"` values from a dict.  Unlike sequence
  patterns, extra keys are ignored.  A wildcard `**rest` is also
  supported.  (But `**_` would be redundant, so it not allowed.)

- Subpatterns may be extracted using the walrus (`:=`) operator:

  ```py
  case (Point(x1, y1), p2 := Point(x2, y2)): ...
  ```

- Patterns may use named constants.  These must be dotted names; a
  single name can be made into a constant value by prefixing it with a
  dot to prevent it from being interpreted as a variable extraction:

  ```py
  RED, GREEN, BLUE = 0, 1, 2

  match color:
      case .RED:
          print("I see red!")
      case .GREEN:
          print("Grass is green")
      case .BLUE:
          print("I'm feeling the blues :(")
  ```

- Classes can customize how they are matched by defining a
  `__match__()` method.
  Read the [PEP](pep-9999.rst#runtime-specification) for details.
