# SPDX-FileCopyrightText: Copyright 2026 Neradoc, https://neradoc.me
# SPDX-License-Identifier: MIT

THIS_FILE=`realpath "$0"`
FILE_DIR=`dirname "$THIS_FILE"`
REPO_DIR=`dirname "$FILE_DIR"`

echo THIS_FILE $THIS_FILE
echo temp $temp
echo REPO_DIR $REPO_DIR

temp_file=`mktemp`
TEMP_DIR="${temp_file}_dir"
mkdir "$TEMP_DIR"

open "$TEMP_DIR"
cd "$TEMP_DIR"

git clone "$REPO_DIR" "$TEMP_DIR"

rm -rf "$TEMP_DIR"/build/
rm -rf "$TEMP_DIR"/dist/

# temp_file=`mktemp`
# version_file="$TEMP_DIR"/discotool/__init__.py
# cp "$version_file" "$temp_file"

./tools/build.sh

#cp "$temp_file" "$version_file"
