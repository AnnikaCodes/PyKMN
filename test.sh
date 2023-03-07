#!/usr/bin/env bash

ruff . && # lint
mypy . && # check types
python3 -m unittest discover tests # run unit tests
