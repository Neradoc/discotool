import os
import setuptools
import sys

here = os.path.abspath(os.path.dirname(__file__))

with open(path.join(here,"README.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open(path.join(here,"requirements.txt"), "r", encoding="utf-8") as fp:
    required_modules = fp.read().split("\n")

platform_req = path.join(here,f"requirements-{sys.platform}.txt")
if os.path.exists(platform_req):
    with open(platform_req, "r", encoding="utf-8") as fp:
        required_modules += fp.read().split("\n")

setuptools.setup(
    name="neradoc-discotool",
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
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    install_requires=required_modules,
    entry_points={"console_scripts": ["discotool=discotool.discotool:main"]},
    keywords="cricuitpython, micropython",
)
