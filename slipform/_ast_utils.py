import ast
import inspect


def _assert_single_func(ast_module: ast.Module) -> ast.FunctionDef:
    assert isinstance(ast_module, ast.Module)
    assert len(ast_module.body) == 1
    assert isinstance(ast_module.body[0], ast.FunctionDef)
    return ast_module.body[0]


def _ast_parse_func(func) -> ast.Module:
    source = inspect.getsource(func)
    ast_module = ast.parse(source)
    _assert_single_func(ast_module)
    return ast_module


def _ast_compile_func(ast_module, scope=None):
    if scope is None:
        scope = {}
    # Compile the new method in the old methods scope. If we don't change the
    # name, this actually overrides the old function with the new one
    code = compile(ast_module, '<string>', 'exec')
    exec(code, scope)
    # return the actual function
    out_func = _assert_single_func(ast_module)
    return scope[out_func.name]


def rewrite_function(func, node_transformer: ast.NodeTransformer, scope=None):
    if scope is None:
        scope = func.__globals__
    # generate AST for function
    in_node = _ast_parse_func(func)
    # manipulate AST
    out_node = node_transformer.visit(in_node)
    # compile and return the function
    return _ast_compile_func(out_node, scope)
