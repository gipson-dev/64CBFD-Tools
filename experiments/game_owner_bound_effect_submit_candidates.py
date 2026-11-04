"""Screen semantic C shapes for the owner-bound effect submit callback."""

import hashlib
import itertools
import json
import struct
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.pad_generated_object import parse_object


ENTRY, ROM, WORDS = 0x1519E464, 0x1CB914, 67
FUNCTION = "func_1519E464"
SOURCE = "conker/src/game/generated_1CA420.c"
OWNER = "generated_1CA420"
BUILD = "conker/build/game-owner-bound-effect-submit-candidates"
ORIGINAL = "s32 func_1519E464() {\n    return 0;\n}"
PLACEHOLDER = ORIGINAL
TYPES = """typedef struct {
    u8 *owner;
    u8 identity;
    u8 reserved5[3];
    s32 preset;
} OwnerEffectPayload1519E464;

typedef struct {
    u8 reserved00;
    u8 context;
    u8 reserved02[10];
    u8 slot;
    u8 flags;
    s16 duration;
    u8 reserved10[24];
    OwnerEffectPayload1519E464 payload;
} OwnerEffectRecord1519E464;
"""
DECLARATIONS = """s32 func_1519D030();
s32 func_1514ED3C();
s32 func_1514EC1C();
"""
INSTALL_DECLARATIONS = """s32 func_1514ED3C();
s32 func_1514EC1C();
"""
SYMBOLS = {
    "func_1519D030": 0x1519D030,
    "func_1514ED3C": 0x1514ED3C,
    "func_1514EC1C": 0x1514EC1C,
}

RAW_U8 = """void func_1519E464(u8 *record) {
    u8 retire;
    u8 *payload;
    u8 *owner;
    u8 *effect;

    retire = 0;
    payload = record + 0x28;
    if (*(s32 *)*(u8 **)payload == 0) {
        retire = 1;
    }
    owner = *(u8 **)payload;
    if (payload[4] != owner[0x3B]) {
        retire = 1;
    }
    if (retire == 0 && *(u8 **)(owner + 0x1D4) != NULL) {
        retire = 1;
        effect = (u8 *)func_1519D030(owner, *(s32 *)(payload + 8),
            *(s16 *)(record + 0xE), record[0xD] & 1, record[0xC], record[1]);
        if (effect != NULL) {
            if (func_1514ED3C(*(u8 **)(*(u8 **)payload + 0x2F4), record, 0) != 0) {
                func_1514EC1C(effect, *(u8 **)payload, 0x10, effect);
            }
        }
    }
    if (retire != 0) {
        *(s16 *)(record + 0xE) = -1;
        record[0xD] |= 1;
    }
}
"""

FLAG_LOCAL = RAW_U8.replace(
    "    u8 *effect;", "    u8 *effect;\n    u8 maskedFlags;"
).replace(
    "        retire = 1;\n        effect =",
    "        maskedFlags = record[0xD];\n        retire = 1;\n        effect =",
).replace("record[0xD] & 1,", "maskedFlags & 1,")

FLAG_EFFECT_WORD = FLAG_LOCAL.replace(
    "    u8 *effect;", "    s32 effect;"
).replace(
    "effect = (u8 *)func_1519D030", "effect = func_1519D030"
).replace("effect != NULL", "effect != 0").replace(
    "func_1514EC1C(effect,", "func_1514EC1C((u8 *)effect,"
).replace(", 0x10, effect);", ", 0x10, (u8 *)effect);")

FLAG_SPLIT_RESULT = FLAG_LOCAL.replace(
    "    u8 *effect;", "    u8 *effect;\n    s32 result;"
).replace(
    "effect = (u8 *)func_1519D030", "result = func_1519D030"
).replace(
    "        if (effect != NULL) {",
    "        if (result != 0) {\n            effect = (u8 *)result;",
)

DONOR_CORRECTED = """void func_1519E464(u8 *record) {
    u8 savedRetire;
    u8 *savedEffect;
    u8 *savedPayload;
    u8 retire;
    u8 *owner;
    s32 result;
    u8 *payload;

    retire = 0;
    payload = record + 0x28;
    if (*(s32 *)*(u8 **)(record + 0x28) == 0) {
        retire = 1;
    }
    owner = *(u8 **)(record + 0x28);
    if (payload[4] != owner[0x3B]) {
        retire = 1;
    }
    if (retire == 0 && *(u8 **)(owner + 0x1D4) != NULL) {
        savedRetire = 1;
        savedPayload = payload;
        result = func_1519D030(owner, *(s32 *)(payload + 8),
            *(s16 *)(record + 0xE), record[0xD] & 1, record[0xC], record[1]);
        retire = 1;
        if (result != 0) {
            savedRetire = 1;
            savedEffect = (u8 *)result;
            savedPayload = payload;
            retire = 1;
            if (func_1514ED3C(*(u8 **)(*(u8 **)payload + 0x2F4), record, 0) != 0) {
                savedRetire = 1;
                func_1514EC1C(savedEffect, *(u8 **)payload, 0x10, savedEffect);
                retire = 1;
            }
        }
    }
    if (retire != 0) {
        *(s16 *)(record + 0xE) = -1;
        record[0xD] |= 1;
    }
}
"""

TYPED_U8 = """void func_1519E464(OwnerEffectRecord1519E464 *record) {
    u8 retire;
    OwnerEffectPayload1519E464 *payload;
    u8 *owner;
    u8 *effect;

    retire = 0;
    payload = &record->payload;
    if (*(s32 *)record->payload.owner == 0) {
        retire = 1;
    }
    owner = payload->owner;
    if (payload->identity != owner[0x3B]) {
        retire = 1;
    }
    if (retire == 0 && *(u8 **)(owner + 0x1D4) != NULL) {
        retire = 1;
        effect = (u8 *)func_1519D030(owner, payload->preset,
            record->duration, record->flags & 1, record->slot, record->context);
        if (effect != NULL) {
            if (func_1514ED3C(*(u8 **)(payload->owner + 0x2F4),
                    (u8 *)record, 0) != 0) {
                func_1514EC1C(effect, payload->owner, 0x10, effect);
            }
        }
    }
    if (retire != 0) {
        record->duration = -1;
        record->flags |= 1;
    }
}
"""

TYPED_FLAG_LOCAL = TYPED_U8.replace(
    "    u8 *effect;", "    u8 *effect;\n    u8 maskedFlags;"
).replace(
    "        retire = 1;\n        effect =",
    "        maskedFlags = record->flags;\n        retire = 1;\n        effect =",
).replace("record->flags & 1,", "maskedFlags & 1,")

SELECTED = TYPED_FLAG_LOCAL.replace(
    "void func_1519E464",
    "/* Submit one owner-bound effect, then retire this callback record. */\n"
    "void func_1519E464",
    1,
)
RETAIL_BINDINGS = {
    0x080: [("R_MIPS_26", "func_1519D030")],
    0x0AC: [("R_MIPS_26", "func_1514ED3C")],
    0x0D0: [("R_MIPS_26", "func_1514EC1C")],
}


def candidates():
    yield "raw-u8", RAW_U8
    yield "typed-u8", TYPED_U8
    yield "typed-u8-flag-local", TYPED_FLAG_LOCAL
    yield "raw-s32", RAW_U8.replace("    u8 retire;", "    s32 retire;")
    yield "typed-s32", TYPED_U8.replace("    u8 retire;", "    s32 retire;")
    yield "raw-u8-effect-word", RAW_U8.replace("    u8 *effect;", "    s32 effect;").replace(
        "effect = (u8 *)func_1519D030", "effect = func_1519D030").replace(
        "effect != NULL", "effect != 0").replace(
        "func_1514EC1C(effect,", "func_1514EC1C((u8 *)effect,").replace(
        ", 0x10, effect);", ", 0x10, (u8 *)effect);")
    yield "typed-u8-effect-word", TYPED_U8.replace("    u8 *effect;", "    s32 effect;").replace(
        "effect = (u8 *)func_1519D030", "effect = func_1519D030").replace(
        "effect != NULL", "effect != 0").replace(
        "func_1514EC1C(effect,", "func_1514EC1C((u8 *)effect,").replace(
        ", 0x10, effect);", ", 0x10, (u8 *)effect);")
    for flag_type in ("u8", "u32", "s32"):
        yield "raw-u8-%s-flag-local" % flag_type, RAW_U8.replace(
            "    u8 *effect;", "    u8 *effect;\n    %s maskedFlags;" % flag_type
        ).replace(
            "        retire = 1;\n        effect =",
            "        maskedFlags = record[0xD];\n        retire = 1;\n        effect =",
        ).replace("record[0xD] & 1,", "maskedFlags & 1,")
    for expression, name in (
        ("((u8)record[0xD]) & 1", "cast-u8"),
        ("((u32)record[0xD]) & 1", "cast-u32"),
        ("(record[0xD] & (u8)1)", "mask-u8"),
    ):
        yield "raw-u8-" + name, RAW_U8.replace("record[0xD] & 1", expression)
    yield "raw-u8-flag-effect-before-owner", FLAG_LOCAL.replace(
        "    u8 *payload;\n    u8 *owner;\n    u8 *effect;",
        "    u8 *payload;\n    u8 *effect;\n    u8 *owner;",
    )
    yield "raw-u8-flag-effect-first", FLAG_LOCAL.replace(
        "    u8 *payload;\n    u8 *owner;\n    u8 *effect;",
        "    u8 *effect;\n    u8 *payload;\n    u8 *owner;",
    )
    yield "raw-u8-flag-owner-first", FLAG_LOCAL.replace(
        "    u8 *payload;\n    u8 *owner;\n    u8 *effect;",
        "    u8 *owner;\n    u8 *payload;\n    u8 *effect;",
    )
    yield "raw-u8-flag-effect-word", FLAG_EFFECT_WORD
    yield "raw-u8-flag-split-result", FLAG_SPLIT_RESULT
    yield "donor-corrected-u8", DONOR_CORRECTED
    yield "donor-corrected-s32", DONOR_CORRECTED.replace(
        "    u8 retire;", "    s32 retire;"
    )
    yield "raw-u8-union-owner-effect", FLAG_LOCAL.replace(
        "    u8 *owner;\n    u8 *effect;",
        "    union { u8 *owner; u8 *effect; } temporary;",
    ).replace("owner =", "temporary.owner =").replace(
        "owner[", "temporary.owner["
    ).replace("(owner +", "(temporary.owner +").replace(
        "func_1519D030(owner,", "func_1519D030(temporary.owner,"
    ).replace("        effect =", "        temporary.effect =").replace(
        "if (effect !=", "if (temporary.effect !="
    ).replace("func_1514EC1C(effect,", "func_1514EC1C(temporary.effect,").replace(
        ", 0x10, effect);", ", 0x10, temporary.effect);"
    )
    yield "raw-u8-combined-success", RAW_U8.replace(
        "        if (effect != NULL) {\n            if (func_1514ED3C(*(u8 **)(*(u8 **)payload + 0x2F4), record, 0) != 0) {\n                func_1514EC1C(effect, *(u8 **)payload, 0x10, effect);\n            }\n        }",
        "        if (effect != NULL &&\n            func_1514ED3C(*(u8 **)(*(u8 **)payload + 0x2F4), record, 0) != 0) {\n            func_1514EC1C(effect, *(u8 **)payload, 0x10, effect);\n        }")


def compile_candidate(root, out, name, body=RAW_U8, profile="o2g3",
                      declarations=DECLARATIONS):
    with patch.multiple(
        compiler,
        ENTRY=ENTRY,
        ROM=ROM,
        WORDS=WORDS,
        FUNCTION=FUNCTION,
        RECORD=TYPES,
        DECLARATIONS=declarations,
        SYMBOLS=SYMBOLS,
    ):
        return compiler.compile_candidate(root, out, name, body, profile)


ROOT = Path(__file__).resolve().parents[2]


def source_with(body):
    live = (ROOT / SOURCE).read_text()
    marker = "#include <ultra64.h>\n"
    declarations = TYPES + INSTALL_DECLARATIONS + "\n"
    if live.count(PLACEHOLDER) == 1:
        if declarations in live or SELECTED in live:
            raise ValueError("Owner-bound effect submit predecessor source changed")
        return live.replace(marker, marker + declarations, 1).replace(
            PLACEHOLDER, body, 1
        )
    if live.count(SELECTED) == 1 and live.count(declarations) == 1:
        return live.replace(SELECTED, body, 1)
    raise ValueError("Owner-bound effect submit source state changed")


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
    retail_object = bytearray(retail)
    for offset, rows in RETAIL_BINDINGS.items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", retail_object, offset,
                         struct.unpack_from(">I", retail_object, offset)[0] & mask)
    object_padded = object_bytes.ljust(WORDS * 4, b"\0")[:WORDS * 4]
    object_words = struct.unpack(">%dI" % WORDS, object_padded)
    retail_object_words = struct.unpack(">%dI" % WORDS, retail_object)
    object_differences = [
        {
            "offset": index * 4,
            "expected": left,
            "replacement": right,
            "expected_relocations": bindings.get(index * 4, []),
            "replacement_relocations": RETAIL_BINDINGS.get(index * 4, []),
        }
        for index, (left, right) in enumerate(
            zip(object_words, retail_object_words)
        )
        if (left != right or
            bindings.get(index * 4, []) != RETAIL_BINDINGS.get(index * 4, []))
    ]
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
        "object_differences": object_differences,
        "diagnostics": diagnostics,
        "object_raw_sha256": hashlib.sha256(object_bytes).hexdigest(),
        "bindings": {
            "0x%03X" % offset: rows for offset, rows in sorted(bindings.items())
        },
        "raw_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
    }


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / "conker/build/game-owner-bound-effect-submit"
    retail = struct.unpack_from(
        ">%dI" % WORDS, (root / "conker/conker.us.bin").read_bytes(), ROM
    )
    records = []
    best = None
    for name, body in candidates():
        meta, words = compile_candidate(root, out, name, body)
        records.append(meta)
        score = (meta["differences"], abs(meta["body_words"] - WORDS))
        if best is None or score < best[0]:
            best = (score, name, words)
        print(name, meta["body_words"], hex(meta["frame"]), meta["differences"], flush=True)
    prototype_variants = {
        "typed-u8-args": """s32 func_1519D030(u8 *, s32, s16, u8, u8, u8);
s32 func_1514ED3C(u8 *, u8 *, s32);
void func_1514EC1C(u8 *, u8 *, s32, u8 *);
""",
        "typed-word-tail": """s32 func_1519D030(u8 *, s32, s16, u8, u32, u32);
s32 func_1514ED3C(u8 *, u8 *, s32);
void func_1514EC1C(u8 *, u8 *, s32, u8 *);
""",
        "pointer-result": """u8 *func_1519D030(u8 *, s32, s16, u8, u32, u32);
s32 func_1514ED3C(u8 *, u8 *, s32);
void func_1514EC1C(u8 *, u8 *, s32, u8 *);
""",
    }
    for suffix, declarations in prototype_variants.items():
        name = "raw-u8-flag-" + suffix
        meta, words = compile_candidate(root, out, name, FLAG_LOCAL,
                                        declarations=declarations)
        records.append(meta)
        score = (meta["differences"], abs(meta["body_words"] - WORDS))
        if best is None or score < best[0]:
            best = (score, name, words)
        print(name, meta["body_words"], hex(meta["frame"]), meta["differences"], flush=True)
    (out / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
    if best is not None:
        _, name, words = best
        print("best", name)
        for index, (actual, expected) in enumerate(
            itertools.zip_longest(words, retail, fillvalue=0)
        ):
            if actual != expected:
                print("%02d +0x%03X %08X %08X" % (index, index * 4, actual, expected))


if __name__ == "__main__":
    main()
