#!/usr/bin/env bash
python3 -m build
pip3 install dist/pykmn-0.0.1-*.whl --force-reinstall
