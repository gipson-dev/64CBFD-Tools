"""Screen semantic source shapes for the menu record submitter."""

import json
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span, link_owner)


SOURCE = "conker/src/game/generated_20AE20.c"
OWNER = "game/generated_20AE20"
TARGET = "func_151E2404"
ROM_OFFSET = 0x20F8B4
WORDS = 59


PREAMBLE = r'''extern s8 D_800AB690[];
extern s8 *D_80082BBC;
void func_150076A0(void);
'''


BODY = r'''void func_151E2404(void) {
    s32 index;
    s8 *source;
    s8 *record;

    source = D_800E0BE0;
    index = D_800AB690[D_8008FDD4[0x42] * 10];
    record = D_80082BBC + index * 10;
    record[0] = 0;
    record[1] = source[2];
    record[2] = source[3];
    record[3] = source[0x10];
    record[4] = source[0x11];
    {switch}
    record[8] = source[0x16];
    record[9] = source[6];
    func_150076A0();
}'''


SWITCHES = {
    "grouped": r'''switch (index) {
        case 0:
            record[5] = source[4];
            break;
        case 1:
        case 2:
            record[5] = source[0xD];
            record[6] = source[0xE];
            break;
        case 5:
        case 7:
            record[5] = source[0x12];
            break;
        case 8:
        case 9:
            record[5] = source[7];
            record[6] = source[0x13];
            break;
    }''',
    "explicit-default": r'''switch (index) {
        case 0:
            record[5] = source[4];
            break;
        case 1:
        case 2:
            record[5] = source[0xD];
            record[6] = source[0xE];
            break;
        case 5:
        case 7:
            record[5] = source[0x12];
            break;
        case 8:
        case 9:
            record[5] = source[7];
            record[6] = source[0x13];
            break;
        default:
            break;
    }''',
}


VARIANTS = {
    "grouped": BODY.replace("{switch}", SWITCHES["grouped"]),
    "register-source": BODY.replace("s8 *source;", "register s8 *source;").replace(
        "{switch}", SWITCHES["grouped"]),
    "volatile-pointee": BODY.replace("s8 *source;", "volatile s8 *source;").replace(
        "{switch}", SWITCHES["grouped"]),
    "register-volatile-pointee": BODY.replace(
        "s8 *source;", "register volatile s8 *source;").replace(
        "{switch}", SWITCHES["grouped"]),
    "explicit-default": BODY.replace("{switch}", SWITCHES["explicit-default"]),
}

_volatile = BODY.replace("s8 *source;", "volatile s8 *source;").replace(
    "{switch}", SWITCHES["grouped"])
_declarations = "    s32 index;\n    volatile s8 *source;\n    s8 *record;"
for _label, _replacement in {
    "source-index-record": "    volatile s8 *source;\n    s32 index;\n    s8 *record;",
    "source-record-index": "    volatile s8 *source;\n    s8 *record;\n    s32 index;",
    "index-record-source": "    s32 index;\n    s8 *record;\n    volatile s8 *source;",
    "record-index-source": "    s8 *record;\n    s32 index;\n    volatile s8 *source;",
    "record-source-index": "    s8 *record;\n    volatile s8 *source;\n    s32 index;",
}.items():
    VARIANTS["volatile-" + _label] = _volatile.replace(_declarations, _replacement)
VARIANTS["volatile-s8-index"] = _volatile.replace("s32 index;", "s8 index;")
VARIANTS["volatile-register-s8-index"] = _volatile.replace(
    "s32 index;", "register s8 index;")
VARIANTS["volatile-s16-index"] = _volatile.replace("s32 index;", "s16 index;")
VARIANTS["volatile-index-before-source"] = _volatile.replace(
    "    source = D_800E0BE0;\n    index = D_800AB690[D_8008FDD4[0x42] * 10];",
    "    index = D_800AB690[D_8008FDD4[0x42] * 10];\n    source = D_800E0BE0;")


def selected_body():
    return _volatile


def candidate_source(before, body):
    lo, hi = function_span(before, TARGET)
    predecessor = before[lo:hi]
    if predecessor not in ("s32 func_151E2404() {\n    return 0;\n}", body):
        raise ValueError("Unknown menu record submitter predecessor")
    if PREAMBLE not in before:
        insertion = before.index("/* Non-matching placeholders")
        before = before[:insertion] + PREAMBLE + "\n" + before[insertion:]
    lo, hi = function_span(before, TARGET)
    return before[:lo] + body + before[hi:]


def differences(actual, retail):
    common = min(len(actual), len(retail))
    offsets = [offset for offset in range(0, common, 4)
               if actual[offset:offset + 4] != retail[offset:offset + 4]]
    offsets.extend(range(common, max(len(actual), len(retail)), 4))
    return offsets


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / "conker/build/game-menu-record-submit-151E2404-candidates"
    output.mkdir(parents=True, exist_ok=True)
    source = (root / SOURCE).read_text()
    retail = (root / "conker/conker.us.bin").read_bytes()[
        ROM_OFFSET:ROM_OFFSET + WORDS * 4]
    records = []
    for label, body in VARIANTS.items():
        candidate = candidate_source(source, body)
        obj, diagnostics = compile_owner(root, output, candidate, label)
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
