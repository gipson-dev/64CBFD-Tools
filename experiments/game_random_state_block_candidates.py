"""Screen semantic C forms for random state-block replacement func_1509C120."""

import hashlib
import itertools
import json
from pathlib import Path
import struct
import sys

from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import (
    compile_owner,
    function_span,
    link_owner,
)


SOURCE = "conker/src/game_C8950.c"
OWNER = "game_C8950"
FUNCTION = "func_1509C120"
ROM = 0xC95D0
WORDS = 66
BUILD = "conker/build/game-random-state-block-1509C120-candidates"
RETAIL_BINDINGS = {
    0x018: [("R_MIPS_26", "func_150ADA20")],
    0x020: [("R_MIPS_HI16", "D_800D2E4C")],
    0x024: [("R_MIPS_LO16", "D_800D2E4C")],
    0x034: [("R_MIPS_26", "func_150ADA20")],
    0x06C: [("R_MIPS_26", "allocate_memory")],
    0x09C: [("R_MIPS_26", "func_10004074")],
    0x0C4: [("R_MIPS_HI16", "D_800D2E4C")],
    0x0CC: [("R_MIPS_LO16", "D_800D2E4C")],
    0x0D0: [("R_MIPS_HI16", "D_800D2E4C")],
    0x0D4: [("R_MIPS_LO16", "D_800D2E4C")],
    0x0DC: [("R_MIPS_26", "bcopy")],
    0x0E4: [("R_MIPS_26", "func_10004074")],
}


SELECTED = """/* Replace the active state block through a randomized allocation slot. */
void func_1509C120(void) {
    s32 index;
    struct102 *old;
    s32 blocks[4];
    s32 i;
    s32 kept;

    index = func_150ADA20() & 3;
    old = D_800D2E4C;
    if ((old == NULL) || ((func_150ADA20() & 4) != 0)) {
        if (index >= 0) {
            i = 0;
            do {
                blocks[i] = allocate_memory(0x1B, 0xFF, 2, 0);
                i++;
            } while (i <= index);
        }

        if (index >= 0) {
            i = 0;
            do {
                if (i != index) {
                    func_10004074((void *)blocks[i]);
                }
                i++;
            } while (i <= index);
        }

        kept = blocks[index];
        D_800D2E4C = (struct102 *)kept;
        if (old != NULL) {
            bcopy(old, D_800D2E4C, 0x1B);
            func_10004074(old);
        }
    }
}"""


def variants():
    yield "selected", SELECTED
    yield "old-after-array", SELECTED.replace(
        "    struct102 *old;\n    s32 blocks[4];",
        "    s32 blocks[4];\n    struct102 *old;",
    )
    yield "old-last", SELECTED.replace(
        "    struct102 *old;\n", ""
    ).replace(
        "    s32 kept;", "    s32 kept;\n    struct102 *old;"
    )
    yield "volatile-old", SELECTED.replace(
        "    struct102 *old;", "    struct102 * volatile old;"
    )
    aggregate = SELECTED.replace(
        "    struct102 *old;\n    s32 blocks[4];",
        "    struct {\n"
        "        struct102 *old;\n"
        "        s32 blocks[4];\n"
        "    } storage;",
    ).replace("blocks[", "storage.blocks[").replace(
        "s32 storage.blocks[4];", "s32 blocks[4];"
    ).replace(
        "    old = D_800D2E4C;", "    storage.old = D_800D2E4C;"
    ).replace("old == NULL", "storage.old == NULL").replace(
        "old != NULL", "storage.old != NULL"
    ).replace("bcopy(old,", "bcopy(storage.old,").replace(
        "func_10004074(old);", "func_10004074(storage.old);"
    )
    yield "aggregate-storage", aggregate
    yield "aggregate-direct", aggregate.replace(
        "    s32 kept;\n", ""
    ).replace(
        "        kept = storage.blocks[index];\n"
        "        D_800D2E4C = (struct102 *)kept;",
        "        D_800D2E4C = (struct102 *)storage.blocks[index];",
    )
    yield "branch-assign", SELECTED.replace(
        "        D_800D2E4C = (struct102 *)kept;\n"
        "        if (old != NULL) {\n"
        "            bcopy(old, D_800D2E4C, 0x1B);\n"
        "            func_10004074(old);\n"
        "        }",
        "        if (old != NULL) {\n"
        "            D_800D2E4C = (struct102 *)kept;\n"
        "            bcopy(old, D_800D2E4C, 0x1B);\n"
        "            func_10004074(old);\n"
        "        } else {\n"
        "            D_800D2E4C = (struct102 *)kept;\n"
        "        }",
    )
    yield "direct-selected", SELECTED.replace(
        "    s32 kept;\n", ""
    ).replace(
        "        kept = blocks[index];\n"
        "        D_800D2E4C = (struct102 *)kept;",
        "        D_800D2E4C = (struct102 *)blocks[index];",
    )
    pointer_array = SELECTED.replace(
        "    s32 blocks[4];", "    struct102 *blocks[4];"
    ).replace(
        "    s32 kept;", "    struct102 *kept;"
    ).replace(
        "                blocks[i] = allocate_memory(0x1B, 0xFF, 2, 0);",
        "                blocks[i] = (struct102 *)allocate_memory(0x1B, 0xFF, 2, 0);",
    ).replace(
        "                    func_10004074((void *)blocks[i]);",
        "                    func_10004074(blocks[i]);",
    ).replace(
        "        D_800D2E4C = (struct102 *)kept;",
        "        D_800D2E4C = kept;",
    )
    yield "pointer-array", pointer_array
    yield "pointer-array-direct", pointer_array.replace(
        "    struct102 *kept;\n", ""
    ).replace(
        "        kept = blocks[index];\n        D_800D2E4C = kept;",
        "        D_800D2E4C = blocks[index];",
    )
    early_return = SELECTED.replace(
        "    if ((old == NULL) || ((func_150ADA20() & 4) != 0)) {",
        "    if ((old != NULL) && ((func_150ADA20() & 4) == 0)) {\n"
        "        return;\n"
        "    }\n"
        "    {",
    )
    yield "early-return", early_return
    yield "early-return-pointer", pointer_array.replace(
        "    if ((old == NULL) || ((func_150ADA20() & 4) != 0)) {",
        "    if ((old != NULL) && ((func_150ADA20() & 4) == 0)) {\n"
        "        return;\n"
        "    }\n"
        "    {",
    )
    yield "for-loops", SELECTED.replace(
        "        if (index >= 0) {\n"
        "            i = 0;\n"
        "            do {\n"
        "                blocks[i] = allocate_memory(0x1B, 0xFF, 2, 0);\n"
        "                i++;\n"
        "            } while (i <= index);\n"
        "        }",
        "        for (i = 0; i <= index; i++) {\n"
        "            blocks[i] = allocate_memory(0x1B, 0xFF, 2, 0);\n"
        "        }",
    ).replace(
        "        if (index >= 0) {\n"
        "            i = 0;\n"
        "            do {\n"
        "                if (i != index) {\n"
        "                    func_10004074((void *)blocks[i]);\n"
        "                }\n"
        "                i++;\n"
        "            } while (i <= index);\n"
        "        }",
        "        for (i = 0; i <= index; i++) {\n"
        "            if (i != index) {\n"
        "                func_10004074((void *)blocks[i]);\n"
        "            }\n"
        "        }",
    )
    yield "less-than-bound", SELECTED.replace(
        "    s32 kept;", "    s32 kept;\n    s32 count;"
    ).replace(
        "        if (index >= 0) {\n            i = 0;",
        "        count = index + 1;\n"
        "        if (index >= 0) {\n            i = 0;",
        1,
    ).replace("while (i <= index);", "while (i < count);", 1)


def candidate_source(before, body):
    start, end = function_span(before, FUNCTION)
    predecessor = before[start:end]
    if predecessor != "void func_1509C120(void) {\n}":
        raise ValueError("Random state-block predecessor changed")
    return before[:start] + body + before[end:]


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    before = (root / SOURCE).read_text()
    retail = (root / "conker/conker.us.bin").read_bytes()[
        ROM:ROM + WORDS * 4
    ]
    retail_words = struct.unpack(">%dI" % WORDS, retail)
    records = []
    for label, body in variants():
        obj, diagnostics = compile_owner(
            root,
            output,
            candidate_source(before, body),
            label,
            flags=("-O2", "-g3"),
        )
        linked, functions = link_owner(root, output, obj, OWNER)
        info = functions[FUNCTION]
        actual = linked[info["value"]:info["value"] + info["size"]]
        actual_words = struct.unpack(">%dI" % (len(actual) // 4), actual)
        differences = [
            index * 4
            for index, (left, right) in enumerate(
                itertools.zip_longest(
                    actual_words, retail_words, fillvalue=0
                )
            )
            if left != right
        ]
        record = {
            "variant": label,
            "words": len(actual_words),
            "frame": (-actual_words[0] & 0xFFFF) if actual_words else 0,
            "differences": len(differences),
            "difference_offsets": differences,
            "linked_sha256": hashlib.sha256(actual).hexdigest(),
            "retail_sha256": hashlib.sha256(retail).hexdigest(),
            "diagnostics": diagnostics,
        }
        records.append(record)
        print(
            label,
            record["words"],
            hex(record["frame"]),
            record["differences"],
            flush=True,
        )
    (output / "candidate-measurements.json").write_text(
        json.dumps(records, indent=2) + "\n"
    )


def print_selected_details():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    raw, bindings = payload(output / "for-loops.o", FUNCTION)
    retail = (root / "conker/conker.us.bin").read_bytes()[
        ROM:ROM + WORDS * 4
    ]
    normalized = bytearray(retail)
    for offset, rows in RETAIL_BINDINGS.items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(
            ">I", normalized, offset,
            struct.unpack_from(">I", normalized, offset)[0] & mask)
    actual_words = struct.unpack(">%dI" % WORDS, raw)
    retail_words = struct.unpack(">%dI" % WORDS, normalized)

    def relocation_spec(rows):
        return "-" if not rows else ";".join(
            kind + ":" + symbol for kind, symbol in rows
        )

    print(json.dumps({
        "words": WORDS,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
        "bindings": {hex(offset): rows for offset, rows in bindings.items()},
        "differences": sum(
            left != right for left, right in zip(actual_words, retail_words)
        ),
    }, indent=2))
    for index, (actual, expected) in enumerate(
        zip(actual_words, retail_words)
    ):
        if actual == expected:
            continue
        offset = index * 4
        print(
            'dict(offset="0x%03X", expected="0x%08X", '
            'replacement="0x%08X", expected_relocations="%s"),' % (
                offset,
                actual,
                expected,
                relocation_spec(bindings.get(offset, [])),
            )
        )


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--details":
        print_selected_details()
    else:
        main()
