# 🏗 slipform
[pythonflow](https://github.com/spotify/pythonflow) decorator for generating dataflow graphs from raw python.

## Why?

- Syntax is natural, you can use a simple decorator to obtain the dataflow graph. No need to rewrite your code for pythonflow.

- Slipform allows you to write and test code as you normally would, debugging it using the debugger of your choice during runtime. When you are happy with your code, finally, at runtime you can generate the dataflow graph.

## Disclaimer

Slipform was born out of a desire to learn more about the python AST, and potentially use it for my own personal projects if it works out.

It is not actively developed, nor should it be considered stable.

## Roadmap

**Priority**
- [x] naming from assignments
- [x] placeholders from args
- [x] constant support
- [ ] functions to operations
- [ ] import support
- [ ] custom operation support
- [ ] ignore comments `#[ignore]` or `#[slipform:ignore]`

**Investigate**
- [ ] module / import detection from function scope
- [ ] sequences (map, list, tuple, zip, sum, filter)
- [ ] for loop replacement?
- [ ] conditionals replacement?
- [ ] assertion replacement?
- [ ] try/catch replacement?
- [ ] explicit dependencies?

## Examples based on [Using Pythonflow](https://pythonflow.readthedocs.io/en/latest/guide.html)

1. Get started by importing slipform

```python3
from slipform import slipform
# "pf" must be part of scope of any @slipfrom annotated
# function. This limitation will be relaxed in future.
import pythonflow as pf
```

2. A simple example is as follows: 

```python3
@slipform
def add_graph(x):
  a = 5
  b = 32
  z = a + b + x
```

With the equivalent pythonflow version:
```python3
with pf.Graph() as add_graph:
    x = pf.placeholder('x')
    a = pf.constant(5, name='a')
    b = pf.constant(32, name='b')
    z = (a + b + x).set_name('z')
```

We can evaluate the graphs like usual using pythonflow:
```python3
add_graph(['b', 'z'], x=5)
>>> (32, 42)
```
