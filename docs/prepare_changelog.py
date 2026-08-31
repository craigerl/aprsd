#!/usr/bin/env python3
"""Prepare the generated Markdown changelog for the Sphinx navigation."""

import re
from pathlib import Path

VERSION_HEADING = re.compile(r'^#{3,4} (?:\[)?(?:v?\d+\.\d+\.\d+)')
CATEGORY_HEADING = re.compile(
    r'^#{3,5} (?:Breaking Changes|Features|Bug Fixes|Refactoring|Security|CI)'
)


def prepare_changelog(source: Path, destination: Path) -> None:
    """Normalize changelog heading levels without changing its entries."""
    lines = source.read_text(encoding='utf-8').splitlines()
    output = []

    for line_number, line in enumerate(lines):
        if line_number == 0 and line.startswith('### Changelog'):
            line = '# Changelog'
        elif VERSION_HEADING.match(line):
            line = f'## {line.split(" ", 1)[1]}'
        elif CATEGORY_HEADING.match(line):
            line = f'### {line.split(" ", 1)[1]}'
        output.append(line)

    destination.write_text('\n'.join(output) + '\n', encoding='utf-8')


if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    prepare_changelog(root / 'ChangeLog.md', root / 'docs/source/changelog.md')
