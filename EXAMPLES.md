# Examples

Since I don't have a parser yet, converted examples may contain bugs.

## Case 1: [Constant matches](https://github.com/python/cpython/blob/ce81a925/Lib/plistlib.py#L319-L351)

Original:

```
def convert_field(self, value, conversion):
    # do any conversion on the resulting object
    if conversion is None:
        return value
    elif conversion == 's':
        return str(value)
    elif conversion == 'r':
        return repr(value)
    elif conversion == 'a':
        return ascii(value)
    raise ValueError("Unknown conversion specifier {0!s}".format(conversion))
```

Converted:

```
def convert_field(self, value, conversion):
    # do any conversion on the resulting object
    match conversion:
        case None:
            return value
        case 's':
            return str(value)
        case 'r':
            return repr(value)
        case 'a':
            return ascii(value)
        case _:
            raise ValueError("Unknown conversion specifier {0!s}".format(conversion))
```

## Case 2: [Mixed constant and type matches](https://github.com/python/cpython/blob/ce81a925/Lib/plistlib.py#L319-L351)

Original:

```
def write_value(self, value):
    if isinstance(value, str):
        self.simple_element("string", value)

    elif value is True:
        self.simple_element("true")

    elif value is False:
        self.simple_element("false")

    elif isinstance(value, int):
        if -1 << 63 <= value < 1 << 64:
            self.simple_element("integer", "%d" % value)
        else:
            raise OverflowError(value)

    elif isinstance(value, float):
        self.simple_element("real", repr(value))

    elif isinstance(value, dict):
        self.write_dict(value)

    elif isinstance(value, (bytes, bytearray)):
        self.write_bytes(value)

    elif isinstance(value, datetime.datetime):
        self.simple_element("date", _date_to_string(value))

    elif isinstance(value, (tuple, list)):
        self.write_array(value)

    else:
        raise TypeError("unsupported type: %s" % type(value))
```

Converted:

```
def write_value(self, value):
    match value:
        case str():
            self.simple_element("string", value)

        case  True:
            self.simple_element("true")

        case False:
            self.simple_element("false")

        case int():
            if -1 << 63 <= value < 1 << 64:
                self.simple_element("integer", "%d" % value)
            else:
                raise OverflowError(value)

        case float():
            self.simple_element("real", repr(value))

        case dict():
            self.write_dict(value)

        case bytes() | bytearray():
            self.write_bytes(value)

        case datetime.datetime():
            self.simple_element("date", _date_to_string(value))

        case tuple() | list():
            self.write_array(value)

        case _:
            raise TypeError("unsupported type: %s" % type(value))
```

## Case 3: [Iterable value matches with extraction](https://github.com/python/cpython/blob/815280e/Lib/_pydecimal.py#L6280-L6301)

Original:

```
def _group_lengths(grouping):
    """Convert a localeconv-style grouping into a (possibly infinite)
    iterable of integers representing group lengths.
    """
    # The result from localeconv()['grouping'], and the input to this
    # function, should be a list of integers in one of the
    # following three forms:
    #
    #   (1) an empty list, or
    #   (2) nonempty list of positive integers + [0]
    #   (3) list of positive integers + [locale.CHAR_MAX], or

    from itertools import chain, repeat
    if not grouping:
        return []
    elif grouping[-1] == 0 and len(grouping) >= 2:
        return chain(grouping[:-1], repeat(grouping[-2]))
    elif grouping[-1] == _locale.CHAR_MAX:
        return grouping[:-1]
    else:
        raise ValueError('unrecognised format for grouping')
```

Converted:

```
def _group_lengths(grouping):
    """Convert a localeconv-style grouping into a (possibly infinite)
    iterable of integers representing group lengths.
    """
    # The result from localeconv()['grouping'], and the input to this
    # function, should be a list of integers in one of the
    # following three forms:
    #
    #   (1) an empty list, or
    #   (2) nonempty list of positive integers + [0]
    #   (3) list of positive integers + [locale.CHAR_MAX], or

    from itertools import chain, repeat
    assert isinstance(grouping, list)  # Else it's more complicated
    match grouping:
        case []:
            return []
        case [*rest, 0] if rest:
            return chain(rest, repeat(rest[-1]))
        case [*rest, _locale.CHAR_MAX]:
            return rest
        case _:
            raise ValueError('unrecognised format for grouping')
```

## Case 4: [Mixed simple type and deep matches](https://github.com/python/cpython/blob/bace59d/Lib/ast.py#L78-L101)

Original:

```
def _convert(node):
    if isinstance(node, Constant):
        return node.value
    elif isinstance(node, Tuple):
        return tuple(map(_convert, node.elts))
    elif isinstance(node, List):
        return list(map(_convert, node.elts))
    elif isinstance(node, Set):
        return set(map(_convert, node.elts))
    elif (isinstance(node, Call) and isinstance(node.func, Name) and
          node.func.id == 'set' and node.args == node.keywords == []):
        return set()
    elif isinstance(node, Dict):
        return dict(zip(map(_convert, node.keys),
                        map(_convert, node.values)))
    elif isinstance(node, BinOp) and isinstance(node.op, (Add, Sub)):
        left = _convert_signed_num(node.left)
        right = _convert_num(node.right)
        if isinstance(left, (int, float)) and isinstance(right, complex):
            if isinstance(node.op, Add):
                return left + right
            else:
                return left - right
    return _convert_signed_num(node)
```

Converted:

```
def _convert(node):
    match node:
        case Constant(value=value):
            return value
        case Tuple(elts=elts):
            return tuple(map(_convert, elts))
        case List(elts=elts):
            return list(map(_convert, elts))
        case Set(elts=elts):
            return set(map(_convert, elts))
        case Call(func=Name(id='set'), args=[], keywords=[]):
            return set()
        case Dict(keys=keys, values=values):
            return dict(zip(map(_convert, keys),
                            map(_convert, values)))
        case BinOp(op=Add()|Sub()):
            left = _convert_signed_num(node.left)
            right = _convert_num(node.right)
            match (left, right, node.op):
                case [int() | float(), complex(), Add()]:
                    return left + right
                case [int() | float(), complex(), Sub()]:
                    return left - right
                case _:
                    return _convert_signed_num(node)
        case _:
            return _convert_signed_num(node)
```

## Case 5: [Deep type, iterable, and value matches with extraction](https://github.com/python/mypy/blob/9076fb0/mypyc/ir/rtypes.py#L490-L500)

Original:

```
def optional_value_type(rtype: RType) -> Optional[RType]:
    """If rtype is the union of none_rprimitive and another type X, return X.
    Otherwise return None.
    """
    if isinstance(rtype, RUnion) and len(rtype.items) == 2:
        if rtype.items[0] == none_rprimitive:
            return rtype.items[1]
        elif rtype.items[1] == none_rprimitive:
            return rtype.items[0]
    return None
```

Converted:

```
def optional_value_type(rtype: RType) -> Optional[RType]:
    """If rtype is the union of none_rprimitive and another type X, return X.
    Otherwise return None.
    """
    match rtype:
        case RUnion(items=[.none_rprimitive, b]):
            return b
        case RUnion(items=[a, .none_rprimitive]):
            return a
        case _:
            return None
```

## Case 6: [A very deep iterable and type match with extraction](https://github.com/gvanrossum/pegen/blob/54d84ad/pegen/grammar.py#L118-L128)

Original:

```
def flatten(self) -> Rhs:
    # If it's a single parenthesized group, flatten it.
    rhs = self.rhs
    if (
        not self.is_loop()
        and len(rhs.alts) == 1
        and len(rhs.alts[0].items) == 1
        and isinstance(rhs.alts[0].items[0].item, Group)
    ):
        rhs = rhs.alts[0].items[0].item.rhs
    return rhs
```

Converted (note that I had to name the classes `Alt` and `NamedItem`,
which are anonymous in the original):

```
def flatten(self) -> Rhs:
    # If it's a single parenthesized group, flatten it.
    rhs = self.rhs
    if not self.is_loop():
        match rhs.alts:
            case [Alt(items=[NamedItem(item=Group(rhs=r))])]:
                rhs = r
    return rhs
```
