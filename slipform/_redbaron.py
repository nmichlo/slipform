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
        try:
            self.new_red = slipform_translate(rb.RedBaron(self.orig_source))  # makes a copy
            self.new_source = self.new_red.dumps()
            self.new_func = redbaron_recompile_func(self.new_red)
        except Exception as e:
            raise RuntimeError(f'Error translating function: {self.orig_func}\n{"="*80}\n{self.orig_source}\n{"="*80}')
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

    def __init__(self, node, skip_types):
        self._stack = deque(node.root if isinstance(node, rb.RedBaron) else [node])
        self._visit_children = True
        self._prev = None
        self._skip_node_types = () if (skip_types is None) else tuple(skip_types)

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
                if not isinstance(v, rb.Node):
                    continue
                if isinstance(v, self._skip_node_types):
                    continue
                self._stack.append(v)
        except (TypeError, AttributeError):
            pass

    def skip_children(self):
        self._visit_children = False


def node_iter(node, skip_types=(rb.EndlNode, str)):
    return _NodeIter(node, skip_types=skip_types)


# ========================================================================= #
# Translation                                                               #
# ========================================================================= #


class NodeTransformer(object):

    def __init__(self):
        self._skip_next = False

    def transform(self, root):
        self.reset()
        # begin
        it = node_iter(root)
        for node in it:
            # if we marked the next node to be skipped
            # skip it by stopping the iterator from traversing its children
            # and not visiting the current node otherwise
            if self._skip_next:
                self._skip_next = False
                it.skip_children()
                continue
            # get the nodes name
            assert isinstance(node, rb.Node), f'node is not an instance of Node: {node} ({type(node)})'
            func = getattr(self, f'visit_{node.__class__.__name__}', None)
            # visit the node if possible
            if func is not None:
                try:
                    visit_children = func(node)
                except Exception as e:
                    print(f'Failed to translate node: {node} Encountered error: {e}')
                    visit_children = False
                # skip if needed
                if visit_children is False:
                    it.skip_children()
        return root

    def skip_next(self):
        self._skip_next = True

    def reset(self):
        pass


# ========================================================================= #
# Translation                                                               #
# ========================================================================= #


SCOPE_ARG = 'ARG'
SCOPE_VAR = 'VAR'
SCOPE_WRAPPED = 'WRAPPED'


class SlipformTranslate(NodeTransformer):

    def __init__(self):
        super().__init__()
        # initialise the scope from the arguments
        # we will use this to keep track of types
        self.scope_required = set()
        self.scope_available = {}

    def visit_DefNode(self, node):
        # add the input arguments to the scope!
        for arg in node.arguments:
            self.scope_available[arg.namenode.value] = SCOPE_ARG

    def visit_AssignmentNode(self, node):
        # >>> ASSIGNMENT ``a = b``
        # add set_name after names in assigment nodes
        for name in node.target.find_all('name')[::-1]:
            # skip ``_name``
            if name.value.startswith('_'):
                continue
            # do not allow ``name.key`` and ``name[key]``
            if isinstance(name.parent, rb.AtomtrailersNode):
                continue
            node.insert_after(f"{name.value}.set_name('{name.value}')")

    def visit_CommentNode(self, node):
        # >>> COMMENT: ``# comment``
        # check if this is a directive
        # ``# []`` and ``#[]`` are valid directives
        comment = node.value[1:].strip()
        if comment == '[ignore]':
            self.skip_next()


def slipform_translate(red: rb.RedBaron):
    # assert len(red.root) == 1
    # root = red.root[0]
    # assert isinstance(root, rb.DefNode), f'{root=} ({type(root)}) is not an instance of {rb.DefNode}'
    # transform the node
    red.help(2)
    SlipformTranslate().transform(red)
    return red


# ========================================================================= #
# Tests                                                                     #
# ========================================================================= #

if __name__ == '__main__':


    @slipform(debug=True)
    def test_func(x):
        (A, (_B, C, x[1], x.a)) = (1, [2, 3, 4, 5])  # [ignore]
        a = 5
        # [ignore]
        b = 32
        z = a + b + x + 1

        q = a if z else b

        # [ignore]
        if a == b:
            print(a)
            Q = a + b

        loop_var = 0
        for i in range(a):
            loop_var += i
            loop_var_2 = i

            if i == 10:
                i = i + 1
                break
            else:
                return i + i

        return i

        return i
