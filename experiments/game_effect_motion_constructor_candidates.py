"""Screen semantic C forms for func_15189900's motion-effect constructor."""

import hashlib
import itertools
import json
import os
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x15189900
ROM = 0x1B6DB0
WORDS = 64
FUNCTION = "func_15189900"
SOURCE = "conker/src/game/generated_1B6DB0.c"
OWNER = "generated_1B6DB0"
BUILD = "conker/build/game-effect-motion-constructor-candidates"
PLACEHOLDER = """s32 func_15189900() {
    return 0;
}"""
TYPES = """typedef struct {
    u8 retained00[0x08];
    f32 positionX;
    f32 positionY;
    f32 positionZ;
    f32 velocityX;
    f32 velocityY;
    f32 velocityZ;
    u8 retained20[0x30];
} MotionEffectDescriptor15189900;

typedef struct {
    u8 retained00[0x10];
    MotionEffectDescriptor15189900 descriptor;
    s16 age;
    u8 retained62[2];
    f32 elapsed;
    f32 baselineY;
    s32 spatialHandle;
    u8 enabled;
    u8 retained71[7];
} MotionEffect15189900;
"""
DECLARATIONS = """void *func_15167A68(s32, s32, s32, s32, u8, u8);
void func_1510F800(s32);
s32 func_1510FD20(s32, s32);
void *memcpy(void *, const void *, u32);
"""
SELECTED = """/* Create and register an effect from a copied motion descriptor. */
void func_15189900(MotionEffectDescriptor15189900 *descriptor, u8 enabled) {
    MotionEffect15189900 *effect;

    effect = (MotionEffect15189900 *)func_15167A68(0x1A, 1,
                                                   sizeof(MotionEffect15189900),
                                                   1, 0xFF, 1);
    if (effect != NULL) {
        memcpy(&effect->descriptor, descriptor, sizeof(*descriptor));
        func_1510F800(0);
        effect->spatialHandle = func_1510FD20(
            (s32)(effect->descriptor.positionX + effect->descriptor.velocityX * 0.5f),
            (s32)(effect->descriptor.positionZ + effect->descriptor.velocityZ * 0.5f));
        effect->enabled = enabled != 0;
        effect->age = 0;
        effect->elapsed = 0.0f;
        if (effect->descriptor.velocityY < 0.0f) {
            effect->baselineY = effect->descriptor.positionY + effect->descriptor.velocityY;
        } else {
            effect->baselineY = effect->descriptor.positionY;
        }
    }
}"""
SELECTED_RAW_POINTER = SELECTED.replace(
    "    MotionEffect15189900 *effect;",
    "    u8 *effect;").replace(
    "    effect = (MotionEffect15189900 *)func_15167A68(0x1A, 1,\n"
    "                                                   sizeof(MotionEffect15189900),\n"
    "                                                   1, 0xFF, 1);",
    "    effect = func_15167A68(0x1A, 1, 0x78, 1, 0xFF, 1);").replace(
    "&effect->descriptor", "effect + 0x10").replace(
    "sizeof(*descriptor)", "0x50").replace(
    "effect->spatialHandle", "*(s32 *)(effect + 0x6C)").replace(
    "effect->descriptor.positionX", "*(f32 *)(effect + 0x18)").replace(
    "effect->descriptor.positionY", "*(f32 *)(effect + 0x1C)").replace(
    "effect->descriptor.positionZ", "*(f32 *)(effect + 0x20)").replace(
    "effect->descriptor.velocityX", "*(f32 *)(effect + 0x24)").replace(
    "effect->descriptor.velocityY", "*(f32 *)(effect + 0x28)").replace(
    "effect->descriptor.velocityZ", "*(f32 *)(effect + 0x2C)").replace(
    "effect->enabled", "effect[0x70]").replace(
    "effect->age", "*(s16 *)(effect + 0x60)").replace(
    "effect->elapsed", "*(f32 *)(effect + 0x64)").replace(
    "effect->baselineY", "*(f32 *)(effect + 0x68)")
SELECTED_DIRECT_BYTE = SELECTED.replace("enabled != 0", "enabled")
SELECTED_EXPLICIT_FLAG = SELECTED.replace(
    "        effect->enabled = enabled != 0;",
    "        if (enabled != 0) {\n"
    "            effect->enabled = 1;\n"
    "        } else {\n"
    "            effect->enabled = 0;\n"
    "        }")
SELECTED_LOCAL_FLAG = SELECTED.replace(
    "    MotionEffect15189900 *effect;\n",
    "    MotionEffect15189900 *effect;\n"
    "    s32 enabledValue;\n").replace(
    "        effect->enabled = enabled != 0;",
    "        enabledValue = 0;\n"
    "        if (enabled != 0) {\n"
    "            enabledValue = 1;\n"
    "        }\n"
    "        effect->enabled = enabledValue;")
SELECTED_LOCAL_FLAG_ELSE = SELECTED.replace(
    "    MotionEffect15189900 *effect;\n",
    "    MotionEffect15189900 *effect;\n"
    "    s32 enabledValue;\n").replace(
    "        effect->enabled = enabled != 0;",
    "        if (enabled != 0) {\n"
    "            enabledValue = 1;\n"
    "        } else {\n"
    "            enabledValue = 0;\n"
    "        }\n"
    "        effect->enabled = enabledValue;")
SELECTED_NEGATED_BRANCH = SELECTED.replace(
    "        if (effect->descriptor.velocityY < 0.0f) {\n"
    "            effect->baselineY = effect->descriptor.positionY + effect->descriptor.velocityY;\n"
    "        } else {\n"
    "            effect->baselineY = effect->descriptor.positionY;\n"
    "        }",
    "        if (effect->descriptor.velocityY >= 0.0f) {\n"
    "            effect->baselineY = effect->descriptor.positionY;\n"
    "        } else {\n"
    "            effect->baselineY = effect->descriptor.positionY + effect->descriptor.velocityY;\n"
    "        }")
SELECTED_SEPARATE_COORDINATES = SELECTED.replace(
    "    MotionEffect15189900 *effect;\n",
    "    MotionEffect15189900 *effect;\n"
    "    s32 midpointX;\n"
    "    s32 midpointZ;\n").replace(
    "        effect->spatialHandle = func_1510FD20(\n"
    "            (s32)(effect->descriptor.positionX + effect->descriptor.velocityX * 0.5f),\n"
    "            (s32)(effect->descriptor.positionZ + effect->descriptor.velocityZ * 0.5f));",
    "        midpointX = (s32)(effect->descriptor.positionX + effect->descriptor.velocityX * 0.5f);\n"
    "        midpointZ = (s32)(effect->descriptor.positionZ + effect->descriptor.velocityZ * 0.5f);\n"
    "        effect->spatialHandle = func_1510FD20(midpointX, midpointZ);")
BASELINE_BLOCK = (
    "        if (effect->descriptor.velocityY < 0.0f) {\n"
    "            effect->baselineY = effect->descriptor.positionY + effect->descriptor.velocityY;\n"
    "        } else {\n"
    "            effect->baselineY = effect->descriptor.positionY;\n"
    "        }")
BASELINE_FIRST_BLOCK = (
    "        effect->baselineY = effect->descriptor.positionY;\n"
    "        if (effect->descriptor.velocityY < 0.0f) {\n"
    "            effect->baselineY += effect->descriptor.velocityY;\n"
    "        }")
SELECTED_BASELINE_FIRST = SELECTED.replace(BASELINE_BLOCK, BASELINE_FIRST_BLOCK)
SELECTED_EXPLICIT_FLAG_BASELINE_FIRST = SELECTED_EXPLICIT_FLAG.replace(
    BASELINE_BLOCK, BASELINE_FIRST_BLOCK)
SELECTED_LOCAL_FLAG_BASELINE_FIRST = SELECTED_LOCAL_FLAG.replace(
    BASELINE_BLOCK, BASELINE_FIRST_BLOCK)
SELECTED_LOCAL_FLAG_ELSE_BASELINE_FIRST = SELECTED_LOCAL_FLAG_ELSE.replace(
    BASELINE_BLOCK, BASELINE_FIRST_BLOCK)
SELECTED = SELECTED_LOCAL_FLAG_ELSE


ROOT = Path(__file__).resolve().parents[2]


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    marker = "#include <ultra64.h>\n"
    installed = marker + "\n" + TYPES + "\n" + DECLARATIONS
    if source.count(PLACEHOLDER) == 1:
        if TYPES in source or DECLARATIONS in source or SELECTED in source:
            raise ValueError("Motion-effect constructor predecessor source changed")
        return source.replace(marker, installed, 1).replace(PLACEHOLDER, body, 1)
    if (source.count(TYPES) == 1 and source.count(DECLARATIONS) == 1 and
            source.count(SELECTED) == 1 and PLACEHOLDER not in source):
        return source.replace(SELECTED, body, 1)
    raise ValueError("Motion-effect constructor source state changed")


def variants():
    yield "typed", SELECTED
    yield "typed-direct-byte", SELECTED_DIRECT_BYTE
    yield "typed-explicit-flag", SELECTED_EXPLICIT_FLAG
    yield "typed-local-flag", SELECTED_LOCAL_FLAG
    yield "typed-local-flag-else", SELECTED_LOCAL_FLAG_ELSE
    yield "typed-baseline-first", SELECTED_BASELINE_FIRST
    yield "typed-explicit-flag-baseline-first", SELECTED_EXPLICIT_FLAG_BASELINE_FIRST
    yield "typed-local-flag-baseline-first", SELECTED_LOCAL_FLAG_BASELINE_FIRST
    yield "typed-local-flag-else-baseline-first", SELECTED_LOCAL_FLAG_ELSE_BASELINE_FIRST
    yield "typed-negated-branch", SELECTED_NEGATED_BRANCH
    yield "typed-separate-coordinates", SELECTED_SEPARATE_COORDINATES
    yield "raw-pointer", SELECTED_RAW_POINTER


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
        "frame": -struct.unpack(">h", ours[2:4])[0] if len(ours) >= 4 else None,
        "differences": len(differences),
        "difference_rows": differences,
        "diagnostics": diagnostics,
        "raw_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
    }


if __name__ == "__main__":
    records = []
    selected = os.environ.get("CANDIDATE_FILTER")
    for name, body in variants():
        if selected and name != selected:
            continue
        for label, flags in (("o2g3", ("-O2", "-g3")), ("o2", ("-O2",))):
            record = compare(name + "-" + label, body, flags)
            records.append(record)
            print(record["name"], record["words"], record["frame"],
                  record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
