# Pattern Matching

```
match x:
    case (1|2, b): ...
    case (a, b): ...
    case (a, b, c): ...
    case MyClass(a, b): ...
```

This is heavily inspired by the work (in 2018) by
[Tobias Kohn](https://tobiaskohn.ch/index.php/2018/09/18/pattern-matching-syntax-in-python/).

The work has evolved quite a bit since then, though.  A fairly
complete proposal can be found in [pep-9999.rst](pep-9999.rst).

There are also some examples in [EXAMPLES.md](EXAMPLES.md).
