#!/usr/bin/env bash

ruff . && # lint
mypy . && # check types
pypy -m unittest discover tests # run unit tests

