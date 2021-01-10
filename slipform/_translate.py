import ast
from astmonkey.transformers import ParentChildNodeTransformer


# ========================================================================= #
# ast.Assign Name Retrieval                                                 #
# ========================================================================= #
from slipform._ast_utils import ast_dfs_walk


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


def get_assign_target_names(assign_node: ast.Assign):
    return tuple([node.id for node in ast_dfs_walk(assign_node) if isinstance(node, ast.Name)])

def _get_assign_target_names_flat(assign_node: ast.Assign):
    names = []
    # visiting nodes with ast.walk does not return them in the right order
    class Visitor(ast.NodeVisitor):
        def visit_Name(self, node):
            names.append(node.id)
    Visitor().visit(assign_node)
    return tuple(names)


def get_assign_target_names(assign_node: ast.Assign, flat=True):
    if flat:
        return _get_assign_target_names_flat(assign_node)
    else:
        return _get_assign_target_names_recursive(assign_node)


# ========================================================================= #
# pythonflow ast                                                            #
# ========================================================================= #


def pf_ast_make_set_name_node(name):
    assert str.isidentifier(name), f'{name=} is not a valid python identifier.'
    # make the ast node for setting the name
    set_name_node = ast.parse(f"{name}.set_name('{name}')")
    return set_name_node


def pf_ast_make_set_name_nodes(node: ast.Assign, skip_underscores=True):
    assert len(node.targets) == 1, 'This should never happen!'
    # make all the nodes for the assign statement
    names = get_assign_target_names(node.targets[0], flat=True)
    if skip_underscores:
        names = (name for name in names if not name.startswith('_'))
    nodes = [pf_ast_make_set_name_node(name) for name in names]
    return nodes


def pf_ast_wrap_constant():
    pass






class SlipformNodeVisitor(ast.NodeVisitor):

    def visit(self, node, parent=None, parent_field=None, parent_idx=None):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        for field, value in ast.iter_fields(node):
            if isinstance(value, ast.AST):
                self._visit_attr(node=value, parent=node, parent_field=field)
            elif isinstance(value, list):
                self._visit_items(items=value, parent=node, parent_field=field)

    def _visit_items(self, items, parent, parent_field):
        for i, item in enumerate(items):
            if isinstance(item, ast.AST):
                self._visit_item(node=item, parent=parent, parent_field=parent_field, parent_idx=i)

    _visit_attr = visit
    _visit_item = visit


class SlipformNodeTransformer(SlipformNodeVisitor):

    def _visit_items(self, items, parent, parent_field):
        # logic taken from ast.NodeTransformer
        new_items = []
        for i, item in enumerate(items):
            if isinstance(item, ast.AST):
                item = self._visit_item(node=item, parent=parent, parent_field=parent_field, parent_idx=i)
                if item is None:
                    continue
                elif not isinstance(item, ast.AST):
                    new_items.extend(item)
                    continue
            new_items.append(item)
        items[:] = new_items

    def _visit_attr(self, node, parent, parent_field):
        # logic taken from ast.NodeTransformer
        new_node = self.visit(node, parent=parent, parent_field=parent_field, parent_idx=None)
        if new_node is None:
            delattr(parent, parent_field)
        else:
            setattr(parent, parent_field, new_node)



# ========================================================================= #
# Transform                                                                 #
# ========================================================================= #

class SlipformTransformer(ast.NodeTransformer):

    def visit(self, node):
        node = ParentChildNodeTransformer().visit(node)
        node = SlipformSetNames().visit(node)
        node = SlipformConstants().visit(node)
        return node

# ========================================================================= #
# END                                                                       #
# ========================================================================= #


class SlipformSetNames(ast.NodeTransformer):
    def visit_Assign(self, node):
        return [
            node,
            pf_ast_make_set_name_nodes(node)
        ]


class SlipformConstants(ast.NodeTransformer):
    def visit_Constant(self, node, parent=None, parent_field=None, parent_index=None):
        return ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id='pf', ctx=ast.Load()),
                    attr='constant',
                    ctx=ast.Load(),
                ),
                args=[node],
                keywords=[],
            )





if __name__ == '__main__':
    from slipform import slipform
    import pythonflow as pf

    @slipform(node_transformer=SlipformTranslator(), debug=True)
    def vae():
        pf.constant(1)
        a = pf.constant("")
        a = 1
        b = 2
        c = a + b + 1
        d, ((g,), f) = 1, ((3,), 2)

    print(vae(['b', 'c', 'd', 'g', 'f']))


