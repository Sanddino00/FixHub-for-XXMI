"""Script used to apply ORFIX to character.ini files.
Code fix and improved by golanah921 / Gustav0 / LeoTorrez
Original idea by Nooble_
"""

import sys
import os
import argparse
import re
from datetime import datetime
from typing import TypedDict

ORFIXRUN: str = r"run = CommandList\\global\\ORFix\\ORFix\n"
NNFIXRUN: str = r"run = CommandList\\global\\ORFix\\NNFix\n"
# We define all the regex patters before the loop to avoid re-compiling them multiple times
ORFIX_PATTERN = re.compile(
    r"[ \t\f]*run\s*=\s*CommandList\\global\\ORFix\\ORFix[ \t\f]*\n",
    re.IGNORECASE,
)
NNFIX_PATTERN = re.compile(
    r"[ \t\f]*run\s*=\s*CommandList\\global\\ORFix\\NNFix[ \t\f]*\n",
    re.IGNORECASE,
)
# Match ps-t lines, allowing blank lines in between (to treat them as one block)
TEXTURE_BLOCK_PATTERN = re.compile(r"((^[ \t\f]*ps-t.*\n(?:[ \t\f]*\n)*)+)", re.IGNORECASE | re.MULTILINE)
INDENT_PATTERN = re.compile(r"\n([ \t\f]*)ps-t", re.IGNORECASE)
# ------------------------------------------------------------------------------------------


class CharacterData(TypedDict):
    name: str
    component: str
    ib_hash: str
    position: str
    normal_parts: list[tuple[str, int]]
    no_normal_parts: list[tuple[str, int]]


def remove_old_shaderfix(lines: list[str], to_print: list[str]) -> list[str]:
    """
    Removes shader code from the given list of lines and checks if the new lines are different.
    """
    ############Old shaderfix remover##########
    old_fixes: list[str] = [
        r"""; Version 1.0.0 AGMG Tool Developer Version 3 Shader Fixer


; Generated shader fix for 3.0+ GIMI importer characters. Please contact the tool developers at https://discord.gg/agmg if you have any questions.

; Variables -----------------------
""",
        r"""[Constants]
global $CharacterIB
;0=none, 1=head, 2=body, 3=dress, 4=extra, etc.

[Present]
post $CharacterIB = 0

[ResourceRefHeadDiffuse]
[ResourceRefHeadLightMap]
[ResourceRefBodyDiffuse]
[ResourceRefBodyLightMap]
[ResourceRefDressDiffuse]
[ResourceRefDressLightMap]
[ResourceRefExtraDiffuse]
[ResourceRefExtraLightMap]

; ShaderOverride ---------------------------

[ShaderRegexCharReflection]
shader_model = ps_5_0
run = CommandListReflectionTexture
[ShaderRegexCharReflection.pattern]
mul r\d+\.\w+, r\d+\.\w+,[^.]*\.\w+\n
mad o\d+\.\w+, r\d+\.\w+, cb\d+\[\d+\]\.\w+, r\d+\.\w+\n
mov o\d+\.\w+, l\(\d+\.\d+\)\n

[ShaderRegexCharOutline]
shader_model = ps_5_0
run = CommandListOutline
[ShaderRegexCharOutline.pattern]
mov o\d+\.\w+, l\(\d+\)\n
mov o\d+\.\w+, r\d+\.\w+\n
mov o\d+\.\w+, l\(\d+\.\d+\)

; OPTIONAL: If regex match breaks, use a [ShaderOverride] command matching shader hash for reflection then use "run = CommandListOutline" under the command

; CommandList -------------------------

[CommandListReflectionTexture]
if $CharacterIB != 0
    if $CharacterIB == 1
        ps-t0 = copy ResourceRefHeadDiffuse
    else if $CharacterIB == 2
        ps-t0 = copy ResourceRefBodyDiffuse
    else if $CharacterIB == 3
        ps-t0 = copy ResourceRefDressDiffuse
    else if $CharacterIB == 4
        ps-t0 = copy ResourceRefExtraDiffuse    
    endif
drawindexed=auto
$CharacterIB = 0
endif

[CommandListOutline]
if $CharacterIB != 0
    if $CharacterIB == 1
        ps-t1 = copy ResourceRefHeadLightMap
    else if $CharacterIB == 2
        ps-t1 = copy ResourceRefBodyLightMap
    else if $CharacterIB == 3
        ps-t1 = copy ResourceRefDressLightMap
    else if $CharacterIB == 4
        ps-t1 = copy ResourceRefExtraLightMap
    endif
drawindexed=auto
$CharacterIB = 0
endif""",
        r"""[Constants]
global $CharacterIB
;0=none, 1=head, 2=body, 3=dress, 4=extra, etc.

[Present]
post $CharacterIB = 0

[ResourceRefHeadDiffuse]
;[ResourceRefHeadLightMap]
[ResourceRefBodyDiffuse]
;[ResourceRefBodyLightMap]
[ResourceRefDressDiffuse]
;[ResourceRefDressLightMap]
[ResourceRefExtraDiffuse]
;[ResourceRefExtraLightMap]

; ShaderOverride ---------------------------

[ShaderRegexCharReflection]
shader_model = ps_5_0
run = CommandListReflectionTexture
[ShaderRegexCharReflection.pattern]
mul r\d+\.\w+, r\d+\.\w+,[^.]*\.\w+\n
mad o\d+\.\w+, r\d+\.\w+, cb\d+\[\d+\]\.\w+, r\d+\.\w+\n
mov o\d+\.\w+, l\(\d+\.\d+\)\n

;[ShaderRegexCharOutline]
;shader_model = ps_5_0
;run = CommandListOutline
;[ShaderRegexCharOutline.pattern]
;mov o\d+\.\w+, l\(\d+\)\n
;mov o\d+\.\w+, r\d+\.\w+\n
;mov o\d+\.\w+, l\(\d+\.\d+\)
;broken as of version 4.0

; OPTIONAL: If regex match breaks, use a [ShaderOverride] command matching shader hash for reflection then use "run = CommandListOutline" under the command

; CommandList -------------------------

[CommandListReflectionTexture]
if $CharacterIB != 0
    if $CharacterIB == 1
        ps-t0 = copy ResourceRefHeadDiffuse
    else if $CharacterIB == 2
        ps-t0 = copy ResourceRefBodyDiffuse
    else if $CharacterIB == 3
        ps-t0 = copy ResourceRefDressDiffuse
    else if $CharacterIB == 4
        ps-t0 = copy ResourceRefExtraDiffuse    
    endif
drawindexed=auto
$CharacterIB = 0
endif

;[CommandListOutline]
;if $CharacterIB != 0
;    if $CharacterIB == 1
;        ps-t1 = copy ResourceRefHeadLightMap
;    else if $CharacterIB == 2
;        ps-t1 = copy ResourceRefBodyLightMap
;    else if $CharacterIB == 3
;        ps-t1 = copy ResourceRefDressLightMap
;    else if $CharacterIB == 4
;        ps-t1 = copy ResourceRefExtraLightMap
;    endif
;drawindexed=auto
;$CharacterIB = 0
;endif""",
        """$CharacterIB = 1
ResourceRefHeadDiffuse = reference ps-t1
ResourceRefHeadLightMap = reference ps-t2""",
        """$CharacterIB = 2
ResourceRefBodyDiffuse = reference ps-t1
ResourceRefBodyLightMap = reference ps-t2""",
        """$CharacterIB = 3
ResourceRefDressDiffuse = reference ps-t1
ResourceRefDressLightMap = reference ps-t2""",
        """$CharacterIB = 4
ResourceRefExtraDiffuse = reference ps-t1
ResourceRefExtraLightMap = reference ps-t2""",
        """$CharacterIB = 1
ResourceRefHeadDiffuse = reference ps-t1""",
        """$CharacterIB = 2
ResourceRefBodyDiffuse = reference ps-t1""",
        """$CharacterIB = 3
ResourceRefDressDiffuse = reference ps-t1""",
        """$CharacterIB = 4
ResourceRefExtraDiffuse = reference ps-t1""",
    ]
    # Convert the list of lines into a single string for easier processing
    content = "".join(lines)

    # Remove the shader code patterns for any Shadercode in the format Shadercode+number
    for old_str in old_fixes:
        content = content.replace(old_str, "")
    # Split the content back into lines
    new_lines = content.splitlines(keepends=True)
    if new_lines != lines:
        to_print.append("\tOld shader fix removed")
    return new_lines


def split_sections(lines: list[str]) -> list[str]:
    """Split the ini body into sections. Each section starts at [xxx] and ends at the next or eof.
    The part prior to the first section is a header"""
    sections = []
    section = ""
    for line in lines:
        if line.strip().startswith("["):
            if section:
                sections.append(section)
            section = ""
        section += line
    if section:
        sections.append(section)
    return sections


def search_part(
    chara_name_position_ib_hash: list[CharacterData],
    section: str,
    lines: list[str],
    args: argparse.Namespace,
    to_print: list[str],
) -> tuple[str, str, bool, str, bool]:
    """Search for the part in the given section.
    Returns the character name, part, a boolean indicating if it needs fix, the fix type ('orfix' or 'nnfix'), and whether character was found in database
    """
    for data in chara_name_position_ib_hash:
        character: str = data["name"]
        component: str = data["component"]
        ib = data["ib_hash"]
        # pos = data["position"]
        normal_parts = data.get("normal_parts", [])
        no_normal_parts = data.get("no_normal_parts", [])

        # Check normal_parts first
        for part, first_index in normal_parts:
            ib_pattern = re.compile(rf"hash\s*=\s*{ib}\s*")
            match_pattern = re.compile(rf"match_first_index\s*=\s*{first_index}\s*")
            if ib_pattern.search(section) and match_pattern.search(section):
                return character, component + part, True, "orfix", True

        # Check no_normal_parts
        for part, first_index in no_normal_parts:
            ib_pattern = re.compile(rf"hash\s*=\s*{ib}\s*")
            match_pattern = re.compile(rf"match_first_index\s*=\s*{first_index}\s*")
            if ib_pattern.search(section) and match_pattern.search(section):
                return character, component + part, True, "nnfix", True

    if args.usename:
        for entry in chara_name_position_ib_hash:
            if entry["name"] in lines[0]:
                to_print.append("\tCharacter found using name")
                part: str = section.split("\n")[0][16 + len(entry["name"]) : -1]
                return entry["name"], part, False, "", True

    character: str = section.split("\n")[0][16:-1]
    return character, "", False, "", False


def split_ifelseblocks(section: str) -> list[str]:
    """Split the section into if-else blocks"""
    blocks: list[str] = []
    block: str = ""
    for line in section.splitlines(keepends=True):
        block += line
        l_strip = line.strip().lower()
        if l_strip.startswith("if") or l_strip.startswith("else"):
            blocks.append(block)
            block = ""
        elif l_strip.startswith("endif"):
            blocks.append(block)
            block = ""
            continue
    if block:
        blocks.append(block)
    return blocks


def fix_ifelse_blocks(commandlist, fix_type: str = "orfix") -> str:
    """Finds ps-t blocks in each ifelse block and adds orfix/nnfix after them"""
    fix_run = ORFIXRUN if fix_type == "orfix" else NNFIXRUN
    ifelse_blocks = split_ifelseblocks(commandlist)
    for j, block in enumerate(ifelse_blocks):
        indent_check = INDENT_PATTERN.search(block)
        indentation: str = indent_check.group(1) if indent_check else ""
        ifelse_blocks[j] = re.sub(
            TEXTURE_BLOCK_PATTERN,
            rf"\1{indentation}{fix_run}",
            block,
        )
    return "".join(ifelse_blocks)


def apply_orfix(
    lines: list[str],
    chara_name_position_ib_hash: list[CharacterData],
    args: argparse.Namespace,
    to_print: list[str],
) -> list[str]:
    """Apply ORFIX to the given list of lines"""
    sections: list[str] = split_sections(lines)
    for i, section in enumerate(sections):
        if not section.lower().startswith("[textureoverride"):
            continue

        chara_name, part, needs_fix, fix_type, found_in_db = search_part(
            chara_name_position_ib_hash, section, lines, args, to_print
        )
        merged_pattern = re.compile(
            rf"(\s*)(run\s*=\s*commandlist{chara_name}{part})", re.IGNORECASE
        )
        
        # Also check for generic CommandList pattern (for merged mods with different naming)
        generic_commandlist_pattern = re.compile(
            r"(\s*)(run\s*=\s*CommandList(\w+))", re.IGNORECASE
        )

        # Determine which pattern and run command to use
        fix_pattern = ORFIX_PATTERN if fix_type == "orfix" else NNFIX_PATTERN
        wrong_fix_pattern = NNFIX_PATTERN if fix_type == "orfix" else ORFIX_PATTERN
        if fix_type == "":  # No specific fix type determined
            fix_pattern = ORFIX_PATTERN  # Default to ORFIX for backward compatibility

        if not needs_fix:
            # Only remove ORFIX/NNFIX if character was found in database but doesn't need fix
            # If character not found in database, skip entirely (don't touch existing ORFIX)
            if not found_in_db:
                continue

            # In this path chara_name contains character+component+part but we don't care about distinction
            chara_name = chara_name + part
            if merged_pattern.search(section):
                # We are in a merged mod
                # follown commandlist and check if it has ib and match_first_index in it.
                # if it doesnt we add it after run = coommandlist{character}
                commandlist = ""
                index = -1
                for idx, sec in enumerate(sections):
                    if sec.lower().startswith(f"[CommandList{chara_name}".lower()):
                        commandlist = sec
                        index = idx
                        break
                else:
                    to_print.append(
                        f"\tFailed to remove ORFix in merged mod that might not need it. CommandList not found for {chara_name}. Skipping..."
                    )
                    continue
                if ORFIX_PATTERN.search(commandlist) or NNFIX_PATTERN.search(
                    commandlist
                ):
                    # Remove orfix/nnfix matches all of them
                    sections[index] = re.sub(ORFIX_PATTERN, "", commandlist)
                    sections[index] = re.sub(NNFIX_PATTERN, "", sections[index])
                    to_print.append(
                        f"\tORFIX/NNFIX removed for {chara_name}'s CommandList. It was not needed"
                    )
                    # We dont continue in this block so it checks for current section also
            # We remove orfix/nnfix if it has it
            if ORFIX_PATTERN.search(section) or NNFIX_PATTERN.search(section):
                sections[i] = re.sub(ORFIX_PATTERN, "", section)
                sections[i] = re.sub(NNFIX_PATTERN, "", sections[i])
                to_print.append(
                    f"\tORFIX/NNFIX removed for {chara_name}. It was not needed"
                )
            continue

        fix_name = "NNFIX" if fix_type == "nnfix" else "ORFIX"
        if wrong_fix_pattern.search(section):
            wrong_fix = "ORFIX" if fix_type == "nnfix" else "NNFIX"
            section = re.sub(wrong_fix_pattern, "", section)
            to_print.append(
                f"Wrong fix({wrong_fix}) found for {chara_name} in part {part}. Removed it before applying {fix_name}."
            )
        if fix_pattern.search(section):
            to_print.append(
                f"\t{fix_name} already applied for {chara_name} in part {part}. Skipping..."
            )
            continue
        if merged_pattern.search(section):
            commandlist = ""
            cl_index = -1
            for j, sec in enumerate(sections):
                if sec.lower().startswith(f"[CommandList{chara_name}{part}".lower()):
                    commandlist = sec
                    cl_index = j
                    break
            else:
                to_print.append(
                    f"\tFailed to apply {fix_name} in merged mod. CommandList not found for {chara_name} in part {part}. Skipping..."
                )
                continue
        elif generic_commandlist_pattern.search(section):
            match = generic_commandlist_pattern.search(section)
            if match:
                commandlist_name = match.group(3)  
                commandlist = ""
                cl_index = -1
                for j, sec in enumerate(sections):
                    if sec.lower().startswith(f"[CommandList{commandlist_name}".lower()):
                        commandlist = sec
                        cl_index = j
                        break
                else:
                    to_print.append(
                        f"\tFailed to apply {fix_name} in merged mod. CommandList not found for {commandlist_name}. Skipping..."
                    )
                    continue
            else:
                new_section = fix_ifelse_blocks(section, fix_type)
                if new_section == section:
                    to_print.append(
                        f"\tFailed to apply {fix_name}. No texture slots found for {chara_name} in part {part}. Skipping..."
                    )
                    continue
                sections[i] = new_section
                to_print.append(f"\t{fix_name} applied for {chara_name} in part {part}!!!")
                continue
        else:
            new_section = fix_ifelse_blocks(section, fix_type)
            if new_section == section:
                to_print.append(
                    f"\tFailed to apply {fix_name}. No texture slots found for {chara_name} in part {part}. Skipping..."
                )
                continue
            sections[i] = new_section
            to_print.append(f"\t{fix_name} applied for {chara_name} in part {part}!!!")
            continue
        if not commandlist:
            continue
            
        if fix_pattern.search(commandlist):
            to_print.append(
                f"\t{fix_name} already applied for {chara_name} in part {part}. Skipping..."
            )
            continue
        newcommandlist = fix_ifelse_blocks(commandlist, fix_type)
        if newcommandlist == commandlist or cl_index == -1:
            to_print.append(
                f"\tFailed to apply {fix_name} in merge mod. No changes made for {chara_name} in part {part}. Skipping..."
            )
            continue

        sections[cl_index] = newcommandlist
        to_print.append(
            f"\t{fix_name} applied for {chara_name} in part {part} in every if else block(please verify)!!!"
        )

    return "".join(sections).splitlines(keepends=True)


def remove_orfix(lines: list[str], to_print: list[str]) -> list[str]:
    """Remove ORFIX and NNFIX from the given list of lines"""
    old_lines = lines.copy()
    joint_lines = "".join(lines)
    joint_lines = re.sub(ORFIX_PATTERN, r"", joint_lines)
    joint_lines = re.sub(NNFIX_PATTERN, r"", joint_lines)
    lines = joint_lines.splitlines(keepends=True)
    if lines != old_lines:
        to_print.append("\tORFIX/NNFIX forcefully removed from INI file.")
    return lines


def undo_orfix_changes() -> None:
    """Restore files from backup files created by previous ORFIX applications"""
    restored_count = 0
    backup_files_dict = {}  # Dictionary to store latest backup for each original file

    print("Searching for backup files...")

    for r, _, f in os.walk(".\\"):
        for file in f:
            if file.startswith("Backup_ORFIX_Applier_") and file.endswith(".txt"):
                backup_path = os.path.join(r, file)
                file_parts = file[len("Backup_ORFIX_Applier_") : -4].split("_")

                if (
                    len(file_parts) >= 3
                    and len(file_parts[-1]) == 6
                    and len(file_parts[-2]) == 8
                ):
                    # New format with datetime
                    original_name = "_".join(file_parts[:-2]) + ".ini"
                    datetime_str = file_parts[-2] + "_" + file_parts[-1]
                    try:
                        backup_datetime = datetime.strptime(
                            datetime_str, "%Y%m%d_%H%M%S"
                        )
                    except ValueError:
                        original_name = "_".join(file_parts) + ".ini"
                        backup_datetime = datetime.min
                else:
                    original_name = "_".join(file_parts) + ".ini"
                    backup_datetime = datetime.min

                original_path = os.path.join(r, original_name)

                if (
                    original_name not in backup_files_dict
                    or backup_datetime > backup_files_dict[original_name][3]
                ):
                    backup_files_dict[original_name] = (
                        backup_path,
                        original_path,
                        original_name,
                        backup_datetime,
                    )

    if not backup_files_dict:
        print("No backup files found. Nothing to restore.")
        return

    # Convert dictionary to list for easier handling
    backup_files_found = list(backup_files_dict.values())

    print(f"Found {len(backup_files_found)} backup file(s) (latest for each file):")
    for (
        backup_path,
        original_path,
        original_name,
        backup_datetime,
    ) in backup_files_found:
        if backup_datetime != datetime.min:
            print(
                f"  {original_name} (backup from {backup_datetime.strftime('%Y-%m-%d %H:%M:%S')})"
            )
        else:
            print(f"  {original_name} (old backup format)")

    confirm = input(f"\nRestore {len(backup_files_found)} file(s) from backup? (y/N): ")
    if confirm.lower() not in ["y", "yes"]:
        print("Undo cancelled.")
        return

    for (
        backup_path,
        original_path,
        original_name,
        backup_datetime,
    ) in backup_files_found:
        try:
            # Read backup with CP1252 (3DMigoto encoding)
            try:
                with open(backup_path, "r", encoding="cp1252") as backup_file:
                    backup_content = backup_file.readlines()
            except (UnicodeDecodeError, UnicodeError):
                with open(backup_path, "r", encoding="utf-8") as backup_file:
                    backup_content = backup_file.readlines()

            # Write back with CP1252
            with open(original_path, "w", encoding="cp1252") as original_file:
                original_file.writelines(backup_content)

            print(f"✓ Restored: {original_name}")
            restored_count += 1

        except FileNotFoundError:
            print(f"Error: Original file not found: {original_name}")
        except Exception as e:
            print(f"Error restoring {original_name}: {str(e)}")

    print(
        f"\nRestore complete! {restored_count}/{len(backup_files_found)} files restored."
    )

    if restored_count > 0:
        delete_confirm = input("Delete backup files? (y/N): ")
        if delete_confirm.lower() in ["y", "yes"]:
            deleted_count = 0
            for backup_path, _, original_name, _ in backup_files_found:
                try:
                    os.remove(backup_path)
                    backup_filename = os.path.basename(backup_path)
                    print(f"✓ Deleted backup: {backup_filename}")
                    deleted_count += 1
                except Exception as e:
                    print(f"✗ Error deleting backup: {str(e)}")
            print(f"Deleted {deleted_count} backup file(s).")


def process_ini(r, file, args) -> None:
    """Process the given .ini file"""
    chara_name_position_ib_hash: list[CharacterData] = [
        {
            "name": "AnnihilationSpecialistMek",
            "component": "",
            "ib_hash": "cf627fd8",
            "position": "da152664",
            "normal_parts": [("Head", 0), ("Body", 73440)],
            "no_normal_parts": [],
        },
        {
            "name": "ArlecchinoBoss",
            "component": "",
            "ib_hash": "97967876",
            "position": "55c132a8",
            "normal_parts": [("Head", 0), ("Body", 30453)],
            "no_normal_parts": [],
        },
        {
            "name": "CapitanoNPC",
            "component": "",
            "ib_hash": "294108e9",
            "position": "dc8e7c02",
            "normal_parts": [("Head", 0), ("Body", 18978), ("Dress", 61614)],
            "no_normal_parts": [],
        },
        {
            "name": "Dottore",
            "component": "",
            "ib_hash": "ce43a52e",
            "position": "3b2689bb",
            "normal_parts": [("Head", 0), ("Body", 26550), ("Dress", 64524)],
            "no_normal_parts": [],
        },
        {
            "name": "Focalors",
            "component": "",
            "ib_hash": "4e30d6d8",
            "position": "c58c01de",
            "normal_parts": [("Head", 0), ("Body", 29280), ("Dress", 51312)],
            "no_normal_parts": [],
        },
        {
            "name": "Furina(NPC) pre4-2",
            "component": "",
            "ib_hash": "d672c825",
            "position": "330c6649",
            "normal_parts": [("Head", 0), ("Body", 57015), ("Dress", 71055)],
            "no_normal_parts": [],
        },
        {
            "name": "Alhaitham",
            "component": "",
            "ib_hash": "639d1fb8",
            "position": "3ef08385",
            "normal_parts": [("Head", 0), ("Body", 28278), ("Dress", 71181)],
            "no_normal_parts": [],
        },
        {
            "name": "Arlecchino",
            "component": "",
            "ib_hash": "e811d2a1",
            "position": "6895f405",
            "normal_parts": [("Head", 0), ("Body", 40179)],
            "no_normal_parts": [("Dress", 74412)],
        },
        {
            "name": "AyakaSpringbloom",
            "component": "",
            "ib_hash": "bb6ced0e",
            "position": "cf78a1d0",
            "normal_parts": [("Head", 0), ("Body", 56223)],
            "no_normal_parts": [("Dress", 69603)],
        },
        {
            "name": "Baizhu",
            "component": "",
            "ib_hash": "be0be707",
            "position": "17baa562",
            "normal_parts": [("Head", 0), ("Body", 42606), ("Dress", 66624)],
            "no_normal_parts": [],
        },
        {
            "name": "Candace",
            "component": "",
            "ib_hash": "a84cc930",
            "position": "9cee8711",
            "normal_parts": [("Head", 0), ("Body", 32682), ("Dress", 58719)],
            "no_normal_parts": [],
        },
        {
            "name": "Charlotte",
            "component": "",
            "ib_hash": "ff554aca",
            "position": "c5a6d98e",
            "normal_parts": [("Head", 0), ("Body", 23271)],
            "no_normal_parts": [],
        },
        {
            "name": "Chasca",
            "component": "",
            "ib_hash": "980cee65",
            "position": "b5a29a7d",
            "normal_parts": [("Head", 0), ("Body", 32064), ("Dress", 79233)],
            "no_normal_parts": [],
        },
        {
            "name": "Chevreuse",
            "component": "",
            "ib_hash": "77208d51",
            "position": "4d8d965a",
            "normal_parts": [("Head", 0), ("Body", 45951)],
            "no_normal_parts": [],
        },
        {
            "name": "Citlali",
            "component": "",
            "ib_hash": "f81f893c",
            "position": "362dc30c",
            "normal_parts": [("Head", 0), ("Body", 27393)],
            "no_normal_parts": [],
        },
        {
            "name": "Clorinde",
            "component": "",
            "ib_hash": "d6371da1",
            "position": "07f8ad68",
            "normal_parts": [("Head", 0), ("Body", 41928), ("Dress", 69225)],
            "no_normal_parts": [],
        },
        {
            "name": "Collei",
            "component": "",
            "ib_hash": "3da6f8c7",
            "position": "348e58c4",
            "normal_parts": [("Head", 0), ("Body", 13077), ("Dress", 60117)],
            "no_normal_parts": [],
        },
        {
            "name": "Cyno",
            "component": "",
            "ib_hash": "af184471",
            "position": "226f076e",
            "normal_parts": [("Head", 0), ("Body", 17913), ("Dress", 54627)],
            "no_normal_parts": [],
        },
        {
            "name": "Dehya",
            "component": "",
            "ib_hash": "63e3e58e",
            "position": "9aeecbcb",
            "normal_parts": [("Head", 0), ("Body", 25566)],
            "no_normal_parts": [],
        },
        {
            "name": "Dori",
            "component": "",
            "ib_hash": "04929496",
            "position": "2a2a63ab",
            "normal_parts": [("Head", 0), ("Body", 22941)],
            "no_normal_parts": [],
        },
        {
            "name": "Emilie",
            "component": "",
            "ib_hash": "ad5364a7",
            "position": "62679081",
            "normal_parts": [
                ("Head", 0),
                ("Body", 27675),
                ("Dress", 66633),
                ("Extra", 77811),
            ],
            "no_normal_parts": [],
        },
        {
            "name": "Faruzan",
            "component": "",
            "ib_hash": "faad3720",
            "position": "6162188c",
            "normal_parts": [("Head", 0), ("Body", 33624)],
            "no_normal_parts": [("Dress", 66996)],
        },
        {
            "name": "Freminet",
            "component": "",
            "ib_hash": "6d40de64",
            "position": "86559a85",
            "normal_parts": [("Head", 0), ("Body", 36975)],
            "no_normal_parts": [("Dress", 73413)],
        },
        {
            "name": "Furina",
            "component": "",
            "ib_hash": "045e580b",
            "position": "8294fe98",
            "normal_parts": [("Head", 0), ("Body", 57279)],
            "no_normal_parts": [("Dress", 73413)],
        },
        {
            "name": "GaMing",
            "component": "",
            "ib_hash": "b5eb19b6",
            "position": "b94ef036",
            "normal_parts": [("Head", 0), ("Body", 21129)],
            "no_normal_parts": [],
        },
        {
            "name": "GaMing",
            "component": "Hood",
            "ib_hash": "6cb43453",
            "position": "ad952c56",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "GanyuTwilight",
            "component": "",
            "ib_hash": "cb283c86",
            "position": "9b3f356e",
            "normal_parts": [("Head", 0), ("Body", 50817), ("Dress", 74235)],
            "no_normal_parts": [],
        },
        {
            "name": "Iansan",
            "component": "",
            "ib_hash": "b5263389",
            "position": "6891e2e2",
            "normal_parts": [("Head", 0), ("Body", 33132), ("Dress", 79230)],
            "no_normal_parts": [],
        },
        {
            "name": "Kachina",
            "component": "",
            "ib_hash": "8f29c0bb",
            "position": "888c4b7c",
            "normal_parts": [("Head", 0), ("Body", 47910)],
            "no_normal_parts": [],
        },
        {
            "name": "Aino",
            "component": "Bangs",
            "ib_hash": "11bba20d",
            "position": "e1ae6ddb",
            "normal_parts": [("A", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Aino",
            "component": "Eyes",
            "ib_hash": "41ed9030",
            "position": "7273ff41",
            "normal_parts": [],
            "no_normal_parts": [("A", 0)],
        },
        {
            "name": "Aino",
            "component": "Body",
            "ib_hash": "3738cbb7",
            "position": "d94c8962",
            "normal_parts": [("A", 0), ("B", 26049)],
            "no_normal_parts": [],
        },
        {
            "name": "Aino",
            "component": "Tail",
            "ib_hash": "ed6830cc",
            "position": "51f2913e",
            "normal_parts": [("A", 0), ("B", 3036)],
            "no_normal_parts": [],
        },
        {
            "name": "Albedo",
            "component": "",
            "ib_hash": "0d7dc936",
            "position": "df65bb00",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 9933), ("Dress", 44766)],
        },
        {
            "name": "Aloy",
            "component": "",
            "ib_hash": "5d1da717",
            "position": "46de82f3",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 15879), ("Dress", 56955)],
        },
        {
            "name": "Amber",
            "component": "",
            "ib_hash": "b03c7e30",
            "position": "a2ea4b2d",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 5670)],
        },
        {
            "name": "Amber",
            "component": "",
            "ib_hash": "b41d4d94",
            "position": "557b2eff",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 5670)],
        },
        {
            "name": "AratakiItto",
            "component": "",
            "ib_hash": "be597118",
            "position": "3e61a41f",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 26520)],
        },
        {
            "name": "Barbara",
            "component": "",
            "ib_hash": "1bc3490d",
            "position": "85282151",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 12015), ("Dress", 46248)],
        },
        {
            "name": "Beidou",
            "component": "",
            "ib_hash": "fed42bef",
            "position": "51197c51",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 8253), ("Dress", 43851)],
        },
        {
            "name": "Bennett",
            "component": "",
            "ib_hash": "cdc66323",
            "position": "6cff51b4",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 9879)],
        },
        {
            "name": "Chongyun",
            "component": "",
            "ib_hash": "0c6dd2d6",
            "position": "489e3621",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 13656)],
        },
        {
            "name": "Diluc",
            "component": "",
            "ib_hash": "e16fa548",
            "position": "71625c4d",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 10896)],
        },
        {
            "name": "Diona",
            "component": "",
            "ib_hash": "740a72e3",
            "position": "e8083f19",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 11076)],
        },
        {
            "name": "Eula",
            "component": "",
            "ib_hash": "660399d1",
            "position": "107ba6e7",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 11349), ("Dress", 51639)],
        },
        {
            "name": "Fischl",
            "component": "",
            "ib_hash": "6428104d",
            "position": "bf6aef4d",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 11535), ("Dress", 42471)],
        },
        {
            "name": "Flins",
            "component": "Bangs",
            "ib_hash": "36713af5",
            "position": "4c608bb6",
            "normal_parts": [("A", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Ganyu",
            "component": "",
            "ib_hash": "1575ec63",
            "position": "a5169f1d",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 12822), ("Dress", 47160)],
        },
        {
            "name": "Gorou",
            "component": "",
            "ib_hash": "b2e57c84",
            "position": "3ce94cac",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 8022)],
        },
        {
            "name": "Heizou",
            "component": "",
            "ib_hash": "d4c9bab4",
            "position": "51a75ba6",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 27585)],
        },
        {
            "name": "HuTao",
            "component": "",
            "ib_hash": "3de1efe2",
            "position": "dd16576c",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 16509)],
        },
        {
            "name": "Jean",
            "component": "",
            "ib_hash": "115737ff",
            "position": "191af650",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 7779)],
        },
        {
            "name": "JeanCN",
            "component": "",
            "ib_hash": "aad861e0",
            "position": "93bb2522",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 7779)],
        },
        {
            "name": "KaedeharaKazuha",
            "component": "",
            "ib_hash": "356cdbde",
            "position": "7c0c47b3",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 7923), ("Dress", 47775)],
        },
        {
            "name": "Kaeya",
            "component": "",
            "ib_hash": "2b3f575a",
            "position": "8a081f34",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 7596), ("Dress", 47349)],
        },
        {
            "name": "KamisatoAyaka",
            "component": "",
            "ib_hash": "0cafd227",
            "position": "0107925f",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 11565), ("Dress", 58209)],
        },
        {
            "name": "KamisatoAyato",
            "component": "",
            "ib_hash": "e59b09d6",
            "position": "b473c856",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 29769), ("Dress", 66183)],
        },
        {
            "name": "Keqing",
            "component": "",
            "ib_hash": "cbf1894b",
            "position": "3aaf3e94",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 10824), ("Dress", 48216)],
        },
        {
            "name": "Klee",
            "component": "",
            "ib_hash": "073c71f5",
            "position": "dcd74904",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 8436)],
        },
        {
            "name": "KujouSara",
            "component": "",
            "ib_hash": "109b3f6c",
            "position": "b82eaa26",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 8877), ("Dress", 47193)],
        },
        {
            "name": "KukiShinobu",
            "component": "",
            "ib_hash": "ff16c309",
            "position": "7cfb62ea",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 22356)],
        },
        {
            "name": "Lisa",
            "component": "",
            "ib_hash": "518a6840",
            "position": "2a557add",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 16815), ("Dress", 45873)],
        },
        {
            "name": "Mona",
            "component": "",
            "ib_hash": "d75308d8",
            "position": "7a1dc890",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 17688)],
        },
        {
            "name": "MonaCN",
            "component": "",
            "ib_hash": "d5ad8084",
            "position": "515f3ce6",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 17688)],
        },
        {
            "name": "Ningguang",
            "component": "",
            "ib_hash": "ad75352c",
            "position": "f9e1b52b",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 12384), ("Dress", 47157)],
        },
        {
            "name": "Noelle",
            "component": "",
            "ib_hash": "9cf0789e",
            "position": "d1384d15",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 12915), ("Dress", 47910)],
        },
        {
            "name": "Qiqi",
            "component": "Body",
            "ib_hash": "56057a2c",
            "position": "cad5bebb",
            "normal_parts": [],
            "no_normal_parts": [("A", 0), ("B", 13488)],
        },
        {
            "name": "RaidenShogun",
            "component": "",
            "ib_hash": "7a583c12",
            "position": "e48c61f3",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 17769), ("Dress", 52473)],
        },
        {
            "name": "Razor",
            "component": "",
            "ib_hash": "1b36c8c9",
            "position": "4662c505",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 7071)],
        },
        {
            "name": "Rosaria",
            "component": "",
            "ib_hash": "65ccd309",
            "position": "748f40a5",
            "normal_parts": [],
            "no_normal_parts": [
                ("Head", 0),
                ("Body", 11139),
                ("Dress", 44088),
                ("Extra", 45990),
            ],
        },
        {
            "name": "RosariaCN",
            "component": "",
            "ib_hash": "bdca273e",
            "position": "59a1f8b1",
            "normal_parts": [],
            "no_normal_parts": [
                ("Head", 0),
                ("Body", 11025),
                ("Dress", 46539),
                ("Extra", 48441),
            ],
        },
        {
            "name": "SangonomiyaKokomi",
            "component": "",
            "ib_hash": "74900c81",
            "position": "dde4750a",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 26424), ("Dress", 52290)],
        },
        {
            "name": "Sayu",
            "component": "",
            "ib_hash": "d26fddb8",
            "position": "c70b7fce",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 8340)],
        },
        {
            "name": "Shenhe",
            "component": "",
            "ib_hash": "33a92492",
            "position": "e44b58b5",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 14385), ("Dress", 48753)],
        },
        {
            "name": "Sucrose",
            "component": "",
            "ib_hash": "06e86a68",
            "position": "b655c335",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 9036)],
        },
        {
            "name": "Tartaglia",
            "component": "",
            "ib_hash": "531d9358",
            "position": "186eac84",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 9261)],
        },
        {
            "name": "Thoma",
            "component": "",
            "ib_hash": "b2155854",
            "position": "24ecd71a",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 10782), ("Dress", 45258)],
        },
        {
            "name": "Venti",
            "component": "",
            "ib_hash": "1afcf31d",
            "position": "09a91a5c",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 7419)],
        },
        {
            "name": "Xiangling",
            "component": "",
            "ib_hash": "6bb79582",
            "position": "9427917d",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 11964), ("Dress", 48120)],
        },
        {
            "name": "Xiao",
            "component": "",
            "ib_hash": "ced409c1",
            "position": "9464bf2d",
            "normal_parts": [],
            "no_normal_parts": [
                ("Head", 0),
                ("Body", 13137),
                ("Dress", 49623),
                ("Extra", 51717),
            ],
        },
        {
            "name": "Xingqiu",
            "component": "",
            "ib_hash": "82c97b1c",
            "position": "25aed172",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 6132)],
        },
        {
            "name": "Xinyan",
            "component": "",
            "ib_hash": "97f78c9b",
            "position": "76ed85f0",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 21852)],
        },
        {
            "name": "YaeMiko",
            "component": "",
            "ib_hash": "5d09aa00",
            "position": "3a7f71f5",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 19968), ("Dress", 62868)],
        },
        {
            "name": "Yanfei",
            "component": "",
            "ib_hash": "776c5330",
            "position": "eb8b62d3",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 12501)],
        },
        {
            "name": "Yelan",
            "component": "",
            "ib_hash": "82e14ea2",
            "position": "c58c76f9",
            "normal_parts": [],
            "no_normal_parts": [
                ("Head", 0),
                ("Body", 20913),
                ("Dress", 51759),
                ("Extra", 54042),
            ],
        },
        {
            "name": "Yoimiya",
            "component": "",
            "ib_hash": "85777bb6",
            "position": "65618289",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 11418), ("Dress", 53652)],
        },
        {
            "name": "YunJin",
            "component": "",
            "ib_hash": "c632b8df",
            "position": "221f052e",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 11550), ("Dress", 56658)],
        },
        {
            "name": "Zhongli",
            "component": "",
            "ib_hash": "4c8480f5",
            "position": "a75ba32e",
            "normal_parts": [],
            "no_normal_parts": [("Head", 0), ("Body", 8976), ("Dress", 37530)],
        },
        {
            "name": "Kaveh",
            "component": "",
            "ib_hash": "5966a63f",
            "position": "b56fd424",
            "normal_parts": [("Head", 0), ("Body", 21831)],
            "no_normal_parts": [],
        },
        {
            "name": "Kirara",
            "component": "",
            "ib_hash": "f6e9af7d",
            "position": "b57d7fe2",
            "normal_parts": [("Head", 0), ("Body", 37128), ("Dress", 75234)],
            "no_normal_parts": [],
        },
        {
            "name": "Layla",
            "component": "",
            "ib_hash": "8ec3c0d8",
            "position": "2656ccca",
            "normal_parts": [("Head", 0), ("Body", 49878), ("Dress", 66474)],
            "no_normal_parts": [],
        },
        {
            "name": "LisaStudent",
            "component": "",
            "ib_hash": "f30eece6",
            "position": "37c70461",
            "normal_parts": [("Head", 0), ("Body", 29730)],
            "no_normal_parts": [],
        },
        {
            "name": "Lynette",
            "component": "",
            "ib_hash": "39d89255",
            "position": "98eb2db4",
            "normal_parts": [("Body", 16257), ("Extra", 68358)],
            "no_normal_parts": [("Dress", 65223)],
        },
        {
            "name": "Lyney",
            "component": "",
            "ib_hash": "09bcb0fd",
            "position": "6f7b7740",
            "normal_parts": [("Head", 0), ("Body", 16599)],
            "no_normal_parts": [("Dress", 63264)],
        },
        {
            "name": "Mavuika",
            "component": "Hair",
            "ib_hash": "f6c93dd3",
            "position": "039618b0",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Mavuika",
            "component": "Body",
            "ib_hash": "43f8af29",
            "position": "80b13a2f",
            "normal_parts": [("Head", 0), ("Body", 16914), ("Dress", 42618)],
            "no_normal_parts": [],
        },
        {
            "name": "Mika",
            "component": "",
            "ib_hash": "41760901",
            "position": "1876e82e",
            "normal_parts": [("Head", 0), ("Body", 21072)],
            "no_normal_parts": [],
        },
        {
            "name": "Mizuki",
            "component": "",
            "ib_hash": "ec1ed3c9",
            "position": "bbdaf598",
            "normal_parts": [("Head", 0), ("Body", 44274), ("Dress", 85404)],
            "no_normal_parts": [],
        },
        {
            "name": "Mualani",
            "component": "",
            "ib_hash": "c511e979",
            "position": "03872d46",
            "normal_parts": [("Head", 0), ("Body", 35445), ("Dress", 81135)],
            "no_normal_parts": [],
        },
        {
            "name": "Nahida",
            "component": "",
            "ib_hash": "9b13c166",
            "position": "7106f05d",
            "normal_parts": [
                ("Head", 0),
                ("Body", 31143),
                ("Dress", 71187),
                ("Extra", 76875),
            ],
            "no_normal_parts": [],
        },
        {
            "name": "Navia",
            "component": "",
            "ib_hash": "7321d0b1",
            "position": "f4e09bd7",
            "normal_parts": [("Head", 0), ("Body", 54342), ("Dress", 74844)],
            "no_normal_parts": [],
        },
        {
            "name": "Neuvillette",
            "component": "",
            "ib_hash": "f055eadd",
            "position": "cad3a022",
            "normal_parts": [("Body", 33879)],
            "no_normal_parts": [],
        },
        {
            "name": "Nilou",
            "component": "",
            "ib_hash": "1e8a5e3c",
            "position": "b2acc1df",
            "normal_parts": [("Head", 0), ("Body", 44844), ("Dress", 64080)],
            "no_normal_parts": [],
        },
        {
            "name": "Sethos",
            "component": "",
            "ib_hash": "2faea4e4",
            "position": "60d33d25",
            "normal_parts": [("Head", 0), ("Body", 38241)],
            "no_normal_parts": [],
        },
        {
            "name": "ShenheFrostFlower",
            "component": "",
            "ib_hash": "83a9116d",
            "position": "ee0980eb",
            "normal_parts": [
                ("Head", 0),
                ("Body", 31326),
                ("Dress", 66588),
                ("Extra", 70068),
            ],
            "no_normal_parts": [],
        },
        {
            "name": "Sigewinne",
            "component": "",
            "ib_hash": "072fe941",
            "position": "c883a144",
            "normal_parts": [("Head", 0), ("Body", 25077)],
            "no_normal_parts": [],
        },
        {
            "name": "Tighnari",
            "component": "",
            "ib_hash": "69a807fc",
            "position": "ed2e7d59",
            "normal_parts": [("Head", 0), ("Body", 44868), ("Dress", 59496)],
            "no_normal_parts": [],
        },
        {
            "name": "TravelerBoy",
            "component": "",
            "ib_hash": "8ed7c5f0",
            "position": "c77e380b",
            "normal_parts": [("Head", 0), ("Body", 8874)],
            "no_normal_parts": [],
        },
        {
            "name": "TravelerGirl",
            "component": "",
            "ib_hash": "e7612ed8",
            "position": "8239be13",
            "normal_parts": [("Head", 0), ("Body", 6915), ("Dress", 40413)],
            "no_normal_parts": [],
        },
        {
            "name": "Varesa",
            "component": "",
            "ib_hash": "488fceb4",
            "position": "9784dbe3",
            "normal_parts": [("Head", 0), ("Body", 40554)],
            "no_normal_parts": [],
        },
        {
            "name": "Wanderer",
            "component": "",
            "ib_hash": "6bba515c",
            "position": "0110e1c7",
            "normal_parts": [("Head", 0), ("Body", 17379)],
            "no_normal_parts": [],
        },
        {
            "name": "Wanderer",
            "component": "Hat",
            "ib_hash": "a16aff98",
            "position": "d74251a0",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Wriothesley",
            "component": "",
            "ib_hash": "9e62b4e7",
            "position": "aa6f1268",
            "normal_parts": [("Head", 0), ("Body", 11634)],
            "no_normal_parts": [],
        },
        {
            "name": "Wriothesley",
            "component": "Jacket",
            "ib_hash": "71be07bd",
            "position": "c351ac3a",
            "normal_parts": [("Head", 0), ("Body", 21042)],
            "no_normal_parts": [],
        },
        {
            "name": "Xianyun",
            "component": "",
            "ib_hash": "7f79ea6e",
            "position": "39838e8f",
            "normal_parts": [("Head", 0), ("Body", 29841), ("Dress", 65361)],
            "no_normal_parts": [],
        },
        {
            "name": "Xianyun",
            "component": "Glasses",
            "ib_hash": "4212b7da",
            "position": "d739f81b",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Xilonen",
            "component": "",
            "ib_hash": "4c2fa96d",
            "position": "a4571ede",
            "normal_parts": [("Head", 0), ("Body", 28959)],
            "no_normal_parts": [],
        },
        {
            "name": "Yaoyao",
            "component": "",
            "ib_hash": "6c14db37",
            "position": "293449d6",
            "normal_parts": [("Head", 0), ("Body", 21678)],
            "no_normal_parts": [],
        },
        {
            "name": "LyneyHat",
            "component": "",
            "ib_hash": "d2a5e79a",
            "position": "5caaa94b",
            "normal_parts": [("Head", 0), ("Body", 4374)],
            "no_normal_parts": [],
        },
        {
            "name": "MavuikasBike",
            "component": "",
            "ib_hash": "9bec497f",
            "position": "04b33215",
            "normal_parts": [("Head", 0), ("Body", 33744)],
            "no_normal_parts": [],
        },
        {
            "name": "NaviasQ",
            "component": "Cannon",
            "ib_hash": "5f7651ab",
            "position": "ff44e657",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "CapitanoNPCCloak",
            "component": "",
            "ib_hash": "a94429ab",
            "position": "f3989fd9",
            "normal_parts": [("Head", 0), ("Body", 18708)],
            "no_normal_parts": [],
        },
        {
            "name": "XilonenCoat",
            "component": "",
            "ib_hash": "24afd7b2",
            "position": "696ed18b",
            "normal_parts": [("Head", 0), ("Body", 8697)],
            "no_normal_parts": [],
        },
        {
            "name": "CandaceShield",
            "component": "",
            "ib_hash": "0954c0d3",
            "position": "6251a4f6",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "YaoyaoYuegui",
            "component": "",
            "ib_hash": "7248d12e",
            "position": "b0ec158e",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "HuntersPath",
            "component": "",
            "ib_hash": "36445316",
            "position": "152282fa",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "CashflowSupervision",
            "component": "",
            "ib_hash": "8e975f87",
            "position": "3b66aa8b",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "JadefallsSplendor",
            "component": "",
            "ib_hash": "15f3d889",
            "position": "d45c086d",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Tullaytullah'sRemembrance",
            "component": "",
            "ib_hash": "0c24d18c",
            "position": "c9a25c6f",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "EarthShaker",
            "component": "",
            "ib_hash": "be98e803",
            "position": "eda1ca6b",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "PortablePowerSaw",
            "component": "",
            "ib_hash": "b78cbb5c",
            "position": "204bf674",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "PortablePowerSaw",
            "component": "Bulb",
            "ib_hash": "a4ee89d6",
            "position": "f1b9ddc0",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Verdict",
            "component": "",
            "ib_hash": "360f93cd",
            "position": "ddf822c4",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "FootprintOfTheRainbow",
            "component": "",
            "ib_hash": "e3489a1e",
            "position": "da07544a",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "CalamityOfEshu",
            "component": "",
            "ib_hash": "4c2cd253",
            "position": "aec47e09",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "TheDockhandsAssistant",
            "component": "",
            "ib_hash": "f849c6a9",
            "position": "2cbb1d41",
            "normal_parts": [("Head", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "KeyOfKhajNisut",
            "component": "",
            "ib_hash": "e27ca3cd",
            "position": "49d0fdd7",
            "normal_parts": [("Head", 0)],
        },
        {
            "name": "Escoffier",
            "component": "",
            "ib_hash": "7ad7e69e",
            "position": "1569d000",
            "normal_parts": [("Head", 0), ("Body", 59307), ("Dress", 69753)],
            "no_normal_parts": [("Extra", 87798)],
        },
        {
            "name": "Ifa",
            "component": "Body",
            "ib_hash": "d561fadc",
            "position": "845f14ca",
            "normal_parts": [("A", 0), ("B", 48570), ("C", 73152)],
            "no_normal_parts": [],
        },
        {
            "name": "Skirk",
            "component": "FrontHair",
            "ib_hash": "74811ddf",
            "position": "1d025d3b",
            "normal_parts": [("A", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Skirk",
            "component": "Body",
            "ib_hash": "1fbe8217",
            "position": "9ce8105a",
            "normal_parts": [],
            "no_normal_parts": [("A", 0)],
        },
        {
            "name": "Skirk",
            "component": "Eyes",
            "ib_hash": "a831e5b5",
            "position": "02c3f76e",
            "normal_parts": [],
            "no_normal_parts": [("A", 0)],
        },
        {
            "name": "Skirk",
            "component": "Skirt",
            "ib_hash": "056da8f3",
            "position": "1795d9cb",
            "normal_parts": [],
            "no_normal_parts": [("A", 0)],
        },
        {
            "name": "Skirk",
            "component": "BackHair",
            "ib_hash": "dafe18b6",
            "position": "a788689b",
            "normal_parts": [("A", 0)],
            "no_normal_parts": [("B", 13650)],
        },
        {
            "name": "SkirkAlt",
            "component": "Torso",
            "ib_hash": "ac3db451",
            "position": "2711cd82",
            "normal_parts": [],
            "no_normal_parts": [("A", 0), ("B", 35019)],
        },
        # {
        #     "name": "BennettSkin",
        #     "component": "",
        #     "ib_hash": "00000000",
        #     "position": "00000000",
        #     "normal_parts": [("Head", 0), ("Body", 10000)],
        #     "no_normal_parts": [],
        # },
        # {
        #     "name": "YelanSkin",
        #     "component": "",
        #     "ib_hash": "00000000",
        #     "position": "00000000",
        #     "normal_parts": [("Head", 0), ("Body", 10000), ("Dress", 20000)],
        #     "no_normal_parts": [],
        # },
        {
            "name": "Ineffa",
            "component": "Eyes",
            "ib_hash": "6f8c4af6",
            "position": "1a349f1a",
            "normal_parts": [],
            "no_normal_parts": [("A", 0)],
        },
        {
            "name": "Ineffa",
            "component": "Bangs",
            "ib_hash": "79353adc",
            "position": "3ee713f6",
            "normal_parts": [("A", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Ineffa",
            "component": "Body",
            "ib_hash": "8a61684d",
            "position": "29fbb239",
            "normal_parts": [("A", 0), ("B", 26166)],
            "no_normal_parts": [],
        },
        {
            "name": "Lauma",
            "component": "Bangs",
            "ib_hash": "5a1345c9",
            "position": "f25edf24",
            "normal_parts": [("A", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Lauma",
            "component": "Eyes",
            "ib_hash": "c3e809a5",
            "position": "7e27b643",
            "normal_parts": [],
            "no_normal_parts": [("A", 0)],
        },
        {
            "name": "Lauma",
            "component": "Body",
            "ib_hash": "ce158bd6",
            "position": "89e96109",
            "normal_parts": [("A", 0), ("C", 75702)],
            "no_normal_parts": [("B", 19074)],
        },
        {
            "name": "Lauma",
            "component": "Horns",
            "ib_hash": "7306ff89",
            "position": "504a7d20",
            "normal_parts": [],
            "no_normal_parts": [("A", 0)],
        },
        {
            "name": "Nefer",
            "component": "Bangs",
            "ib_hash": "5a665e02",
            "position": "1bf11413",
            "normal_parts": [("A", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Nefer",
            "component": "Body",
            "ib_hash": "606a6e40",
            "position": "be085382",
            "normal_parts": [("A", 0), ("B", 31560), ("C", 77442)],
            "no_normal_parts": [],
        },
        {
            "name": "Nefer",
            "component": "CapeSide",
            "ib_hash": "345cb65a",
            "position": "5a2cf942",
            "normal_parts": [("A", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Nefer",
            "component": "CapeMiddle",
            "ib_hash": "e46f6e57",
            "position": "e3f60e00",
            "normal_parts": [("A", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Nefer",
            "component": "CapeGlow",
            "ib_hash": "cd690a66",
            "position": "004b76c5",
            "normal_parts": [("A", 0)],
            "no_normal_parts": [],
        },
        {
            "name": "Nefer",
            "component": "Eyes",
            "ib_hash": "6a090a16",
            "position": "e6b32dac",
            "normal_parts": [],
            "no_normal_parts": [("A", 0)],
        },
    ]

    to_print: list[str] = [f"INI file found!: {os.path.join(r, file)}"]

    try:
        with open(os.path.join(r, file), "r", encoding="cp1252") as open_file:
            lines = open_file.readlines()
            used_encoding = "cp1252"
    except (UnicodeDecodeError, UnicodeError):
        try:
            with open(os.path.join(r, file), "r", encoding="utf-8") as open_file:
                lines = open_file.readlines()
                used_encoding = "utf-8"
        except Exception as e:
            print(f"ERROR: Could not read file {file}: {e}")
            return
    
    og_lines = lines.copy()

    if args.force:
        lines = remove_orfix(lines, to_print)
    if not args.ignoreshaderfix:
        lines = remove_old_shaderfix(lines, to_print)
    lines = apply_orfix(lines, chara_name_position_ib_hash, args, to_print)

    # if the file changed Create backup file and write new file
    if og_lines != lines:
        # Write back using the same encoding (CP1252 for 3DMigoto compatibility)
        with open(os.path.join(r, file), "w", encoding="cp1252") as newfile:
            newfile.writelines(lines)

        # Create backup with datetime stamp
        datetime_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = (
            f"Backup_ORFIX_Applier_{file.replace('.ini', '')}_{datetime_stamp}.txt"
        )
        with open(os.path.join(r, backup_file), "w", encoding="cp1252") as file:
            file.writelines(og_lines)
        to_print.append(f"\tBackup file created: {backup_file}")
    else:
        if args.nonverbose:
            return
        to_print.append("\tNo changes needed for this file. Skipping...")
    text_to_print: str = "\n".join(to_print)
    print(text_to_print)


def main() -> None:
    """Main function to apply ORFIX to character.ini files"""
    parser = argparse.ArgumentParser(description="Apply ORFIX to character.ini")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forcefully removes past applications of ORFix before applying new ones. It might help in poorly formatted merged inis.",
    )
    parser.add_argument(
        "-im", "--merged", action="store_true", help="ORFIX ignore to merged.ini"
    )
    parser.add_argument(
        "-ic", "--ignorechar", action="store_true", help="ORFIX ignore character.ini"
    )
    parser.add_argument(
        "-isf",
        "--ignoreshaderfix",
        action="store_true",
        help="ORFIX ignore chara file that has shader fix script applied",
    )
    parser.add_argument(
        "-id",
        "--ignoredisabled",
        action="store_true",
        help="ORFIX ignore file begin with DISABLED",
    )
    parser.add_argument(
        "-un",
        "--usename",
        action="store_true",
        help="ORFIX detect using character name if no matching hash found",
    )
    parser.add_argument(
        "-nv",
        "--nonverbose",
        action="store_true",
        help="Won't print unless the file was changed",
    )
    parser.add_argument(
        "--undo",
        action="store_true",
        help="Restore files from backup files created by previous ORFIX applications",
    )
    args = parser.parse_args()

    # Handle undo functionality
    if args.undo:
        undo_orfix_changes()
        return

    curr_game_v: str = "5.5 first half"
    input(
        "IMPORTANT:\n\n"
        + f"\tORFIXApplier only works for character released up to genshin patch {curr_game_v}.\n"
        + f"\tCheck for newer version if the character is release after {curr_game_v} patch.\n"
        + "\tPress Enter to start applying ORFIX\n"
    )

    for r, _, f in os.walk(".\\"):
        for file in f:
            if (
                not file.lower().endswith(".ini")
                or file.lower().endswith("desktop.ini")
                or file.lower().endswith("orfix.ini")
                or "BufferValues" in os.path.join(r, file)
                or "NOAPP" in os.path.join(r, file)
                or "NOAPPLIER" in os.path.join(r, file)
                or (args.ignoredisabled and file.lower().startswith("disabled"))
                or (args.merged and file.lower().startswith("merged"))
            ):
                continue
            process_ini(r, file, args)
    print("\nDone! C12H22O11")


def check_python_version(version: tuple[int, int]) -> None:
    """Check if the script is running on Python X or higher"""
    if sys.version_info < version:
        input(
            f"This script requires Python {version[0]}.{version[1]} or higher.\n"
            "Please update your Python version and try again. Press enter to exit."
        )
        sys.exit(1)


if __name__ == "__main__":
    try:
        check_python_version((3, 11))
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\nPress Enter to exit...")
