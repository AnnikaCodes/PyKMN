#!/usr/bin/env bash

ruff . && # lint
mypy . && # check types
pushd pykmn
pypy -m unittest discover ../tests # run unit tests
popd
