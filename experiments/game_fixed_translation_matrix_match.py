"""Qualify the fixed-point translation-matrix constructor and overflow closure."""

from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import struct
import subprocess

from tools.experiments.game_actor_state_tick_integration import elf_slot_offset, symbol_rows
from tools.experiments.game_four_head_lookup_match import payload
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, parse_object, read_c_string


FUNCTION = "func_150A7D00"
PRIVATE = "__retail_overflow_" + FUNCTION
OWNER = "game_D51B0"
ENTRY = 0x150A7D00
ROM = 0xD51B0
SIZE = 160
WORDS = 40
PRIVATE_ENTRY = 0x15F005E4
PRIVATE_SIZE = 172
ROM_CURSOR_DELTA = 176
SOURCE = "conker/src/game_D51B0.c"
OBJECT = "conker/build/src/game_D51B0.c.o"
BUILD = "conker/build/game-fixed-translation-matrix-150A7D00-match"
RAW_SHA = "64d82d1b5d5f3dd442ca6d724034018ac8a0be6de25f73507801e5d3db7fe566"
RETAIL_SHA = "39eb5fa689bd570e196daf99f4d7df5fa78711afad16195dbca92f1df5f026c1"
EXPECTED_WARNING = "cc: Warning: -mips3 should not be used for ucode 32-bit compiles"

PATHS = {
    "source": SOURCE,
    "object": OBJECT,
    "elf": "conker/build/conker.us.elf",
    "map": "conker/build/conker.us.map",
    "linker": "conker/build/conker.ld",
    "makefile": "conker/Makefile",
    "guards": "conker/retail_word_patches.us.csv",
    "layout": "conker/retail_layout.us.txt",
    "progress": "conker/progress.csv",
    "rom": "conker/conker.us.bin",
    "sdk_asm": "tools/ultralib/src/mgu/translate.s",
    "sdk_c": "tools/ultralib/src/gu/translate.c",
}

BASELINE = {
    "source": "c66b4becd8251396c9cba79244951d09c5c0e5b9697ab6aa241d61c8ad116004",
    "object": "0887d13f7da6397aa1d0d3036759ae3ab3fae2d3d66be6f52df1771a301b949e",
    "elf": "9bd8b47f72c3aaf7cd478dd013d3505e361582e94800f9d90ae1646a98ea3166",
    "map": "ebb679dbafe5095950abc7ea997853701ce7cf975c8529cf54230dc13f2f0b51",
    "linker": "6479ca7cef48dc77d746c16afcc244de6bfb80c6789ba79a03d6f110e42a98d5",
    "makefile": "6c359d9fec730f4f53b612e9babd43ede1df1d006de553fd447e6301a993aa3c",
    "guards": "37ccb6fa579487bf28e1399022df648c259213cdb908cb8b2ae2376d24462a20",
    "layout": "1eb1e705545ec2e19f6b68ef5025d816f4d513684518968a6806008b6dc17612",
    "progress": "96a7f15ab5207027a204f795e91b8f9f3453482ce4ec4d47bd8bcb4b5a305502",
    "rom": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "sdk_asm": "4a289e0aaf60f9b3adb9a23e885930be1404ab4217c479b278375519e7b7458e",
    "sdk_c": "a5c6a9a5d5c2e8dc38c2a3ae3b50eb0b5a086377dc8d5625b2b37652f428f141",
}

SELECTED = '''#include <ultra64.h>

/* Build an N64 fixed-point translation matrix from three floating-point offsets. */
void func_150A7D00(volatile s16 *matrix, f32 x, f32 y, f32 z) {
    s32 fixedX = x * 65536.0f;
    s32 fixedY = y * 65536.0f;
    s32 fixedZ = z * 65536.0f;
    u64 *words = (u64 *)matrix;

    words[0] = 0;
    words[1] = 0;
    words[2] = 0;
    words[3] = 0;
    words[4] = 0;
    words[5] = 0;
    words[6] = 0;
    words[7] = 0;
    matrix[0] = 1;
    matrix[5] = 1;
    matrix[10] = 1;
    matrix[15] = 1;
    matrix[12] = fixedX >> 16;
    matrix[13] = fixedY >> 16;
    matrix[14] = fixedZ >> 16;
    matrix[28] = fixedX;
    matrix[29] = fixedY;
    matrix[30] = fixedZ;
}
'''

PROFILE = """# This fixed-translation leaf uses retail's eight 64-bit zero stores.
$(BUILD_DIR)/$(SRC_DIR)/game_D51B0.c.o: MIPSBIT := -mips3

"""
PROFILE_MARKER = "# uses native 64-bit ops (func_150ADA20's PRNG step) - needs MIPS III, not\n"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def before_path(output, key):
    return output / ("before-" + key)


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    manifest = output / "baseline.json"
    if not manifest.exists():
        values = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: digest(data) for key, data in values.items()}
        if hashes != BASELINE:
            raise ValueError("Changed fixed-translation baseline: " + repr(hashes))
        for key, data in values.items():
            before_path(output, key).write_bytes(data)
        manifest.write_text(json.dumps(BASELINE, indent=2) + "\n")
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError("Modified fixed-translation baseline manifest")
    for key, expected in BASELINE.items():
        if digest(before_path(output, key).read_bytes()) != expected:
            raise ValueError("Modified fixed-translation frozen input: " + key)
    return {key: before_path(output, key) for key in PATHS}


def compiler_command(root, source, obj):
    includes = [".", "include", "include/2.0L", "include/2.0L/PR", "include/libc",
                "src/libultra/os", "src/libultra/audio", "src/libultra/io"]
    return [str(root / "ido/ido5.3_recomp/cc"), "-c", "-32", "-G", "0",
        "-Xfullwarn", "-Xcpluscomm", "-signed", "-nostdinc", "-non_shared",
        "-Wab,-r4300_mul", "-D_LANGUAGE_C", "-D_FINALROM", "-DF3DEX_GBI_2",
        "-D_MIPS_SZLONG=32", "-woff", "649,838",
        *[item for path in includes for item in ("-I", path)],
        "-O2", "-g3", "-mips3", "-o32", "-o", str(obj), str(source)]


def compile_candidate(root, output, source=SELECTED, name="candidate"):
    raw = output / (name + ".c")
    obj = output / (name + ".o")
    raw.write_text(source)
    command = compiler_command(root, raw.relative_to(root / "conker"),
                               obj.relative_to(root / "conker"))
    result = subprocess.run(command, cwd=root / "conker", capture_output=True, text=True)
    diagnostics = (result.stdout + result.stderr).strip()
    (output / (name + "-diagnostics.txt")).write_text(diagnostics + ("\n" if diagnostics else ""))
    if result.returncode or diagnostics != EXPECTED_WARNING:
        raise ValueError("Unexpected fixed-translation compiler result: " + diagnostics)
    return obj


def checked_candidate(obj):
    raw, bindings = payload(obj, FUNCTION)
    if (len(raw), digest(raw), bindings) != (SIZE, RAW_SHA, {}):
        raise ValueError("Fixed-translation raw payload changed")
    return raw


def complete_symbol(obj):
    data, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = data[info["value"]:info["value"] + info["size"]]
    selected = {at - info["value"]: rows for at, rows in bindings.items()
                if info["value"] <= at < info["value"] + info["size"]}
    return raw, selected, functions


def guard_manifest(before, raw, retail):
    if (len(raw), digest(raw), len(retail), digest(retail)) != (
            SIZE, RAW_SHA, SIZE, RETAIL_SHA):
        raise ValueError("Fixed-translation guard input changed")
    stream = io.StringIO(before.decode(), newline="")
    reader = csv.DictReader(stream)
    fields = reader.fieldnames
    expected_fields = ["filename", "function", "offset", "expected", "replacement",
        "expected_relocations", "replacement_relocations", "note", "insert_after",
        "insert_after_relocations", "omit"]
    if fields != expected_fields or any(row["function"] == FUNCTION for row in reader):
        raise ValueError("Fixed-translation guard predecessor changed")
    old_words = struct.unpack(">40I", raw)
    new_words = struct.unpack(">40I", retail)
    newline = "\r\n" if before.endswith(b"\r\n") else "\n"
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator=newline)
    count = 0
    for index, (old, new) in enumerate(zip(old_words, new_words)):
        if old == new:
            continue
        writer.writerow({"filename": OWNER, "function": FUNCTION,
            "offset": "0x%03X" % (index * 4), "expected": "0x%08X" % old,
            "replacement": "0x%08X" % new, "expected_relocations": "-",
            "replacement_relocations": "-",
            "note": "Normalize fixed-translation matrix handwritten scheduling",
            "insert_after": "", "insert_after_relocations": "", "omit": "false"})
        count += 1
    if count != 39:
        raise ValueError("Fixed-translation guard count changed: %d" % count)
    return before + output.getvalue().encode()


def recovered_makefile(before):
    if before.count(PROFILE_MARKER) != 1 or PROFILE in before:
        raise ValueError("Fixed-translation Makefile marker changed")
    return before.replace(PROFILE_MARKER, PROFILE + PROFILE_MARKER, 1)


def build_padded(root, output, candidate, guards):
    padded = output / "qualified-padded.s"
    qualified = output / "qualified-padded.o"
    subprocess.run(["python3", str(root / "tools/pad_c_object.py"), str(candidate),
        str(root / "conker/retail_layout.us.txt"), OWNER, str(padded),
        "--word-patches", str(guards)], cwd=root / "conker", check=True,
        capture_output=True, text=True)
    subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(qualified),
        str(padded)], check=True, capture_output=True, text=True)
    raw, bindings, functions = complete_symbol(qualified)
    if raw != (root / "conker/conker.us.bin").read_bytes()[ROM:ROM + SIZE] or bindings:
        raise ValueError("Fixed-translation padded object differs from retail")
    if PRIVATE in functions:
        raise ValueError("Fixed-translation padded object retained overflow body")
    return qualified


def replay_make_recipe(root, output, proposed_makefile, proposed_source, guards, qualified):
    command = ["make", "-f", str(proposed_makefile.relative_to(root / "conker")),
               "-n", "-B", "build/src/game_D51B0.c.o"]
    plan = subprocess.run(command, cwd=root / "conker", capture_output=True,
                          text=True, check=True).stdout.splitlines()
    plan = [line for line in plan if line and not line.startswith("Makefile:")]
    if len(plan) != 4 or "-mips3" not in plan[0] or "src/game_D51B0.c" not in plan[0]:
        raise ValueError("Fixed-translation Make recipe changed: " + repr(plan))
    (output / "Make-commands.json").write_text(json.dumps(plan, indent=2) + "\n")
    shadow = output / "make-shadow/src"
    shadow.mkdir(parents=True, exist_ok=True)
    compact = shadow / "game_D51B0.c.o.compact"
    padded = shadow / "game_D51B0.c.o.padded.s"
    final = shadow / "game_D51B0.c.o"
    result = subprocess.run(compiler_command(root, proposed_source.relative_to(root / "conker"),
        compact.relative_to(root / "conker")), cwd=root / "conker", capture_output=True, text=True)
    diagnostics = (result.stdout + result.stderr).strip()
    if result.returncode or diagnostics != EXPECTED_WARNING:
        raise ValueError("Fixed-translation Make compiler replay changed: " + diagnostics)
    subprocess.run(["python3", str(root / "tools/pad_c_object.py"), str(compact),
        str(root / "conker/retail_layout.us.txt"), OWNER, str(padded),
        "--word-patches", str(guards)], cwd=root / "conker", check=True,
        capture_output=True, text=True)
    subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(final),
        str(padded)], check=True, capture_output=True, text=True)
    if final.read_bytes() != qualified.read_bytes():
        raise ValueError("Fixed-translation Make replay object differs")
    return final


def predict_image(before, retail):
    if digest(before) != BASELINE["elf"] or (len(retail), digest(retail)) != (SIZE, RETAIL_SHA):
        raise ValueError("Fixed-translation image input changed")
    header = list(ELF_HEADER.unpack_from(before))
    sections = [list(SECTION_HEADER.unpack_from(before, header[6] + i * header[11]))
                for i in range(header[12])]
    if header[12:] != [12, 11]:
        raise ValueError("Fixed-translation ELF section inventory changed")
    names = before[sections[11][4]:sections[11][4] + sections[11][5]]
    if [read_c_string(names, row[0]) for row in sections][8:] != [
            ".game_overflow", ".symtab", ".strtab", ".shstrtab"]:
        raise ValueError("Fixed-translation terminal sections changed")
    overflow, symtab, strtab = sections[8], sections[9], sections[10]
    strings = before[strtab[4]:strtab[4] + strtab[5]]
    symbols = [list(SYMBOL.unpack_from(before, at))
               for at in range(symtab[4], symtab[4] + symtab[5], 16)]
    symbol_names = [read_c_string(strings, row[0]) for row in symbols]
    deleted_index = symbol_names.index(PRIVATE)
    file_name = "game_D51B0.c.o"
    file_index = symbol_names.index(file_name)
    removed = symbols[deleted_index]
    if symbol_names.count(PRIVATE) != 1 or tuple(removed[1:]) != (
            PRIVATE_ENTRY, PRIVATE_SIZE, 2, 0, 8):
        raise ValueError("Fixed-translation private definition changed")
    if symbol_names.count(file_name) != 1 or tuple(symbols[file_index][1:]) != (
            0, 0, 4, 0, 0xFFF1):
        raise ValueError("Fixed-translation owner file symbol changed")
    cut_va, length = removed[1:3]
    end_va = cut_va + length
    moved = {name: row[1] for name, row in zip(symbol_names, symbols)
             if row[5] == 8 and end_va <= row[1] < overflow[3] + overflow[5]}
    if set(moved) != {"__retail_overflow_func_15125490"}:
        raise ValueError("Fixed-translation moved-private set changed")
    root_index = symbol_names.index(FUNCTION)
    root = symbols[root_index]
    if tuple(root[1:]) != (ENTRY, SIZE, 18, 0, 5):
        raise ValueError("Fixed-translation canonical definition changed")
    prefix = bytearray(before[:overflow[4]])
    target_at = elf_slot_offset(before, ENTRY, SIZE)
    if struct.unpack_from(">I", prefix, target_at)[0] != (
            0x08000000 | ((PRIVATE_ENTRY >> 2) & 0x03FFFFFF)):
        raise ValueError("Fixed-translation predecessor is not its trampoline")
    prefix[target_at:target_at + SIZE] = retail

    by_name = dict(zip(symbol_names, symbols))
    trampolines = []
    for private, old_address in moved.items():
        canonical = private.removeprefix("__retail_overflow_")
        row = by_name[canonical]
        at = elf_slot_offset(before, row[1], 4)
        word = struct.unpack_from(">I", before, at)[0]
        if word == 0x08000000 | ((old_address >> 2) & 0x03FFFFFF):
            struct.pack_into(">I", prefix, at,
                0x08000000 | (((old_address - length) >> 2) & 0x03FFFFFF))
            trampolines.append(canonical)
    if trampolines:
        raise ValueError("Fixed-translation retargeted-trampoline set changed")
    scanned = []
    for section in sections[1:9]:
        if not (section[2] & 4):
            continue
        for offset in range(0, section[5], 4):
            at = section[4] + offset
            word = struct.unpack_from(">I", before, at)[0]
            if word >> 26 not in (2, 3):
                continue
            address = ((section[3] + offset + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
            if address in moved.values():
                scanned.append(at)
    if set(scanned) != {elf_slot_offset(before, by_name[name][1], 4)
                        for name in trampolines}:
        raise ValueError("Fixed-translation private jump closure changed")

    cut_string = removed[0]
    old_name = PRIVATE.encode() + b"\0"
    if strings[cut_string:cut_string + len(old_name)] != old_name:
        raise ValueError("Fixed-translation private string changed")
    root_text = FUNCTION.encode() + b"\0"
    if root[0] != cut_string + len("__retail_overflow_"):
        raise ValueError("Fixed-translation shared public-name suffix changed")
    file_string = symbols[file_index][0]
    file_text = file_name.encode() + b"\0"
    if strings[file_string:file_string + len(file_text)] != file_text:
        raise ValueError("Fixed-translation owner file string changed")
    removals = sorted(((file_string, file_text), (cut_string, old_name)))
    if removals[0][0] + len(removals[0][1]) > removals[1][0]:
        raise ValueError("Fixed-translation removed strings overlap")

    def compact_offset(offset):
        reduction = 0
        for start, text in removals:
            if start <= offset < start + len(text):
                raise ValueError("Unexpected shared fixed-translation string")
            if start + len(text) <= offset:
                reduction += len(text)
        return offset - reduction

    if symbol_names[root_index - 1:root_index + 2] != [
            "func_151D2258", FUNCTION, "func_1000E17C"]:
        raise ValueError("Fixed-translation global symbol ordering changed")
    insertion_old = (symbols[root_index - 1][0]
                     + len(symbol_names[root_index - 1].encode()) + 1)
    insertion = compact_offset(insertion_old)
    compact_parts = []
    cursor = 0
    for start, text in removals:
        compact_parts.append(strings[cursor:start])
        cursor = start + len(text)
    compact_parts.append(strings[cursor:])
    compact = b"".join(compact_parts)
    new_strings = compact[:insertion] + root_text + compact[insertion:]
    if len(new_strings) != len(strings) - len("__retail_overflow_") - len(file_text):
        raise ValueError("Fixed-translation compact string table changed")

    new_symbols = []
    for index, (name, row) in enumerate(zip(symbol_names, symbols)):
        if index in (deleted_index, file_index):
            continue
        fresh = row[:]
        if name == FUNCTION:
            fresh[0] = insertion
        else:
            at = compact_offset(row[0])
            fresh[0] = at + (len(root_text) if at >= insertion else 0)
        if read_c_string(new_strings, fresh[0]) != name:
            raise ValueError("Fixed-translation symbol-string rewrite changed")
        if name in moved:
            fresh[1] -= length
        if name in ("__romPos", "debugger_overflow_ROM_START"):
            if tuple(row[1:]) != (0x25ACE0, 0, 16, 0, 0xFFF1):
                raise ValueError("Fixed-translation absolute ROM symbol changed")
            fresh[1] -= ROM_CURSOR_DELTA
        new_symbols.append(fresh)
    new_symtab = b"".join(SYMBOL.pack(*row) for row in new_symbols)
    old_overflow = before[overflow[4]:overflow[4] + overflow[5]]
    cut = cut_va - overflow[3]
    new_overflow = old_overflow[:cut] + old_overflow[cut + length:]
    if len(new_overflow) != 0x64C:
        raise ValueError("Fixed-translation overflow size changed")

    result = prefix
    payloads = {8: new_overflow, 9: new_symtab, 10: new_strings,
                11: before[sections[11][4]:sections[11][4] + sections[11][5]]}
    for index in range(8, 12):
        section = sections[index]
        alignment = max(1, section[8])
        result.extend(b"\0" * ((-len(result)) % alignment))
        section[4] = len(result)
        section[5] = len(payloads[index])
        result.extend(payloads[index])
    sections[9][7] -= 2
    result.extend(b"\0" * ((-len(result)) % 4))
    header[6] = len(result)
    result.extend(b"".join(SECTION_HEADER.pack(*row) for row in sections))
    result[:ELF_HEADER.size] = ELF_HEADER.pack(*header)
    program = struct.Struct(">8I")
    changed = 0
    for index in range(header[10]):
        at = header[5] + index * header[9]
        row = list(program.unpack_from(before, at))
        if row[2] == 0x15F00000:
            if row[4:6] != [0x6F8, 0x6F8]:
                raise ValueError("Fixed-translation overflow program header changed")
            row[4] -= length
            row[5] -= length
            program.pack_into(result, at, *row)
            changed += 1
    if changed != 1:
        raise ValueError("Fixed-translation overflow segment count changed")
    proof = {"removed_private_body": PRIVATE, "removed_body_bytes": length,
        "removed_owner_file_symbol": file_name,
        "moved_private_definitions": moved,
        "retargeted_trampolines": trampolines,
        "rom_cursor_bytes_removed": ROM_CURSOR_DELTA,
        "strict_exclusions": 0}
    return bytes(result), proof


def link_private_image(root, output, qualified, baseline):
    old = "build/src/game_D51B0.c.o"
    new = str(qualified.relative_to(root / "conker")).replace("\\", "/")
    script_text = baseline["linker"].read_text()
    if script_text.count(old) != 1:
        raise ValueError("Fixed-translation linker owner references changed")
    script = output / "first-link.ld"
    script.write_text(script_text.replace(old, new))
    elf = output / "first-linked.elf"
    map_path = output / "first-linked.map"
    subprocess.run(["mips-linux-gnu-ld", "-T", str(script.relative_to(root / "conker")),
        "-Map", str(map_path.relative_to(root / "conker")), "-T", "undefined_syms.us.txt",
        "-T", "undefined_funcs.us.txt", "-T", "undefined_syms_auto.txt", "-T",
        "undefined_funcs_auto.txt", "--no-check-sections", "--no-warn-mismatch", "-o",
        str(elf.relative_to(root / "conker"))], cwd=root / "conker", check=True,
        capture_output=True, text=True)
    retail = baseline["rom"].read_bytes()[ROM:ROM + SIZE]
    expected, proof = predict_image(baseline["elf"].read_bytes(), retail)
    (output / "expected-conker.us.elf").write_bytes(expected)
    if elf.read_bytes() != expected:
        raise ValueError("Fixed-translation private link differs from independent prediction")
    (output / "overflow-prediction.json").write_text(json.dumps(proof, indent=2) + "\n")
    return elf, map_path, expected


def closure_audit(before_path, after_path):
    from tools.match_progress import load_elf_functions
    before = before_path.read_bytes()
    after = after_path.read_bytes()
    old, _, old_addresses = load_elf_functions(str(before_path), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(str(after_path), "mips-linux-gnu-objdump")
    if set(old) - set(new) != {PRIVATE} or set(new) - set(old):
        raise ValueError("Fixed-translation function inventory changed")
    changed = []
    for name, words in new.items():
        expected_address = old_addresses[name] - (
            PRIVATE_SIZE if name == "__retail_overflow_func_15125490" else 0)
        if new_addresses[name] != expected_address:
            raise ValueError("Fixed-translation function address changed: " + name)
        if name == FUNCTION:
            slot = elf_slot_offset(after, ENTRY, SIZE)
            if digest(after[slot:slot + SIZE]) != RETAIL_SHA:
                raise ValueError("Fixed-translation target is not retail exact")
            changed.append(name)
            continue
        if new[name] != words:
            raise ValueError("Fixed-translation executable body changed: " + name)
        if not name.startswith("__retail_overflow_") and new_addresses[name] != old_addresses[name]:
            raise ValueError("Fixed-translation canonical address moved: " + name)
    result = {"functions_before": len(old), "functions_after": len(new),
        "removed_private_body": PRIVATE,
        "moved_private_bodies": ["__retail_overflow_func_15125490"],
        "changed_canonical_bodies": changed,
        "all_canonical_addresses_fixed": True, "strict_exclusions": 0}
    return result


def map_closure(path):
    text = path.read_text(errors="replace")
    checks = [".game_overflow  0x15f00000      0x64c load address 0x0025a5e0",
              "0x15f005e4       0x68 build/src/game_14FF90.c.o",
              "0x0025ac30                        debugger_overflow_ROM_START"]
    if not all(item in text for item in checks) or PRIVATE in text:
        raise ValueError("Fixed-translation linker-map closure changed")
    if re.search(r"\.game_overflow\s*\n\s*0x15f[0-9a-f]+\s+0x[0-9a-f]+ .*game_D51B0", text):
        raise ValueError("Fixed-translation owner retained overflow allocation")
    return {"overflow_size": 0x64C, "successor_address": 0x15F005E4,
            "rom_cursor": 0x25AC30, "target_owner_overflow_removed": True}


def prepare(root):
    root = Path(root)
    output = root / BUILD
    baseline = freeze(root, output)
    candidate = compile_candidate(root, output)
    raw = checked_candidate(candidate)
    retail = baseline["rom"].read_bytes()[ROM:ROM + SIZE]
    guards = output / "proposed-guards.csv"
    guards.write_bytes(guard_manifest(baseline["guards"].read_bytes(), raw, retail))
    source = output / "proposed-game_D51B0.c"
    source.write_text(SELECTED)
    makefile = output / "proposed-Makefile"
    makefile.write_text(recovered_makefile(baseline["makefile"].read_text()))
    qualified = build_padded(root, output, candidate, guards)
    replay = replay_make_recipe(root, output, makefile, source, guards, qualified)
    first_link, first_map, expected = link_private_image(root, output, qualified, baseline)
    closure = closure_audit(baseline["elf"], first_link)
    map_result = map_closure(first_map)
    (output / "closure.json").write_text(json.dumps({**closure, **map_result}, indent=2) + "\n")
    expected_path = output / "expected-conker.us.elf"
    expected_path.write_bytes(expected)
    return baseline, candidate, guards, qualified, replay, first_link, first_map, expected_path


def main():
    root = Path(__file__).resolve().parents[2]
    values = prepare(root)
    output = root / BUILD
    print(json.dumps({"function": FUNCTION, "words": WORDS, "frame": 0,
        "raw_sha256": RAW_SHA, "retail_sha256": RETAIL_SHA, "guards": 39,
        "relocations": 0, "caller_jals": 5, "literal_pointers": 0,
        "qualified_owner_sha256": digest(values[3].read_bytes()),
        "expected_elf_sha256": digest(values[7].read_bytes()),
        "closure": json.loads((output / "closure.json").read_text())}, indent=2))


if __name__ == "__main__":
    main()
