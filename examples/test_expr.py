from expr import BinaryOp, UnaryOp, VarExpr, eval_expr, format_expr, simplify_expr

def test_eval_binary():
    assert eval_expr(BinaryOp('+', 1, 2)) == 3
    assert eval_expr(BinaryOp('-', 1, 2)) == -1
    assert eval_expr(BinaryOp('*', 1, 2)) == 2
    assert eval_expr(BinaryOp('/', 1, 2)) == 0.5

def test_eval_unary():
    assert eval_expr(UnaryOp('+', 1)) == 1
    assert eval_expr(UnaryOp('-', 1)) == -1

def test_format_simple():
    assert format_expr(BinaryOp('+', 1, 2)) == '1 + 2'
    assert format_expr(BinaryOp('-', 1, 2)) == '1 - 2'
    assert format_expr(BinaryOp('*', 1, 2)) == '1 * 2'
    assert format_expr(BinaryOp('/', 1, 2)) == '1 / 2'
    assert format_expr(UnaryOp('+', 1)) == '+1'
    assert format_expr(UnaryOp('-', 1)) == '-1'

def test_format_complex():
    # Same operator
    assert format_expr(BinaryOp('+', BinaryOp('+', 1, 2), 3)) == '1 + 2 + 3'
    assert format_expr(BinaryOp('+', 1, BinaryOp('+', 2, 3))) == '1 + (2 + 3)'

    assert format_expr(BinaryOp('-', BinaryOp('-', 1, 2), 3)) == '1 - 2 - 3'
    assert format_expr(BinaryOp('-', 1, BinaryOp('-', 2, 3))) == '1 - (2 - 3)'

    assert format_expr(BinaryOp('*', BinaryOp('*', 1, 2), 3)) == '1 * 2 * 3'
    assert format_expr(BinaryOp('*', 1, BinaryOp('*', 2, 3))) == '1 * (2 * 3)'

    assert format_expr(BinaryOp('/', BinaryOp('/', 1, 2), 3)) == '1 / 2 / 3'
    assert format_expr(BinaryOp('/', 1, BinaryOp('/', 2, 3))) == '1 / (2 / 3)'

    # Equal precedence
    assert format_expr(BinaryOp('+', BinaryOp('-', 1, 2), 3)) == '1 - 2 + 3'
    assert format_expr(BinaryOp('-', BinaryOp('+', 1, 2), 3)) == '1 + 2 - 3'
    assert format_expr(BinaryOp('+', 1, BinaryOp('-', 2, 3))) == '1 + (2 - 3)'
    assert format_expr(BinaryOp('-', 1, BinaryOp('+', 2, 3))) == '1 - (2 + 3)'

    assert format_expr(BinaryOp('*', BinaryOp('/', 1, 2), 3)) == '1 / 2 * 3'
    assert format_expr(BinaryOp('/', BinaryOp('*', 1, 2), 3)) == '1 * 2 / 3'
    assert format_expr(BinaryOp('*', 1, BinaryOp('/', 2, 3))) == '1 * (2 / 3)'
    assert format_expr(BinaryOp('/', 1, BinaryOp('*', 2, 3))) == '1 / (2 * 3)'

    # Different precedence
    assert format_expr(BinaryOp('+', BinaryOp('*', 1, 2), 3)) == '1 * 2 + 3'
    assert format_expr(BinaryOp('*', BinaryOp('+', 1, 2), 3)) == '(1 + 2) * 3'
    assert format_expr(BinaryOp('+', 1, BinaryOp('*', 2, 3))) == '1 + 2 * 3'
    assert format_expr(BinaryOp('*', 1, BinaryOp('+', 2, 3))) == '1 * (2 + 3)'

def test_simplify():
    # Constants
    assert format_expr(simplify_expr(BinaryOp('+', 1, 3))) == '4'
    assert format_expr(simplify_expr(UnaryOp('-', 1))) == '-1'

    # Variables
    assert format_expr(simplify_expr(BinaryOp('+', 2, VarExpr('x')))) == '2 + x'
    assert format_expr(simplify_expr(BinaryOp('-', 2, VarExpr('x')))) == '2 - x'
    assert format_expr(simplify_expr(BinaryOp('*', 2, VarExpr('x')))) == '2 * x'
    assert format_expr(simplify_expr(BinaryOp('/', 2, VarExpr('x')))) == '2 / x'
    assert format_expr(simplify_expr(BinaryOp('+', VarExpr('x'), 2))) == 'x + 2'
    assert format_expr(simplify_expr(BinaryOp('-', VarExpr('x'), 2))) == 'x - 2'
    assert format_expr(simplify_expr(BinaryOp('*', VarExpr('x'), 2))) == 'x * 2'
    assert format_expr(simplify_expr(BinaryOp('/', VarExpr('x'), 2))) == 'x / 2'

    # Add zero
    assert format_expr(simplify_expr(BinaryOp('+', 0, VarExpr('x')))) == 'x'
    assert format_expr(simplify_expr(BinaryOp('+', VarExpr('x'), 0))) == 'x'

    # Subtract zero
    assert format_expr(simplify_expr(BinaryOp('-', 0, VarExpr('x')))) == '-x'
    assert format_expr(simplify_expr(BinaryOp('-', VarExpr('x'), 0))) == 'x'

    # Multiply zero
    assert format_expr(simplify_expr(BinaryOp('*', 0, VarExpr('x')))) == '0'
    assert format_expr(simplify_expr(BinaryOp('*', VarExpr('x'), 0))) == '0'

    # Multiply one
    assert format_expr(simplify_expr(BinaryOp('*', 1, VarExpr('x')))) == 'x'
    assert format_expr(simplify_expr(BinaryOp('*', VarExpr('x'), 1))) == 'x'

    # Divide one
    assert format_expr(simplify_expr(BinaryOp('/', VarExpr('x'), 1))) == 'x'

    # Nested
    assert format_expr(simplify_expr(
        BinaryOp('+',
            BinaryOp('*', 1, VarExpr('x')),
            BinaryOp('+', 0, VarExpr('y'))
        ))) == 'x + y'

    # Unary plus
    assert format_expr(simplify_expr(UnaryOp('+', VarExpr('x')))) == 'x'

    # Double minus
    assert format_expr(simplify_expr(UnaryOp('-', UnaryOp('-', VarExpr('x'))))) == 'x'
