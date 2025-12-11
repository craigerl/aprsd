#!/usr/bin/env python3

"""Post-process readme.rst after m2r conversion to fix logo path and heading levels."""

import re
from pathlib import Path


def fix_readme_rst(file_path: Path) -> None:
    """Fix logo path and heading levels in readme.rst."""
    content = file_path.read_text(encoding='utf-8')

    # Fix logo path: change ./aprsd_logo.png to ../images/aprsd_logo.png
    content = re.sub(
        r'\.\. image:: \./aprsd_logo\.png',
        '.. image:: ../images/aprsd_logo.png',
        content,
    )
    content = re.sub(
        r':target: \./aprsd_logo\.png', ':target: ../images/aprsd_logo.png', content
    )
    content = re.sub(r':alt: image', ':alt: APRSD Logo', content)

    # Fix heading levels:
    # - Main title uses === (level 1) - keep as is
    # - "KM6LYW and WB4BOR" uses --- (level 2) - keep as is
    # - Major sections like "What is APRSD" use ^^^^^ (level 3) but should be --- (level 2)
    # - Subsections like "Current list plugins" use ~~~~ (level 4) but should be ^^^ (level 3)

    lines = content.split('\n')
    fixed_lines = []
    i = 0

    # Major sections that should be level 2 (---)
    # Note: "Configuration" and "server" are subsections under "Commands", so they stay level 3
    major_sections = [
        'What is APRSD',
        'APRSD Plugins/Extensions',
        'List of existing plugins',
        'List of existing extensions',
        'APRSD Overview Diagram',
        'Typical use case',
        'Installation',
        'Example usage',
        'Help',
        'Commands',
        'send-message',
        'Development',
        'Docker Container',
        'Running the container',
        'Activity',
    ]

    while i < len(lines):
        line = lines[i]

        # Check if this is a heading underline
        if i > 0 and lines[i - 1].strip() and not lines[i - 1].startswith(' '):
            # Check what kind of underline this is
            if line.strip() and all(c == line[0] for c in line.strip()):
                underline_char = line.strip()[0]
                heading_text = lines[i - 1].strip()

                # Skip "KM6LYW and WB4BOR" and "Star History" - they're fine as level 2
                if 'KM6LYW' in heading_text or 'Star History' in heading_text:
                    # The heading text was already added, just add the underline
                    fixed_lines.append(line)
                    i += 1
                    continue

                # Convert level 3 headings (^^^^) to level 2 (---) for major sections
                if underline_char == '^' and len(line.strip()) >= 3:
                    if any(section in heading_text for section in major_sections):
                        # The heading text should already be the last line, replace underline
                        if fixed_lines and fixed_lines[-1].strip() == heading_text:
                            fixed_lines[-1] = heading_text
                        fixed_lines.append('-' * len(heading_text))
                        i += 1
                        continue

                # Convert level 4 headings (~~~~) to level 3 (^^^) for subsections
                if underline_char == '~' and len(line.strip()) >= 3:
                    # The heading text should already be the last line, replace underline
                    if fixed_lines and fixed_lines[-1].strip() == heading_text:
                        fixed_lines[-1] = heading_text
                    fixed_lines.append('^' * len(heading_text))
                    i += 1
                    continue

        fixed_lines.append(line)
        i += 1

    # Remove duplicate consecutive heading lines
    cleaned_lines = []
    for i, line in enumerate(fixed_lines):
        # Skip duplicate heading text lines (consecutive identical non-empty lines)
        if (
            i > 0
            and line.strip()
            and fixed_lines[i - 1].strip() == line.strip()
            and not line.strip().startswith('..')
            and not any(char in line for char in ['=', '-', '^', '~'])
            and len(line.strip()) > 0
        ):
            continue
        cleaned_lines.append(line)

    file_path.write_text('\n'.join(cleaned_lines), encoding='utf-8')


def main() -> None:
    """Main entry point."""
    docs_dir = Path(__file__).resolve().parent
    readme_rst = docs_dir / 'source' / 'readme.rst'

    if not readme_rst.exists():
        print(f'Warning: {readme_rst} does not exist')
        return

    fix_readme_rst(readme_rst)
    print(f'Fixed {readme_rst}')


if __name__ == '__main__':
    main()
