#!/bin/bash

THIS_FILE=`realpath "$0"`
temp=`dirname "$THIS_FILE"`
THIS_DIR=`dirname "$temp"`
version_file="$THIS_DIR"/discotool/__init__.py

cd "$THIS_DIR"

rm -rf "$THIS_DIR"/build/
rm -rf "$THIS_DIR"/dist/

temp_file=`mktemp`
cp "$version_file" "$temp_file"

python3 .building/build_help.py update
python3 -m build
python3 -m twine upload dist/*

cp "$temp_file" "$version_file"
