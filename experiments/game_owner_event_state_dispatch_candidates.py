"""Screen semantic C shapes for the owner event-state dispatcher."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.experiments.game_actor_classifier_candidates import PROFILES
from tools.pad_generated_object import parse_object


ENTRY, ROM, WORDS = 0x151C86AC, 0x1F5B5C, 64
FUNCTION = "func_151C86AC"
SOURCE = "conker/src/game/generated_1F4650.c"
OWNER = "generated_1F4650"
BUILD = "conker/build/game-owner-event-state-dispatch-candidates"
PLACEHOLDER = "s32 func_151C86AC() {\n    return 0;\n}"
RETAIL_BINDINGS = {
    0x068: [("R_MIPS_26", "func_151C87E0")],
    0x07C: [("R_MIPS_26", "func_151C899C")],
    0x0E8: [("R_MIPS_26", "func_151C899C")],
}
DECLARATIONS = """s32 func_151C87E0();
s32 func_151C899C();
"""

DONOR_CORRECTED = """void func_151C86AC(u8 *owner, u8 *event, s32 eventCode) {
    s32 code;
    u8 selector;
    u8 *state;

    code = eventCode & 0xFF;
    switch (code) {
    case 0x20:
        state = owner + 0x110;
        if ((state[0x86] & 0x10) &&
                *(s32 *)(state + 0x28) == *(s32 *)(event + 4) &&
                func_151C87E0(*(s32 *)event, owner, code, event) != 0) {
            func_151C899C(*(s32 *)event, owner);
            return;
        }
        return;
    case 0x3A:
        state = owner + 0x110;
        if (*(s32 *)(owner + 0x138) == *(s32 *)event) {
            selector = event[4];
            switch (selector) {
            case 0:
                state[0x86] |= 2;
                return;
            case 1:
                state[0x86] &= 0xFD;
                return;
            case 2:
                func_151C899C(NULL, owner, code, event);
                break;
            }
        }
        break;
    }
}
"""

M2C_SHAPE = """void func_151C86AC(void *owner, void *event, s32 eventCode) {
    s32 code;
    u8 selector;
    u8 *state20;
    u8 *state3A;

    code = eventCode & 0xFF;
    switch (code) {
    case 0x20:
        state20 = (u8 *)owner + 0x110;
        if ((state20[0x86] & 0x10) &&
                *(s32 *)(state20 + 0x28) == *(s32 *)((u8 *)event + 4) &&
                func_151C87E0(*(s32 *)event, owner, code, event) != 0) {
            func_151C899C(*(s32 *)event, owner);
            return;
        }
        return;
    case 0x3A:
        state3A = (u8 *)owner + 0x110;
        if (*(s32 *)((u8 *)owner + 0x138) == *(s32 *)event) {
            selector = *((u8 *)event + 4);
            switch (selector) {
            case 0:
                state3A[0x86] |= 2;
                return;
            case 1:
                state3A[0x86] &= 0xFD;
                return;
            case 2:
                func_151C899C(NULL, owner, code, event);
                break;
            }
        }
        break;
    }
}
"""

ADDRESS_HOME = """void func_151C86AC(u8 *owner, u8 *event, s32 eventCode) {
    u8 **ownerHome;
    s32 code;
    u8 selector;
    u8 *state;

    ownerHome = &owner;
    code = eventCode & 0xFF;
    switch (code) {
    case 0x20:
        state = *ownerHome + 0x110;
        if ((state[0x86] & 0x10) &&
                *(s32 *)(state + 0x28) == *(s32 *)(event + 4) &&
                func_151C87E0(*(s32 *)event, *ownerHome, code, event) != 0) {
            func_151C899C(*(s32 *)event, *ownerHome);
            return;
        }
        return;
    case 0x3A:
        state = *ownerHome + 0x110;
        if (*(s32 *)(*ownerHome + 0x138) == *(s32 *)event) {
            selector = event[4];
            switch (selector) {
            case 0:
                state[0x86] |= 2;
                return;
            case 1:
                state[0x86] &= 0xFD;
                return;
            case 2:
                func_151C899C(NULL, *ownerHome, code, event);
                break;
            }
        }
        break;
    }
}
"""

ADDRESS_HOME_NARROW = ADDRESS_HOME.replace(
    "    s32 code;\n", ""
).replace(
    "    code = eventCode & 0xFF;\n    switch (code)",
    "    eventCode &= 0xFF;\n    switch (eventCode)",
).replace(
    "*ownerHome, code, event", "*ownerHome, eventCode, event"
)

ADDRESS_HOME_BYTE = ADDRESS_HOME.replace(
    "    s32 code;", "    u8 code;"
).replace(
    "code = eventCode & 0xFF", "code = eventCode"
)

ADDRESS_HOME_U8_ARG = ADDRESS_HOME_NARROW.replace(
    "s32 eventCode", "u8 eventCode"
).replace(
    "    eventCode &= 0xFF;\n", ""
)

ADDRESS_HOME_U8_KNR = ADDRESS_HOME_U8_ARG.replace(
    "void func_151C86AC(u8 *owner, u8 *event, u8 eventCode) {",
    "void func_151C86AC(owner, event, eventCode)\n"
    "u8 *owner;\n"
    "u8 *event;\n"
    "u8 eventCode;\n"
    "{",
)

ADDRESS_HOME_U8_TWO_ARGS = ADDRESS_HOME_U8_ARG.replace(
    "func_151C87E0(*(s32 *)event, *ownerHome, eventCode, event)",
    "func_151C87E0(*(s32 *)event, *ownerHome)",
).replace(
    "func_151C899C(NULL, *ownerHome, eventCode, event);",
    "func_151C899C(NULL, *ownerHome);",
)

ADDRESS_HOME_U8_TWO_ARGS_KNR = ADDRESS_HOME_U8_TWO_ARGS.replace(
    "void func_151C86AC(u8 *owner, u8 *event, u8 eventCode) {",
    "void func_151C86AC(owner, event, eventCode)\n"
    "u8 *owner;\n"
    "u8 *event;\n"
    "u8 eventCode;\n"
    "{",
)

ADDRESS_HOME_U8_STATE_BASE = ADDRESS_HOME_U8_TWO_ARGS.replace(
    "        state = *ownerHome + 0x110;\n"
    "        if (*(s32 *)(*ownerHome + 0x138) == *(s32 *)event) {\n"
    "            selector = event[4];",
    "        state = *ownerHome;\n"
    "        if (*(s32 *)(state + 0x138) == *(s32 *)event) {\n"
    "            state += 0x110;\n"
    "            selector = event[4];",
    1,
)

ADDRESS_HOME_U8_STATE_FIELD = ADDRESS_HOME_U8_TWO_ARGS.replace(
    "        if (*(s32 *)(*ownerHome + 0x138) == *(s32 *)event) {",
    "        if (*(s32 *)(state + 0x28) == *(s32 *)event) {",
    1,
).replace(
    "state[0x86] &= 0xFD;", "state[0x86] &= 0xFFFD;"
)

SELECTED = ADDRESS_HOME_U8_STATE_FIELD.replace(
    "void func_151C86AC",
    "/* Apply owner state events and forward matching action requests. */\n"
    "void func_151C86AC",
    1,
)


def candidates():
    yield "address-home-u8-state-field", ADDRESS_HOME_U8_STATE_FIELD
    yield "address-home-u8-state-base", ADDRESS_HOME_U8_STATE_BASE
    yield "address-home-u8-two-args", ADDRESS_HOME_U8_TWO_ARGS
    yield "address-home-u8-two-args-knr", ADDRESS_HOME_U8_TWO_ARGS_KNR
    yield "address-home-u8-arg", ADDRESS_HOME_U8_ARG
    yield "address-home-u8-knr", ADDRESS_HOME_U8_KNR
    yield "address-home-narrow", ADDRESS_HOME_NARROW
    yield "address-home-byte", ADDRESS_HOME_BYTE
    yield "address-home", ADDRESS_HOME
    yield "address-home-m2c", ADDRESS_HOME.replace(
        "    u8 selector;", "    u8 selector;\n    u8 *state20;\n    u8 *state3A;"
    ).replace(
        "    u8 *state;\n", ""
    ).replace(
        "        state = *ownerHome + 0x110;", "        state20 = *ownerHome + 0x110;", 1
    ).replace(
        "state[0x86]", "state20[0x86]", 1
    ).replace(
        "state + 0x28", "state20 + 0x28", 1
    ).replace(
        "        state = *ownerHome + 0x110;", "        state3A = *ownerHome + 0x110;", 1
    ).replace(
        "state[0x86]", "state3A[0x86]"
    )
    yield "m2c-shape-knr", M2C_SHAPE.replace(
        "void func_151C86AC(void *owner, void *event, s32 eventCode) {",
        "void func_151C86AC(owner, event, eventCode)\n"
        "void *owner;\nvoid *event;\ns32 eventCode;\n{",
    )
    yield "donor-knr", DONOR_CORRECTED.replace(
        "void func_151C86AC(u8 *owner, u8 *event, s32 eventCode) {",
        "void func_151C86AC(owner, event, eventCode)\n"
        "u8 *owner;\nu8 *event;\ns32 eventCode;\n{",
    )
    yield "m2c-shape-volatile-owner", M2C_SHAPE.replace(
        "void func_151C86AC(void *owner, void *event, s32 eventCode)",
        "void func_151C86AC(void * volatile owner, void *event, s32 eventCode)",
    )
    yield "donor-volatile-owner", DONOR_CORRECTED.replace(
        "void func_151C86AC(u8 *owner, u8 *event, s32 eventCode)",
        "void func_151C86AC(u8 * volatile owner, u8 *event, s32 eventCode)",
    )
    yield "m2c-shape", M2C_SHAPE
    yield "m2c-shape-byte-code", M2C_SHAPE.replace(
        "    s32 code;", "    u8 code;"
    ).replace("code = eventCode & 0xFF", "code = eventCode")
    yield "m2c-shape-typed-args", M2C_SHAPE.replace(
        "void func_151C86AC(void *owner, void *event, s32 eventCode)",
        "void func_151C86AC(u8 *owner, u8 *event, s32 eventCode)",
    ).replace("(u8 *)owner", "owner").replace("(u8 *)event", "event")
    yield "donor-corrected", DONOR_CORRECTED
    yield "narrow-in-place", DONOR_CORRECTED.replace(
        "    s32 code;\n", ""
    ).replace(
        "    code = eventCode & 0xFF;\n    switch (code)",
        "    eventCode &= 0xFF;\n    switch (eventCode)",
    ).replace(
        "owner, code, event", "owner, eventCode, event"
    )
    yield "unsigned-code", DONOR_CORRECTED.replace("    s32 code;", "    u32 code;")
    yield "byte-code", DONOR_CORRECTED.replace("    s32 code;", "    u8 code;").replace(
        "code = eventCode & 0xFF", "code = eventCode"
    )
    yield "direct-selector", DONOR_CORRECTED.replace(
        "    u8 selector;\n", ""
    ).replace(
        "            selector = event[4];\n            switch (selector)",
        "            switch (event[4])",
    )


ROOT = Path(__file__).resolve().parents[2]


def source_with(body):
    live = (ROOT / SOURCE).read_text()
    marker = "#include <ultra64.h>\n"
    if live.count(PLACEHOLDER) == 1:
        if SELECTED in live or DECLARATIONS in live:
            raise ValueError("Owner event-state dispatcher predecessor source changed")
        return live.replace(marker, marker + DECLARATIONS, 1).replace(
            PLACEHOLDER, body, 1
        )
    if live.count(SELECTED) == 1 and live.count(DECLARATIONS) == 1:
        return live.replace(SELECTED, body, 1)
    raise ValueError("Owner event-state dispatcher source state changed")


def compare(name, body=SELECTED, flags=("-O2", "-g3")):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(
        ROOT, output, source_with(body), name, flags=flags
    )
    text_bytes, functions, relocations = parse_object(obj)
    info = functions[FUNCTION]
    start, size = info["value"], info["size"]
    object_bytes = text_bytes[start:start + size]
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
        if record["differences"]:
            for row in record["difference_rows"]:
                print("+0x%03X %08X %08X" % (
                    row["offset"], row["ours"], row["retail"]
                ))
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
