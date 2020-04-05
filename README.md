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

I agree with his assessment that we should closely mimic tuple
unpacking syntax.  However, I'm not thrilled having to write `(Num(x),
Num(y))`, so (in addition to that) I propose `(x: Num, y: Num)`.  Now
that we've been using type annotations for 5 years this looks less
weird than it did in 2018.

In addition, I think we can use the walrus operator for some corner
cases, e.g. to capture the sub-tuple here:

```
    case [a, b := [x, y], c]: ...
```
