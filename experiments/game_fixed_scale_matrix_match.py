"""Qualify the isolated fixed-point scale-matrix constructor as guarded C."""

import csv
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

from tools.experiments.game_actor_state_tick_integration import elf_slot_offset, symbol_rows
from tools.experiments.game_four_head_lookup_match import payload
from tools.pad_generated_object import emit_padded_assembly, parse_object


FUNCTION = "func_150A7C10"
OWNER = "generated_D50C0"
ENTRY = 0x150A7C10
ROM = 0xD50C0
SIZE = 160
WORDS = 40
SOURCE = "conker/src/game/generated_D50C0.c"
OBJECT = "conker/build/src/game/generated_D50C0.c.o"
ASSEMBLY = "conker/asm/D50C0.s"
BUILD = "conker/build/game-fixed-scale-matrix-150A7C10-match"
RAW_SHA = "a084312c1c589353c2884a6bd6221d669320f53ba34c58007ab9a7a038e7d0cd"
RETAIL_SHA = "6d90a2cacb1541d0ae93057609ae5ebd2f8dbffef99097d84f913e89910b2ab4"
BASELINE_ELF_SHA = "752feb861f0a37a4ce3ee397f1a52952a048048aff9c3521ad2b3ff3d9b122da"
EXPECTED_ELF_SHA = "9bd8b47f72c3aaf7cd478dd013d3505e361582e94800f9d90ae1646a98ea3166"
EXPECTED_WARNING = "cc: Warning: -mips3 should not be used for ucode 32-bit compiles"

PATHS = {
    "source": SOURCE,
    "object": OBJECT,
    "elf": "conker/build/conker.us.elf",
    "map": "conker/build/conker.us.map",
    "makefile": "conker/Makefile",
    "guards": "conker/retail_word_patches.us.csv",
    "progress": "conker/progress.csv",
    "assembly": ASSEMBLY,
    "rom": "conker/conker.us.bin",
    "sdk_asm": "tools/ultralib/src/mgu/scale.s",
    "sdk_c": "tools/ultralib/src/gu/scale.c",
}

BASELINE = {
    "source": "ed3f7af77694d529bf9e94a4e2d3954459f9bd2d0e97c40e52224591b10ea0f1",
    "object": "c4ef26c69ca6d98061f04603851165f0952d930bff99777c69c897d0823df8ee",
    "elf": BASELINE_ELF_SHA,
    "map": "ebb679dbafe5095950abc7ea997853701ce7cf975c8529cf54230dc13f2f0b51",
    "makefile": "48bf792a2cb38a554c94864ca3c16772171e789097c3542d0fac9fc7714077bf",
    "guards": "71ae31f48d7e66e33d563a84edd63b33bdb7b6385d3082579cb2c276365b4e2c",
    "progress": "96a7f15ab5207027a204f795e91b8f9f3453482ce4ec4d47bd8bcb4b5a305502",
    "assembly": "507f86dba1f89664c71d62542baf79ba99bcab2c5fb51bbd5e575a04b364a0d2",
    "rom": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "sdk_asm": "13ac06817763eceeef6dfa278168ac443fd5b8dc62aae129de85767f233d8129",
    "sdk_c": "5868e7f4494bade5c72942b966af29db7f0ca1319379dc6678e0b31ee36dc481",
}

SELECTED = '''#include <ultra64.h>

/* Build an N64 fixed-point scale matrix from three floating-point factors. */
void func_150A7C10(volatile s16 *matrix, f32 x, f32 y, f32 z) {
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
    matrix[0] = fixedX >> 16;
    matrix[5] = fixedY >> 16;
    matrix[10] = fixedZ >> 16;
    matrix[16] = fixedX;
    matrix[21] = fixedY;
    matrix[26] = fixedZ;
}
'''

PROFILE = """# This fixed-matrix leaf uses retail's eight 64-bit zero stores.
$(BUILD_DIR)/$(SRC_DIR)/game/generated_D50C0.c.o: MIPSBIT := -mips3

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
            raise ValueError("Changed fixed-scale baseline")
        for key, data in values.items():
            before_path(output, key).write_bytes(data)
        manifest.write_text(json.dumps(BASELINE, indent=2) + "\n")
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError("Modified fixed-scale baseline manifest")
    for key, expected in BASELINE.items():
        if digest(before_path(output, key).read_bytes()) != expected:
            raise ValueError("Modified fixed-scale frozen input: " + key)
    return {key: before_path(output, key) for key in PATHS}


def compile_candidate(root, output, source=SELECTED, name="candidate"):
    raw = output / (name + ".c")
    processed = output / (name + "-processed.c")
    obj = output / (name + ".o")
    raw.write_text(source)
    processor = [sys.executable, str(root / "tools/asm-processor/asm_processor.py"),
                 "-O2", "-g3", str(raw.relative_to(root / "conker"))]
    result = subprocess.run(processor, cwd=root / "conker", capture_output=True,
                            text=True, check=True)
    if result.stderr:
        raise ValueError(result.stderr)
    processed.write_text(result.stdout)
    includes = [".", "include", "include/2.0L", "include/2.0L/PR", "include/libc",
                "src/libultra/os", "src/libultra/audio", "src/libultra/io"]
    command = [str(root / "ido/ido5.3_recomp/cc"), "-c", "-32", "-G", "0",
        "-Xfullwarn", "-Xcpluscomm", "-signed", "-nostdinc", "-non_shared",
        "-Wab,-r4300_mul", "-D_LANGUAGE_C", "-D_FINALROM", "-DF3DEX_GBI_2",
        "-D_MIPS_SZLONG=32", "-woff", "649,838",
        *[item for path in includes for item in ("-I", path)],
        "-O2", "-g3", "-mips3", "-o", str(obj.relative_to(root / "conker")),
        str(processed.relative_to(root / "conker"))]
    result = subprocess.run(command, cwd=root / "conker", capture_output=True, text=True)
    diagnostics = (result.stdout + result.stderr).strip()
    (output / (name + "-diagnostics.txt")).write_text(diagnostics + ("\n" if diagnostics else ""))
    if result.returncode or diagnostics != EXPECTED_WARNING:
        raise ValueError("Unexpected fixed-scale compiler result: " + diagnostics)
    subprocess.run([*processor, "--post-process", str(obj.relative_to(root / "conker")),
        "--assembler", "mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include",
        "--asm-prelude", "include/asm_processor_prelude.inc"], cwd=root / "conker",
        capture_output=True, text=True, check=True)
    return obj


def checked_candidate(obj):
    raw, bindings = payload(obj, FUNCTION)
    if (len(raw), digest(raw), bindings) != (SIZE, RAW_SHA, {}):
        raise ValueError("Fixed-scale raw payload changed")
    return raw


def complete_symbol(obj):
    data, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = data[info["value"]:info["value"] + info["size"]]
    selected = {
        at - info["value"]: rows for at, rows in bindings.items()
        if info["value"] <= at < info["value"] + info["size"]
    }
    return raw, selected


def guard_manifest(before, raw, retail):
    if (len(raw), digest(raw), len(retail), digest(retail)) != (
            SIZE, RAW_SHA, SIZE, RETAIL_SHA):
        raise ValueError("Fixed-scale guard input changed")
    stream = io.StringIO(before.decode(), newline="")
    reader = csv.DictReader(stream)
    fields = reader.fieldnames
    expected_fields = ["filename", "function", "offset", "expected", "replacement",
        "expected_relocations", "replacement_relocations", "note", "insert_after",
        "insert_after_relocations", "omit"]
    if fields != expected_fields or any(row["function"] == FUNCTION for row in reader):
        raise ValueError("Fixed-scale guard predecessor changed")
    old_words = struct.unpack(">40I", raw)
    new_words = struct.unpack(">40I", retail)
    newline = "\r\n" if before.endswith(b"\r\n") else "\n"
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator=newline)
    count = 0
    for index, (old, new) in enumerate(zip(old_words, new_words)):
        if old == new:
            continue
        writer.writerow({
            "filename": OWNER,
            "function": FUNCTION,
            "offset": "0x%03X" % (index * 4),
            "expected": "0x%08X" % old,
            "replacement": "0x%08X" % new,
            "expected_relocations": "-",
            "replacement_relocations": "-",
            "note": "Normalize fixed-scale matrix handwritten scheduling",
            "insert_after": "",
            "insert_after_relocations": "",
            "omit": "false",
        })
        count += 1
    if count != 39:
        raise ValueError("Fixed-scale guard count changed: %d" % count)
    return before + output.getvalue().encode()


def recovered_makefile(before):
    if before.count(PROFILE_MARKER) != 1 or PROFILE in before:
        raise ValueError("Fixed-scale Makefile marker changed")
    return before.replace(PROFILE_MARKER, PROFILE + PROFILE_MARKER, 1)


def expected_image(before, retail):
    if digest(before) != BASELINE_ELF_SHA or (len(retail), digest(retail)) != (SIZE, RETAIL_SHA):
        raise ValueError("Fixed-scale image input changed")
    rows = [row for row in symbol_rows(before) if row[1] == FUNCTION]
    if len(rows) != 1 or rows[0][2][1:3] != (ENTRY, 12):
        raise ValueError("Fixed-scale predecessor symbol changed")
    result = bytearray(before)
    offset = elf_slot_offset(before, ENTRY, SIZE)
    result[offset:offset + SIZE] = retail
    struct.pack_into(">I", result, rows[0][0] + 8, SIZE)
    result = bytes(result)
    if digest(result) != EXPECTED_ELF_SHA:
        raise ValueError("Fixed-scale complete-image prediction changed")
    return result


def prepare(root):
    root = Path(root)
    output = root / BUILD
    baseline = freeze(root, output)
    candidate = compile_candidate(root, output)
    raw = checked_candidate(candidate)
    retail = baseline["rom"].read_bytes()[ROM:ROM + SIZE]
    guards = output / "proposed-guards.csv"
    guards.write_bytes(guard_manifest(baseline["guards"].read_bytes(), raw, retail))
    proposed_source = output / "proposed-generated_D50C0.c"
    proposed_source.write_text(SELECTED)
    proposed_makefile = output / "proposed-Makefile"
    proposed_makefile.write_text(recovered_makefile(baseline["makefile"].read_text()))
    padded = output / "private-qualified.s"
    padded.write_text(emit_padded_assembly(candidate, baseline["assembly"],
        word_patches_path=guards, filename=OWNER))
    qualified = output / "private-qualified.o"
    subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
                    "-mabi=32", "-I", str(root / "conker/include"), "-o",
                    str(qualified), str(padded)], check=True)
    qualified_raw, qualified_bindings = complete_symbol(qualified)
    if qualified_raw != retail or qualified_bindings:
        raise ValueError("Fixed-scale padded owner differs from retail")
    expected = output / "expected-conker.us.elf"
    expected.write_bytes(expected_image(baseline["elf"].read_bytes(), retail))
    return baseline, candidate, guards, qualified, expected


def main():
    root = Path(__file__).resolve().parents[2]
    baseline, candidate, guards, qualified, expected = prepare(root)
    print(json.dumps({
        "function": FUNCTION,
        "words": WORDS,
        "frame": 0,
        "raw_sha256": RAW_SHA,
        "retail_sha256": RETAIL_SHA,
        "guards": 39,
        "relocations": 0,
        "candidate": str(candidate),
        "guard_manifest": str(guards),
        "qualified_owner": str(qualified),
        "expected_elf_sha256": digest(expected.read_bytes()),
        "caller_jals": 0,
        "literal_pointers": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
