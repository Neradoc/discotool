import os
import re
import setuptools
import subprocess
import sys

here = os.path.abspath(os.path.dirname(__file__))

repository_name = "Neradoc/discotool"
current_tag = "main"

try:
    if shutil.which("git") is not None:
        current_tag = subprocess.run("git describe --tags --abbrev=0",
            capture_output = True,
            encoding = "utf-8",
            shell = True,
        ).stdout.strip()
except Exception:
    pass

with open(os.path.join(here,"README.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()

    long_description = re.sub(r'\(docs/(.*.png)\)',
        r'(https://raw.githubusercontent.com/' + repository_name
        + '/' + current_tag + r'/docs/\1)',
        long_description)
    long_description = re.sub(r'\(docs/(.*.md)\)',
        r'(https://github.com/' + repository_name
        + '/blob/' + current_tag+r'/docs/\1)',
        long_description)

required_modules = [
    "click >= 7.1.2",
    "click-aliases == 1.0.1",
    "psutil >= 5.8.0",
    "pyserial >= 3.4",
    "wmi;platform_system=='Windows'",
    "pywin32;platform_system=='Windows'",
    "pyudev;platform_system=='Linux'",
]

setuptools.setup(
    name="discotool",
    author="Neradoc",
    author_email="neraOnGit@ri1.fr",
    description="Discover, list, and use USB microcontoller boards.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Neradoc/discotool",
    license="MIT",
    project_urls={
        "Bug Tracker": "https://github.com/Neradoc/discotool/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ],
    packages=setuptools.find_packages(where="."),
    python_requires=">=3.6",
    use_scm_version={
        'write_to': 'discotool/_version.py'
    },
    setup_requires=["setuptools_scm"],
    install_requires=required_modules,
    entry_points={"console_scripts": ["discotool=discotool.discotool:main"]},
    keywords="circuitpython, micropython",
)
