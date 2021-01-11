import ast

import pythonflow as pf
from slipform import slipform
from slipform._ast_utils import ast_decompile_func, ast_rewrite_function, ast_compile_func
from slipform._translate import get_assign_target_names


def test_get_assign_target_names():
    def func():
        a = 1
        a, b = 1, 2
        a, (b, c) = 1, (2, 3)
        [(a, (d,)), (b, c)] = (1, (4,)), (2, 3)

    line_nodes = ast_decompile_func(func, unindent=True).body[0].body

    assert get_assign_target_names(line_nodes[0], flat=True) == ('a',)
    assert get_assign_target_names(line_nodes[1], flat=True) == ('a', 'b')
    assert get_assign_target_names(line_nodes[2], flat=True) == ('a', 'b', 'c')
    assert get_assign_target_names(line_nodes[3], flat=True) == ('a', 'd', 'b', 'c')

    assert get_assign_target_names(line_nodes[0], flat=False) == 'a'
    assert get_assign_target_names(line_nodes[1], flat=False) == ('a', 'b')
    assert get_assign_target_names(line_nodes[2], flat=False) == ('a', ('b', 'c'))
    assert get_assign_target_names(line_nodes[3], flat=False) == (('a', ('d',)), ('b', 'c'))


def test_slipform():
    def func():
        pass

        pass
# invalid indent
        pass

    # check compile & decompile
    node = ast_decompile_func(func)
    ast_compile_func(node)
    # check rewrite
    ast_rewrite_function(func, ast.NodeTransformer())
    # check non-decorated slipform
    print(slipform(func)([]))
    print(slipform()(func)([]))


def test_slipform_decorator():
    @slipform
    def func():
        pass
    assert isinstance(func, pf.Graph)

    @slipform()
    def func():
        pass
    assert isinstance(func, pf.Graph)


def test_slipform_assign():
    @slipform(debug=True)
    def func():
        a = pf.constant(1)
        b, c = pf.constant(2), pf.constant(3)
        d, e = [4, 5]
    a, b, c, d, e = func(['a', 'b', 'c', 'd', 'e'])
    assert (a, b, c, d, e) == (1, 2, 3, 4, 5)