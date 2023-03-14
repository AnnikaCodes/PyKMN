"""Sets up the build of the PyKMN package."""
from setuptools import setup

setup(
    cffi_modules=[
        "build_bindings.py:libpkmn_showdown_trace",
        "build_bindings.py:libpkmn_showdown_no_trace",
        "build_bindings.py:libpkmn_trace",
        "build_bindings.py:libpkmn_no_trace",
    ],
    packages=["pykmn.engine", "pykmn.data"],
    include_package_data=True,
)
