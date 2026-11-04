"""Screen semantic C forms for path-offset condition callback func_15075938."""

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


SOURCE = "conker/src/game_A28B0.c"
OWNER = "game_A28B0"
FUNCTION = "func_15075938"
ROM = 0xA2DE8
WORDS = 70
BUILD = "conker/build/game-path-offset-condition-15075938-candidates"


SELECTED = """/* Test the wrapped path offset against the script condition. */
void func_15075938(void) {
    s32 changed;
    s32 current;
    s32 target;
    u8 pathCount;

    changed = 0;
    current = D_800D154C->unk21E - D_800D154C->unk221;
    if (current < 0) {
        pathCount = D_800D2108[D_800D154C->unk13F];
        current = current + pathCount - 1;
    } else {
        pathCount = D_800D2108[D_800D154C->unk13F];
        if (current >= pathCount - 1) {
            current = current - pathCount + 1;
        }
    }

    if (D_800D1891 == 0xFF) {
        target = pathCount - 2;
    } else {
        target = D_800D1891;
    }

    if (D_800D1892 == 0) {
        if (target == current) {
            changed = 1;
        }
    } else if (D_800D1892 == 1) {
        if (target != current) {
            changed = 1;
        }
    } else if (D_800D1892 == 2) {
        if (target < current) {
            changed = 1;
        }
    } else if (target > current) {
        changed = 1;
    }

    if (changed != 0) {
        func_15075400(D_800D1890);
    }
}"""


def variants():
    yield "selected", SELECTED
    yield "byte-changed", SELECTED.replace("    s32 changed;", "    u8 changed;")
    signed_path_count = SELECTED.replace(
        "    u8 pathCount;", "    s32 pathCount;"
    )
    yield "signed-path-count", signed_path_count
    yield "ordered-negative", signed_path_count.replace(
        "    s32 target;\n    s32 pathCount;",
        "    s32 target;\n    s32 pathCount;\n    u8 *pathCounts;",
    ).replace(
        "        pathCount = D_800D2108[D_800D154C->unk13F];",
        "        pathCounts = D_800D2108;\n"
        "        pathCount = pathCounts[D_800D154C->unk13F];",
        1,
    )
    yield "ordered-negative-block", signed_path_count.replace(
        "    if (current < 0) {\n"
        "        pathCount = D_800D2108[D_800D154C->unk13F];",
        "    if (current < 0) {\n"
        "        u8 *pathCounts;\n"
        "        pathCounts = D_800D2108;\n"
        "        pathCount = pathCounts[D_800D154C->unk13F];",
        1,
    )
    yield "pointer-sum-negative", signed_path_count.replace(
        "    s32 target;\n    s32 pathCount;",
        "    s32 target;\n    s32 pathCount;\n    u8 *pathCountPointer;",
    ).replace(
        "        pathCount = D_800D2108[D_800D154C->unk13F];",
        "        pathCountPointer = D_800D2108 + D_800D154C->unk13F;\n"
        "        pathCount = *pathCountPointer;",
        1,
    )
    yield "pointer-sum-negative-block", signed_path_count.replace(
        "    if (current < 0) {\n"
        "        pathCount = D_800D2108[D_800D154C->unk13F];",
        "    if (current < 0) {\n"
        "        u8 *pathCountPointer;\n"
        "        pathCountPointer = D_800D2108 + D_800D154C->unk13F;\n"
        "        pathCount = *pathCountPointer;",
        1,
    )
    yield "pointer-deref-negative", signed_path_count.replace(
        "        pathCount = D_800D2108[D_800D154C->unk13F];",
        "        pathCount = *(D_800D2108 + D_800D154C->unk13F);",
        1,
    )
    yield "unsigned-current", SELECTED.replace("    s32 current;", "    u32 current;")
    yield "nested-final", SELECTED.replace(
        "    } else if (target > current) {\n"
        "        changed = 1;\n"
        "    }",
        "    } else {\n"
        "        if (target > current) {\n"
        "            changed = 1;\n"
        "        }\n"
        "    }",
    )
    yield "direct-return-condition", SELECTED.replace(
        "    if (changed != 0) {", "    if (changed) {"
    )
    yield "count-minus-one", SELECTED.replace(
        "    u8 pathCount;", "    u8 pathCount;\n    s32 wrap;"
    ).replace(
        "        current = current + pathCount - 1;",
        "        wrap = pathCount - 1;\n        current += wrap;",
    ).replace(
        "        if (current >= pathCount - 1) {\n"
        "            current = current - pathCount + 1;",
        "        wrap = pathCount - 1;\n"
        "        if (current >= wrap) {\n"
        "            current -= wrap;",
    )


def candidate_source(before, body):
    start, end = function_span(before, FUNCTION)
    predecessor = before[start:end]
    if predecessor != "s32 func_15075938() {\n    return 0;\n}":
        raise ValueError("Path-offset condition predecessor changed")
    if before.count("s32 func_15075938();") != 1:
        raise ValueError("Path-offset condition declaration anchor changed")
    before = before.replace(
        "s32 func_15075938();", "void func_15075938(void);", 1
    )
    start, end = function_span(before, FUNCTION)
    return before[:start] + body + before[end:]


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    before = (root / SOURCE).read_text()
    retail = (root / "conker/conker.us.bin").read_bytes()[
        ROM : ROM + WORDS * 4
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
        actual = linked[info["value"] : info["value"] + info["size"]]
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
            "raw_sha256": hashlib.sha256(actual).hexdigest(),
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
    raw, bindings = payload(output / "signed-path-count.o", FUNCTION)
    retail = (root / "conker/conker.us.bin").read_bytes()[
        ROM : ROM + WORDS * 4
    ]
    actual_words = struct.unpack(">%dI" % WORDS, raw)
    retail_words = struct.unpack(">%dI" % WORDS, retail)
    print(json.dumps({
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
        if actual != expected:
            print(
                "0x%03X 0x%08X -> 0x%08X" %
                (index * 4, actual, expected)
            )


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--details":
        print_selected_details()
    else:
        main()
