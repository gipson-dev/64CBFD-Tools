"""Screen semantic C shapes for the twin resource-cleanup callbacks."""

import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span, link_owner)


SOURCE = "conker/src/game/generated_1F4650.c"
OWNER = "generated_1F4650"
TARGETS = (
    ("func_151C94D4", 0x151C94D4, 0x1F6984, "func_1513CA6C"),
    ("func_151C95D8", 0x151C95D8, 0x1F6A88, "func_1513CAA0"),
)
WORDS = 65


def body(name, finalizer, mode):
    lines = [
        "void %s(u8 *owner) {" % name,
        "    u8 *state = owner + 0x110;",
        "    void *resource;",
        "",
        "    if (*(void **)(owner + 0x13C) != NULL) {",
        "        func_1516972C(*(u8 **)(state + 0x2C));",
        "        func_1000FD38(func_151C87AC, state, 0);",
        "    }",
        "",
    ]
    if mode == "reload_owner":
        lines.extend((
            "    resource = *(void **)(owner + 0x144);",
            "    state = owner + 0x110;",
        ))
    elif mode == "state_first":
        lines.extend((
            "    state = owner + 0x110;",
            "    resource = *(void **)(state + 0x34);",
        ))
    elif mode == "direct_first":
        lines.append("    resource = *(void **)(owner + 0x144);")
    else:
        raise ValueError(mode)
    lines.extend((
        "    if (resource != NULL) {",
        "        func_1516972C(resource);",
        "    }",
    ))
    for offset in range(0x38, 0x54, 4):
        lines.extend((
            "    resource = *(void **)(state + 0x%X);" % offset,
            "    if (resource != NULL) {",
            "        func_1516972C(resource);",
            "    }",
        ))
    lines.extend((
        "    %s(owner);" % finalizer,
        "}",
    ))
    return "\n".join(lines)


def candidate_source(before, mode):
    result = before
    for name, _, _, finalizer in TARGETS:
        lo, hi = function_span(result, name)
        result = result[:lo] + body(name, finalizer, mode) + result[hi:]
    return result


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / "conker/build/game-cleanup-pair-candidates"
    output.mkdir(parents=True, exist_ok=True)
    before = (root / SOURCE).read_text()
    rom = (root / "conker/conker.us.bin").read_bytes()
    results = []
    for mode in ("reload_owner", "state_first", "direct_first"):
        source = candidate_source(before, mode)
        obj, diagnostics = compile_owner(root, output, source, mode)
        data, functions = link_owner(root, output, obj, OWNER)
        for name, _, rom_offset, _ in TARGETS:
            info = functions[name]
            actual = struct.unpack_from(">%dI" % (info["size"] // 4), data,
                                        info["value"])
            retail = struct.unpack_from(">%dI" % WORDS, rom, rom_offset)
            differences = tuple(index * 4 for index, pair in enumerate(zip(actual, retail))
                                if pair[0] != pair[1])
            differences += tuple(range(min(len(actual), WORDS) * 4,
                                       max(len(actual), WORDS) * 4, 4))
            row = {
                "mode": mode,
                "function": name,
                "words": len(actual),
                "retail_words": WORDS,
                "differences": len(differences),
                "offsets": ["0x%03X" % offset for offset in differences],
                "diagnostics": diagnostics,
            }
            results.append(row)
            print(json.dumps({key: value for key, value in row.items()
                              if key != "diagnostics"}), flush=True)
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
