#!/usr/bin/env bash

if [ -z "$1" ]; then
    echo "Usage: $0 <python interpreter>"
    exit 1
fi
$1 -m build
for x in `ls dist/*.whl`; do
    $1 -m pip install $x --force-reinstall
done
