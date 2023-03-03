# PYkmn
[![Cross-Platform Build](https://github.com/AnnikaCodes/pykmn/actions/workflows/cross-platform-build.yml/badge.svg)](https://github.com/AnnikaCodes/pykmn/actions/workflows/cross-platform-build.yml)
[![Lint & Test](https://github.com/AnnikaCodes/pykmn/actions/workflows/test.yml/badge.svg)](https://github.com/AnnikaCodes/pykmn/actions/workflows/test.yml)

Python bindings for [libpkmn](https://github.com/pkmn/engine).

## Development
First, install dependencies:
```bash
python3 -m pip install flake8 mypy flake8-docstrings build coverage cffi requests types-cffi types-requests types-setuptools
```

Then, you can build with `python3 -m build`.

You can lint and test with
```bash
flake8 . # lint
mypy . # check types
python3 -m unittest discover tests # run unit tests
```