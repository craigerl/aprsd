#!/usr/bin/env python3

"""Removes temporary Sphinx build artifacts to ensure a clean build.

This is needed if the Python source being documented changes significantly. Old sphinx-apidoc
RST files can be left behind.
"""

import shutil
from pathlib import Path


def main() -> None:
    docs_dir = Path(__file__).resolve().parent
    for folder in ('build', 'source/apidoc'):
        delete_dir = docs_dir / folder
        if delete_dir.exists():
            shutil.rmtree(delete_dir)


if __name__ == '__main__':
    main()
