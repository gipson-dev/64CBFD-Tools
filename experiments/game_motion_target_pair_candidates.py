"""Screen C forms for the split motion-target callback pair at 150C84F4."""

import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import (
    compile_owner,
    function_span,
)


SOURCE = "conker/src/game/generated_F5800.c"
BUILD = "conker/build/game-motion-target-pair-candidates"
FUNCTIONS = {
    "func_150C84F4": {
        "rom": 0xF59A4,
        "words": 10,
        "bindings": {0x10: [("R_MIPS_26", "func_150C8350")]},
    },
    "func_150C851C": {
        "rom": 0xF59CC,
        "words": 57,
        "bindings": {
            0x008: [("R_MIPS_HI16", "D_800BE4E0")],
            0x014: [("R_MIPS_LO16", "D_800BE4E0")],
            0x038: [("R_MIPS_26", "func_150CDB6C")],
            0x088: [("R_MIPS_26", "func_150ADA20")],
        },
    },
}

DECLARATIONS = """extern s32 D_800BE4E0;
s32 func_150ADA20(void);
void func_150CDB6C(s32 value);
"""

WRAPPER = """/* Advance the motion table once for the primary frame layer. */
void func_150C84F4(s32 view) {
    if (view == 0) {
        func_150C8350();
    }
}"""

INITIALIZER = """/* Randomize ten motion targets from the selected intensity. */
void func_150C851C(s32 intensity) {
    s32 offset;
    s32 base;
    u32 span;

    if (D_800BE4E0 != 0) {
        func_150CDB6C(intensity);
        base = (intensity * 300) >> 8;
        span = ((intensity * 50) >> 8) + 50;
        for (offset = 0; offset != 100; offset += 10) {
            *(s16 *)(D_800BE4E0 + offset + 8) =
                base + ((u32)func_150ADA20() % span);
        }
    }
}"""


def variants():
    yield "selected", INITIALIZER
    staged = INITIALIZER.replace(
        "    u32 span;", "    u32 span;\n    s32 target;"
    ).replace(
        "            *(s16 *)(D_800BE4E0 + offset + 8) =\n"
        "                base + ((u32)func_150ADA20() % span);",
        "            target = base;\n"
        "            target += (u32)func_150ADA20() % span;\n"
        "            *(s16 *)(D_800BE4E0 + offset + 8) = target;",
    )
    yield "staged-target", staged
    yield "staged-target-signed-span", staged.replace(
        "    u32 span;", "    s32 span;"
    )
    yield "signed-span", INITIALIZER.replace("    u32 span;", "    s32 span;")
    yield "less-than", INITIALIZER.replace(
        "offset != 100", "offset < 100"
    )
    yield "do-while", INITIALIZER.replace(
        "        for (offset = 0; offset != 100; offset += 10) {\n"
        "            *(s16 *)(D_800BE4E0 + offset + 8) =\n"
        "                base + ((u32)func_150ADA20() % span);\n"
        "        }",
        "        offset = 0;\n"
        "        do {\n"
        "            *(s16 *)(D_800BE4E0 + offset + 8) =\n"
        "                base + ((u32)func_150ADA20() % span);\n"
        "            offset += 10;\n"
        "        } while (offset != 100);",
    )
    yield "unsigned-random-local", INITIALIZER.replace(
        "    u32 span;", "    u32 span;\n    u32 random;"
    ).replace(
        "            *(s16 *)(D_800BE4E0 + offset + 8) =\n"
        "                base + ((u32)func_150ADA20() % span);",
        "            random = func_150ADA20();\n"
        "            *(s16 *)(D_800BE4E0 + offset + 8) =\n"
        "                base + (random % span);",
    )
    yield "byte-pointer", INITIALIZER.replace(
        "    u32 span;", "    u32 span;\n    u8 *records;"
    ).replace(
        "        func_150CDB6C(intensity);",
        "        func_150CDB6C(intensity);\n"
        "        records = (u8 *)D_800BE4E0;",
    ).replace("D_800BE4E0 + offset + 8", "records + offset + 8")


def candidate_source(before, initializer):
    if before.count("extern f32 D_800BE9A4;\n") != 1:
        raise ValueError("Motion-target declaration anchor changed")
    result = before.replace(
        "extern f32 D_800BE9A4;\n",
        "extern f32 D_800BE9A4;\n" + DECLARATIONS,
        1,
    )
    for name, body in (
        ("func_150C84F4", WRAPPER),
        ("func_150C851C", initializer),
    ):
        start, end = function_span(result, name)
        predecessor = result[start:end]
        if predecessor != "s32 %s() {\n    return 0;\n}" % name:
            raise ValueError("Motion-target predecessor changed: " + name)
        result = result[:start] + body + result[end:]
    return result


def normalized_retail(image, info):
    data = bytearray(
        image[info["rom"] : info["rom"] + info["words"] * 4]
    )
    for offset, rows in info["bindings"].items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(
            ">I", data, offset,
            struct.unpack_from(">I", data, offset)[0] & mask,
        )
    return bytes(data)


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    before = (root / SOURCE).read_text()
    image = (root / "conker/conker.us.bin").read_bytes()
    records = []
    for label, initializer in variants():
        obj, diagnostics = compile_owner(
            root,
            output,
            candidate_source(before, initializer),
            label,
            flags=("-O2", "-g3"),
        )
        row = {"variant": label, "diagnostics": diagnostics, "functions": {}}
        for name, info in FUNCTIONS.items():
            raw, bindings = payload(obj, name)
            retail = normalized_retail(image, info)
            actual_words = struct.unpack(">%dI" % (len(raw) // 4), raw)
            retail_words = struct.unpack(">%dI" % info["words"], retail)
            differences = [
                index * 4
                for index, (actual, expected) in enumerate(
                    itertools.zip_longest(
                        actual_words, retail_words, fillvalue=None
                    )
                )
                if actual != expected
            ]
            result = {
                "words": len(actual_words),
                "frame": (-actual_words[0] & 0xFFFF) if actual_words else 0,
                "differences": len(differences),
                "difference_offsets": differences,
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "retail_sha256": hashlib.sha256(
                    image[info["rom"] : info["rom"] + info["words"] * 4]
                ).hexdigest(),
                "bindings": {hex(offset): value for offset, value in bindings.items()},
            }
            row["functions"][name] = result
        records.append(row)
        print(
            label,
            *[
                "%s:%d/%d" %
                (name, values["words"], values["differences"])
                for name, values in row["functions"].items()
            ],
            flush=True,
        )
    (output / "candidate-measurements.json").write_text(
        json.dumps(records, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
