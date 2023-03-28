# flake8: noqa
"""PyKMN is a Python library that allows you to use the [libpkmn](https://pkmn.cc/engine) library
to simulate Pokémon battles.

PyKMN has two main components: `pykmn.engine`, which can actually simulate battles,
and `pykmn.data`, which just repackages a bunch of data about Pokémon from the pkmn project.
You may want to check out the [examples](https://github.com/AnnikaCodes/PyKMN/tree/main/examples)
for real-world demonstrations of how to use PyKMN.

## Installation
PyKMN ~~is available~~ hasn't yet been released [on PyPI](https://pypi.org/project/pykmn/),
so you ~~can~~ will be able to install it with `pip`:
```bash
python3 -m pip install PyKMN
```

PyKMN is [open source](https://github.com/AnnikaCodes/PyKMN), so you can install the latest code from
GitHub, though this way you may get an untested, and possibly broken, version:
```bash
git clone https://github.com/AnnikaCodes/PyKMN.git
cd PyKMN
python3 -m pip install build cffi requests
python3 -m build
python3 -m pip install --find-links=dist pykmn
```

## Performance Considerations
PyKMN has been written to be relatively performant — certainly much faster than using Pokémon Showdown.
If the default performance isn't sufficient, the following tips can lead to significant speedups:
* Avoid calling methods on `pykmn.engine.gen1.Battle` if possible.
  These methods instantiate new classes for data access, which can be slow.
* Use an alternate build of libpkmn. The default build supports protocol logging and is compatible with Pokémon Showdown,
  but PyKMN ships with three other builds which you can pass to the `pykmn.engine.gen1.Battle` constructor.
  If you don't need to inspect battle protocol,
  choosing a build without protocol trace logging can be significantly faster.
  See `pykmn.engine.libpkmn` for more details.
* Consider switching to the [PyPy](https://www.pypy.org/) Python interpreter.
  PyKMN is fully compatible with PyPy, and PyKMN will run around 10 times faster when using PyPy.
  However, not all libraries support PyPy; if you're using [pytorch](https://github.com/pytorch/pytorch/issues/17835)
  or another incompatible library in your program alongside PyKMN, you may not be able to use PyPy.
* If you're still struggling with performance, [libpkmn bindings are available](https://github.com/pkmn/engine#usage)
  for other languages, such as JavaScript, C, Zig, and C++.
  Some of these may be faster, but you'll have to give up Python.

Lastly, if PyKMN isn't performant enough for you, you can reach out to me by
[opening an issue](https://github.com/AnnikaCodes/PyKMN/issues/new) and I can try to find a way
to improve PyKMN's performance for your use case.
"""