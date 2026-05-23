#!/bin/bash
# SPDX-FileCopyrightText: Copyright 2026 Neradoc, https://neradoc.me
# SPDX-License-Identifier: MIT

if [[ -z `command -v python3` ]]; then
	alias python3=python
fi

gitversion=`git describe --always --dirty`
if [[ "$gitversion" == *"dirty"* ]]; then
	echo "ERROR: git is dirty"
	exit 1
fi


python3 tools/build_help.py update
# python3 setup.py sdist
python3 -m build
python3 -m twine upload --username __token__ -- dist/*
