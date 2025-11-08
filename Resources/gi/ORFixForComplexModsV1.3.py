import os
import re
import shutil
from datetime import datetime
import sys

# Detect color support
SUPPORTS_COLOR = sys.stdout.isatty()
RED = "\033[91m" if SUPPORTS_COLOR else ""
GREEN = "\033[92m" if SUPPORTS_COLOR else ""
RESET = "\033[0m" if SUPPORTS_COLOR else ""

# Auto-exclusion patterns
AUTO_EXCLUDE_PATTERNS = [
    re.compile(r'^\[.*IB\]$', re.IGNORECASE),  # Skip any section ending with IB
    re.compile(r'^\[(CommandList|TextureOverride).*Position\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*Texcoord\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*Blend\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*Info\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*VertexLimitRaise\]$', re.IGNORECASE),
    # Full list of CommandList exclusions
    re.compile(r'^\[CommandListCreditInfo\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListLoadA2\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListLoadA\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListLoadB2\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListLoadB\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListLoadC2\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListLoadC\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListLoadD2\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListLoadD\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListMenu\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListRandom0D\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListRandom0\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListRandom1D\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListRandom1\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListRandom2D\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListRandom2\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListRandom3D\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListRandom3\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListRandom4D\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListRandom4\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListRandom5D\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListRandom5\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListSaveA2\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListSaveA\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListSaveB2\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListSaveB\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListSaveC2\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListSaveC\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListSaveD2\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListSaveD\]$', re.IGNORECASE),
]

# Patterns
RUN_LINE_PATTERN = re.compile(r'\s*run\s*=\s*CommandList\\global\\ORFix\\(NNFix|ORFix)', re.IGNORECASE)

rename_extra_ps = None  # global toggle


def process_block_full(block, section_name, clean_only=False):
    if not block:
        return block, []

    changes = []
    new_block = []
    last_ps_index = None
    has_normal = any("NormalMap" in line for line in block)

    for line in block:
        stripped = line.lstrip()

        if not clean_only and rename_extra_ps and re.match(r'ps-t0\s*=', stripped) and "Extra" in stripped and "Diffuse" in stripped:
            new_line = line.replace("ps-t0", "ps-t1", 1)
            changes.append(f"{section_name} → RENAMED: {stripped} -> {stripped.replace('ps-t0','ps-t1',1)}")
        else:
            new_line = line

        new_block.append(new_line)

        if re.match(r'ps-t\d+', stripped):
            last_ps_index = len(new_block) - 1

    temp_block = []
    for line in new_block:
        if RUN_LINE_PATTERN.match(line):
            changes.append(f"{section_name} → REMOVED misplaced run: {line.strip()}")
            continue
        temp_block.append(line)
    new_block = temp_block

    if not clean_only and last_ps_index is not None:
        correct_run = "run = CommandList\\global\\ORFix\\ORFix\n" if has_normal else "run = CommandList\\global\\ORFix\\NNFix\n"
        if not (len(new_block) > last_ps_index + 1 and new_block[last_ps_index + 1].strip() == correct_run.strip()):
            new_block.insert(last_ps_index + 1, correct_run)
            changes.append(f"{section_name} → ADDED run line: {correct_run.strip()}")

    return new_block, changes


def process_ini_preview(file_path, exclude_sections):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    block_lines = []
    current_section = None
    all_changes = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("[CommandList") or stripped.startswith("[TextureOverride"):
            if block_lines:
                contains_ps_t0 = any(re.match(r'\s*ps-t0\s*=', l, re.IGNORECASE) for l in block_lines)
                inside_auto_excluded = any(pat.match(current_section.strip()) for pat in AUTO_EXCLUDE_PATTERNS)
                inside_manual_excluded = current_section.strip() in exclude_sections

                clean_only = inside_auto_excluded or inside_manual_excluded or not contains_ps_t0

                processed, changes = process_block_full(block_lines, current_section, clean_only=clean_only)
                new_lines.extend(processed)
                all_changes.extend(changes)
                block_lines.clear()

            current_section = stripped
            new_lines.append(line)
            continue

        if current_section:
            block_lines.append(line)
        else:
            new_lines.append(line)

    if block_lines:
        contains_ps_t0 = any(re.match(r'\s*ps-t0\s*=', l, re.IGNORECASE) for l in block_lines)
        inside_auto_excluded = any(pat.match(current_section.strip()) for pat in AUTO_EXCLUDE_PATTERNS)
        inside_manual_excluded = current_section.strip() in exclude_sections
        clean_only = inside_auto_excluded or inside_manual_excluded or not contains_ps_t0
        processed, changes = process_block_full(block_lines, current_section, clean_only=clean_only)
        new_lines.extend(processed)
        all_changes.extend(changes)

    return all_changes, new_lines


def main():
    global rename_extra_ps

    while True:
        choice = input(
            'Rename ps-t0 lines containing "Extra" and "Diffuse" to ps-t1 in sections? (y/n): '
        ).strip().lower()
        if choice in ('y','n'):
            rename_extra_ps = choice == 'y'
            break

    recursive = input("Scan subfolders too? (y/n): ").strip().lower() == 'y'

    ini_files = []
    sections_found = set()

    for root, dirs, files in os.walk('.', topdown=True):
        if not recursive and root != '.':
            continue
        for file in files:
            if file.lower().endswith('.ini'):
                path = os.path.join(root, file)
                ini_files.append(path)
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("[CommandList") or line.startswith("[TextureOverride"):
                            sections_found.add(line)
        if not recursive:
            break

    exclude_sections = set()
    for section in sorted(sections_found):
        if any(pat.match(section) for pat in AUTO_EXCLUDE_PATTERNS):
            print(f"Auto-excluded {section}")
            continue
        choice = input(f"Exclude {section}? (y/n): ").strip().lower()
        if choice == "y":
            exclude_sections.add(section)

    all_changes = {}
    for fpath in ini_files:
        changes, _ = process_ini_preview(fpath, exclude_sections)
        if changes:
            all_changes[fpath] = changes

    if not all_changes:
        print("\nNo changes detected.")
    else:
        print("\n=== Proposed Changes ===")
        for f, changes in all_changes.items():
            print(f"\nFile: {f}")
            for c in changes:
                if "ADDED" in c:
                    print(f"  {GREEN}{c}{RESET}")
                elif "REMOVED" in c or "RENAMED" in c:
                    print(f"  {RED}{c}{RESET}")
                else:
                    print(f"  {c}")
        print("=========================")

        proceed = input("\nApply changes? (y/n): ").strip().lower()
        if proceed == 'y':
            for fpath in all_changes.keys():
                _, new_lines = process_ini_preview(fpath, exclude_sections)
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                backup_path = f"{fpath}.bak_{timestamp}"
                shutil.copyfile(fpath, backup_path)
                with open(fpath, 'w', encoding='utf-8') as out:
                    out.writelines(new_lines)
                print(f"\n✅ Updated: {fpath}\n  Backup: {backup_path}")
            print("\nDone.")
        else:
            print("No changes applied.")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
