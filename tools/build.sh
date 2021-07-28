#!/bin/bash

if [[ -z `command -v python3` ]]; then
	alias python3=python
fi

gitversion=`git describe --always --dirty`
if [[ "$gitversion" == *"dirty"* ]]; then
	echo "ERROR: git is dirty"
	exit 1
fi

python3 setup.py sdist
python3 -m twine upload --username __token__ dist/*
