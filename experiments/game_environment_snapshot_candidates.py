"""Screen semantic C forms for func_151732E0's environment snapshot setup."""

import hashlib
import itertools
import json
import os
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x151732E0
ROM = 0x1A0790
WORDS = 62
FUNCTION = "func_151732E0"
SOURCE = "conker/src/game/generated_1A0790.c"
OWNER = "generated_1A0790"
BUILD = "conker/build/game-environment-snapshot-candidates"
OLD_TYPES = """typedef struct {
    u8 pad[0x46];
    s8 value;
} Generated1A0790State;
"""
INSTALL_TYPES = """typedef struct {
    u16 fallbackValue;
    u16 selectedValue;
    u8 retained04[0x36];
    s16 firstRange;
    s16 secondRange;
    s16 thirdRange;
    s16 fourthRange;
    u8 red;
    u8 green;
    u8 blue;
    u8 alpha;
    s8 value;
} Generated1A0790State;

typedef struct {
    u8 red;
    u8 green;
    u8 blue;
    u8 alpha;
    s16 firstRange;
    s16 secondRange;
    s16 thirdRange;
    s16 fourthRange;
    u16 selectedValue;
    u16 fallbackValue;
} EnvironmentSnapshot151732E0;
"""
DECLARATIONS = """extern EnvironmentSnapshot151732E0 D_8008CC70;
extern s8 D_800DD2E0;
s32 func_151733E4();
"""
PLACEHOLDER = """s32 func_151732E0() {
    return 0;
}"""
SELECTED = """/* Snapshot the live environment and select its initial provider row. */
void func_151732E0(s32 context) {
    s16 secondRange;
    s8 selection;

    secondRange = D_800B0DF0->secondRange;
    if ((D_800B0DF0->fourthRange == secondRange) && (secondRange == 0)) {
        D_800B0DF0->fourthRange = 100;
    }
    D_8008CC70.red = D_800B0DF0->red;
    D_8008CC70.green = D_800B0DF0->green;
    D_8008CC70.blue = D_800B0DF0->blue;
    D_8008CC70.alpha = D_800B0DF0->alpha;
    D_8008CC70.firstRange = D_800B0DF0->firstRange;
    D_8008CC70.secondRange = D_800B0DF0->secondRange;
    D_8008CC70.thirdRange = D_800B0DF0->thirdRange;
    D_8008CC70.fourthRange = D_800B0DF0->fourthRange;
    D_8008CC70.selectedValue = D_800B0DF0->selectedValue;
    D_8008CC70.fallbackValue = D_800B0DF0->fallbackValue;
    if (D_800B0DF0->value != -1) {
        D_800DD2E0 = 1;
        selection = D_800B0DF0->value;
        func_151733E4(selection, selection, context, 0, -1);
        return;
    }
    D_800DD2E0 = 0;
    func_151733E4(0, 0, context, 0, -1);
}"""
SELECTED_NO_RETURN = SELECTED.replace(
    "        return;\n    }\n    D_800DD2E0 = 0;",
    "    } else {\n        D_800DD2E0 = 0;").replace(
    "    func_151733E4(0, 0, context, 0, -1);\n}",
    "        func_151733E4(0, 0, context, 0, -1);\n    }\n}")
SELECTED_REVERSED_COMPARE = SELECTED.replace(
    "D_800B0DF0->fourthRange == secondRange",
    "secondRange == D_800B0DF0->fourthRange", 1)
SELECTED_NESTED = SELECTED.replace(
    "    if ((D_800B0DF0->fourthRange == secondRange) && (secondRange == 0)) {\n"
    "        D_800B0DF0->fourthRange = 100;\n"
    "    }",
    "    if (D_800B0DF0->fourthRange == secondRange) {\n"
    "        if (secondRange == 0) {\n"
    "            D_800B0DF0->fourthRange = 100;\n"
    "        }\n"
    "    }", 1)
SELECTED_GOTO = SELECTED.replace(
    "    if ((D_800B0DF0->fourthRange == secondRange) && (secondRange == 0)) {\n"
    "        D_800B0DF0->fourthRange = 100;\n"
    "    }\n"
    "    D_8008CC70.red",
    "    if (D_800B0DF0->fourthRange != secondRange) {\n"
    "        goto snapshot;\n"
    "    }\n"
    "    if (secondRange == 0) {\n"
    "        D_800B0DF0->fourthRange = 100;\n"
    "    }\n"
    "snapshot:\n"
    "    D_8008CC70.red", 1)
SELECTED_LOCAL = SELECTED.replace(
    "    s8 selection;\n\n",
    "    s8 selection;\n    Generated1A0790State *state = D_800B0DF0;\n\n").replace(
    "D_800B0DF0->", "state->")


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    declarations = DECLARATIONS + "\n"
    if source.count(OLD_TYPES) == 1 and source.count(PLACEHOLDER) == 1:
        if INSTALL_TYPES in source or declarations in source or SELECTED in source:
            raise ValueError("Environment snapshot predecessor source changed")
        return source.replace(OLD_TYPES, INSTALL_TYPES, 1).replace(
            "extern Generated1A0790State *D_800B0DF0;\n",
            "extern Generated1A0790State *D_800B0DF0;\n" + declarations, 1).replace(
            PLACEHOLDER, body, 1)
    if source.count(INSTALL_TYPES) == 1 and source.count(declarations) == 1:
        for selected in (SELECTED, SELECTED_NO_RETURN, SELECTED_REVERSED_COMPARE,
                         SELECTED_NESTED, SELECTED_GOTO, SELECTED_LOCAL):
            if source.count(selected) == 1:
                return source.replace(selected, body, 1)
    raise ValueError("Environment snapshot source state changed")


def variants():
    yield "typed-direct", SELECTED
    yield "typed-reversed-compare", SELECTED_REVERSED_COMPARE
    yield "typed-nested", SELECTED_NESTED
    yield "typed-goto", SELECTED_GOTO
    yield "typed-else", SELECTED_NO_RETURN
    yield "typed-local", SELECTED_LOCAL
    yield "typed-local-else", SELECTED_NO_RETURN.replace(
        "    s8 selection;\n\n",
        "    s8 selection;\n    Generated1A0790State *state = D_800B0DF0;\n\n").replace(
        "D_800B0DF0->", "state->")


def compare(name, body, flags=("-O2", "-g3")):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(ROOT, output, source_with(body), name,
                                     flags=flags)
    linked, functions = link_owner(ROOT, output, obj, OWNER)
    info = functions[FUNCTION]
    ours = linked[info["value"]:info["value"] + info["size"]]
    retail = (ROOT / "conker/conker.us.bin").read_bytes()[ROM:ROM + WORDS * 4]
    our_words = struct.unpack(">%dI" % (len(ours) // 4), ours)
    retail_words = struct.unpack(">%dI" % WORDS, retail)
    differences = [
        {"offset": index * 4, "ours": left, "retail": right}
        for index, (left, right) in enumerate(
            itertools.zip_longest(our_words, retail_words, fillvalue=0))
        if left != right
    ]
    return {
        "name": name,
        "flags": flags,
        "words": len(our_words),
        "differences": len(differences),
        "difference_rows": differences,
        "diagnostics": diagnostics,
        "raw_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
    }


ROOT = Path(__file__).resolve().parents[2]


if __name__ == "__main__":
    records = []
    selected = os.environ.get("CANDIDATE_FILTER")
    for name, body in variants():
        if selected and name != selected:
            continue
        for label, flags in (("o2g3", ("-O2", "-g3")), ("o2", ("-O2",))):
            record = compare(name + "-" + label, body, flags)
            records.append(record)
            print(record["name"], record["words"], record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
