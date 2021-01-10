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
- [ ] naming from assignments
- [ ] placeholders from args
- [ ] constant support
- [ ] functions to operations
- [ ] import support
- [ ] custom operation support

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
```

2. The most basic example is as follows: 

```python3
@slipform
def add_graph():
  a = 4
  b = 38
  x = a + b
```

With the equivalent pythonflow version:
```python3
with pf.Graph() as add_graph:
    a = pf.constant(4)
    b = pf.constant(38)
    x = a + b
```

We can evaluate the graph like usual using pythonflow:


```python3
add_graph('x')
>>> 42
```

