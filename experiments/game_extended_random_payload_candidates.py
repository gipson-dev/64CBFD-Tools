"""Screen semantic C forms for func_1515AA84's extended random payload."""

import hashlib
import itertools
import json
import os
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner,
    function_span,
    link_owner,
)
from tools.pad_generated_object import parse_object


FUNCTION = "func_1515AA84"
OWNER = "generated_185560"
SOURCE = "conker/src/game/generated_185560.c"
ROM = 0x187F34
WORDS = 65
BUILD = "conker/build/game-extended-random-payload-candidates"
PLACEHOLDER = """s32 func_1515AA84() {
    return 0;
}"""
TYPES = """typedef struct {
    f32 x;
    f32 y;
    f32 z;
} PayloadVector1515AA84;

typedef struct {
    u32 words[10];
} OwnerState1515AA84;

typedef struct {
    f32 zero;
    PayloadVector1515AA84 position;
    f32 scalar;
    OwnerState1515AA84 ownerState;
} ExtendedRandomPayload1515AA84;

typedef struct {
    u8 retained00[0x80];
    s16 minimumLifetime;
    s16 lifetimeRangeMinusOne;
    OwnerState1515AA84 ownerState;
} ExtendedRandomOwner1515AA84;

typedef struct {
    u32 retained[2];
    ExtendedRandomPayload1515AA84 payload;
} ExtendedRandomWorkspace1515AA84;

typedef struct {
    s16 minimum;
    s16 rangeMinusOne;
} LifetimeRange1515AA84;

s32 func_150ADA20(void);
u8 *func_15149130(s16, s8, s8, s8, u8, u8, void *, u8, s32);
"""

INSTALL_TYPES = """#include <string.h>
typedef struct {
    f32 x;
    f32 y;
    f32 z;
} PayloadVector1515AA84;

typedef struct {
    u32 words[10];
} OwnerState1515AA84;

typedef struct {
    f32 zero;
    PayloadVector1515AA84 position;
    f32 scalar;
    OwnerState1515AA84 ownerState;
} ExtendedRandomPayload1515AA84;

typedef struct {
    s16 minimum;
    s16 rangeMinusOne;
} LifetimeRange1515AA84;
"""
DECLARATIONS = """s32 func_150ADA20(void);
u8 *func_15149130(s16, s8, s8, s8, u8, u8, void *, u8, s32);
"""


def selected(duration_type="u32", modulo_cast="", record_type="u8 *",
             range_expression="owner->lifetimeRangeMinusOne + 1U",
             minimum_expression="owner->minimumLifetime"):
    return """/* Submit the position and retained owner state with a randomized lifetime. */
void func_1515AA84(ExtendedRandomOwner1515AA84 *owner,
        PayloadVector1515AA84 *position, f32 scalar, s32 unused3) {
    ExtendedRandomPayload1515AA84 payload;
    RECORD_TYPE record;
    DURATION_TYPE lifetime;

    payload.zero = 0.0f;
    payload.position = *position;
    payload.scalar = scalar;
    payload.ownerState = owner->ownerState;
    lifetime = func_150ADA20() % MODULO_CAST(RANGE_EXPRESSION) + MINIMUM_EXPRESSION;
    record = (RECORD_TYPE)func_15149130((s16)lifetime,
        -1, 0x3F, -1, 1, 0, (void *)0x3C,
        ((u8 *)owner)[0xC], ((u8 *)owner)[1]);
    if (record != NULL) {
        memcpy((u8 *)record + 0x28, &payload, sizeof(payload));
    }
}""".replace("RECORD_TYPE", record_type).replace(
        "DURATION_TYPE", duration_type).replace(
        "MODULO_CAST", modulo_cast).replace(
        "RANGE_EXPRESSION", range_expression).replace(
        "MINIMUM_EXPRESSION", minimum_expression)


def raw_owner(body):
    return body.replace(
        "ExtendedRandomOwner1515AA84 *owner", "u8 *owner").replace(
        "payload.ownerState = owner->ownerState;",
        "payload.ownerState = *(OwnerState1515AA84 *)(owner + 0x84);").replace(
        "owner->lifetimeRangeMinusOne", "*(s16 *)(owner + 0x82)").replace(
        "owner->minimumLifetime", "*(s16 *)(owner + 0x80)").replace(
        "((u8 *)owner)", "owner")


def volatile_owner(body):
    return body.replace("u8 *owner", "u8 * volatile owner", 1)


def address_taken_owner(body):
    body = raw_owner(body)
    body = body.replace(
        "    ExtendedRandomPayload1515AA84 payload;\n",
        "    ExtendedRandomPayload1515AA84 payload;\n    u8 *ownerAfter;\n")
    body = body.replace(
        "payload.ownerState = *(OwnerState1515AA84 *)(owner + 0x84);",
        "payload.ownerState = *(OwnerState1515AA84 *)"
        "((*(u8 * volatile *)&owner) + 0x84);")
    body = body.replace(
        "    lifetime = func_150ADA20() %",
        "    ownerAfter = *(u8 * volatile *)&owner;\n"
        "    lifetime = func_150ADA20() %")
    # Move the second forced reload to the far side of the RNG call.
    body = body.replace(
        "    ownerAfter = *(u8 * volatile *)&owner;\n"
        "    lifetime = func_150ADA20() %",
        "    lifetime = func_150ADA20();\n"
        "    ownerAfter = *(u8 * volatile *)&owner;\n"
        "    lifetime %=", 1)
    body = body.replace("(owner + 0x82)", "(ownerAfter + 0x82)")
    body = body.replace("(owner + 0x80)", "(ownerAfter + 0x80)")
    body = body.replace(
        ") + *(s16 *)(ownerAfter + 0x80);",
        ");\n    lifetime += *(s16 *)(ownerAfter + 0x80);")
    body = body.replace("owner[0xC]", "ownerAfter[0xC]")
    body = body.replace("owner[1]", "ownerAfter[1]")
    return body


def volatile_split_owner(body):
    body = volatile_owner(raw_owner(body))
    body = body.replace(
        "    ExtendedRandomPayload1515AA84 payload;\n",
        "    ExtendedRandomPayload1515AA84 payload;\n"
        "    u8 *ownerAfter;\n    u32 random;\n")
    body = body.replace(
        "    lifetime = func_150ADA20() %",
        "    random = func_150ADA20();\n"
        "    ownerAfter = owner;\n"
        "    lifetime = random %")
    body = body.replace("(owner + 0x82)", "(ownerAfter + 0x82)")
    body = body.replace("(owner + 0x80)", "(ownerAfter + 0x80)")
    body = body.replace("owner[0xC]", "ownerAfter[0xC]")
    body = body.replace("owner[1]", "ownerAfter[1]")
    return body


def inline_duration_owner(declarations):
    return """/* Submit the position and retained owner state with a randomized lifetime. */
void func_1515AA84(u8 * volatile owner,
        PayloadVector1515AA84 *position, f32 scalar, s32 unused3) {
    ExtendedRandomPayload1515AA84 payload;
DECLARATIONS

    payload.zero = 0.0f;
    payload.position = *position;
    payload.scalar = scalar;
    payload.ownerState = *(OwnerState1515AA84 *)(owner + 0x84);
    random = func_150ADA20();
    ownerAfter = owner;
    range = (LifetimeRange1515AA84 *)(ownerAfter + 0x80);
    record = func_15149130(
        (s16)(random % (range->rangeMinusOne + 1U) + range->minimum),
        -1, 0x3F, -1, 1, 0, (void *)0x3C,
        ownerAfter[0xC], ownerAfter[1]);
    if (record != NULL) {
        memcpy(record + 0x28, &payload, sizeof(payload));
    }
}""".replace("DECLARATIONS", declarations)


def volatile_split_range(body):
    body = volatile_split_owner(body)
    body = body.replace(
        "    u8 *ownerAfter;\n",
        "    u8 *ownerAfter;\n    LifetimeRange1515AA84 *range;\n")
    body = body.replace(
        "    ownerAfter = owner;\n",
        "    ownerAfter = owner;\n"
        "    range = (LifetimeRange1515AA84 *)(ownerAfter + 0x80);\n")
    body = body.replace(
        "*(s16 *)(ownerAfter + 0x82)", "range->rangeMinusOne")
    body = body.replace(
        "*(s16 *)(ownerAfter + 0x80)", "range->minimum")
    return body


def volatile_split_mutated_range(body, compound=False):
    body = volatile_split_owner(body)
    body = body.replace(
        "    u8 *ownerAfter;\n",
        "    u8 *ownerAfter;\n    u8 *rangeOwner;\n")
    assignment = ("    rangeOwner = ownerAfter;\n    rangeOwner += 0x80;\n"
                  if compound else "    rangeOwner = ownerAfter + 0x80;\n")
    body = body.replace(
        "    ownerAfter = owner;\n",
        "    ownerAfter = owner;\n" + assignment)
    body = body.replace(
        "*(s16 *)(ownerAfter + 0x82)", "*(s16 *)(rangeOwner + 2)")
    body = body.replace(
        "*(s16 *)(ownerAfter + 0x80)", "*(s16 *)rangeOwner")
    return body


SELECTED_MATCH = volatile_split_range(selected(duration_type="u16"))


def variants():
    yield "typed-u32", selected()
    yield "typed-s32", selected(duration_type="s32")
    yield "typed-u16", selected(duration_type="u16")
    yield "typed-s16", selected(duration_type="s16")
    yield "typed-cast-u32-range", selected(modulo_cast="(u32)")
    yield "typed-signed-one", selected(
        range_expression="owner->lifetimeRangeMinusOne + 1")
    yield "typed-cast-s16-minimum", selected(
        minimum_expression="(s16)owner->minimumLifetime")
    yield "raw-u32", raw_owner(selected())
    yield "raw-s32", raw_owner(selected(duration_type="s32"))
    yield "raw-u16", raw_owner(selected(duration_type="u16"))
    yield "raw-s16", raw_owner(selected(duration_type="s16"))
    yield "raw-signed-one", raw_owner(selected(
        range_expression="owner->lifetimeRangeMinusOne + 1"))
    yield "raw-volatile-u32", volatile_owner(raw_owner(selected()))
    yield "raw-volatile-s32", volatile_owner(raw_owner(selected(
        duration_type="s32")))
    yield "raw-volatile-u16", volatile_owner(raw_owner(selected(
        duration_type="u16")))
    yield "raw-volatile-s16", volatile_owner(raw_owner(selected(
        duration_type="s16")))
    yield "address-taken-u32", address_taken_owner(selected())
    yield "address-taken-s32", address_taken_owner(selected(
        duration_type="s32"))
    yield "address-taken-u16", address_taken_owner(selected(
        duration_type="u16"))
    yield "address-taken-s16", address_taken_owner(selected(
        duration_type="s16"))
    yield "volatile-split-u32", volatile_split_owner(selected())
    yield "volatile-split-s32", volatile_split_owner(selected(
        duration_type="s32"))
    yield "volatile-split-u16", volatile_split_owner(selected(
        duration_type="u16"))
    yield "volatile-split-s16", volatile_split_owner(selected(
        duration_type="s16"))
    declaration_sets = (
        "    u8 *record;\n    u32 random;\n    u8 *ownerAfter;\n"
        "    LifetimeRange1515AA84 *range;",
        "    u8 *ownerAfter;\n    LifetimeRange1515AA84 *range;\n"
        "    u8 *record;\n    u32 random;",
        "    u32 random;\n    u8 *ownerAfter;\n"
        "    LifetimeRange1515AA84 *range;\n    u8 *record;",
        "    LifetimeRange1515AA84 *range;\n    u8 *ownerAfter;\n"
        "    u32 random;\n    u8 *record;",
    )
    for index, declarations in enumerate(declaration_sets):
        yield "inline-duration-%d" % index, inline_duration_owner(declarations)
    yield "volatile-split-range-u32", volatile_split_range(selected())
    yield "volatile-split-range-s32", volatile_split_range(selected(
        duration_type="s32"))
    yield "volatile-split-range-u16", volatile_split_range(selected(
        duration_type="u16"))
    yield "volatile-split-range-s16", volatile_split_range(selected(
        duration_type="s16"))
    yield "volatile-split-mutated-range-s16", volatile_split_mutated_range(
        selected(duration_type="s16"))
    yield "volatile-split-compound-range-s16", volatile_split_mutated_range(
        selected(duration_type="s16"), compound=True)


def source_with(before, body):
    if before.count(PLACEHOLDER) != 1:
        raise ValueError("Extended-random-payload predecessor source changed")
    include = "#include <ultra64.h>\n"
    if before.count(include) != 1:
        raise ValueError("Extended-random-payload include anchor changed")
    return before.replace(include, include + "#include <string.h>\n" + TYPES + "\n", 1).replace(
        PLACEHOLDER, body, 1)


def qualified_source(live, body):
    marker = "#include <ultra64.h>\n"
    declarations = INSTALL_TYPES + DECLARATIONS + "\n"
    if live.count(PLACEHOLDER) == 1:
        return live.replace(marker, marker + declarations, 1).replace(
            PLACEHOLDER, body, 1)
    if live.count(SELECTED_MATCH) == 1 and live.count(declarations) == 1:
        return live if body == SELECTED_MATCH else live.replace(
            SELECTED_MATCH, body, 1)
    raise ValueError("Extended-random-payload source state changed")


def words(obj):
    data, functions, _ = parse_object(obj)
    info = functions[FUNCTION]
    raw = data[info["value"]:info["value"] + info["size"]]
    values = struct.unpack(">%dI" % (len(raw) // 4), raw)
    end = max(index for index, value in enumerate(values) if value == 0x03E00008) + 2
    return values[:end]


def compare(name, body, flags=("-O2", "-g3")):
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    live = (root / SOURCE).read_text()
    obj, diagnostics = compile_owner(
        root, output, qualified_source(live, body), name, flags=flags)
    linked, functions = link_owner(root, output, obj, OWNER)
    info = functions[FUNCTION]
    ours = linked[info["value"]:info["value"] + info["size"]]
    retail = (root / "conker/conker.us.bin").read_bytes()[ROM:ROM + WORDS * 4]
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
        "frame": (-our_words[0] & 0xFFFF) if our_words else 0,
        "differences": len(differences),
        "difference_rows": differences,
        "diagnostics": diagnostics,
        "raw_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
    }


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    before = (root / SOURCE).read_text()
    retail_raw = (root / "conker/conker.us.bin").read_bytes()[ROM:ROM + WORDS * 4]
    retail = struct.unpack(">%dI" % WORDS, retail_raw)
    rows = []
    selected_filter = os.environ.get("CANDIDATE_FILTER")
    for label, body in variants():
        if selected_filter and label != selected_filter:
            continue
        obj, diagnostics = compile_owner(root, output, source_with(before, body), label)
        linked, functions = link_owner(root, output, obj, OWNER)
        at = functions[FUNCTION]["value"]
        actual = struct.unpack(">%dI" % WORDS, linked[at:at + WORDS * 4])
        differences = [index for index, pair in enumerate(zip(actual, retail))
                       if pair[0] != pair[1]]
        raw_words = words(obj)
        row = {
            "label": label,
            "raw_words": len(raw_words),
            "linked_differences": len(differences),
            "difference_indices": differences,
            "diagnostics": diagnostics,
            "raw_sha256": hashlib.sha256(struct.pack(">%dI" % len(raw_words), *raw_words)).hexdigest(),
        }
        rows.append(row)
        print(label, "raw", len(raw_words), "diffs", len(differences), differences)
        subprocess.run([
            "mips-linux-gnu-objdump", "-dr", str(obj)
        ], check=True, stdout=(output / (label + "-objdump.txt")).open("w"))
    (output / "screen.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
