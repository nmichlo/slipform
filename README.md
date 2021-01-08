# 🏗 slipform
[pythonflow](https://github.com/spotify/pythonflow) decorator for generating dataflow graphs from raw python.

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

1. Get started by importing slipfrom

```python3
from slipfrom import slipfrom
```

2. The most basic example is as follows: 

```python3
@slipfrom
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

