from setuptools import setup

# Sadly, it doesn't seem possible to express this in pyproject.toml.
setup(cffi_modules=["build.py:ffibuilder"])