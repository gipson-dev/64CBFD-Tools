"""Compile and compare semantic source forms for func_1515EB84."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import parse_object


FUNCTION = "func_1515EB84"
SOURCE = "conker/src/game/generated_18A8F0.c"
BUILD = "conker/build/game-point-record-search-1515EB84-candidates"
ROM_IMAGE = "conker/conker.us.bin"
ENTRY = 0x1515EB84
ROM = 0x18C034
WORDS = 61
SIZE = WORDS * 4
FRAME = 0x360
STUB = "s32 func_1515EB84() {\n    return 0;\n}"
DECLARATION = "s32 func_150A1DA0(struct127 *, s32, s32);\n"
ANCHOR = "f32 func_15144598(struct134 *);\n"
BINDINGS = {0x0B0: [("R_MIPS_26", "func_150A1DA0")]}


SELECTED = """/* Find the first enabled record accepting the supplied point. */
u8 *func_1515EB84(s32 x, s32 y, s32 z, s32 mask, LinkedNode *node) {
    struct127 query;
    u8 *record;

    query.y_position = y;
    query.unk180 = y;
    query.old_y_position = y;
    query.x_position = x;
    query.old_x_position = x;
    query.z_position = z;
    query.old_z_position = z;

    if (node != 0) {
        do {
            record = *(u8 **)&node->data[0];
            if (record[0x14] == 0 &&
                (mask == 0 || ((*(u32 *)(record + 0x18) >> 24) & mask) != 0) &&
                ((record[0x15] >> 2) == 24 ||
                 (*(u32 *)(record + 0x18) >> 31) == 0) &&
                func_150A1DA0(&query, (s32)record, 0) == 0) {
                return *(u8 **)&node->data[0];
            }
            node = node->next;
        } while (node != 0);
    }
    return 0;
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    if source.count(STUB) != 1 or source.count(DECLARATION) != 0:
        raise ValueError("Point-record-search source state changed")
    return source.replace(ANCHOR, ANCHOR + DECLARATION, 1).replace(STUB, body, 1)


def function_blob(obj):
    text, functions, relocations = parse_object(obj)
    info = functions[FUNCTION]
    start = info["value"]
    end = start + info["size"]
    bindings = {
        offset - start: rows for offset, rows in relocations.items()
        if start <= offset < end
    }
    return text[start:end], bindings


def normalized(data, bindings):
    result = bytearray(data)
    for offset, rows in bindings.items():
        word = struct.unpack_from(">I", result, offset)[0]
        if rows[0][0] == "R_MIPS_26":
            word &= 0xFC000000
        elif rows[0][0] in ("R_MIPS_HI16", "R_MIPS_LO16"):
            word &= 0xFFFF0000
        struct.pack_into(">I", result, offset, word)
    return bytes(result)


def compare(body, label="selected"):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(ROOT, output, source_with(body), label)
    raw, bindings = function_blob(obj)
    retail = (ROOT / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(retail) != SIZE:
        raise ValueError("Point-record-search retail slice changed")
    candidate = normalized(raw, bindings)
    expected = normalized(retail, BINDINGS)
    limit = max(len(candidate), len(expected))
    differences = []
    for offset in range(0, limit, 4):
        ours = candidate[offset:offset + 4]
        theirs = expected[offset:offset + 4]
        if ours != theirs:
            differences.append({
                "offset": hex(offset),
                "candidate": ours.hex() if len(ours) == 4 else None,
                "retail": theirs.hex() if len(theirs) == 4 else None,
            })
    disassembly = subprocess.run([
        "mips-linux-gnu-objdump", "-dr", str(obj)
    ], check=True, capture_output=True, text=True).stdout
    (output / (label + "-objdump.txt")).write_text(disassembly)
    report = {
        "label": label,
        "words": len(raw) // 4,
        "frame": (-struct.unpack_from(">I", raw)[0]) & 0xFFFF,
        "differences": len(differences),
        "bindings": {hex(offset): rows for offset, rows in bindings.items()},
        "candidate_sha256": digest(raw),
        "retail_sha256": digest(retail),
        "diagnostics": diagnostics.splitlines(),
        "difference_rows": differences,
    }
    (output / (label + "-report.json")).write_text(
        json.dumps(report, indent=2) + "\n")
    return report


ROOT = Path(__file__).resolve().parents[2]


if __name__ == "__main__":
    print(json.dumps(compare(SELECTED), indent=2))
