"""
# Slipform
pythonflow decorator for generating dataflow graphs using natural syntax.
https://github.com/nmichlo/slipform
"""

__version__ = "0.0.1-alpha1"


from pythonflow import Graph as _Graph
from pythonflow import constant as _constant
from slipform._ast_utils import ast_rewrite_function as _ast_rewrite_function, ast_decompile_func, ast_compile_func
from slipform._translate import SlipformTransformer as _SlipformTransformer


ORIG_FN_NAME = '_orig_fn'


def slipform(*args, node_transformer=None, add_scope=None, debug=False, **kwargs):
    assert 0 <= len(args) <= 1, 'no args are supported yet'
    assert not kwargs, 'no kwargs are supported yet'

    def _slipform_wrapper(func) -> _Graph:
        # transform the function into its pythonflow equivalent
        transformer = node_transformer if node_transformer is not None else _SlipformTransformer()
        graph_generator = _ast_rewrite_function(func, node_transformer=transformer, add_scope=add_scope, debug=debug)
        # generate the dataflow graph using the transformed function
        with _Graph() as graph:
            graph_generator()
            # make sure we can access the original function
            # insert the function both as an operation on the graph
            assert ORIG_FN_NAME not in graph.operations, f'{ORIG_FN_NAME} operation is reserved'
            _constant(func, name=ORIG_FN_NAME)
            # insert the function both as an attribute of the graph
            assert not hasattr(graph, ORIG_FN_NAME), f'{ORIG_FN_NAME} attribute is reserved'
            setattr(graph, ORIG_FN_NAME, func)
        return graph

    if args:
        return _slipform_wrapper(args[0])
    else:
        return _slipform_wrapper

