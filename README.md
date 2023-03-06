# PYkmn
[![Cross-Platform Build](https://github.com/AnnikaCodes/pykmn/actions/workflows/cross-platform-build.yml/badge.svg)](https://github.com/AnnikaCodes/pykmn/actions/workflows/cross-platform-build.yml)
[![Lint & Test](https://github.com/AnnikaCodes/pykmn/actions/workflows/test.yml/badge.svg)](https://github.com/AnnikaCodes/pykmn/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/AnnikaCodes/pykmn/branch/main/graph/badge.svg?token=604F57HO3O)](https://codecov.io/gh/AnnikaCodes/pykmn)

Python bindings for [libpkmn](https://github.com/pkmn/engine).

## Development
First, install dependencies:
```bash
python3 -m pip install ruff mypy build coverage cffi requests types-cffi types-requests types-setuptools
```

Then, you can build with `python3 -m build`.

You can lint and test with
```bash
ruff check . # lint
mypy . # check types
python3 -m unittest discover tests # run unit tests
```