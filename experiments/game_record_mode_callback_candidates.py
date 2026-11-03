"""Screen semantic C forms for record mode callback func_15013C38."""

import itertools
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler


ENTRY, ROM, WORDS = 0x15013C38, 0x410E8, 64
FUNCTION = "func_15013C38"
SYMBOLS = {
    "D_80082F28": 0x80082F28,
    "D_80096650": 0x80096650,
    "D_800BE9F0": 0x800BE9F0,
    "D_800C35E8": 0x800C35E8,
    "D_800C35EA": 0x800C35EA,
    "D_800D2E4C": 0x800D2E4C,
}
RECORD = """typedef void (*RecordModeCallback15013C38)(u8 *, f32);
"""
DECLARATIONS = """extern RecordModeCallback15013C38 D_80082F28[];
extern f32 D_80096650;
extern s32 D_800BE9F0;
extern u8 D_800C35E8;
extern u8 D_800C35EA;
extern u8 *D_800D2E4C;
"""

SELECTED = """s32 func_15013C38(u8 *record) {
    RecordModeCallback15013C38 callback;
    s32 mode;

    record[0x16] |= 4;
    mode = *(s32 *)(record + 0x18);
    if ((D_800D2E4C[0x11] & 4) && D_800BE9F0 == 0x13) {
        return 1;
    }
    if (D_800C35EA == 1 &&
        (D_800C35E8 == 0xF || D_800C35E8 == 0x10 ||
         D_800C35E8 == 0x11)) {
        return 1;
    }
    if (mode >= 6) {
        return 1;
    }
    callback = D_80082F28[mode];
    if (callback != NULL) {
        callback(record, (f32)*(u32 *)(record + 0x1C) * D_80096650);
    }
    return 1;
}"""


def candidates():
    yield "selected", SELECTED
    yield "mode-before-flag", SELECTED.replace(
        "    record[0x16] |= 4;\n    mode = *(s32 *)(record + 0x18);",
        "    mode = *(s32 *)(record + 0x18);\n    record[0x16] |= 4;")
    yield "flat-special-modes", SELECTED.replace(
        "    if (D_800C35EA == 1 &&\n"
        "        (D_800C35E8 == 0xF || D_800C35E8 == 0x10 ||\n"
        "         D_800C35E8 == 0x11)) {",
        "    if ((D_800C35EA == 1 && D_800C35E8 == 0xF) ||\n"
        "        (D_800C35EA == 1 && D_800C35E8 == 0x10) ||\n"
        "        (D_800C35EA == 1 && D_800C35E8 == 0x11)) {")
    yield "nested-special-modes", SELECTED.replace(
        "    if (D_800C35EA == 1 &&\n"
        "        (D_800C35E8 == 0xF || D_800C35E8 == 0x10 ||\n"
        "         D_800C35E8 == 0x11)) {\n"
        "        return 1;\n"
        "    }",
        "    if (D_800C35EA == 1) {\n"
        "        if (D_800C35E8 == 0xF || D_800C35E8 == 0x10 ||\n"
        "            D_800C35E8 == 0x11) {\n"
        "            return 1;\n"
        "        }\n"
        "    }")
    yield "unsigned-mode", SELECTED.replace("    s32 mode;", "    u32 mode;")
    yield "inline-callback", SELECTED.replace(
        "    callback = D_80082F28[mode];\n"
        "    if (callback != NULL) {\n"
        "        callback(record, (f32)*(u32 *)(record + 0x1C) * D_80096650);\n"
        "    }",
        "    if (D_80082F28[mode] != NULL) {\n"
        "        D_80082F28[mode](record,\n"
        "            (f32)*(u32 *)(record + 0x1C) * D_80096650);\n"
        "    }")
    scaled_local = SELECTED.replace(
        "    s32 mode;", "    s32 mode;\n    f32 scaled;").replace(
        "        callback(record, (f32)*(u32 *)(record + 0x1C) * D_80096650);",
        "        scaled = (f32)*(u32 *)(record + 0x1C) * D_80096650;\n"
        "        callback(record, scaled);")
    yield "scaled-local", scaled_local
    yield "scaled-local-before-callback", scaled_local.replace(
        "    callback = D_80082F28[mode];\n    if (callback != NULL) {",
        "    scaled = (f32)*(u32 *)(record + 0x1C) * D_80096650;\n"
        "    callback = D_80082F28[mode];\n    if (callback != NULL) {").replace(
        "        scaled = (f32)*(u32 *)(record + 0x1C) * D_80096650;\n", "", 1)
    value_local = SELECTED.replace(
        "    s32 mode;", "    s32 mode;\n    u32 value;").replace(
        "    callback = D_80082F28[mode];",
        "    callback = D_80082F28[mode];\n"
        "    value = *(u32 *)(record + 0x1C);").replace(
        "(f32)*(u32 *)(record + 0x1C)", "(f32)value")
    yield "value-local", value_local
    yield "explicit-product", SELECTED.replace(
        "        callback(record, (f32)*(u32 *)(record + 0x1C) * D_80096650);",
        "        callback(record, ((f32)*(u32 *)(record + 0x1C)) *\n"
        "            D_80096650);")
    yield "cached-scale", SELECTED.replace(
        "    s32 mode;", "    s32 mode;\n    f32 scale = D_80096650;").replace(
        "* D_80096650", "* scale")
    yield "signed-value", SELECTED.replace("(f32)*(u32 *)", "(f32)*(s32 *)")


def compile_candidate(root, output, name, body):
    output.mkdir(parents=True, exist_ok=True)
    with patch.multiple(
            compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        record, words = compiler.compile_candidate(
            root, output, name, body, "o2g3")
    retail = struct.unpack_from(
        ">%dI" % WORDS, (root / "conker/conker.us.bin").read_bytes(), ROM)
    record["differences"] = sum(
        left != right for left, right in
        itertools.zip_longest(words, retail, fillvalue=0))
    return record


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / "conker/build/game-record-mode-callback-15013C38-candidates"
    records = []
    for name, body in candidates():
        record = compile_candidate(root, output, name, body)
        records.append(record)
        print(name, record["body_words"], hex(record["frame"]),
              record["differences"], flush=True)
    (output / "candidate-measurements.json").write_text(
        json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
