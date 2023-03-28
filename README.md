# PyKMN
[![Cross-Platform Build](https://github.com/AnnikaCodes/PyKMN/actions/workflows/cross-platform-build.yml/badge.svg)](https://github.com/AnnikaCodes/PyKMN/actions/workflows/cross-platform-build.yml)
[![Lint & Test](https://github.com/AnnikaCodes/PyKMN/actions/workflows/test.yml/badge.svg)](https://github.com/AnnikaCodes/PyKMN/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/AnnikaCodes/PyKMN/branch/main/graph/badge.svg?token=604F57HO3O)](https://codecov.io/gh/AnnikaCodes/PyKMN)

Python bindings for [libpkmn](https://github.com/pkmn/engine).

For usage information, check out [the documentation](https://annikacodes.github.io/PyKMN/latest/) or [the examples](https://github.com/AnnikaCodes/PyKMN/tree/main/examples).

## Development
First, install dependencies:
```bash
python3 -m pip install ruff mypy build coverage cffi requests types-cffi types-requests types-setuptools
```

Then, you can build and install PyKMN:
```bash
python3 -m build 
python3 -m pip install --find-links=dist pykmn
```

Alternatively, a shell script is provided to make this simpler — just run `./build.sh python3` once you've installed dependencies.

You can lint and test with
```bash
ruff check . # lint
mypy . # check types
python3 -m unittest discover tests # run unit tests
```
