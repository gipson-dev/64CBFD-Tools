"""Screen semantic C shapes for the event effect-band packet callback."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_actor_classifier_candidates import PROFILES
from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ENTRY, ROM, WORDS = 0x150C2700, 0xEFBB0, 65
FUNCTION = "func_150C2700"
SOURCE = "conker/src/game_EF410.c"
OWNER = "game_EF410"
BUILD = "conker/build/game-effect-band-packet-callback-candidates"
PLACEHOLDER = "s32 func_150C2700() {\n    return 0;\n}"
PLACEHOLDER_COMMENT = (
    "/* Non-matching C placeholders for "
    "asm/nonmatchings/game_EF410/func_150C2700.s. */"
)
PLACEHOLDER_BLOCK = PLACEHOLDER_COMMENT + "\n" + PLACEHOLDER
RETAIL_BINDINGS = {
    0x02C: [("R_MIPS_HI16", "D_800A0274")],
    0x030: [("R_MIPS_LO16", "D_800A0274")],
    0x034: [("R_MIPS_HI16", "D_800A0278")],
    0x038: [("R_MIPS_LO16", "D_800A0278")],
    0x044: [("R_MIPS_HI16", "D_800A027C")],
    0x04C: [("R_MIPS_LO16", "D_800A027C")],
    0x0E8: [("R_MIPS_26", "func_15150178")],
}
DECLARATIONS = """typedef struct {
    s16 kind;
    s16 mode;
    s16 offset;
    s16 eventCode;
} EffectBandDescriptor150C2700;

typedef struct {
    f32 x;
    f32 y;
    f32 z;
    s16 type;
    s16 variant;
    f32 width;
    f32 height;
    s16 lifetime;
    s16 zero;
    f32 parameter0;
    f32 parameter1;
    u8 opacity;
    u8 scale;
    u8 reserved26[2];
    f32 parameter2;
    f32 velocity;
    u8 active;
    u8 classId;
    u8 reserved32[2];
    f32 acceleration;
    u8 loop;
    u8 reserved39[3];
    f32 phase;
} EffectBandPayload150C2700;

typedef struct {
    EffectBandDescriptor150C2700 descriptor;
    EffectBandPayload150C2700 payload;
} EffectBandLocals150C2700;

extern f32 D_800A0274;
extern f32 D_800A0278;
extern f32 D_800A027C;
void func_15150178(EffectBandDescriptor150C2700 *,
                   EffectBandPayload150C2700 *, s32, u8, s32);
"""

SIGNATURE = """s32 func_150C2700(
        void *unusedOwner, s32 unusedEvent, f32 x, f32 y, f32 z,
        s32 unused5, s32 unused6, s32 unused7, s32 unused8, s32 unused9,
        s32 unused10, s32 unused11, s32 unused12, s32 unused13, u8 channel)"""
OLD_PROTOTYPE = "s32 func_150C2700();"
PROTOTYPE = SIGNATURE + ";"

BODY = SIGNATURE + """ {
    EffectBandLocals150C2700 locals;

    locals.descriptor.kind = 0x6B;
    locals.descriptor.mode = 0x46;
    locals.descriptor.offset = -0x1F;
    locals.descriptor.eventCode = 0x2E;
    locals.payload.x = x;
    locals.payload.y = y;
    locals.payload.z = z;
    locals.payload.type = 6;
    locals.payload.variant = 5;
    locals.payload.width = 30.0f;
    locals.payload.height = 35.0f;
    locals.payload.lifetime = 100;
    locals.payload.zero = 0;
    locals.payload.parameter0 = D_800A0274;
    locals.payload.parameter1 = D_800A0278;
    locals.payload.opacity = 0x9B;
    locals.payload.scale = 100;
    locals.payload.parameter2 = D_800A027C;
    locals.payload.velocity = 0.0f;
    locals.payload.active = 1;
    locals.payload.classId = 6;
    locals.payload.acceleration = 0.0f;
    locals.payload.loop = 1;
    locals.payload.phase = 0.0f;
    func_15150178(&locals.descriptor, &locals.payload, 0, channel, 1);
    return 1;
}
"""

TYPE_REUSE = BODY.replace(
    "locals.payload.classId = 6;",
    "locals.payload.classId = locals.payload.type;",
    1,
)
CLASS_CHAIN = BODY.replace(
    "locals.payload.type = 6;",
    "locals.payload.classId = (u8)(locals.payload.type = 6);",
    1,
).replace(
    "    locals.payload.classId = 6;\n    locals.payload.acceleration",
    "    locals.payload.acceleration",
    1,
)
TYPE_CHAIN = BODY.replace(
    "locals.payload.type = 6;",
    "locals.payload.type = (s16)(locals.payload.classId = 6);",
    1,
).replace(
    "    locals.payload.classId = 6;\n    locals.payload.acceleration",
    "    locals.payload.acceleration",
    1,
)
CLASS_REUSE = BODY.replace(
    "locals.payload.type = 6;",
    "locals.payload.classId = 6;\n    locals.payload.type = locals.payload.classId;",
    1,
).replace("    locals.payload.classId = 6;\n", "", 1)

SCALAR_M2C = SIGNATURE + """ {
    f32 phase;
    s8 loop;
    f32 acceleration;
    s8 classId;
    s8 active;
    f32 velocity;
    f32 parameter2;
    s8 scale;
    s8 opacity;
    f32 parameter1;
    f32 parameter0;
    s16 zero;
    s16 lifetime;
    f32 height;
    f32 width;
    s16 variant;
    s16 type;
    f32 positionZ;
    f32 positionY;
    f32 positionX;
    s16 eventCode;
    s16 offset;
    s16 mode;
    s16 kind;

    variant = 5;
    kind = 0x6B;
    positionX = x;
    positionY = y;
    type = 6;
    mode = 0x46;
    offset = -0x1F;
    eventCode = 0x2E;
    lifetime = 100;
    zero = 0;
    opacity = 0x9B;
    scale = 100;
    velocity = 0.0f;
    active = 1;
    classId = 6;
    acceleration = 0.0f;
    loop = 1;
    phase = 0.0f;
    width = 30.0f;
    height = 35.0f;
    parameter0 = D_800A0274;
    parameter1 = D_800A0278;
    positionZ = z;
    parameter2 = D_800A027C;
    func_15150178(&kind, &positionX, 0, channel, 1);
    return 1;
}
"""

COMMON_SIX = BODY.replace(
    "    EffectBandLocals150C2700 locals;",
    "    EffectBandLocals150C2700 locals;\n    s32 six;",
    1,
).replace(
    "    locals.descriptor.kind = 0x6B;",
    "    six = 6;\n    locals.descriptor.kind = 0x6B;",
    1,
).replace(
    "locals.payload.type = locals.payload.classId = 6;",
    "locals.payload.type = six;",
    1,
).replace(
    "    locals.payload.active = 1;",
    "    locals.payload.active = 1;\n    locals.payload.classId = six;",
    1,
)

SELECTED = BODY.replace(
    "s32 func_150C2700(",
    "/* Submit the fixed effect-band descriptor and caller position packet. */\n"
    "s32 func_150C2700(",
    1,
)


def candidates():
    yield "class-chain", CLASS_CHAIN
    yield "type-chain", TYPE_CHAIN
    yield "type-reuse", TYPE_REUSE
    yield "class-reuse", CLASS_REUSE
    yield "scalar-m2c", SCALAR_M2C
    yield "common-six", COMMON_SIX
    yield "composite-struct-order", BODY
    yield "composite-payload-first", BODY.replace(
        "    locals.descriptor.kind = 0x6B;",
        "    locals.payload.x = x;\n"
        "    locals.payload.y = y;\n"
        "    locals.payload.z = z;\n"
        "    locals.descriptor.kind = 0x6B;",
        1,
    ).replace(
        "    locals.payload.x = x;\n"
        "    locals.payload.y = y;\n"
        "    locals.payload.z = z;\n",
        "",
        1,
    )
    yield "composite-scalars-first", BODY.replace(
        "    locals.payload.x = x;\n"
        "    locals.payload.y = y;\n"
        "    locals.payload.z = z;",
        "    locals.payload.type = 6;\n"
        "    locals.payload.variant = 5;\n"
        "    locals.payload.width = 31.0f;\n"
        "    locals.payload.height = 35.0f;\n"
        "    locals.payload.x = x;\n"
        "    locals.payload.y = y;\n"
        "    locals.payload.z = z;",
        1,
    ).replace(
        "    locals.payload.type = 6;\n"
        "    locals.payload.variant = 5;\n"
        "    locals.payload.width = 31.0f;\n"
        "    locals.payload.height = 35.0f;\n",
        "",
        1,
    )
    yield "separate-locals", BODY.replace(
        "    EffectBandLocals150C2700 locals;",
        "    EffectBandDescriptor150C2700 descriptor;\n"
        "    EffectBandPayload150C2700 payload;",
    ).replace("locals.descriptor", "descriptor").replace(
        "locals.payload", "payload"
    )
    yield "separate-payload-first", BODY.replace(
        "    EffectBandLocals150C2700 locals;",
        "    EffectBandPayload150C2700 payload;\n"
        "    EffectBandDescriptor150C2700 descriptor;",
    ).replace("locals.descriptor", "descriptor").replace(
        "locals.payload", "payload"
    )


ROOT = Path(__file__).resolve().parents[2]


def source_with(body):
    live = (ROOT / SOURCE).read_text()
    marker = "extern f32 D_800A026C;\n"
    declarations = DECLARATIONS + "\n"
    if live.count(PLACEHOLDER_BLOCK) == 1:
        if declarations in live or SELECTED in live or PROTOTYPE in live:
            raise ValueError("Effect-band callback predecessor source changed")
        if live.count(OLD_PROTOTYPE) != 1:
            raise ValueError("Effect-band callback predecessor prototype changed")
        return live.replace(OLD_PROTOTYPE, PROTOTYPE, 1).replace(
            marker, marker + declarations, 1
        ).replace(PLACEHOLDER_BLOCK, body, 1)
    if (live.count(SELECTED) == 1 and live.count(declarations) == 1 and
            live.count(PROTOTYPE) == 1):
        return live.replace(SELECTED, body, 1)
    raise ValueError("Effect-band callback source state changed")


def compare(name, body=SELECTED, flags=("-O2", "-g3")):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(
        ROOT, output, source_with(body), name, flags=flags
    )
    text, functions, relocations = parse_object(obj)
    info = functions[FUNCTION]
    start, size = info["value"], info["size"]
    object_bytes = text[start:start + size]
    bindings = {
        offset - start: rows for offset, rows in relocations.items()
        if start <= offset < start + size
    }
    linked, linked_functions = link_owner(ROOT, output, obj, OWNER)
    linked_info = linked_functions[FUNCTION]
    ours = linked[
        linked_info["value"]:linked_info["value"] + linked_info["size"]
    ]
    retail = (ROOT / "conker/conker.us.bin").read_bytes()[ROM:ROM + WORDS * 4]
    our_words = struct.unpack(">%dI" % (len(ours) // 4), ours)
    retail_words = struct.unpack(">%dI" % WORDS, retail)
    differences = [
        {"offset": index * 4, "ours": left, "retail": right}
        for index, (left, right) in enumerate(
            itertools.zip_longest(our_words, retail_words, fillvalue=0)
        ) if left != right
    ]
    frame = next(((-word) & 0xFFFF for word in our_words
                  if word & 0xFFFF0000 == 0x27BD0000 and word & 0x8000), 0)
    return {
        "name": name,
        "flags": flags,
        "words": len(our_words),
        "frame": frame,
        "differences": len(differences),
        "difference_rows": differences,
        "diagnostics": diagnostics,
        "object_raw_sha256": hashlib.sha256(object_bytes).hexdigest(),
        "bindings": {
            "0x%03X" % offset: rows for offset, rows in sorted(bindings.items())
        },
        "raw_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=[name for name, _ in candidates()])
    parser.add_argument("--profile", choices=PROFILES, default="o2g3")
    args = parser.parse_args()
    records = []
    for name, body in candidates():
        if args.candidate is not None and name != args.candidate:
            continue
        record = compare(name + "-" + args.profile, body, PROFILES[args.profile])
        records.append(record)
        print(name, record["words"], hex(record["frame"]),
              record["differences"], flush=True)
        for row in record["difference_rows"]:
            print("+0x%03X %08X %08X" % (
                row["offset"], row["ours"], row["retail"]
            ))
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
