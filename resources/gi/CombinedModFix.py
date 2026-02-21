#!/usr/bin/env python3
import os
import re
import shutil
import sys
import platform
import concurrent.futures
from datetime import datetime

PRODUCT_NAME = "CombinedModFix"
VERSION = "1.0.0"
AUTHOR = "Sanddino (combined)"

# -----------------------------------------------------------
# Color Support
# -----------------------------------------------------------
def supports_color():
    if sys.platform.startswith('win'):
        return os.getenv('ANSICON') or 'WT_SESSION' in os.environ or platform.release() >= '10'
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

COLOR_ENABLED = supports_color()
RED = "\033[91m" if COLOR_ENABLED else ""
GREEN = "\033[92m" if COLOR_ENABLED else ""
YELLOW = "\033[93m" if COLOR_ENABLED else ""
RESET = "\033[0m" if COLOR_ENABLED else ""

# -----------------------------------------------------------
# Safe Wait for Exit
# -----------------------------------------------------------
def wait_for_exit():
    """Pause safely before exiting."""
    try:
        input("\nPress ENTER to exit...")
    except Exception:
        import time
        print("\nExiting...")
        time.sleep(2)

# -----------------------------------------------------------
# Auto-exclusion patterns for ORFix processing
# -----------------------------------------------------------
AUTO_EXCLUDE_PATTERNS = [
    re.compile(r'^\[.*IB\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*Position\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*Texcoord\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*Blend\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*Info\]$', re.IGNORECASE),
    re.compile(r'^\[(CommandList|TextureOverride).*VertexLimitRaise\]$', re.IGNORECASE),
]

# Specific CommandList exclusions
COMMANDLIST_EXCLUSIONS = [
    re.compile(r'^\[CommandListCreditInfo\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListLoadA2?\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListLoadB2?\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListLoadC2?\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListLoadD2?\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListMenu\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListRandom[0-5]D?\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListSaveA2?\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListSaveB2?\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListSaveC2?\]$', re.IGNORECASE),
    re.compile(r'^\[CommandListSaveD2?\]$', re.IGNORECASE),
]

AUTO_EXCLUDE_PATTERNS.extend(COMMANDLIST_EXCLUSIONS)

# Auto mode exclusion patterns (exclude sections containing face, limb, or limbs)
AUTO_MODE_EXCLUDE_PATTERNS = [
    re.compile(r'face', re.IGNORECASE),
    re.compile(r'limbs?', re.IGNORECASE),  # matches both limb and limbs
]

# -----------------------------------------------------------
# Pattern matching
# -----------------------------------------------------------
SECTION_HEADER_RE = re.compile(r'^\s*\[(.+?)\]\s*$', re.IGNORECASE)
PS_T0_RE = re.compile(r'^(\s*)(ps-t0)\s*=\s*(.+?)(\s*)$', re.IGNORECASE)
RUN_FACE_RE = re.compile(r'^\s*run\s*=\s*(CommandList\w*Face\w*)\s*$', re.IGNORECASE)
RUN_LINE_PATTERN = re.compile(r'\s*run\s*=\s*CommandList\\global\\ORFix\\(NNFix|ORFix)', re.IGNORECASE)

# -----------------------------------------------------------
# Section processing utilities
# -----------------------------------------------------------
def split_into_sections(text):
    """Split file text into sections: list of (header, lines) tuples."""
    lines = text.splitlines(True)
    sections = []
    current_header = None
    current_lines = []

    for line in lines:
        m = SECTION_HEADER_RE.match(line)
        if m:
            if current_lines or current_header is not None:
                sections.append((current_header, current_lines))
            current_header = m.group(1).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines or current_header is not None:
        sections.append((current_header, current_lines))
    return sections

def is_face_section_by_header(header):
    """Return True if section header indicates face-related section."""
    if not header:
        return False
    h = header.lower()
    if 'face' not in h:
        return False
    if h.startswith('commandlist') or h.startswith('textureoverride'):
        return True
    return False

def section_has_run_face(lines):
    """Return True if section contains run = CommandList*Face*."""
    for line in lines:
        if RUN_FACE_RE.match(line):
            return True
    return False

def should_auto_exclude_section(header):
    """Check if section should be auto-excluded based on patterns."""
    if not header:
        return False
    full_header = f"[{header}]"
    return any(pat.match(full_header) for pat in AUTO_EXCLUDE_PATTERNS)

def should_auto_mode_exclude(header):
    """Check if section matches auto-mode exclusion patterns."""
    if not header:
        return False
    # Check for exclusion patterns
    return any(pat.search(header) for pat in AUTO_MODE_EXCLUDE_PATTERNS)

# -----------------------------------------------------------
# FaceFix processing
# -----------------------------------------------------------
def process_face_sections(sections, auto_mode=False, manual_excludes=None):
    """
    Process sections for FaceFix (ps-t0 -> this replacement in face sections).
    FaceFix always processes normally - auto_mode exclusions don't apply here.
    Returns (changed_lines_info, new_text).
    """
    if manual_excludes is None:
        manual_excludes = set()
    
    changed = []
    out_lines = []
    file_line_no = 0

    for header, lines in sections:
        # Determine if this section should be processed
        # FaceFix ignores auto_mode exclusions - only respects manual excludes
        full_section = f"[{header}]" if header else None
        if full_section in manual_excludes:
            allowed = False
        else:
            allowed = is_face_section_by_header(header) or section_has_run_face(lines)
        
        for ln in lines:
            file_line_no += 1
            if allowed:
                m = PS_T0_RE.match(ln)
                if m:
                    indent, ps_token, rhs, trailing = m.groups()
                    newline = ''
                    if ln.endswith('\r\n'):
                        newline = '\r\n'
                    elif ln.endswith('\n'):
                        newline = '\n'
                    new_line = f"{indent}this = {rhs}{trailing}{newline}"
                    out_lines.append(new_line)
                    changed.append(('FACE', header, file_line_no, ln.rstrip('\r\n'), new_line.rstrip('\r\n')))
                    continue
            out_lines.append(ln)

    new_text = ''.join(out_lines)
    return changed, new_text

# -----------------------------------------------------------
# ORFix processing
# -----------------------------------------------------------
def process_orfix_block(block, section_name):
    """Process a section block for ORFix (add/remove run commands)."""
    if not block:
        return block, []

    changes = []
    new_block = []
    last_ps_index = None
    has_normal = any("NormalMap" in line for line in block)

    # First pass: collect lines and find last ps-t index
    for line in block:
        new_block.append(line)
        stripped = line.lstrip()
        if re.match(r'ps-t\d+', stripped):
            last_ps_index = len(new_block) - 1

    # Remove misplaced run lines
    temp_block = []
    for line in new_block:
        if RUN_LINE_PATTERN.match(line):
            changes.append(('ORFIX_REMOVE', section_name, line.strip()))
            continue
        temp_block.append(line)
    new_block = temp_block

    # Add correct run line after last ps-t
    if last_ps_index is not None and last_ps_index < len(new_block):
        correct_run = "run = CommandList\\global\\ORFix\\ORFix\n" if has_normal else "run = CommandList\\global\\ORFix\\NNFix\n"
        # Check if next line is already the correct run
        if not (len(new_block) > last_ps_index + 1 and new_block[last_ps_index + 1].strip() == correct_run.strip()):
            new_block.insert(last_ps_index + 1, correct_run)
            changes.append(('ORFIX_ADD', section_name, correct_run.strip()))

    return new_block, changes

def process_orfix_sections(text, auto_mode=False, manual_excludes=None):
    """
    Process file for ORFix changes.
    Returns (changes, new_lines).
    """
    if manual_excludes is None:
        manual_excludes = set()
    
    lines = text.splitlines(True)
    new_lines = []
    block_lines = []
    current_section = None
    all_changes = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("[CommandList") or stripped.startswith("[TextureOverride"):
            if block_lines:
                # Process previous block
                contains_ps_t0 = any(re.match(r'\s*ps-t0\s*=', l, re.IGNORECASE) for l in block_lines)
                
                # Determine if should process
                inside_auto_excluded = should_auto_exclude_section(current_section)
                
                if auto_mode:
                    inside_mode_excluded = should_auto_mode_exclude(current_section)
                    process_block = not inside_auto_excluded and not inside_mode_excluded and contains_ps_t0
                else:
                    inside_manual_excluded = f"[{current_section}]" in manual_excludes
                    process_block = not inside_auto_excluded and not inside_manual_excluded and contains_ps_t0

                if process_block:
                    processed, changes = process_orfix_block(block_lines, current_section)
                    new_lines.extend(processed)
                    all_changes.extend(changes)
                else:
                    new_lines.extend(block_lines)
                
                block_lines.clear()

            current_section = stripped[1:-1]  # Remove [ ]
            new_lines.append(line)
            continue

        if current_section:
            block_lines.append(line)
        else:
            new_lines.append(line)

    # Process final block
    if block_lines:
        contains_ps_t0 = any(re.match(r'\s*ps-t0\s*=', l, re.IGNORECASE) for l in block_lines)
        inside_auto_excluded = should_auto_exclude_section(current_section)
        
        if auto_mode:
            inside_mode_excluded = should_auto_mode_exclude(current_section)
            process_block = not inside_auto_excluded and not inside_mode_excluded and contains_ps_t0
        else:
            inside_manual_excluded = f"[{current_section}]" in manual_excludes
            process_block = not inside_auto_excluded and not inside_manual_excluded and contains_ps_t0

        if process_block:
            processed, changes = process_orfix_block(block_lines, current_section)
            new_lines.extend(processed)
            all_changes.extend(changes)
        else:
            new_lines.extend(block_lines)

    return all_changes, ''.join(new_lines)

# -----------------------------------------------------------
# Combined processing
# -----------------------------------------------------------
def process_file_combined(file_path, auto_mode=False, manual_excludes=None, process_disabled=False):
    """
    Process file with both FaceFix and ORFix logic.
    Returns (has_changes, all_changes, new_text).
    """
    if manual_excludes is None:
        manual_excludes = set()
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "DISABLED" in content and not process_disabled:
            return False, [], content

        # Process FaceFix
        sections = split_into_sections(content)
        face_changes, text_after_face = process_face_sections(sections, auto_mode, manual_excludes)

        # Process ORFix on the result
        orfix_changes, final_text = process_orfix_sections(text_after_face, auto_mode, manual_excludes)

        all_changes = face_changes + [(change_type, section, data) for change_type, section, data in orfix_changes]
        
        has_changes = len(all_changes) > 0

        return has_changes, all_changes, final_text

    except Exception as e:
        print(f"❌ Error processing '{file_path}': {e}")
        return False, [], ""

# -----------------------------------------------------------
# File discovery
# -----------------------------------------------------------
def is_disabled_file(file_path):
    try:
        basename = os.path.basename(file_path).lower()
        if "disabled" in basename:
            return True
        with open(file_path, 'r', encoding='utf-8') as f:
            return 'DISABLED' in f.read()
    except:
        return False

def get_exclusion_patterns():
    """Get manual folder exclusion patterns from user."""
    patterns = ['*_backup.bak', '*.bak']
    print("\nEnter folder names to exclude (ENTER to finish):")
    while True:
        folder_name = input("Folder to exclude: ").strip()
        if not folder_name:
            break
        patterns.append(f"*{folder_name}*")
    return patterns

def should_exclude(path, patterns):
    """Check if path should be excluded based on patterns."""
    path_norm = path.replace('\\', '/').lower()
    return any(pattern.strip('*').lower() in path_norm for pattern in patterns)

def collect_sections(ini_files):
    """Collect all unique sections from ini files."""
    sections_found = set()
    for path in ini_files:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("[CommandList") or line.startswith("[TextureOverride"):
                        sections_found.add(line)
        except:
            pass
    return sections_found

# -----------------------------------------------------------
# Preview display
# -----------------------------------------------------------
def display_preview(changes_by_file):
    """Display all proposed changes."""
    print(f"\n{YELLOW}=== PREVIEW OF CHANGES ==={RESET}")
    for fpath, changes in changes_by_file.items():
        print(f"\n{YELLOW}File: {os.path.relpath(fpath)}{RESET}")
        for change in changes:
            if change[0] == 'FACE':
                _, header, lineno, old, new = change
                highlighted_old = re.sub(r'(ps-t0)', lambda m: f"{RED}{m.group(1)}{RESET}", old, flags=re.IGNORECASE)
                highlighted_new = new.replace("this", f"{GREEN}this{RESET}", 1)
                header_display = f" [{header}]" if header else ""
                print(f"  {GREEN}FACE{RESET} Line {lineno}{header_display}:")
                print(f"    {highlighted_old} → {highlighted_new}")
            elif change[0] == 'ORFIX_ADD':
                _, section, run_line = change
                print(f"  {GREEN}ORFIX ADD{RESET} [{section}]: {run_line}")
            elif change[0] == 'ORFIX_REMOVE':
                _, section, run_line = change
                print(f"  {RED}ORFIX REMOVE{RESET} [{section}]: {run_line}")
    print(f"{YELLOW}========================={RESET}\n")

# -----------------------------------------------------------
# Main Logic
# -----------------------------------------------------------
def main():
    print(f"{PRODUCT_NAME} {VERSION} — by {AUTHOR}\n")
    print("This tool combines FaceFix and ORFix functionality.")

    folder = os.getcwd()
    print(f"Working directory: {folder}")

    # Mode selection
    print("\n=== MODE SELECTION ===")
    print("[A]UTO: Automatically excludes ORFix for sections containing: face, limb, limbs")
    print("      (FaceFix always runs normally, ORFix excluded for face/limb sections)")
    print("[M]ANUAL: You manually choose which sections to exclude for both fixes")
    while True:
        mode_choice = input("\nChoose mode (A/M): ").strip().lower()
        if mode_choice in ('a', 'auto'):
            auto_mode = True
            break
        if mode_choice in ('m', 'manual'):
            auto_mode = False
            break
        print("Please enter A for Auto or M for Manual.")

    # Other options
    process_disabled = input("Process disabled files? (Y/N): ").strip().lower() == 'y'
    scan_subfolders = input("Scan subfolders? (Y/N): ").strip().lower() == 'y'
    make_backup = input("Create backups before modifying? (Y/N): ").strip().lower() == 'y'

    print("\nYour choices:")
    print(f"• Mode: {'Auto' if auto_mode else 'Manual'}")
    print(f"• Process disabled: {'Yes' if process_disabled else 'No'}")
    print(f"• Scan subfolders: {'Yes' if scan_subfolders else 'No'}")
    print(f"• Create backups: {'Yes' if make_backup else 'No'}")

    if input("\nConfirm? (Y/N): ").strip().lower() != 'y':
        print("Cancelled.")
        wait_for_exit()
        return

    # Get folder exclusions
    exclusion_patterns = get_exclusion_patterns()

    # Collect files
    print("\nScanning for .ini files...")
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

    print(f"Found {len(ini_files)} .ini files.")

    # Manual section exclusion
    manual_excludes = set()
    if not auto_mode:
        print("\nCollecting sections for manual exclusion...")
        sections_found = collect_sections(ini_files)
        
        for section in sorted(sections_found):
            if should_auto_exclude_section(section[1:-1]):  # Remove [ ]
                print(f"Auto-excluded: {section}")
                continue
            choice = input(f"Exclude {section}? (y/n): ").strip().lower()
            if choice == "y":
                manual_excludes.add(section)

    # Preview changes
    print("\nAnalyzing files and generating preview...")
    changes_by_file = {}
    final_texts = {}

    for ini_file in ini_files:
        has_changes, changes, new_text = process_file_combined(
            ini_file, 
            auto_mode=auto_mode, 
            manual_excludes=manual_excludes,
            process_disabled=process_disabled
        )
        if has_changes:
            changes_by_file[ini_file] = changes
            final_texts[ini_file] = new_text

    if not changes_by_file:
        print("\n✓ No changes needed.")
        wait_for_exit()
        return

    # Display preview
    display_preview(changes_by_file)

    # Confirm application
    if input(f"Apply changes to {len(changes_by_file)} file(s)? (Y/N): ").strip().lower() != 'y':
        print("Cancelled.")
        wait_for_exit()
        return

    # Apply changes
    print("\nApplying changes...")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    for ini_file, new_text in final_texts.items():
        try:
            if make_backup:
                backup_path = f"{ini_file}.bak_{timestamp}"
                shutil.copyfile(ini_file, backup_path)
            
            with open(ini_file, "w", encoding="utf-8") as f:
                f.write(new_text)
            
            print(f"✅ Updated: {os.path.relpath(ini_file)}")
        except Exception as e:
            print(f"❌ Error updating {ini_file}: {e}")

    print(f"\n✓ Done! Processed {len(final_texts)} files.")
    wait_for_exit()

# -----------------------------------------------------------
if __name__ == "__main__":
    main()
