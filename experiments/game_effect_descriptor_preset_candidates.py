"""Compile semantic source shapes for func_150D64E8 without installing them."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ROOT = Path(__file__).resolve().parents[2]
FUNCTION = "func_150D64E8"
OWNER = "generated_1028F0"
SOURCE = "conker/src/game/generated_1028F0.c"
BUILD = "conker/build/game-effect-descriptor-preset-candidates"
ENTRY, ROM, WORDS = 0x150D64E8, 0x103998, 66
PLACEHOLDER = "s32 func_150D64E8() {\n    return 0;\n}"
DECLARATIONS = """typedef struct {
    s32 kind;
    s32 variant;
    u8 reserved08[0xC];
    f32 value14;
    f32 value18;
    f32 value1C;
    f32 value20;
    f32 value24;
    f32 value28;
    s32 selector2C;
    s32 selector30;
    f32 value34;
    f32 value38;
    f32 value3C;
    f32 value40;
    s16 value44;
    s16 value46;
    s16 value48;
    s16 value4A;
    s16 value4C;
    s16 value4E;
    s8 mode;
} EffectPreset150D64E8;

extern f32 D_800A0AB8;
extern f32 D_800A0ABC;
extern f32 D_800A0AC0;
extern f32 D_800A0AC4;
extern f32 D_800A0AC8;
extern s32 D_80082FA0;
extern s8 D_8008FD8C;

"""
SELECTED = """/* Initialize the fixed effect descriptor and its auxiliary scalar. */
void func_150D64E8(EffectPreset150D64E8 *preset, f32 *auxiliary) {
    preset->kind = 6;
    preset->variant = 3;
    *auxiliary = D_800A0AB8;
    preset->value14 = D_800A0ABC;
    preset->value18 = D_800A0AC0;
    preset->value1C = 150.0f;
    preset->value20 = 105.0f;
    preset->value24 = 396.0f;
    preset->value28 = 612.0f;
    preset->selector2C = 4;
    preset->selector30 = 3;
    preset->value34 = 25.0f;
    preset->value38 = D_800A0AC4;
    preset->value3C = -2.0f;
    preset->value40 = D_800A0AC8;
    preset->value44 = 20;
    preset->value46 = 30;
    preset->value48 = 100;
    preset->value4A = 100;
    preset->value4C = 12;
    preset->value4E = 20;
    if ((D_80082FA0 >= 2) || (D_8008FD8C >= 8)) {
        preset->mode = -1;
    } else {
        preset->mode = 0;
    }
}
"""


def source_states(live):
    marker = '#include "structs.h"\n'
    if live.count(PLACEHOLDER) == 1:
        if live.count(marker) != 1 or DECLARATIONS in live or SELECTED in live:
            raise ValueError("Effect descriptor predecessor changed")
        qualified = live.replace(marker, marker + "\n" + DECLARATIONS, 1)
        qualified = qualified.replace(PLACEHOLDER, SELECTED, 1)
        return live, qualified, False
    if live.count(SELECTED) == 1 and live.count(DECLARATIONS) == 1:
        predecessor = live.replace("\n" + DECLARATIONS, "", 1)
        predecessor = predecessor.replace(SELECTED, PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Effect descriptor source state changed")


def source_with(body):
    _, qualified, _ = source_states((ROOT / SOURCE).read_text())
    return qualified.replace(SELECTED, body, 1)


def compare(body=SELECTED, label="selected"):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(ROOT, output, source_with(body), label)
    text, functions, relocations = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info["value"]:info["value"] + info["size"]]
    linked, _ = link_owner(ROOT, output, obj, OWNER)
    ours = linked[info["value"]:info["value"] + info["size"]]
    retail = (ROOT / "conker/conker.us.bin").read_bytes()[ROM:ROM + WORDS * 4]
    differences = [
        {"offset": offset * 4, "ours": raw_word, "retail": retail_word}
        for offset, (raw_word, retail_word) in enumerate(zip(
            struct.unpack(">%dI" % (len(ours) // 4), ours),
            struct.unpack(">%dI" % WORDS, retail)))
        if raw_word != retail_word
    ]
    return {
        "words": len(raw) // 4,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "linked_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
        "differences": differences,
        "bindings": {offset - info["value"]: rows for offset, rows in relocations.items()
                     if info["value"] <= offset < info["value"] + info["size"]},
        "diagnostics": diagnostics,
    }


if __name__ == "__main__":
    tail = """    if ((D_80082FA0 >= 2) || (D_8008FD8C >= 8)) {
        preset->mode = -1;
    } else {
        preset->mode = 0;
    }
"""
    variants = {
        "selected": SELECTED,
        "accept-and": SELECTED.replace(tail, """    if ((D_80082FA0 < 2) && (D_8008FD8C < 8)) {
        preset->mode = 0;
    } else {
        preset->mode = -1;
    }
"""),
        "early-reject": SELECTED.replace(tail, """    if ((D_80082FA0 >= 2) || (D_8008FD8C >= 8)) {
        preset->mode = -1;
        return;
    }
    preset->mode = 0;
"""),
        "nested": SELECTED.replace(tail, """    if (D_80082FA0 < 2) {
        if (D_8008FD8C < 8) {
            preset->mode = 0;
            return;
        }
    }
    preset->mode = -1;
"""),
    }
    for label, body in variants.items():
        result = compare(body, label)
        print(json.dumps({"label": label, **{key: value for key, value in result.items()
                                          if key not in ("bindings", "diagnostics")}}, indent=2))
