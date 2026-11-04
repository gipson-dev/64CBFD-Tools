"""Screen semantic C forms for func_1512B630's threshold transition."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner,
    link_owner,
)


FUNCTION = "func_1512B630"
OWNER = "generated_157840"
SOURCE = "conker/src/game/generated_157840.c"
BUILD = "conker/build/game-record-threshold-transition-1512B630-candidates"
ENTRY = 0x1512B630
ROM = 0x158AE0
WORDS = 64

PLACEHOLDER = """s32 func_1512B630() {
    return 0;
}"""

DECLARATIONS = """extern s16 D_800DC204[];
extern s16 D_800DC206[];
"""

BODY_TEMPLATE = """/* Update a directional transition from the actor's signed threshold. */
s32 func_1512B630(u8 *actor, u8 *transition, s32 threshold, s32 value,
                  s32 otherValue, s32 alternate) {
    s32 actorThreshold;

    if (alternate == 0) {
        actorThreshold = D_800DC204[actor[0x23D] * 0x10 +
                                   *(s16 *)(actor + 0x1B4) * 4];
    } else {
        actorThreshold = D_800DC206[actor[0x23D] * 0x10 +
                                   *(s16 *)(actor + 0x1B4) * 4];
    }
    if (*(s32 *)(actor + 0x84) & 0x8000) {
        actorThreshold = DOUBLE_EXPR;
    }
    if ((actorThreshold < threshold) && (value < otherValue)) {
        transition[0] = 2;
        func_1512B5FC(transition, value, threshold);
        return 1;
    }
    if ((actorThreshold < threshold) && (otherValue < value)) {
        transition[0] = 1;
        func_1512B5FC(transition, value, threshold);
        return 1;
    }
    transition[1] = 0;
    transition[0] = 0;
    *(s32 *)(transition + 8) = 0xFFFC;
    return 0;
}"""

TYPED_BODY_TEMPLATE = """typedef struct {
    u8 state;
    u8 active;
    u8 previous;
    u8 pad3;
    s32 value;
    s32 threshold;
} ActorThresholdTransition;

/* Update a directional transition from the actor's signed threshold. */
s32 func_1512B630(u8 *actor, ActorThresholdTransition *transition,
                  s32 threshold, s32 value, s32 otherValue, s32 alternate) {
    s32 actorThreshold;

    if (alternate == 0) {
        actorThreshold = D_800DC204[actor[0x23D] * 0x10 +
                                   *(s16 *)(actor + 0x1B4) * 4];
    } else {
        actorThreshold = D_800DC206[actor[0x23D] * 0x10 +
                                   *(s16 *)(actor + 0x1B4) * 4];
    }
    if (*(s32 *)(actor + 0x84) & 0x8000) {
        actorThreshold = DOUBLE_EXPR;
    }
    if ((actorThreshold < threshold) && (value < otherValue)) {
        transition->state = 2;
        func_1512B5FC((u8 *)transition, value, threshold);
        return 1;
    }
    if ((actorThreshold < threshold) && (otherValue < value)) {
        transition->state = 1;
        func_1512B5FC((u8 *)transition, value, threshold);
        return 1;
    }
    transition->active = 0;
    transition->state = 0;
    transition->threshold = 0xFFFC;
    return 0;
}"""

FULL_TYPED_BODY_TEMPLATE = """typedef struct {
    u8 state;
    u8 active;
    u8 previous;
    u8 pad3;
    s32 value;
    s32 threshold;
} ActorThresholdTransition;

typedef struct {
    u8 pad0[0x84];
    s32 flags;
    u8 pad88[0x12C];
    s16 thresholdIndex;
    u8 pad1B6[0x87];
    u8 playerIndex;
} ThresholdActor1512B630;

/* Update a directional transition from the actor's signed threshold. */
s32 func_1512B630(ThresholdActor1512B630 *actor,
                  ActorThresholdTransition *transition, s32 threshold,
                  s32 value, s32 otherValue, s32 alternate) {
    s32 actorThreshold;

    if (alternate == 0) {
        actorThreshold = *(s16 *)((u8 *)D_800DC204 +
                                  actor->thresholdIndex * 8 +
                                  actor->playerIndex * 0x20);
    } else {
        actorThreshold = *(s16 *)((u8 *)D_800DC206 +
                                  actor->thresholdIndex * 8 +
                                  actor->playerIndex * 0x20);
    }
    if (actor->flags & 0x8000) {
        actorThreshold = DOUBLE_EXPR;
    }
    if ((actorThreshold < threshold) && (value < otherValue)) {
        transition->state = 2;
        func_1512B5FC((u8 *)transition, value, threshold);
        return 1;
    }
    if ((actorThreshold < threshold) && (otherValue < value)) {
        transition->state = 1;
        func_1512B5FC((u8 *)transition, value, threshold);
        return 1;
    }
    transition->active = 0;
    transition->state = 0;
    transition->threshold = 0xFFFC;
    return 0;
}"""


DOUBLE_FORMS = {
    "signed-shift": "(s16)(actorThreshold << 1)",
    "signed-multiply": "(s16)(actorThreshold * 2)",
    "unsigned-shift": "(s16)((u16)actorThreshold << 1)",
    "plain-shift": "actorThreshold << 1",
    "plain-multiply": "actorThreshold * 2",
}

TYPED_POINTER_REVERSED = TYPED_BODY_TEMPLATE.replace(
    "D_800DC204[actor[0x23D] * 0x10 +\n"
    "                                   *(s16 *)(actor + 0x1B4) * 4]",
    "*(s16 *)((u8 *)D_800DC204 +\n"
    "                                  *(s16 *)(actor + 0x1B4) * 8 +\n"
    "                                  actor[0x23D] * 0x20)",
).replace(
    "D_800DC206[actor[0x23D] * 0x10 +\n"
    "                                   *(s16 *)(actor + 0x1B4) * 4]",
    "*(s16 *)((u8 *)D_800DC206 +\n"
    "                                  *(s16 *)(actor + 0x1B4) * 8 +\n"
    "                                  actor[0x23D] * 0x20)",
)
SELECTED = TYPED_POINTER_REVERSED.replace(
    "DOUBLE_EXPR", DOUBLE_FORMS["signed-multiply"]
)


def variants():
    for label, expression in DOUBLE_FORMS.items():
        yield "byte-" + label, BODY_TEMPLATE.replace("DOUBLE_EXPR", expression)
        yield "typed-" + label, TYPED_BODY_TEMPLATE.replace(
            "DOUBLE_EXPR", expression
        )
    pointer = BODY_TEMPLATE.replace(
        "D_800DC204[actor[0x23D] * 0x10 +\n"
        "                                   *(s16 *)(actor + 0x1B4) * 4]",
        "*(s16 *)((u8 *)D_800DC204 + actor[0x23D] * 0x20 +\n"
        "                 *(s16 *)(actor + 0x1B4) * 8)",
    ).replace(
        "D_800DC206[actor[0x23D] * 0x10 +\n"
        "                                   *(s16 *)(actor + 0x1B4) * 4]",
        "*(s16 *)((u8 *)D_800DC206 + actor[0x23D] * 0x20 +\n"
        "                 *(s16 *)(actor + 0x1B4) * 8)",
    )
    yield "byte-pointer-signed-shift", pointer.replace(
        "DOUBLE_EXPR", DOUBLE_FORMS["signed-shift"]
    )
    yield "byte-pointer-signed-multiply", pointer.replace(
        "DOUBLE_EXPR", DOUBLE_FORMS["signed-multiply"]
    )
    reversed_pointer = pointer.replace(
        "actor[0x23D] * 0x20 +\n"
        "                 *(s16 *)(actor + 0x1B4) * 8",
        "*(s16 *)(actor + 0x1B4) * 8 +\n"
        "                 actor[0x23D] * 0x20",
    )
    yield "byte-pointer-reversed-signed-shift", reversed_pointer.replace(
        "DOUBLE_EXPR", DOUBLE_FORMS["signed-shift"]
    )
    yield "byte-pointer-reversed-signed-multiply", reversed_pointer.replace(
        "DOUBLE_EXPR", DOUBLE_FORMS["signed-multiply"]
    )
    yield "fully-typed-reversed-signed-shift", FULL_TYPED_BODY_TEMPLATE.replace(
        "DOUBLE_EXPR", DOUBLE_FORMS["signed-shift"]
    )
    yield "fully-typed-reversed-signed-multiply", FULL_TYPED_BODY_TEMPLATE.replace(
        "DOUBLE_EXPR", DOUBLE_FORMS["signed-multiply"]
    )
    yield "typed-transition-pointer-reversed-signed-shift", TYPED_POINTER_REVERSED.replace(
        "DOUBLE_EXPR", DOUBLE_FORMS["signed-shift"]
    )
    yield "typed-transition-pointer-reversed-signed-multiply", TYPED_POINTER_REVERSED.replace(
        "DOUBLE_EXPR", DOUBLE_FORMS["signed-multiply"]
    )


def candidate_source(before, body):
    if before.count(PLACEHOLDER) != 1:
        raise ValueError("Threshold-transition placeholder anchor changed")
    anchor = "#include \"structs.h\"\n"
    if before.count(anchor) != 1:
        raise ValueError("Threshold-transition declaration anchor changed")
    return before.replace(anchor, anchor + DECLARATIONS, 1).replace(
        PLACEHOLDER, body, 1
    )


def retail_bytes(root):
    image = (root / "conker/conker.us.bin").read_bytes()
    return image[ROM:ROM + WORDS * 4]


def compare(actual, retail):
    actual_words = list(struct.iter_unpack(">I", actual))
    retail_words = list(struct.iter_unpack(">I", retail))
    limit = max(len(actual_words), len(retail_words))
    return [
        index for index in range(limit)
        if (actual_words[index] if index < len(actual_words) else None) !=
           (retail_words[index] if index < len(retail_words) else None)
    ]


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    before = (root / SOURCE).read_text()
    retail = retail_bytes(root)
    records = []
    for label, body in variants():
        source = candidate_source(before, body)
        obj, diagnostics = compile_owner(root, output, source, label + "-" + OWNER)
        linked, functions = link_owner(root, output, obj, OWNER)
        info = functions[FUNCTION]
        actual = linked[info["value"]:info["value"] + info["size"]]
        differences = compare(actual, retail)
        record = {
            "variant": label,
            "words": len(actual) // 4,
            "retail_words": WORDS,
            "differences": len(differences),
            "difference_indices": differences,
            "body_sha256": hashlib.sha256(actual).hexdigest(),
            "retail_sha256": hashlib.sha256(retail).hexdigest(),
            "diagnostics": diagnostics,
        }
        records.append(record)
        print(json.dumps({
            key: value for key, value in record.items() if key != "diagnostics"
        }))
    (output / "candidates.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
