"""Screen semantic C forms for func_150DFCA8 without editing production."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner,
    function_span,
    link_owner,
)
from tools.pad_generated_object import parse_object


OWNER = "generated_10CD70"
FUNCTION = "func_150DFCA8"
SOURCE = "conker/src/game/generated_10CD70.c"
BUILD = "conker/build/game-motion-target-clamp-150DFCA8-candidates"
ROM = 0x10D158
SIZE = 0xFC

DECLARATION_ANCHOR = "extern f32 D_800A0FB0;\n"
DECLARATIONS = (
    "extern f32 D_800A0FA0, D_800A0FA4, D_800A0FA8, D_800A0FAC;\n"
    "extern s32 D_800BE9E4;\n"
)
PLACEHOLDER = "s32 func_150DFCA8() {\n    return 0;\n}"

STRUCT = """typedef struct MotionTargetState150DFCA8 {
    f32 field0;
    f32 position;
    u8 reserved08[0x5C];
    f32 velocity;
    u8 reserved68[0x14];
    f32 targetVelocity;
} MotionTargetState150DFCA8;

"""

SELECTED = """/* Integrate the vertical position and approach its selected velocity. */
void func_150DFCA8(MotionTargetState150DFCA8 *state) {
    state->position += state->velocity * (f32)D_800BE9E4;
    if (state->position < 11.0f) {
        state->targetVelocity = D_800A0FA0;
    } else if (55.0f < state->position) {
        state->targetVelocity = -D_800A0FA4;
    }

    if (state->velocity < state->targetVelocity) {
        state->velocity += D_800A0FA8;
        if (state->targetVelocity < state->velocity) {
            state->velocity = state->targetVelocity;
        }
    } else if (state->targetVelocity < state->velocity) {
        state->velocity -= D_800A0FAC;
        if (state->velocity < state->targetVelocity) {
            state->velocity = state->targetVelocity;
        }
    }
}"""

BRANCH_TARGET = """/* Integrate the vertical position and approach its selected velocity. */
void func_150DFCA8(MotionTargetState150DFCA8 *state) {
    f32 target;

    state->position += state->velocity * (f32)D_800BE9E4;
    if (state->position < 11.0f) {
        target = D_800A0FA0;
        state->targetVelocity = target;
    } else if (55.0f < state->position) {
        target = -D_800A0FA4;
        state->targetVelocity = target;
    } else {
        target = state->targetVelocity;
    }

    if (state->velocity < target) {
        state->velocity += D_800A0FA8;
        if (target < state->velocity) {
            state->velocity = target;
        }
    } else if (target < state->velocity) {
        state->velocity -= D_800A0FAC;
        if (state->velocity < target) {
            state->velocity = target;
        }
    }
}"""


def recovered_owner(before, body=SELECTED, use_struct=True):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != PLACEHOLDER:
        raise ValueError("Unknown motion-target predecessor")
    if before.count(DECLARATION_ANCHOR) != 1:
        raise ValueError("Unknown motion-target declaration anchor")
    prefix = STRUCT if use_struct else ""
    return (before[:lo] + prefix + body + before[hi:]).replace(
        DECLARATION_ANCHOR, DECLARATION_ANCHOR + DECLARATIONS, 1)


def forms():
    yield "selected-struct", SELECTED, True
    yield "explicit-assignment", SELECTED.replace(
        "state->position += state->velocity * (f32)D_800BE9E4;",
        "state->position = state->position + state->velocity * (f32)D_800BE9E4;"), True
    yield "branch-target", BRANCH_TARGET, True
    yield "branch-target-explicit", BRANCH_TARGET.replace(
        "state->position += state->velocity * (f32)D_800BE9E4;",
        "state->position = state->position + state->velocity * (f32)D_800BE9E4;"), True
    yield "cached-position", SELECTED.replace(
        "    state->position += state->velocity * (f32)D_800BE9E4;\n"
        "    if (state->position < 11.0f) {",
        "    f32 position = state->position + state->velocity * (f32)D_800BE9E4;\n"
        "    state->position = position;\n"
        "    if (position < 11.0f) {").replace(
        "    } else if (55.0f < state->position) {",
        "    } else if (55.0f < position) {"), True
    yield "named-target", SELECTED.replace(
        "void func_150DFCA8(MotionTargetState150DFCA8 *state) {",
        "void func_150DFCA8(MotionTargetState150DFCA8 *state) {\n    f32 target;").replace(
        "        state->targetVelocity = D_800A0FA0;",
        "        target = D_800A0FA0;\n        state->targetVelocity = target;").replace(
        "        state->targetVelocity = -D_800A0FA4;",
        "        target = -D_800A0FA4;\n        state->targetVelocity = target;").replace(
        "\n\n    if (state->velocity < state->targetVelocity)",
        "\n\n    target = state->targetVelocity;\n    if (state->velocity < target)").replace(
        "state->targetVelocity < state->velocity", "target < state->velocity").replace(
        "state->velocity < state->targetVelocity", "state->velocity < target").replace(
        "state->velocity = state->targetVelocity", "state->velocity = target"), True
    raw = SELECTED.replace(
        "MotionTargetState150DFCA8 *state", "u8 *state").replace(
        "state->position", "*(f32 *)(state + 4)").replace(
        "state->velocity", "*(f32 *)(state + 0x64)").replace(
        "state->targetVelocity", "*(f32 *)(state + 0x7C)")
    yield "raw-offsets", raw, False


def measure(root, out, label, body, use_struct):
    before = (root / SOURCE).read_text()
    obj, diagnostics = compile_owner(
        root, out, recovered_owner(before, body, use_struct), label)
    if diagnostics:
        raise ValueError("Motion-target compiler diagnostics: " + diagnostics)
    linked, functions = link_owner(root, out, obj, OWNER)
    info = functions[FUNCTION]
    candidate = linked[info["value"]:info["value"] + info["size"]]
    retail = (root / "conker/conker.us.bin").read_bytes()[ROM:ROM + SIZE]
    aligned = min(len(candidate), len(retail)) // 4
    candidate_words = struct.unpack_from(">%dI" % aligned, candidate)
    retail_words = struct.unpack_from(">%dI" % aligned, retail)
    _, _, relocations = parse_object(obj)
    rows = [
        (index * 4, expected, actual)
        for index, (expected, actual) in enumerate(zip(retail_words, candidate_words))
        if expected != actual
    ]
    result = {
        "label": label,
        "words": len(candidate) // 4,
        "retail_words": SIZE // 4,
        "extent_gap": len(candidate) - SIZE,
        "differences": len(rows) + abs(len(candidate) - SIZE) // 4,
        "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
        "relocations": sum(
            len(items) for offset, items in relocations.items()
            if info["value"] <= offset < info["value"] + info["size"]),
        "difference_rows": [
            {"offset": offset, "retail": expected, "candidate": actual}
            for offset, expected, actual in rows
        ],
    }
    (out / (label + "-audit.json")).write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    out.mkdir(parents=True, exist_ok=True)
    rows = [measure(root, out, *form) for form in forms()]
    rows.sort(key=lambda row: (row["differences"], abs(row["extent_gap"]), row["label"]))
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
