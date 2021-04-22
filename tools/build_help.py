import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


DIR = Path(__file__).parent.parent
original_path = DIR / "discotool" / "__init__.py"


def get_current_version(path):
	procs = subprocess.run([
			"git",
			"describe",
			"--tags",
			"--exact-match",
		],
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		cwd=path,
	)
	if procs.returncode != 0:
		return None
	return procs.stdout.decode("utf8").strip()


def update_version_number(original_file, temp_file, current_version):
	with open(original_path, "rb") as original_file:
		for line in original_file:
			line = line.decode("utf-8")
			if line.startswith("__version__"):
				line = line.replace("0.0.0-auto.0", current_version)
			temp_file.write(line.encode("utf-8"))
	temp_file.flush()


def change_version_info():
	current_version = get_current_version(DIR)
	if current_version:
		# create the temp
		with tempfile.NamedTemporaryFile() as temp_file:
			update_version_number(original_path, temp_file, get_current_version(DIR))
			print(temp_file.name)
			# replace the file with the temp
			shutil.copyfile(temp_file.name, original_path)
	else:
		v = subprocess.check_output(["git","describe","--tags"]).decode('utf8').strip()
		print(f"Not a tag: {v} don't upload to pypi")


def temporary_change_version():
	current_version = get_current_version(DIR)
	temporary_save = DIR / "_temp_backup_file.py"
	# print(current_version)
	if current_version:
		# save the current file
		shutil.copyfile(original_path, temporary_save)
		# create the temp
		change_version_info()
		# do a thing
		pass
		# then restore the file
		shutil.copyfile(temporary_save, original_path)
		os.remove(temporary_save)
	else:
		v = subprocess.check_output(["git","describe","--tags"]).decode('utf8').strip()
		print(f"Not a tag: {v} don't upload to pypi")

if __name__ == "__main__":
	print(DIR)
	print(original_path)
	print(get_current_version(DIR))
	print(sys.argv)
	if len(sys.argv) > 1 and sys.argv[1] == "update":
		change_version_info()
