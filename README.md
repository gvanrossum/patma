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

## Grammar ideas

Using a simple addition to pegen we could just use the syntax shown
above.  The toplevel grammar would be:

```
...
compound_statement:
    | if_stmt
    ...
    | match_stmt
match_stmt: "match" expression ':' NEWLINE INDENT case_block+ DEDENT
case_block: "case" pattern ['if' named_expression] ':' block
pattern:
    # TBD
```

The addition to pegen would be that a keyword in double quotes (like
`"match"` and `"case"` above) is only a keyword in context -- the
tokenizer does not recognize it as a reserved word.  (In the early
days of pegen this was how all keywords were handled, but strict
compatibility with the old Python parser required that we made all
keywords "reserved words" regardless of context.)

This works because of the colon in the syntax.  There are valid
expressions that can be combined with a preceding identifier to form
another valid expression.  For example, if we take the valid
expression `[x]` and prepend the identifier `match`, we get the valid
expression `match[x]`.  But no current Python statement can start with
`match[x]:`.

With the grammar given above, given a line starting with `match x+1:`,
the parser would first attempt to parse it as an expression, fail to
parse at the `+` operator, then backtrack and attempt to parse the
same input as a match statement.  And a line comprising of `match [x]
<NEWLINE>` will be parsed as an expression statement.

Note that the `"case"` keyword is not strictly necessary.  We could
just as well define `case_block` as follows:

```
case_block: pattern ['if' named_expression] ':' block
```

But I believe, with Kohn, that adding a keyword makes the code more
readable (to those not versed in functional languages, anyways).

### Examples

See [EXAMPLES file](EXAMPLES.md)
