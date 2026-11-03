"""Screen semantic C forms for dual-identity event handler func_151B5A9C."""

import itertools
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler


ENTRY, ROM, WORDS = 0x151B5A9C, 0x1E2F4C, 64
FUNCTION = "func_151B5A9C"
SYMBOLS = {"func_1516972C": 0x1516972C}
RECORD = """typedef struct {
    u8 pad0[0x580];
    s32 key0;
    u8 tag0;
    u8 pad5AD[3];
    s32 key1;
    u8 tag1;
} DualIdentityState151B5A9C;
typedef struct {
    u8 pad0[0x28];
    DualIdentityState151B5A9C identity;
} DualIdentity151B5A9C;
typedef struct {
    s32 key0;
    s32 key1;
    u8 tag0;
    u8 tag1;
} IdentityEvent151B5A9C;
"""
DECLARATIONS = """void func_1516972C(DualIdentity151B5A9C *);
"""

SELECTED = """void func_151B5A9C(DualIdentity151B5A9C *owner,
                       IdentityEvent151B5A9C *event, u8 command) {
    DualIdentityState151B5A9C *state = &owner->identity;

    if (command == 0x2D) {
        if (event->key0 == state->key0) {
            state->key0 = event->key1;
            state->tag0 = event->tag1;
        } else if (event->key1 == state->key0) {
            state->key0 = event->key0;
            state->tag0 = event->tag0;
        }
        if (event->key0 == state->key1) {
            state->key1 = event->key1;
            state->tag1 = event->tag1;
        } else if (event->key1 == state->key1) {
            state->key1 = event->key0;
            state->tag1 = event->tag0;
        }
    } else if (command == 0 &&
               (event->key0 == state->key0 ||
                event->key0 == state->key1 ||
                ((u8 *)event)[4] == state->tag0 ||
                ((u8 *)event)[4] == state->tag1)) {
        func_1516972C(owner);
    }
}"""


def candidates():
    yield "selected", SELECTED
    state_first = SELECTED
    for left, right in (
            ("event->key0 == state->key0", "state->key0 == event->key0"),
            ("event->key1 == state->key0", "state->key0 == event->key1"),
            ("event->key0 == state->key1", "state->key1 == event->key0"),
            ("event->key1 == state->key1", "state->key1 == event->key1")):
        state_first = state_first.replace(left, right)
    yield "state-first-comparisons", state_first
    state_first_key = state_first.replace(
        "    DualIdentityState151B5A9C *state = &owner->identity;",
        "    DualIdentityState151B5A9C *state = &owner->identity;\n    s32 key;")
    state_first_key = state_first_key.replace(
        "    } else if (command == 0 &&\n"
        "               (state->key0 == event->key0 ||\n"
        "                state->key1 == event->key0 ||\n"
        "                ((u8 *)event)[4] == state->tag0 ||\n"
        "                ((u8 *)event)[4] == state->tag1)) {\n"
        "        func_1516972C(owner);\n"
        "    }",
        "    } else if (command == 0) {\n"
        "        key = event->key0;\n"
        "        if (state->key0 == key || state->key1 == key ||\n"
        "            ((u8 *)event)[4] == state->tag0 ||\n"
        "            ((u8 *)event)[4] == state->tag1) {\n"
        "            func_1516972C(owner);\n"
        "        }\n"
        "    }")
    yield "state-first-local-key", state_first_key
    yield "wide-command", SELECTED.replace(
        "IdentityEvent151B5A9C *event, u8 command",
        "IdentityEvent151B5A9C *event, s32 command")
    yield "nested-zero", SELECTED.replace(
        "    } else if (command == 0 &&\n"
        "               (event->key0 == state->key0 ||\n"
        "                event->key0 == state->key1 ||\n"
        "                ((u8 *)event)[4] == state->tag0 ||\n"
        "                ((u8 *)event)[4] == state->tag1)) {\n"
        "        func_1516972C(owner);\n"
        "    }",
        "    } else if (command == 0) {\n"
        "        if (event->key0 == state->key0 ||\n"
        "            event->key0 == state->key1 ||\n"
        "            ((u8 *)event)[4] == state->tag0 ||\n"
        "            ((u8 *)event)[4] == state->tag1) {\n"
        "            func_1516972C(owner);\n"
        "        }\n"
        "    }")
    yield "independent-first", SELECTED.replace(
        "        } else if (event->key1 == state->key0) {",
        "        }\n        if (event->key1 == state->key0) {")
    yield "independent-second", SELECTED.replace(
        "        } else if (event->key1 == state->key1) {",
        "        }\n        if (event->key1 == state->key1) {")


def compile_candidate(root, output, name, body):
    output.mkdir(parents=True, exist_ok=True)
    with patch.multiple(
            compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        record, words = compiler.compile_candidate(
            root, output, name, body, "o2g3")
    retail = struct.unpack_from(
        ">%dI" % WORDS, (root / "conker/conker.us.bin").read_bytes(), ROM)
    record["differences"] = sum(
        left != right for left, right in
        itertools.zip_longest(words, retail, fillvalue=0))
    return record


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / "conker/build/game-dual-identity-event-151B5A9C-match"
    records = []
    for name, body in candidates():
        record = compile_candidate(root, output, name, body)
        records.append(record)
        print(name, record["body_words"], hex(record["frame"]),
              record["differences"], flush=True)
    (output / "candidate-measurements.json").write_text(
        json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
