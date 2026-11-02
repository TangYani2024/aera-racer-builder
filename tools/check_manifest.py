#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET

KNOWN_PREFIXES = [
    "platform/", "kernel/", "hardware/", "external/",
    "prebuilts/", "packages/", "system/", "frameworks/",
    "device/", "vendor/", "toolchain/"
]

def check_manifest(filepath):
    try:
        tree = ET.parse(filepath)
    except ET.ParseError as e:
        print(f"Error: XML is not well-formed in {filepath}: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return False

    root = tree.getroot()
    if root.tag != 'manifest':
        print(f"Error: Root element is not <manifest> in {filepath}", file=sys.stderr)
        return False

    seen_projects = set()
    duplicates = set()
    project_names = []

    has_errors = False

    for remove_project in root.findall('remove-project'):
        name = remove_project.get('name')
        if not name:
            print(f"Error: <remove-project> element missing 'name' attribute in {filepath}", file=sys.stderr)
            has_errors = True
            continue

        if name in seen_projects:
            duplicates.add(name)
        else:
            seen_projects.add(name)
            project_names.append(name)

        # Check prefix
        if not any(name.startswith(prefix) for prefix in KNOWN_PREFIXES):
            print(f"Error: Project '{name}' does not start with a known AOSP prefix in {filepath}", file=sys.stderr)
            has_errors = True

    if duplicates:
        print(f"Error: Duplicate <remove-project> entries found in {filepath}:", file=sys.stderr)
        for dup in sorted(duplicates):
            print(f"  - {dup}", file=sys.stderr)
        has_errors = True

    # Check alphabetical order
    sorted_names = sorted(project_names)
    if project_names != sorted_names:
        print(f"Warning: <remove-project> entries are not sorted alphabetically in {filepath}", file=sys.stderr)
        # Find the first out-of-order element
        for i, name in enumerate(project_names):
            if name != sorted_names[i]:
                print(f"  First mismatch: expected '{sorted_names[i]}', found '{name}'", file=sys.stderr)
                break

    return not has_errors

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 check_manifest.py <path-to-manifest.xml>")
        sys.exit(1)

    all_success = True
    for filepath in sys.argv[1:]:
        if not check_manifest(filepath):
            all_success = False

    sys.exit(0 if all_success else 1)
