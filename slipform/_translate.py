import ast
from astmonkey.transformers import ParentChildNodeTransformer
from slipform._ast_utils import ast_dfs_walk


# ========================================================================= #
# ast.Assign Name Retrieval                                                 #
# ========================================================================= #


def _get_assign_target_names_recursive(assign_node: ast.Assign):
    # get the names to be assigned to
    assert len(assign_node.targets) == 1, 'This should never happen'  # tuples are tuples here
    targets = assign_node.targets[0]
    # recursive handler
    def recurse(targets):
        # handle multiple assignment
        if isinstance(targets, ast.Name):
            names = targets.id
        elif isinstance(targets, (ast.Tuple, ast.List)):
            names = tuple(recurse(name) for name in targets.elts)
        else:
            raise TypeError(f'Unsupported assignment target: {targets}')
        # return ordered list of names
        return names
    return recurse(targets)


def _get_assign_target_names_flat(assign_node: ast.Assign):
    # visiting nodes with ast.walk does not return them in the right order
    return tuple([node.id for node in ast_dfs_walk(assign_node) if isinstance(node, ast.Name)])


def get_assign_target_names(assign_node: ast.Assign, flat=True):
    if flat:
        return _get_assign_target_names_flat(assign_node)
    else:
        return _get_assign_target_names_recursive(assign_node)


# ========================================================================= #
# Ast Walks                                                                 #
# ========================================================================= #


def walk_parents(node, include_self=False):
    if include_self:
        yield node
    while True:
        if not hasattr(node, 'parent'):
            raise AttributeError('node not visited by astmonkey.ParentChildNodeTransformer')
        if node.parent is None:
            break
        node = node.parent
        yield node


def walk_calls(node, include_self=True):
    if include_self:
        yield node
    run = True
    while run:
        if isinstance(node, (ast.Attribute, ast.Subscript)):
            node = node.value
        elif isinstance(node, (ast.Call)):
            node = node.func
        elif isinstance(node, (ast.Name, ast.Constant)):
            run = False
        else:
            raise TypeError(f'Unsupported node type: {node} ({type(node)}). Probably not a set of function calls or attributes.')
        yield node


def get_root_call(node):
    root_node = None
    for root_node in walk_calls(node):
        pass
    return root_node


# ========================================================================= #
# Transform                                                                 #
# ========================================================================= #


class SlipformTransformer(ast.NodeTransformer):

    def visit(self, node):
        node = ParentChildNodeTransformer().visit(node)
        node = SlipformConstants().visit(node)     # pf.constant
        node = SlipformSetNames().visit(node)      # a.set_name('a')
        node = SlipformPlaceholders().visit(node)  # def func(a) ->  def func(): pl.placeholder('a')
        node = SlipformIn().visit(node)
        node = SlipformCondition().visit(node)
        return node


# ========================================================================= #
# END                                                                       #
# ========================================================================= #


class SlipformSetNames(ast.NodeTransformer):
    """
    Append set_name functions to all assignments.
    Assignments that start with an underscore are ignored.

    from:
        a, _b = 1, 2
    to:
        a, _b = 1, 2
        a.set_name('a')
    """

    def visit_Assign(self, node):
        return [
            node,
            *self.make_set_name_nodes(node)
        ]

    @classmethod
    def make_set_name_node(cls, name):
        assert str.isidentifier(name), f'{name=} is not a valid python identifier.'
        # make the ast node for setting the name
        set_name_node = ast.parse(f"{name}.set_name('{name}')").body[0]
        return set_name_node

    @classmethod
    def make_set_name_nodes(cls, node: ast.Assign, skip_underscores=True):
        assert len(node.targets) == 1, 'This should never happen!'
        # make all the nodes for the assign statement
        names = get_assign_target_names(node.targets[0])
        if skip_underscores:
            names = (name for name in names if not name.startswith('_'))
        nodes = [cls.make_set_name_node(name) for i, name in enumerate(names)]
        return nodes


class SlipformConstants(ast.NodeTransformer):
    """
    Replace constants ``value`` with a call
    to ``pl.constant(value)``

    from:
        value
    to:
        pl.constant(value)
    """

    def visit_Constant(self, node):
        if not self.constant_needs_wrapper(node):
            return node
        # wrap the actual constant
        # node -> pf.constant(node)
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='pf', ctx=ast.Load()),
                attr='constant',
                ctx=ast.Load(),
            ),
            args=[node],
            keywords=[],
        )

    @classmethod
    def constant_needs_wrapper(cls, node):
        """
        check if we can skip the node based on the call tree.
        eg. we can skip ``pf.constant(5)`` so it doesn't
        become ``pf.constant(pf.constant(5))``
        TODO: the rules for this need to be fleshed out.
        """
        try:
            root_call = get_root_call(node.parent)
        except:
            return True
        if isinstance(root_call, ast.Name):
            if root_call.id == 'pf':
                return False
        return True


class SlipformPlaceholders(ast.NodeTransformer):
    """
    from:
        def func(a):
    to:
        def func():
            a = pl.placeholder('a')
    """

    def visit_FunctionDef(self, node):
        assert not node.args.posonlyargs, f'FunctionDef.args.posonlyargs is not yet supported: {node.args.posonlyargs}'
        assert not node.args.vararg,      f'FunctionDef.args.vararg is not yet supported: {node.args.vararg}'
        assert not node.args.kwonlyargs,  f'FunctionDef.args.kwonlyargs is not yet supported: {node.args.kwonlyargs}'
        assert not node.args.kw_defaults, f'FunctionDef.args.kw_defaults is not yet supported: {node.args.kw_defaults}'
        assert not node.args.kwarg,       f'FunctionDef.args.kwarg is not yet supported: {node.args.kwarg}'
        assert not node.args.defaults,    f'FunctionDef.args.defaults is not yet supported: {node.args.defaults}'
        # convert arguments to placeholders
        # at the start of the function
        for arg in node.args.args[::-1]:
            assert str.isidentifier(arg.arg)
            placeholder = ast.parse(f"{arg.arg} = pf.placeholder('{arg.arg}')").body[0]
            node.body.insert(0, placeholder)
        # clear the arguments from the function definition
        node.args.args.clear()
        return node


class SlipformIn(ast.NodeTransformer):

    def visit_Compare(self, node):
        # basic checks
        if len(node.comparators) != 1 or len(node.ops) != 1:
            print('WARNING: skipped in node, this is a bug, better checks are needed!')
            return
        if not isinstance(node.ops[0], ast.In):
            return
        # wrap the in comparator
        # a in B -> pf.contains(B, a)
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='pf', ctx=ast.Load()),
                attr='contains',
                ctx=ast.Load(),
            ),
            args=[
                node.comparators[0],  # right
                node.left,            # left
            ],
            keywords=[],
        )


class SlipformCondition(ast.NodeTransformer):

    def visit_IfExp(self, node):
        # wrap an if expression (not if statement)
        # left if condition else right -> pf.conditional(condition, left, right)
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='pf', ctx=ast.Load()),
                attr='conditional',
                ctx=ast.Load(),
            ),
            args=[
                node.test,   # condition
                node.body,   # left
                node.orelse, # right
            ],
            keywords=[],
        )

    @classmethod
    def ast_make_import_assign(cls, alias):
        name = alias.name
        asname = alias.asname if (alias.asname is not None) else name.split('.')[0]
        assert str.isidentifier(asname), 'This should never happen...'
        import_node = ast.parse(f"{asname} = pf.import_('{name}')").body[0]
        return import_node

    @classmethod
    def ast_make_import_from_assign(cls, node, alias):
        # modify alias to be compatible
        if alias.asname is None:
            alias.asname = alias.name
        alias.name, name = node.module, alias.name
        # place attribute after assign
        # {asname} = pf.import_('{node.module}').{alias.name}
        assign_node = cls.ast_make_import_assign(alias)
        assign_node.value = ast.Attribute(
            value=assign_node.value,
            attr=name,
            ctx=ast.Load(),
        )
        return assign_node

    def visit_Import(self, node):
        return [self.ast_make_import_assign(alias) for alias in node.names]

    def visit_ImportFrom(self, node):
        return [self.ast_make_import_from_assign(node, alias) for alias in node.names]

if __name__ == '__main__':
    from slipform import slipform
    import pythonflow as pf




    # @slipform(debug=True)
    # def vae(b, x):
    #     # pf.constant(1)
    #     # a = pf.constant("")
    #     a = 1
    #
    #     # b = 2
    #     c = a + b + 1
    #     d, ((g,), f) = 1, ((3,), 2)
    #
    #
    # print(vae(['b', 'c', 'd', 'g', 'f'], b=10))
    #
    # astpretty.pprint(ast.parse('1 if condition else 2'))



