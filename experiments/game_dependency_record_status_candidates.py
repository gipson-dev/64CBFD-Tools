"""Screen source shapes for the indexed dependency-record status query."""

import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span, link_owner)


SOURCE = "conker/src/game/generated_C9EC0.c"
OWNER = "game/generated_C9EC0"
GUARD_OWNER = "generated_C9EC0"
TARGET = "func_1509D08C"
ENTRY = 0x1509D08C
ROM_OFFSET = 0xCA53C
WORDS = 61


BODY = r'''s32 func_1509D08C(s32 arg0, s32 index, s32 *first, s32 *second) {{
    u8 *base = D_800D2FB0;
    u8 *entry = base + index * 8;
    u8 *record;
    s16 *dependency;
    u32 count;
    u32 position;
    s32 resource;

    if (base == NULL) {{
        if (first != NULL) {{
            *first = 0xBF;
        }}
        if (second != NULL) {{
            *second = 0;
        }}
        return 0;
    }}

    record = *(u8 **)(entry + 8);
    if (record == NULL) {{
        if (first != NULL) {{
            *first = 0xBF;
        }}
        if (second != NULL) {{
            *second = 0;
        }}
        return 0;
    }}

    if (first != NULL) {{
        *first = **(s16 **)(record + 8);
        record = *(u8 **)(entry + 8);
    }}
    if (second != NULL) {{
        *second = **(s16 **)record;
        record = *(u8 **)(entry + 8);
    }}

    {loop}
    return 1;
}}
'''


LOOPS = {
    "wrapped-do": r'''count = *(u32 *)(record + 0xC);
    position = 0;
    if (count != 0) {
        dependency = *(s16 **)(record + 8);
        do {
            resource = *dependency;
            position++;
            if ((D_800D2E4C[resource >> 3] & (1 << (resource & 7))) == 0) {
                return 0;
            }
            dependency++;
        } while (position < count);
    }''',
    "wrapped-while": r'''count = *(u32 *)(record + 0xC);
    position = 0;
    dependency = *(s16 **)(record + 8);
    while (position < count) {
        resource = *dependency;
        position++;
        if ((D_800D2E4C[resource >> 3] & (1 << (resource & 7))) == 0) {
            return 0;
        }
        dependency++;
    }''',
    "early-do": r'''count = *(u32 *)(record + 0xC);
    if (count == 0) {
        return 1;
    }
    dependency = *(s16 **)(record + 8);
    position = 0;
    do {
        resource = *dependency;
        position++;
        if ((D_800D2E4C[resource >> 3] & (1 << (resource & 7))) == 0) {
            return 0;
        }
        dependency++;
    } while (position < count);''',
}


def selected_body():
    """Return the only screened source shape with the retail 61-word extent."""
    return BODY.format(loop=LOOPS["wrapped-do"])


def candidate_source(before):
    """Install the selected body or accept an already-installed production body."""
    selected = selected_body()
    if selected in before:
        return before
    lo, hi = function_span(before, TARGET)
    predecessor = before[lo:hi]
    if predecessor != "s32 func_1509D08C() {\n    return 0;\n}":
        raise ValueError("Unknown dependency-record status predecessor")
    return before[:lo] + selected + before[hi:]


def replace_body(source, body):
    lo, hi = function_span(source, TARGET)
    return source[:lo] + body + source[hi:]


def differences(actual, retail):
    common = min(len(actual), len(retail))
    offsets = [offset for offset in range(0, common, 4)
               if actual[offset:offset + 4] != retail[offset:offset + 4]]
    offsets.extend(range(common, max(len(actual), len(retail)), 4))
    return offsets


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / "conker/build/game-dependency-record-status-1509D08C-candidates"
    output.mkdir(parents=True, exist_ok=True)
    source = (root / SOURCE).read_text()
    retail = (root / "conker/conker.us.bin").read_bytes()[
        ROM_OFFSET:ROM_OFFSET + WORDS * 4]
    records = []
    for label, loop in LOOPS.items():
        candidate_source = replace_body(source, BODY.format(loop=loop))
        obj, diagnostics = compile_owner(root, output, candidate_source, label)
        linked, functions = link_owner(root, output, obj, OWNER)
        info = functions[TARGET]
        actual = linked[info["value"]:info["value"] + info["size"]]
        offsets = differences(actual, retail)
        record = {
            "variant": label,
            "words": len(actual) // 4,
            "retail_words": WORDS,
            "differences": len(offsets),
            "difference_offsets": offsets,
            "diagnostics": diagnostics,
        }
        records.append(record)
        print(json.dumps({key: value for key, value in record.items()
                          if key != "diagnostics"}), flush=True)
    (output / "results.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
