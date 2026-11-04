"""Screen semantic C shapes for the actor-position effect factory."""

import argparse
import hashlib
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ENTRY, ROM, WORDS = 0x151B6320, 0x1E37D0, 64
FUNCTION = "func_151B6320"
SOURCE = "conker/src/game/generated_1E37D0.c"
OWNER = "generated_1E37D0"
BUILD = "conker/build/game-actor-position-effect-factory-candidates"
ORIGINAL = "s32 func_151B6320() {\n    return 0;\n}"
PLACEHOLDER = ORIGINAL
TYPES = """typedef struct {
    f32 x;
    f32 y;
    f32 z;
} ActorPosition151B6320;

typedef struct {
    ActorPosition151B6320 position;
    s16 duration;
    u16 flags;
    s32 kind;
    u8 reserved14; /* Preserved stack byte copied by the retail helper. */
    u8 count;
    u8 reserved16[2]; /* Preserved stack bytes copied by the retail helper. */
} ActorEffectRequest151B6320;

typedef struct {
    u8 *owner;
    u8 identity;
    u8 reserved05[3];
    ActorPosition151B6320 position;
    f32 velocityX;
    f32 velocityY;
    f32 lowerBound;
    f32 upperBound;
    f32 velocityZ;
    u32 reserved28; /* Retail copies this untouched stack word. */
} ActorEffectPayload151B6320;

typedef struct {
    ActorEffectPayload151B6320 payload;
    u32 layoutGap; /* Original local spacing; not part of either packet. */
    ActorEffectRequest151B6320 request;
    u32 layoutTail; /* Preserves the original 0x90-byte frame. */
} ActorEffectLocals151B6320;

u8 *func_15147A80(void *, s32, s32, s32, s32, s32, s32, s32,
    void *, u8, s32);
void *memcpy(void *, const void *, unsigned int);
"""
DECLARATIONS = TYPES
RETAIL_BINDINGS = {
    0x0D0: [("R_MIPS_26", "func_15147A80")],
    0x0E4: [("R_MIPS_26", "memcpy")],
}
PADDED_TYPES = TYPES.replace(
    "    u32 reserved28;\n} ActorEffectPayload151B6320;",
    "    u32 reserved28;\n"
    "    u32 layoutPad2C;\n"
    "} ActorEffectPayload151B6320;",
)
REQUEST_PADDED_TYPES = TYPES.replace(
    "    u8 reserved16[2];\n} ActorEffectRequest151B6320;",
    "    u8 reserved16[2];\n"
    "    u32 layoutPad18;\n"
    "} ActorEffectRequest151B6320;",
)
SYMBOLS = {"func_15147A80": 0x15147A80, "memcpy": 0x10022EC0}

BASE = """void func_151B6320(u8 *actor, s32 channel, s32 context) {
    ActorEffectRequest151B6320 request;
    ActorEffectPayload151B6320 payload;
    u8 *record;

    request.count = 10;
    request.position.x = *(f32 *)(actor + 0x14);
    request.position.y = *(f32 *)(actor + 0x18);
    request.duration = 300;
    request.flags = 6;
    payload.owner = actor;
    request.position.z = *(f32 *)(actor + 0x1C);
    payload.identity = actor[0x3B];
    payload.position = request.position;
    payload.velocityX = 0.0f;
    payload.velocityY = 0.0f;
    payload.lowerBound = -16384.0f;
    payload.upperBound = -16384.0f;
    payload.velocityZ = 0.0f;
    request.kind = 13;
    record = func_15147A80(&request, 0x30, 0x1C, 0xB, 0xB, 0xB,
        0, 0, NULL, (u8)channel, context);
    if (record != NULL) {
        memcpy(*(void **)(record + 0x98), &payload, sizeof(payload));
    }
}
"""
COMPOSITE_BASE = (
    BASE.replace(
        "void func_151B6320(u8 *actor, s32 channel, s32 context)",
        "void func_151B6320(u8 *actor, u8 channel, s32 context)",
    )
    .replace(
        "    ActorEffectRequest151B6320 request;\n"
        "    ActorEffectPayload151B6320 payload;",
        "    ActorEffectLocals151B6320 locals;",
    )
    .replace("request.", "locals.request.")
    .replace("payload.", "locals.payload.")
    .replace("&request", "&locals.request")
    .replace("&payload", "&locals.payload")
    .replace("sizeof(payload)", "0x2C")
    .replace("(u8)channel", "channel")
)


def composite_schedule(block, reverse_bounds=True):
    body = COMPOSITE_BASE.replace(
        "    locals.request.count = 10;\n"
        "    locals.request.position.x = *(f32 *)(actor + 0x14);\n"
        "    locals.request.position.y = *(f32 *)(actor + 0x18);\n"
        "    locals.request.duration = 300;\n"
        "    locals.request.flags = 6;\n"
        "    locals.payload.owner = actor;\n"
        "    locals.request.position.z = *(f32 *)(actor + 0x1C);\n"
        "    locals.payload.identity = actor[0x3B];\n"
        "    locals.payload.position = locals.request.position;",
        block,
    )
    if reverse_bounds:
        body = body.replace(
            "    locals.payload.lowerBound = -16384.0f;\n"
            "    locals.payload.upperBound = -16384.0f;",
            "    locals.payload.upperBound = -16384.0f;\n"
            "    locals.payload.lowerBound = -16384.0f;",
        )
    return body


SELECTED_BLOCK = (
    "    locals.request.count = 10;\n"
    "    locals.request.position.x = *(f32 *)(actor + 0x14);\n"
    "    locals.request.position.y = *(f32 *)(actor + 0x18);\n"
    "    locals.request.position.z = *(f32 *)(actor + 0x1C);\n"
    "    locals.request.duration = 300;\n"
    "    locals.request.flags = 6;\n"
    "    locals.payload.owner = actor;\n"
    "    locals.payload.identity = actor[0x3B];\n"
    "    locals.payload.position = locals.request.position;"
)
SELECTED = composite_schedule(SELECTED_BLOCK).replace(
    "void func_151B6320",
    "/* Snapshot one actor position and submit its retail effect packet. */\n"
    "void func_151B6320",
    1,
)


def candidates():
    yield "typed-components", BASE
    yield "typed-components-literal-copy", BASE.replace(
        "sizeof(payload)", "0x2C"
    )
    yield "typed-components-unsigned-channel", BASE.replace(
        "u8 *actor, s32 channel, s32 context",
        "u8 *actor, u8 channel, s32 context",
    ).replace("(u8)channel", "channel")
    yield "typed-components-no-channel-cast", BASE.replace(
        "(u8)channel", "channel"
    )
    yield "payload-first", BASE.replace(
        "    ActorEffectRequest151B6320 request;\n"
        "    ActorEffectPayload151B6320 payload;",
        "    ActorEffectPayload151B6320 payload;\n"
        "    ActorEffectRequest151B6320 request;",
    )
    yield "record-first", BASE.replace(
        "    u8 *record;\n", ""
    ).replace(
        "    ActorEffectRequest151B6320 request;",
        "    u8 *record;\n    ActorEffectRequest151B6320 request;",
        1,
    )
    yield "record-between", BASE.replace(
        "    ActorEffectPayload151B6320 payload;\n    u8 *record;",
        "    u8 *record;\n    ActorEffectPayload151B6320 payload;",
    )
    yield "request-struct-copy", BASE.replace(
        "    request.position.x = *(f32 *)(actor + 0x14);\n"
        "    request.position.y = *(f32 *)(actor + 0x18);\n"
        "    request.duration = 300;\n"
        "    request.flags = 6;\n"
        "    payload.owner = actor;\n"
        "    request.position.z = *(f32 *)(actor + 0x1C);",
        "    request.position = *(ActorPosition151B6320 *)(actor + 0x14);\n"
        "    request.duration = 300;\n"
        "    request.flags = 6;\n"
        "    payload.owner = actor;",
    )
    yield "payload-position-components", BASE.replace(
        "    payload.position = request.position;",
        "    payload.position.x = request.position.x;\n"
        "    payload.position.y = request.position.y;\n"
        "    payload.position.z = request.position.z;",
    )
    yield "direct-payload-position", BASE.replace(
        "    payload.position = request.position;",
        "    payload.position = *(ActorPosition151B6320 *)(actor + 0x14);",
    )
    yield "chained-zero", BASE.replace(
        "    payload.velocityX = 0.0f;\n"
        "    payload.velocityY = 0.0f;",
        "    payload.velocityX = payload.velocityY = 0.0f;",
    ).replace(
        "    payload.velocityZ = 0.0f;",
        "    payload.velocityZ = 0.0f;",
    )
    yield "bounds-before-zero", BASE.replace(
        "    payload.velocityX = 0.0f;\n"
        "    payload.velocityY = 0.0f;\n"
        "    payload.lowerBound = -16384.0f;\n"
        "    payload.upperBound = -16384.0f;\n"
        "    payload.velocityZ = 0.0f;",
        "    payload.lowerBound = -16384.0f;\n"
        "    payload.upperBound = -16384.0f;\n"
        "    payload.velocityX = 0.0f;\n"
        "    payload.velocityY = 0.0f;\n"
        "    payload.velocityZ = 0.0f;",
    )
    yield "request-kind-earlier", BASE.replace(
        "    request.kind = 13;\n", ""
    ).replace(
        "    payload.identity = actor[0x3B];",
        "    payload.identity = actor[0x3B];\n    request.kind = 13;",
    )
    yield "payload-owner-first", BASE.replace(
        "    request.count = 10;",
        "    payload.owner = actor;\n    request.count = 10;",
    ).replace("    payload.owner = actor;\n", "", 1)
    yield "padded-components", BASE.replace("sizeof(payload)", "0x2C")
    yield "padded-components-unsigned-channel", BASE.replace(
        "u8 *actor, s32 channel, s32 context",
        "u8 *actor, u8 channel, s32 context",
    ).replace("(u8)channel", "channel").replace("sizeof(payload)", "0x2C")
    yield "padded-bounds-before-zero", BASE.replace(
        "    payload.velocityX = 0.0f;\n"
        "    payload.velocityY = 0.0f;\n"
        "    payload.lowerBound = -16384.0f;\n"
        "    payload.upperBound = -16384.0f;\n"
        "    payload.velocityZ = 0.0f;",
        "    payload.lowerBound = -16384.0f;\n"
        "    payload.upperBound = -16384.0f;\n"
        "    payload.velocityX = 0.0f;\n"
        "    payload.velocityY = 0.0f;\n"
        "    payload.velocityZ = 0.0f;",
    ).replace("sizeof(payload)", "0x2C")
    yield "request-padded-components", BASE
    yield "request-padded-components-unsigned-channel", BASE.replace(
        "u8 *actor, s32 channel, s32 context",
        "u8 *actor, u8 channel, s32 context",
    ).replace("(u8)channel", "channel")
    yield "composite-components-unsigned-channel", COMPOSITE_BASE
    yield "composite-reverse-bounds", composite_schedule(
        "    locals.request.count = 10;\n"
        "    locals.request.position.x = *(f32 *)(actor + 0x14);\n"
        "    locals.request.position.y = *(f32 *)(actor + 0x18);\n"
        "    locals.request.duration = 300;\n"
        "    locals.request.flags = 6;\n"
        "    locals.payload.owner = actor;\n"
        "    locals.request.position.z = *(f32 *)(actor + 0x1C);\n"
        "    locals.payload.identity = actor[0x3B];\n"
        "    locals.payload.position = locals.request.position;"
    )
    yield "composite-z-before-scalars", composite_schedule(
        SELECTED_BLOCK
    )
    yield "composite-kind-before-z", composite_schedule(
        "    locals.request.count = 10;\n"
        "    locals.request.position.x = *(f32 *)(actor + 0x14);\n"
        "    locals.request.position.y = *(f32 *)(actor + 0x18);\n"
        "    locals.request.kind = 13;\n"
        "    locals.request.position.z = *(f32 *)(actor + 0x1C);\n"
        "    locals.request.duration = 300;\n"
        "    locals.request.flags = 6;\n"
        "    locals.payload.owner = actor;\n"
        "    locals.payload.identity = actor[0x3B];\n"
        "    locals.payload.position = locals.request.position;"
    ).replace("    locals.request.kind = 13;\n    record =", "    record =")


def compile_candidate(root, out, name, body=BASE, profile="o2g3"):
    out.mkdir(parents=True, exist_ok=True)
    source, obj, elf = (out / (name + suffix) for suffix in (".c", ".o", ".elf"))
    declarations = (
        PADDED_TYPES
        if name.startswith("padded-")
        else REQUEST_PADDED_TYPES
        if name.startswith("request-padded-")
        else TYPES
    )
    source.write_text("#include <ultra64.h>\n" + declarations + "\n" + body)
    result = subprocess.run(
        [
            "ido/ido5.3_recomp/cc",
            "-c",
            "-32",
            "-G",
            "0",
            "-Xfullwarn",
            "-Xcpluscomm",
            "-signed",
            "-nostdinc",
            "-non_shared",
            "-Wab,-r4300_mul",
            "-mips2",
            "-o32",
            "-I",
            "conker/include",
            "-I",
            "conker/include/2.0L",
            "-I",
            "conker/include/2.0L/PR",
            "-I",
            "conker/include/libc",
            "-D_LANGUAGE_C",
            "-D_FINALROM",
            "-DF3DEX_GBI_2",
            "-D_MIPS_SZLONG=32",
            *PROFILES[profile],
            "-o",
            str(obj.relative_to(root)),
            str(source.relative_to(root)),
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    script = out / "actor-position-effect-factory.ld"
    script.write_text(
        "SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n" % ENTRY
    )
    subprocess.run(
        [
            "mips-linux-gnu-ld",
            "-m",
            "elf32btsmip",
            "-T",
            str(script),
            "-e",
            FUNCTION,
            *["--defsym=%s=0x%X" % item for item in SYMBOLS.items()],
            "-o",
            str(elf),
            str(obj),
        ],
        check=True,
        capture_output=True,
    )
    _, functions, relocations = parse_object(obj)
    meta, pools = functions[FUNCTION], sections(elf)
    words = list(
        struct.unpack_from(
            ">%dI" % (meta["size"] // 4), pools[".text"][1], meta["value"]
        )
    )
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    assert not any(words[end:])
    words = words[:end]
    retail = struct.unpack_from(
        ">%dI" % WORDS, (root / "conker/conker.us.bin").read_bytes(), ROM
    )
    frames = [
        (-word) & 0xFFFF
        for word in words
        if word & 0xFFFF0000 == 0x27BD0000 and word & 0x8000
    ]
    return (
        {
            "name": name,
            "profile": profile,
            "body_words": end,
            "frame": frames[0] if frames else 0,
            "differences": sum(
                a != b for a, b in itertools.zip_longest(words, retail, fillvalue=0)
            ),
            "relocations": relocations,
            "pool_bytes": sum(
                len(value[1])
                for section, value in pools.items()
                if section in (".rodata", ".data")
            ),
        },
        words,
    )


ROOT = Path(__file__).resolve().parents[2]


def source_with(body):
    live = (ROOT / SOURCE).read_text()
    marker = "#include <ultra64.h>\n"
    declarations = DECLARATIONS + "\n"
    if live.count(PLACEHOLDER) == 1:
        if declarations in live or SELECTED in live:
            raise ValueError("Actor-position effect factory predecessor source changed")
        return live.replace(marker, marker + declarations, 1).replace(
            PLACEHOLDER, body, 1
        )
    if live.count(SELECTED) == 1 and live.count(declarations) == 1:
        return live.replace(SELECTED, body, 1)
    raise ValueError("Actor-position effect factory source state changed")


def compare(name, body=SELECTED, flags=("-O2", "-g3")):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(
        ROOT, output, source_with(body), name, flags=flags
    )
    text_bytes, object_functions, relocations = parse_object(obj)
    info = object_functions[FUNCTION]
    start = info["value"]
    object_bytes = text_bytes[start:start + info["size"]]
    bindings = {
        offset - start: rows
        for offset, rows in relocations.items()
        if start <= offset < start + info["size"]
    }
    linked, functions = link_owner(ROOT, output, obj, OWNER)
    linked_info = functions[FUNCTION]
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
        )
        if left != right
    ]
    frame = 0
    if our_words and our_words[0] >> 16 == 0x27BD:
        frame = (-our_words[0]) & 0xFFFF
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--profiles", action="store_true")
    mode.add_argument("--candidate", choices=[name for name, _ in candidates()])
    mode.add_argument("--owner", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.owner:
        print(json.dumps(compare("selected-owner"), indent=2, default=str))
        return
    out = root / "conker/build/game-actor-position-effect-factory-candidates"
    forms = (
        [("profile-" + profile, BASE, profile) for profile in PROFILES]
        if args.profiles
        else [
            (name, body, "o2g3")
            for name, body in candidates()
            if args.candidate is None or name == args.candidate
        ]
    )
    records = []
    for name, body, profile in forms:
        record, _ = compile_candidate(root, out, name, body, profile)
        records.append(record)
        print(
            name,
            record["body_words"],
            hex(record["frame"]),
            record["differences"],
            flush=True,
        )
    filename = "profiles.json" if args.profiles else "measurements.json"
    (out / filename).write_text(json.dumps(records, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
