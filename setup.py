"""Sets up the build of the pykmn package."""
from setuptools import setup

# Sadly, it doesn't seem possible to express this in pyproject.toml.
setup(
    cffi_modules=["build_bindings.py:ffibuilder"],
    packages=["pykmn.engine", "pykmn.data"],
    include_package_data=True
)
