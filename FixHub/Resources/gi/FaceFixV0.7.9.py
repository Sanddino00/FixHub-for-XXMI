#!/usr/bin/env python3
import os
import re
import shutil
import sys
import platform
import concurrent.futures

PRODUCT_NAME = "FaceFix"
VERSION = "0.7.9"
AUTHOR = "Sanddino"

# -----------------------------------------------------------
# Color Support (safe)
# -----------------------------------------------------------
def supports_color():
    if sys.platform.startswith('win'):
        return os.getenv('ANSICON') or 'WT_SESSION' in os.environ or platform.release() >= '10'
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

COLOR_ENABLED = supports_color()
RED = "\033[91m" if COLOR_ENABLED else ""
GREEN = "\033[92m" if COLOR_ENABLED else ""
RESET = "\033[0m" if COLOR_ENABLED else ""

# -----------------------------------------------------------
# Safe Wait for Exit
# -----------------------------------------------------------
def wait_for_exit():
    """Pause safely before exiting without using console-attaching APIs."""
    try:
        input("\nPress ENTER to exit...")
    except Exception:
        # When stdin isn't available (double-click execution), delay briefly.
        import time
        print("\nExiting...")
        time.sleep(2)

# -----------------------------------------------------------
# Smart Replace Engine
# -----------------------------------------------------------
def smart_replace(file_path, make_backup=True, preview=True, apply_changes=False, process_disabled=False):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "DISABLED" in content and not process_disabled:
            return False, []

        lines = content.splitlines(True)
        new_lines = []
        changed_lines = []

        # Safe, validated regex
        pattern = re.compile(
            r'^\s*ps-t\d+\s*=\s*(Resource\w*Face\w*(?:Diffuse|NormalMap)(?:[.\w]*)?)\s*$',
            re.IGNORECASE
        )

        for idx, line in enumerate(lines, 1):
            stripped = line.rstrip("\n")
            match = pattern.match(stripped)
            if match:
                rhs = match.group(1)
                indent = re.match(r'^(\s*)', line).group(1)
                new_line = f"{indent}this = {rhs}\n"

                new_lines.append(new_line)
                changed_lines.append((idx, stripped, new_line.rstrip("\n")))
            else:
                new_lines.append(line)

        if not changed_lines:
            return False, []

        if preview:
            print(f"\nPreview changes for '{os.path.relpath(file_path)}':")
            for idx, old, new in changed_lines:
                highlighted_old = re.sub(r'ps-t\d+', lambda m: f"{RED}{m.group(0)}{RESET}", old)
                highlighted_new = new.replace("this", f"{GREEN}this{RESET}")
                print(f"  Line {idx}: '{highlighted_old}' → '{highlighted_new}'")

        if apply_changes:
            if make_backup:
                backup_path = f"{os.path.splitext(file_path)[0]}_backup.bak"
                shutil.copyfile(file_path, backup_path)
                print(f"💾 Backup saved as '{os.path.relpath(backup_path)}'")

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

        return True, changed_lines

    except Exception as e:
        print(f"❌ Error processing '{file_path}': {e}")
        return False, []

# -----------------------------------------------------------
# Exclusion system
# -----------------------------------------------------------
def get_exclusion_patterns():
    patterns = ['*_backup.bak']
    print("\nEnter folder names to exclude (ENTER to finish):")
    while True:
        folder_name = input("Folder to exclude: ").strip()
        if not folder_name:
            break
        patterns.append(f"*{folder_name}*")
    return patterns

def is_disabled_file(file_path):
    try:
        basename = os.path.basename(file_path).lower()
        if "disabled" in basename:
            return True

        with open(file_path, 'r', encoding='utf-8') as f:
            return 'DISABLED' in f.read()
    except:
        return False

def should_exclude(path, patterns):
    path_norm = path.replace('\\', '/').lower()
    return any(pattern.strip('*').lower() in path_norm for pattern in patterns)

# -----------------------------------------------------------
# Main Logic
# -----------------------------------------------------------
def main():
    print(f"{PRODUCT_NAME} {VERSION} — by {AUTHOR}\n")

    folder = os.getcwd()
    print(f"Working directory: {folder}")

    process_disabled = input("Process disabled files? (Y/N): ").strip().lower() == 'y'
    scan_subfolders = input("Scan subfolders? (Y/N): ").strip().lower() == 'y'
    make_backup = input("Create backups before modifying? (Y/N): ").strip().lower() == 'y'

    print("\nYour choices:")
    print(f"• Process disabled: {'Yes' if process_disabled else 'No'}")
    print(f"• Scan subfolders: {'Yes' if scan_subfolders else 'No'}")
    print(f"• Create backups: {'Yes' if make_backup else 'No'}")

    if input("\nConfirm? (Y/N): ").strip().lower() != 'y':
        print("Cancelled.")
        wait_for_exit()
        return

    exclusion_patterns = get_exclusion_patterns()

    # Collect files
    ini_files = []
    for dirpath, _, filenames in os.walk(folder):
        if should_exclude(dirpath, exclusion_patterns):
            continue

        for f in filenames:
            if f.lower().endswith(".ini"):
                file_path = os.path.join(dirpath, f)
                if not is_disabled_file(file_path) or process_disabled:
                    ini_files.append(file_path)

        if not scan_subfolders:
            break

    if not ini_files:
        print("No .ini files found.")
        wait_for_exit()
        return

    print(f"\nFound {len(ini_files)} files. Previewing...")

    files_to_modify = []
    for ini_file in ini_files:
        changed, _ = smart_replace(ini_file, make_backup, preview=True, process_disabled=process_disabled)
        if changed:
            files_to_modify.append(ini_file)

    if not files_to_modify:
        print("\nNo changes needed.")
        wait_for_exit()
        return

    if input(f"\nApply changes to {len(files_to_modify)} file(s)? (Y/N): ").strip().lower() != 'y':
        print("Cancelled.")
        wait_for_exit()
        return

    max_workers = min(32, (os.cpu_count() or 1) + 4)

    # Apply changes using threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for ini_file in files_to_modify:
            executor.submit(
                smart_replace,
                ini_file,
                make_backup,
                False,       # no preview during actual write
                True,        # apply changes
                process_disabled
            )

    print("\nDone!")
    wait_for_exit()

# -----------------------------------------------------------
if __name__ == "__main__":
    main()
