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
version_file="$TEMP_DIR"/discotool/__init__.py

rm -rf "$TEMP_DIR"/build/
rm -rf "$TEMP_DIR"/dist/

#temp_file=`mktemp`
#cp "$version_file" "$temp_file"

python3 "$REPO_DIR"/tools/build_help.py update
python3 -m build
python3 -m twine upload --username __token__ -- dist/*

#cp "$temp_file" "$version_file"
