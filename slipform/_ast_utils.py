import ast
import inspect
from typing import Optional


def ast_assert_single_func(ast_module: ast.Module) -> ast.FunctionDef:
    assert isinstance(ast_module, ast.Module)
    assert len(ast_module.body) == 1
    assert isinstance(ast_module.body[0], ast.FunctionDef)
    return ast_module.body[0]


def is_comment_line(line):
    line = line.strip()
    return not line or line.startswith('#')

def inspect_get_source(func, unindent=True, strip_decorators=True):
    lines, _ = inspect.getsourcelines(func)
    if unindent:
        indents = min(len(line) - len(line.lstrip()) for line in lines if not is_comment_line(line))
        # this is a bit hacky, should modify indents of comments
        lines = [line[indents:] for line in lines if not is_comment_line(line)]
    if strip_decorators:
        i = 0
        while lines[i].lstrip().startswith('@'):
            i += 1
        lines = lines[i:]
    return ''.join(lines)


def ast_decompile_func(func, unindent=True, strip_decorators=True) -> ast.Module:
    source = inspect_get_source(func, unindent=unindent, strip_decorators=strip_decorators)
    ast_module = ast.parse(source)
    ast_assert_single_func(ast_module)
    return ast_module


def ast_compile_func(ast_module, scope=None):
    if scope is None:
        scope = {}
    # Compile the new method in the old methods scope. If we don't change the
    # name, this actually overrides the old function with the new one
    try:
        code = compile(ast_module, '<string>', 'exec')
    except Exception as e:
        raise RuntimeError(f'Could not compile transformed node: {ast_module}')
    exec(code, scope)
    # return the actual function
    out_func = ast_assert_single_func(ast_module)
    return scope[out_func.name]


def ast_rewrite_function(func, node_transformer: Optional[ast.NodeTransformer], scope=None, add_scope=None, debug=False, unindent=True, strip_decorators=True):
    if scope is None:
        scope = func.__globals__
    if add_scope is not None:
        scope = scope.copy()
        scope.update(add_scope)
    # generate AST for function
    in_node = ast_decompile_func(func, unindent=unindent, strip_decorators=strip_decorators)
    # manipulate AST
    out_node = node_transformer.visit(in_node)
    ast.fix_missing_locations(out_node)
    if debug:
        import astunparse
        print('='*100, astunparse.unparse(out_node), '='*100, sep='\n')
    # compile and return the function
    return ast_compile_func(out_node, scope=scope)


def ast_dfs_walk(node):
    from collections import deque
    todo = deque([node])
    while todo:
        node = todo.pop()
        children = list(ast.iter_child_nodes(node))[::-1]
        todo.extend(children)
        yield node


