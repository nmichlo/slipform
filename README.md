
---------------

**NB!** This project is unmaintained. It was started as a way to learn more about the python AST.

---------------
---------------
---------------

# 🏗 slipform &nbsp; ![](https://badge.fury.io/py/slipform.svg)
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
- [x] import support
- [ ] custom operation support
- [ ] ignore comments `#[ignore]` or `#[slipform:ignore]`

**Investigate**
- [ ] module / import detection from function scope
- [ ] sequences (map, list, tuple, zip, sum, filter)
- [ ] for loop replacement?
- [x] conditional expression replacement?
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

3. A more complicated example

```python3
@slipfrom()
def vae(x, x_target, encoder, decoder, mse):
    # import ... from ... (as ...) are all supported
    import torch
    import torch.nn.functional as F
    # get the encoding!
    z_params = encoder(x)
    # deterministic, we dont reparameterize here
    z = z_params.z_mean
    # reconstruct here
    x_pre_recon = decoder(z)
    # final activation
    x_recon = x_pre_recon if mse else torch.sigmoid(x_pre_recon)
    # compute loss
    loss = F.mse_loss(x_recon, x_target) if mse else F.binary_cross_entropy_with_logits(x_pre_recon, x_target)
```

The above will generate code equivalent in functionality to:

```python3
with pf.Graph() as add_graph:
    x        = pf.placeholder('x')
    x_target = pf.placeholder('x_target')
    encoder  = pf.placeholder('encoder')
    decoder  = pf.placeholder('decoder')
    mse      = pf.placeholder('mse')
    # import everything
    torch = pf.import_('torch')
    F = pf.import_('torch.nn.functional')
    # get the encoding!
    z_params = encoder(x)
    z_params.set_name('z_params')
    # deterministic, we dont reparameterize here
    z = z_params.z_mean
    z.set_name('z')
    # reconstruct here
    x_pre_recon = decoder(z)
    x_pre_recon.set_name('x_pre_recon')
    # final activation
    x_recon = pf.conditional(mse, x_pre_recon, torch.sigmoid(x_pre_recon))
    x_recon.set_name('x_recon')
    # compute loss
    loss = pf.conditional(mse, F.mse_loss(x_recon, x_target), F.binary_cross_entropy_with_logits(x_pre_recon, x_target))
    loss.set_name('loss')
```
