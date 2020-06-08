# Sample program that incorporates many uses of `match`.
import re
import sys
import tokenize
from enum import Enum
from collections import namedtuple

# Note: The tokenizer doesn't use `match`, skip this part - more interesting code below.
class TokenStream:
    """Class representing a consumable stream of input tokens"""
    def __init__(self, input):
        lines = iter([input])  # We're only parsing a single line, not a whole file
        self.stream = tokenize.generate_tokens(lambda: next(lines))
        self.input = input  # original input text
        self.next()  # prime the pump

    def next(self):
        while True:
            try:
                token = next(self.stream)
                if token.type == tokenize.NEWLINE:
                    continue
                self.token = (token.type, token.string)
                self.pos = token.start[1]
                break
            except StopIteration:
                self.token = (tokenize.ENDMARKER, None)
                break

    def syntax(self, msg):
        """Print a syntax error."""
        print(f"{msg} at column {self.pos + 1}:")
        print(self.input)
        print(" " * self.pos, "^", sep='')
        # TODO: Should probably raise here, and catch in main()
        return None

    @property
    def token_type(self):
        return self.token[0]

    @property
    def token_value(self):
        return self.token[1]

# Note definition of __match_args__ to support sequence destructuring.
class BinaryOp:
    """A binary operator expression."""
    __match_args__ = ["op", "left", "right"]

    def __init__(self, op, left, right, precedence = 0):
        self.op = op
        self.left = left
        self.right = right
        self.precedence = precedence

    def __repr__(self):
        return f"{repr(self.left)} {self.op} {repr(self.right)}"

    def __str__(self):
        return f"{str(self.left)} {self.op} {str(self.right)}"

class UnaryOp:
    """A unary operator expression."""
    __match_args__ = ["op", "arg"]

    def __init__(self, op, arg):
        self.op = op
        self.arg = arg

class VarExpr:
    """A reference to a variable."""
    __match_args__ = ["name"]

    def __init__(self, name):
        self.name = name

def parse_expr(tokstream: TokenStream):
    """Parse an expression."""
    result = parse_binop(tokstream)
    if tokstream.token_type != tokenize.ENDMARKER:
        tokstream.syntax(f"Unrecognized token '{tokenize.tok_name[tokstream.token_type]}'")
        return None
    elif result is None:
        tokstream.syntax(f"Expression expected")
    return result

OpStackEntry = namedtuple("OpStackEntry", "op precedence")

def parse_binop(tokstream: TokenStream):
    """Parse binary operator."""
    # Parse the left-hand side
    arg0 = parse_unop(tokstream)
    if arg0 is None:
        return None

    # Structure of the operator stack is:
    # [ value,
    #   (op, prededence),
    #   value,
    #   (op, prededence),
    #   value,
    #   etc...
    # ]
    opstack = [arg0]

    # While precedence on the stack is higher than the precedence of the next operator,
    # combine the top three stack items into one.
    def reduce(precedence):
        # Note: changing >= to > here makes operators right-associative.
        while len(opstack) > 2 and opstack[-2].precedence >= precedence:
            opstack[-3:] = [
              BinaryOp(opstack[-2].op, opstack[-3], opstack[-1], opstack[-2].precedence)
            ]

    # Simple operator precedence parser
    while tokstream.token_type != tokenize.ENDMARKER:
        token, value = tokstream.token
        if token != tokenize.OP:
            break
        elif value == "*" or value == "/":
            reduce(4)
            tokstream.next()
            opstack.append(OpStackEntry(value, 4))
        elif value == "+" or value == "-":
            reduce(3)
            tokstream.next()
            opstack.append(OpStackEntry(value, 3))
        else:
            # TODO: Support power
            break

        # Parse the right-hand side
        arg1 = parse_unop(tokstream)
        if arg1 is None:
            tokstream.syntax("Expression expected after operator")
            return None
        opstack.append(arg1)

    reduce(0)
    assert len(opstack) == 1
    return opstack[0]

def parse_unop(tokstream: TokenStream):
    """Parse unary operator."""
    if tokstream.token_type == tokenize.OP:
        value = tokstream.token_value
        if value == "+" or value == "-":
            tokstream.next()
            arg = parse_unop(tokstream)
            if arg is None:
                return None
            return UnaryOp(value, arg)

    return parse_primary(tokstream)

def parse_primary(tokstream: TokenStream):
  """Parse a primary expression."""
  token, value = tokstream.token
  match token:
      case tokenize.ENDMARKER:
          return None
      case tokenize.NAME:
          tokstream.next()
          return VarExpr(value)
      case tokenize.NUMBER:
          tokstream.next()
          if "." in value:
              return float(value)
          else:
              return int(value)
      case tokenize.LPAR:
          tokstream.next()
          expr = parse_binop(tokstream)
          if not expr:
              return None
          token, value = tokstream.token
          if token == tokenize.RPAR:
              tokstream.next()
              return expr
          else:
              tokstream.syntax("Closing paren expected")
              return None
      case _:
          return None

def format_expr(expr, precedence = 0):
    """Format an expression as a string."""
    match expr:
        case BinaryOp(op, left, right):
            result = \
                f"{format_expr(left, expr.precedence)} {op} {format_expr(right, expr.precedence)}"
            # Surround the result in parentheses if needed
            if precedence > expr.precedence:
                return f"({result})"
            else:
                return result
        case UnaryOp(op, arg):
            return f"{op} {format_expr(arg, 0)}"
        case VarExpr(name):
            return name
        case float() | int():
            return str(expr)
        case _:
            raise ValueError(f"Invalid expression value: {repr(expr)}")

def format_expr_tree(expr, indent=""):
    """Format an expression as a hierarchical tree."""
    match expr:
        case BinaryOp(op, left, right):
            return (f"{indent}({op}\n"
                + format_expr_tree(left, indent + "  ") + "\n"
                + format_expr_tree(right, indent + "  ") + ")")
        case UnaryOp(op, arg):
            return f"{indent}({op}\n" + format_expr_tree(arg, indent + "  ") + ")"
        case float() | int():
            return f"{indent}{expr}"
        case VarExpr(name):
            return f"{indent}{name}"
        case _:
            raise ValueError(f"Invalid expression value: {repr(expr)}")

def eval_expr(expr):
    """Evaluate an expression and return the result."""
    match expr:
        case BinaryOp('+', left, right):
            return eval_expr(left) + eval_expr(right)
        case BinaryOp('-', left, right):
            return eval_expr(left) - eval_expr(right)
        case BinaryOp('*', left, right):
            return eval_expr(left) * eval_expr(right)
        case BinaryOp('/', left, right):
            return eval_expr(left) / eval_expr(right)
        case UnaryOp('+', arg):
            return eval_expr(arg)
        case UnaryOp('-', arg):
            return -eval_expr(arg)
        case VarExpr(name):
            raise ValueError(f"Unknown value of: {name}")
        case float() | int():
            return expr
        case _:
            raise ValueError(f"Invalid expression value: {repr(expr)}")

def simplify_expr(expr):
    """Simplify an expression by folding constants and removing identities."""
    match expr:
      case BinaryOp(op, left, right):
          left = simplify_expr(left)
          right = simplify_expr(right)
          match (op, left, right):
              case [_, float() | int(), float() | int()]:
                  return eval_expr(BinaryOp(op, left, right))
              case ['+', 0, _] | ['*', 1, _]:
                  return right
              case ['+' | '-', _, 0] | ['*' | '/', _, 1]:
                  return left
              case ['-', 0, _]:
                  return UnaryOp('-', right)
              case ['*', 0, _] | ['*', _, 0]:
                  return 0
              case _:
                  return BinaryOp(op, left, right)
      case UnaryOp(op, arg):
          arg = simplify_expr(arg)
          match (op, arg):
              case ['+', _]:
                  return arg
              case ['-', float() | int()]:
                  return -arg
              case _:
                  return UnaryOp(op, arg)
      case VarExpr(name):
          return expr
      case float() | int():
          return expr
      case _:
          raise ValueError(f"Invalid expression value: {repr(expr)}")

def main():
    print("Enter an command followed by an arithmetic expression.")
    print("Supported commands are:")
    print(" * print <expr>      print the expression")
    print(" * tree <expr>       print the expression in tree form")
    print(" * eval <expr>       evaluate the expression")
    print(" * simplify <expr>   fold constants and remove identities")
    print(" * quit, q           exit the program")

    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            return
        tokstream = TokenStream(line)
        tok, command = tokstream.token
        if tok == tokenize.NAME:
            tokstream.next()
            if command == "quit" or command == "q":
                break
            match command:
                case "print":
                    expr = parse_expr(tokstream)
                    if expr is not None:
                        print(format_expr(expr))
                case "tree":
                    expr = parse_expr(tokstream)
                    if expr is not None:
                        print(format_expr_tree(expr))
                case "eval":
                    expr = parse_expr(tokstream)
                    if expr is not None:
                        print(eval_expr(expr))
                case "simplify":
                    expr = parse_expr(tokstream)
                    if expr is not None:
                        print(format_expr(simplify_expr(expr)))
                case _:
                    print(f"Unknown command: {command}")
        else:
            print("Command expected")

if __name__ == "__main__":
    main()
