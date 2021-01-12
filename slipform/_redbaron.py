from collections import deque
import redbaron as rb
from uuid import uuid4
from slipform._ast_utils import inspect_get_source
import pythonflow as pf


# ========================================================================= #
# RedBaron Helper                                                           #
# ========================================================================= #


def redbaron_decompile_func(func):
    source = inspect_get_source(func, unindent=True, strip_decorators=False)
    red = rb.RedBaron(source)
    return red


def redbaron_recompile_func(red: rb.RedBaron):
    # replace the function name
    defnode = red.defnode
    # update the node
    name = f'_slipform_{str(uuid4())[:8]}'
    old_name, defnode.name = defnode.name, name
    old_decs, defnode.decorators = defnode.decorators, []
    # compile the function
    exec(red.dumps())
    # restore the node
    defnode.name = old_name
    defnode.decorators = old_decs
    # return the function
    return locals()[name]


# ========================================================================= #
# Slipform Decorator                                                        #
# ========================================================================= #


class Slipform(object):

    def __init__(self, func, debug=False):
        # original data
        self.orig_func = func
        self.orig_source = self._get_source(self.orig_func)
        self.orig_red = rb.RedBaron(self.orig_source)
        # transpiled data
        self.new_red = slipform_translate(rb.RedBaron(self.orig_source))  # makes a copy
        self.new_source = self.new_red.dumps()
        self.new_func = redbaron_recompile_func(self.new_red)
        # debugging
        if debug:
            print(self.new_source)

    @staticmethod
    def _get_source(func):
        return inspect_get_source(func, unindent=True, strip_decorators=False)

    def __call__(self, *args, **kwargs):
        with pf.Graph() as graph:
            self.new_func(*args, **kwargs)
        return graph


def slipform(fn=None, debug=False):
    def wrapper(func):
        return Slipform(func, debug=debug)
    return wrapper if (fn is None) else wrapper(fn)


# ========================================================================= #
# Node Iterator                                                             #
# ========================================================================= #


class _NodeIter(object):
    """
    Node iterator that supports skipping the nodes children
    as well as skipping certain types of nodes.
    """

    def __init__(self, node, skip_types=(rb.EndlNode, str)):
        self._stack = deque([node])
        self._visit_children = True
        self._prev = None
        self._skip_node_types = None if (skip_types is None) else tuple(skip_types)

    def __iter__(self):
        return self

    def __next__(self):
        # try extend the stack
        if self._prev is not None:
            if self._visit_children:
                self._try_extend_stack(self._prev)
                self._visit_children = True
        # we have run out of things
        if not self._stack:
            raise StopIteration
        # get the next item
        self._prev = self._stack.pop()
        return self._prev

    def _try_extend_stack(self, node):
        try:
            for v in reversed(node.value):
                if not isinstance(v, self._skip_node_types):
                    self._stack.append(v)
        except (TypeError, AttributeError):
            pass

    def skip_children(self):
        self._visit_children = False


def node_iter(node, skip_types=None):
    return _NodeIter(node, skip_types=skip_types)


# ========================================================================= #
# Translation                                                               #
# ========================================================================= #


SCOPE_ARG = 'ARG'
SCOPE_VAR = 'VAR'
SCOPE_WRAPPED = 'WRAPPED'


def slipform_translate(red: rb.RedBaron):
    root = red.root[0]
    assert len(red.root) == 1
    assert isinstance(root, rb.DefNode), f'{root=} ({type(root)}) is not an instance of {rb.DefNode}'

    # initialise the scope from the arguments
    # we will use this to keep track of types
    scope_required = set()
    scope_available = {}
    for arg in root.arguments:
        scope_available[arg.namenode.value] = SCOPE_ARG

    # process each line one at a time
    # update the available scope if an assignment takes place
    # update the required scope if a variable is accessed
    it = node_iter(node=root, skip_types=(rb.EndlNode, str))
    for node in it:
        try:
            # >>> ASSIGNMENT ``a = b``
            if isinstance(node, rb.AssignmentNode):
                # add set_name after names in assigment nodes
                names = [n.value for n in node.target.find_all('name') if not n.value.startswith('_')]
                for name in names[::-1]:
                    node.insert_after(f"{name}.set_name('{name}')")

            # >>> COMMENT: ``# comment``
            elif isinstance(node, rb.CommentNode):
                it.skip_children()
                # check if this is a directive
                # ``# []`` and ``#[]`` are valid directives
                comment = node.value[1:].strip()
                if comment == '[ignore]':
                    next(it)

        except Exception as e:
            print(f'Failed to translate node: {node} Encountered error: {e}')

    return red


# ========================================================================= #
# Tests                                                                     #
# ========================================================================= #

if __name__ == '__main__':

    @slipform(debug=True)
    def test_func(x):
        (A, (_B, C)) = (1, [2, 3])
        a = 5
        b = 32
        z = a + b + x + 1

        q = a if z else b

        # [ignore]
        if a == b:
            print(a)
            a + b

        loop_var = 0
        for i in range(a):
            loop_var += i
            loop_var_2 = i

            if i == 10:
                i = i + 1
                break
            else:
                return i

        return i
