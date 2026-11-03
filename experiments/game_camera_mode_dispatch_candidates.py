"""Screen semantic C forms for the camera mode dispatcher func_151283B8."""

import itertools
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler


ENTRY, ROM, WORDS = 0x151283B8, 0x155868, 67
FUNCTION = "func_151283B8"
SYMBOLS = {
    "func_15120158": 0x15120158,
    "func_15121C80": 0x15121C80,
    "func_151220D0": 0x151220D0,
    "func_15122170": 0x15122170,
    "func_15122440": 0x15122440,
    "func_15122980": 0x15122980,
    "func_15129934": 0x15129934,
    "func_1512DEA4": 0x1512DEA4,
}
RECORD = """typedef struct {
    u8 padding[0x2C];
    s32 mode;
} CameraMode151283B8;
"""
DECLARATIONS = """void func_15120158(CameraMode151283B8 *);
s32 func_15121C80();
void func_151220D0(CameraMode151283B8 *);
void func_15122170(CameraMode151283B8 *);
void func_15122440(CameraMode151283B8 *);
void func_15122980(CameraMode151283B8 *);
void func_15129934(CameraMode151283B8 *);
void func_1512DEA4(CameraMode151283B8 *);
"""

SELECTED = """void func_151283B8(CameraMode151283B8 *camera) {
    switch (camera->mode) {
    case 0x80:
        func_15122440(camera);
        break;
    case 0x40:
        func_15129934(camera);
        break;
    case 1:
        func_15122980(camera);
        break;
    case 8:
        func_15121C80(camera, 0);
        break;
    case 2:
        func_151220D0(camera);
        break;
    case 0x400:
        func_15122170(camera);
        break;
    case 0x800:
        func_15122980(camera);
        break;
    case 0x100:
        func_15120158(camera);
        break;
    case 0x800000:
        func_1512DEA4(camera);
        break;
    case 0x2000:
        break;
    }
}"""


def candidates():
    yield "switch", SELECTED
    for name, zero in (
            ("zero-s8", "(s8)0"), ("zero-u8", "(u8)0"),
            ("zero-s16", "(s16)0"), ("zero-u16", "(u16)0"),
            ("zero-s32", "(s32)0"), ("zero-u32", "(u32)0")):
        yield name, SELECTED.replace("camera, 0);", "camera, %s);" % zero)
    yield "switch-signed-local", SELECTED.replace(
        "    switch (camera->mode) {",
        "    s32 mode = camera->mode;\n    switch (mode) {")
    yield "switch-unsigned-local", SELECTED.replace(
        "    switch (camera->mode) {",
        "    u32 mode = camera->mode;\n    switch (mode) {")
    chain = """void func_151283B8(CameraMode151283B8 *camera) {
    s32 mode = camera->mode;
    if (mode == 1 || mode == 0x800) {
        func_15122980(camera);
    } else if (mode == 2) {
        func_151220D0(camera);
    } else if (mode == 8) {
        func_15121C80(camera, 0);
    } else if (mode == 0x40) {
        func_15129934(camera);
    } else if (mode == 0x80) {
        func_15122440(camera);
    } else if (mode == 0x100) {
        func_15120158(camera);
    } else if (mode == 0x400) {
        func_15122170(camera);
    } else if (mode == 0x800000) {
        func_1512DEA4(camera);
    }
}"""
    yield "if-chain", chain


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
    output = root / "conker/build/game-camera-mode-dispatch-151283B8-match"
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
