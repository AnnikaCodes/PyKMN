#!/usr/bin/env bash

flake8 . # lint
mypy . # check types
python3 -m unittest discover tests # run unit tests
