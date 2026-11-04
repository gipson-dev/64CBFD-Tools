"""Screen semantic C forms for boot-logo phase controller func_151DE6D4."""

import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span, link_owner)


SOURCE = "conker/src/game/generated_20AE20.c"
OWNER = "game/generated_20AE20"
FUNCTION = "func_151DE6D4"
ROM = 0x20BB84
WORDS = 64
BUILD = "conker/build/game-boot-logo-phase-151DE6D4-candidates"
DECLARATION = "extern s32 D_80000300;\n"

DONOR = """void func_151DE6D4(void) {
    s32 timer;

    func_151E530C();
    D_800CC2D0[0].unk25C = D_800CC2D0[0].unk25C | 0x200;
    D_800CC2D0[0].y_position = 1000.0f;
    if (D_80000300 == 0) {
        D_800E0A90 = 0;
    }
    timer = D_800E0A90;
    if ((timer >= 0x14B) && ((s16)D_800E0B9A & 0x8000)) {
        if (timer < 0x1E0) {
            timer = 0x1E0;
            D_800E0A90 = 0x1E0;
        }
        if ((timer >= 0x259) && (timer < 0x2D0)) {
            timer = 0x2D0;
            D_800E0A90 = 0x2D0;
        }
    }
    if (timer >= 0x349) {
        D_8008FE28 = 2;
        D_800E0B94 = 1;
        D_800D2E40 = 0;
        func_1501C730(6, 0x21, 0U, 0, 1);
        D_800E0B96 = 0xFF;
    }
}"""


def variants():
    yield "donor-adapted", DONOR
    yield "global-then-local-chain", DONOR.replace(
        "            timer = 0x1E0;\n"
        "            D_800E0A90 = 0x1E0;",
        "            D_800E0A90 = timer = 0x1E0;").replace(
        "            timer = 0x2D0;\n"
        "            D_800E0A90 = 0x2D0;",
        "            D_800E0A90 = timer = 0x2D0;")
    yield "local-then-global-chain", DONOR.replace(
        "            timer = 0x1E0;\n"
        "            D_800E0A90 = 0x1E0;",
        "            timer = D_800E0A90 = 0x1E0;").replace(
        "            timer = 0x2D0;\n"
        "            D_800E0A90 = 0x2D0;",
        "            timer = D_800E0A90 = 0x2D0;")
    yield "compound-or", DONOR.replace(
        "D_800CC2D0[0].unk25C = D_800CC2D0[0].unk25C | 0x200;",
        "D_800CC2D0[0].unk25C |= 0x200;")
    yield "uncast-flags", DONOR.replace("(s16)D_800E0B9A", "D_800E0B9A")
    yield "signed-zero", DONOR.replace("0U, 0, 1", "0, 0, 1")
    yield "combined", DONOR.replace(
        "D_800CC2D0[0].unk25C = D_800CC2D0[0].unk25C | 0x200;",
        "D_800CC2D0[0].unk25C |= 0x200;").replace(
        "(s16)D_800E0B9A", "D_800E0B9A").replace(
        "0U, 0, 1", "0, 0, 1")


def candidate_source(before, body):
    start, end = function_span(before, FUNCTION)
    predecessor = before[start:end]
    if predecessor != "s32 func_151DE6D4() {\n    return 0;\n}":
        raise ValueError("Boot-logo phase controller predecessor changed")
    if DECLARATION not in before:
        marker = "extern s32 D_800E0A90;\n"
        if before.count(marker) != 1:
            raise ValueError("Boot-logo declaration anchor changed")
        before = before.replace(marker, marker + DECLARATION, 1)
        start, end = function_span(before, FUNCTION)
    return before[:start] + body + before[end:]


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    before = (root / SOURCE).read_text()
    retail = (root / "conker/conker.us.bin").read_bytes()[
        ROM:ROM + WORDS * 4]
    retail_words = struct.unpack(">%dI" % WORDS, retail)
    records = []
    for label, body in variants():
        obj, diagnostics = compile_owner(
            root, output, candidate_source(before, body), label)
        linked, functions = link_owner(root, output, obj, OWNER)
        info = functions[FUNCTION]
        actual = linked[info["value"]:info["value"] + info["size"]]
        actual_words = struct.unpack(">%dI" % (len(actual) // 4), actual)
        differences = [
            index * 4 for index, (left, right) in enumerate(
                itertools.zip_longest(
                    actual_words, retail_words, fillvalue=0))
            if left != right
        ]
        record = {
            "variant": label,
            "words": len(actual_words),
            "frame": (-actual_words[0] & 0xFFFF) if actual_words else 0,
            "differences": len(differences),
            "difference_offsets": differences,
            "raw_sha256": hashlib.sha256(actual).hexdigest(),
            "retail_sha256": hashlib.sha256(retail).hexdigest(),
            "diagnostics": diagnostics,
        }
        records.append(record)
        print(label, record["words"], hex(record["frame"]),
              record["differences"], flush=True)
    (output / "candidate-measurements.json").write_text(
        json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
