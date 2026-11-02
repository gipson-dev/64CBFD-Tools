"""Recover the two-row tagged effect-overlap scanner from semantic C."""

import csv
import hashlib
import io
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import emit_padded_assembly


FUNCTION = "func_151555AC"
OWNER = "generated_17CAF0"
ENTRY = 0x151555AC
ROM = 0x182A5C
SIZE = 384
WORDS = 96
FRAME = 72
SOURCE = "conker/src/game/generated_17CAF0.c"
OBJECT = "conker/build/src/game/generated_17CAF0.c.o"
ASM = "conker/asm/17CAF0.s"
BUILD = "conker/build/game-effect-overlap-scanner-151555AC-match"
RAW_SHA = "622b82f3ea6c9912453a5986fcef3597b78d08107cf9f7ce24c88cab3769cf4b"
RETAIL_SHA = "6c4c31148b9ec2611d3f735c3731f0ee8ce044cb8620ce572f8542d9e432b04f"
RAW_BINDINGS = {
    0x20: [("R_MIPS_HI16", "D_800A6030")],
    0x24: [("R_MIPS_LO16", "D_800A6030")],
    0x2C: [("R_MIPS_HI16", "D_800DCE50")],
    0x30: [("R_MIPS_HI16", "D_800DD190")],
    0x3C: [("R_MIPS_LO16", "D_800DCE50")],
    0x40: [("R_MIPS_LO16", "D_800DD190")],
}
RETAIL_BINDINGS = {
    0x1C: [("R_MIPS_HI16", "D_800A6030")],
    0x20: [("R_MIPS_LO16", "D_800A6030")],
    0x30: [("R_MIPS_HI16", "D_800DCE50")],
    0x34: [("R_MIPS_HI16", "D_800DD190")],
    0x38: [("R_MIPS_LO16", "D_800DD190")],
    0x3C: [("R_MIPS_LO16", "D_800DCE50")],
}

DECLARATIONS = """extern s32 D_800A6030[2];
extern u8 D_800DCE50[];
extern s8 D_800DD190;

typedef struct {
    s32 first;
    s32 second;
} EffectOverlapColumns151555AC;

s32 func_151555AC(f32 *, f32 *, s32 *, s32);
"""

HEADERS = """#include <ultra64.h>

extern s32 D_800A6030[2];
extern u8 D_800DCE50[];
extern s8 D_800DD190;

typedef struct {
    s32 first;
    s32 second;
} EffectOverlapColumns151555AC;

"""

SELECTED = """/* Report whether a tagged live effect overlaps the requested rectangle. */
s32 func_151555AC(f32 *center, f32 *extent, s32 *tags, s32 tagCount) {
    EffectOverlapColumns151555AC columns =
        *(EffectOverlapColumns151555AC *)D_800A6030;
    u8 *row;
    u8 column;

    row = D_800DCE50;
    do {
        column = 0;
        do {
            u8 *node = *(u8 **)(row + ((s32 *)&columns)[column] * 4);
            u8 *next;
            if (node != NULL) {
                do {
                    next = *(u8 **)(node + 8);
                    {
                    s32 matched = 0;
                    if (tagCount > 0) {
                        s32 offset = tagCount * 4;
                        s32 *cursor = (s32 *)((u8 *)tags + offset);
                        do {
                            if (node[0x2A] == *(cursor - 1)) {
                                matched = 1;
                            } else {
                                offset -= 4;
                                cursor--;
                            }
                        } while (offset >= 4 && matched == 0);
                    }
                    if (matched != 0) {
                        f32 extentX = *(f32 *)(node + 0x18) + extent[0];
                        f32 extentY = *(f32 *)(node + 0x1C) + extent[1];
                        f32 nodeX = *(f32 *)(node + 0x10);
                        f32 nodeY = *(f32 *)(node + 0x14);
                        if (center[0] - extentX <= nodeX &&
                            nodeX <= center[0] + extentX &&
                            center[1] - extentY <= nodeY &&
                            nodeY <= center[1] + extentY) {
                            return 1;
                        }
                    }
                    }
                } while ((node = next) != NULL);
            }
            column++;
        } while (column < 2);
        row += 0x1A0;
    } while (row != (u8 *)&D_800DD190);
    return 0;
}
"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def before_path(output, name):
    return output / ("before-" + name.replace("/", "_"))


def freeze(root, output):
    names = (SOURCE, OBJECT, "conker/build/conker.us.elf",
             "conker/build/conker.us.map", "conker/retail_word_patches.us.csv",
             "conker/conker.us.bin")
    manifest = output / "baseline.json"
    if not manifest.exists():
        values = {name: (root / name).read_bytes() for name in names}
        for name, data in values.items():
            before_path(output, name).write_bytes(data)
        manifest.write_text(json.dumps(
            {name: digest(data) for name, data in values.items()}, indent=2) + "\n")
    for name, expected in json.loads(manifest.read_text()).items():
        if digest(before_path(output, name).read_bytes()) != expected:
            raise ValueError("Modified effect-overlap baseline: " + name)
    return {name: before_path(output, name) for name in names}


def relocation_spec(rows):
    return ";".join(kind + ":" + symbol for kind, symbol in rows) or "-"


def checked_payload(obj, expected_sha, expected_bindings):
    raw, bindings = payload(obj, FUNCTION)
    if (len(raw), digest(raw), bindings) != (SIZE, expected_sha, expected_bindings):
        raise ValueError("Effect-overlap scanner payload or bindings changed")
    return raw, bindings


def recovered_owner(before):
    prototype = "s32 func_151555AC(u8 *, f32 *, s32 *, s32);"
    pragma = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_17CAF0/func_151555AC.s")'
    call = "func_151555AC(descriptor, position, pair, pairCount)"
    if (before.count(prototype) != 1 or before.count(pragma) != 1 or
            before.count(call) != 1):
        raise ValueError("Effect-overlap scanner predecessor changed")
    return before.replace(prototype, DECLARATIONS.rstrip(), 1).replace(
        call, "func_151555AC((f32 *)descriptor, position, pair, pairCount)", 1
    ).replace(pragma, SELECTED.rstrip(), 1)


def guard_manifest(before, compiled_raw, compiled_bindings, retail_raw, retail_bindings):
    if (len(compiled_raw), digest(compiled_raw), compiled_bindings) != (
            SIZE, RAW_SHA, RAW_BINDINGS):
        raise ValueError("Effect-overlap scanner compiled input changed")
    if (len(retail_raw), digest(retail_raw), retail_bindings) != (
            SIZE, RETAIL_SHA, RETAIL_BINDINGS):
        raise ValueError("Effect-overlap scanner retail input changed")
    reader = csv.DictReader(io.StringIO(before.decode()))
    fields = reader.fieldnames
    expected_fields = ["filename", "function", "offset", "expected", "replacement",
        "expected_relocations", "replacement_relocations", "note", "insert_after",
        "insert_after_relocations", "omit"]
    if fields != expected_fields:
        raise ValueError("Effect-overlap scanner guard schema changed")
    if any(row["function"] == FUNCTION for row in reader):
        raise ValueError("Effect-overlap scanner guards already exist")
    old_words = struct.unpack(">96I", compiled_raw)
    new_words = struct.unpack(">96I", retail_raw)
    newline = "\r\n" if before.endswith(b"\r\n") else "\n"
    if not before.endswith(newline.encode()):
        raise ValueError("Effect-overlap scanner guard terminator missing")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator=newline)
    count = 0
    for index, (old, new) in enumerate(zip(old_words, new_words)):
        offset = index * 4
        old_relocations = compiled_bindings.get(offset, [])
        new_relocations = retail_bindings.get(offset, [])
        if old == new and old_relocations == new_relocations:
            continue
        writer.writerow({
            "filename": OWNER,
            "function": FUNCTION,
            "offset": "0x%03X" % offset,
            "expected": "0x%08X" % old,
            "replacement": "0x%08X" % new,
            "expected_relocations": relocation_spec(old_relocations),
            "replacement_relocations": relocation_spec(new_relocations),
            "note": "Normalize complete effect-overlap scanner compiler scheduling",
            "insert_after": "",
            "insert_after_relocations": "",
            "omit": "false",
        })
        count += 1
    if count != 81:
        raise ValueError("Effect-overlap scanner guard count changed: %d" % count)
    return before + stream.getvalue().encode()


def prove_private_candidate(root, candidate, baseline=None):
    root = Path(root)
    output = root / BUILD
    baseline = baseline or freeze(root, output)
    original = baseline[OBJECT]
    compiled_raw, compiled_bindings = checked_payload(candidate, RAW_SHA, RAW_BINDINGS)
    retail_raw, retail_bindings = checked_payload(original, RETAIL_SHA, RETAIL_BINDINGS)
    guards = output / "proposed-guards.csv"
    guards.write_bytes(guard_manifest(
        baseline["conker/retail_word_patches.us.csv"].read_bytes(),
        compiled_raw, compiled_bindings, retail_raw, retail_bindings))
    owner, diagnostics = compile_owner(
        root, output, (root / SOURCE).read_text(), "private-current-owner")
    if diagnostics:
        raise ValueError(diagnostics)
    padded = output / "private-qualified.s"
    padded.write_text(emit_padded_assembly(
        owner, root / ASM, function_objects={FUNCTION: candidate},
        word_patches_path=guards, filename=OWNER))
    qualified = output / "private-qualified.o"
    subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
                    "-mabi=32", "-I", str(root / "conker/include"), "-o",
                    str(qualified), str(padded)], check=True)
    if qualified.read_bytes() != original.read_bytes():
        raise ValueError("Guarded effect-overlap owner differs from predecessor")
    return guards, qualified


def prepare(root):
    root = Path(root)
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    baseline = freeze(root, output)
    selected, diagnostics = compile_owner(root, output, HEADERS + SELECTED,
                                          "selected-final")
    if diagnostics:
        raise ValueError(diagnostics)
    checked_payload(selected, RAW_SHA, RAW_BINDINGS)
    proposed = recovered_owner(baseline[SOURCE].read_text())
    (output / ("proposed-" + OWNER + ".c")).write_text(proposed)
    owner, diagnostics = compile_owner(root, output, proposed, "qualified-owner-raw")
    if diagnostics:
        raise ValueError(diagnostics)
    if payload(owner, FUNCTION) != payload(selected, FUNCTION):
        raise ValueError("Effect-overlap scanner changed in its owner")
    guards, qualified = prove_private_candidate(root, selected, baseline)
    return selected, owner, guards, qualified


if __name__ == "__main__":
    repository = Path(__file__).resolve().parents[2]
    candidate_path, owner_path, guards_path, object_path = prepare(repository)
    print("candidate=%s" % candidate_path)
    print("owner=%s" % owner_path)
    print("guards=%s" % guards_path)
    print("object=%s" % object_path)
