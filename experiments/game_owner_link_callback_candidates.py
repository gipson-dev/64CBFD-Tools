"""Screen semantic C forms for owner-link callback func_1519E1F4."""

import argparse
import itertools
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler


ENTRY, ROM, WORDS = 0x1519E1F4, 0x1CB6A4, 68
FUNCTION = "func_1519E1F4"
SYMBOLS = {"func_1519CFA0": 0x1519CFA0}
RECORD = """typedef struct {
    u8 *owner;
    u8 identity;
    u8 opaque5[0x47];
    u8 category;
} OwnerLinkCallback1519E1F4;

typedef struct {
    u8 *before;
    u8 *after;
    u8 beforeIdentity;
    u8 afterIdentity;
    u8 opaqueA[2];
} OwnerLinkEvent1519E1F4;
"""
DECLARATIONS = """void func_1519CFA0(u8 *);
"""

TYPED = """void func_1519E1F4(u8 *record, s32 eventAddress, u8 command) {
    OwnerLinkCallback1519E1F4 *link;
    OwnerLinkEvent1519E1F4 *event;

    link = *(OwnerLinkCallback1519E1F4 **)(record + 0x98);
    event = (OwnerLinkEvent1519E1F4 *)eventAddress;
    if (command == 0) {
        if (link->owner == event->before ||
                link->identity == ((u8 *)event)[4]) {
            func_1519CFA0(record);
        }
    } else if (command == 6) {
        if (((u8 *)event)[0] == link->category) {
            func_1519CFA0(record);
        }
    } else if (command == 7) {
        if (link->owner == event->before ||
                link->identity == ((u8 *)event)[4]) {
            func_1519CFA0(record);
        }
    } else if (command == 0x2D) {
        u8 *current = link->owner;

        if (current == event->before) {
            link->owner = event->after;
            link->identity = event->afterIdentity;
        } else if (current == event->after) {
            link->owner = event->before;
            link->identity = event->beforeIdentity;
        }
    }
}"""

SELECTED = """void func_1519E1F4(u8 *record, s32 eventAddress, u8 command) {
    u8 *link;
    u8 *event;

    link = *(u8 **)(record + 0x98);
    event = (u8 *)eventAddress;
    if (command == 0) {
        if (*(s32 *)link == *(s32 *)event || link[4] == event[4]) {
            func_1519CFA0(record);
        }
    } else if (command == 6) {
        if (event[0] == link[0x4C]) {
            func_1519CFA0(record);
        }
    } else if (command == 7) {
        if (*(s32 *)link == *(s32 *)event || link[4] == event[4]) {
            func_1519CFA0(record);
        }
    } else if (command == 0x2D) {
        if (*(u8 **)event == *(u8 **)link) {
            *(u8 **)link = *(u8 **)(event + 4);
            link[4] = event[9];
        } else if (*(u8 **)(event + 4) == *(u8 **)link) {
            *(u8 **)link = *(u8 **)event;
            link[4] = event[8];
        }
    }
}"""


def candidates():
    yield "selected", SELECTED
    yield "typed", TYPED
    yield "event-first", TYPED.replace(
        "    OwnerLinkCallback1519E1F4 *link;\n"
        "    OwnerLinkEvent1519E1F4 *event;",
        "    OwnerLinkEvent1519E1F4 *event;\n"
        "    OwnerLinkCallback1519E1F4 *link;")
    yield "initialized-locals", TYPED.replace(
        "    OwnerLinkCallback1519E1F4 *link;\n"
        "    OwnerLinkEvent1519E1F4 *event;\n\n"
        "    link = *(OwnerLinkCallback1519E1F4 **)(record + 0x98);\n"
        "    event = (OwnerLinkEvent1519E1F4 *)eventAddress;",
        "    OwnerLinkCallback1519E1F4 *link =\n"
        "        *(OwnerLinkCallback1519E1F4 **)(record + 0x98);\n"
        "    OwnerLinkEvent1519E1F4 *event =\n"
        "        (OwnerLinkEvent1519E1F4 *)eventAddress;")
    yield "cached-code", TYPED.replace(
        "    OwnerLinkEvent1519E1F4 *event;",
        "    OwnerLinkEvent1519E1F4 *event;\n    s32 code;").replace(
        "    event = (OwnerLinkEvent1519E1F4 *)eventAddress;\n"
        "    if (command == 0)",
        "    event = (OwnerLinkEvent1519E1F4 *)eventAddress;\n"
        "    code = command;\n    if (code == 0)").replace(
        "else if (command ==", "else if (code ==")
    yield "event-pointer-parameter", TYPED.replace(
        "s32 eventAddress", "u8 *eventBytes").replace(
        "event = (OwnerLinkEvent1519E1F4 *)eventAddress;",
        "event = (OwnerLinkEvent1519E1F4 *)eventBytes;")
    yield "raw-command-zero", TYPED.replace(
        "link->owner == event->before ||\n"
        "                link->identity == ((u8 *)event)[4]",
        "*(s32 *)link == *(s32 *)event ||\n"
        "                ((u8 *)link)[4] == ((u8 *)event)[4]", 1)
    yield "raw-command-seven", TYPED.replace(
        "link->owner == event->before ||\n"
        "                link->identity == ((u8 *)event)[4]",
        "*(s32 *)link == *(s32 *)event ||\n"
        "                ((u8 *)link)[4] == ((u8 *)event)[4]", 2)
    retail_order = TYPED.replace(
        "link->owner == event->before ||\n"
        "                link->identity == ((u8 *)event)[4]",
        "*(s32 *)link == *(s32 *)event ||\n"
        "                ((u8 *)link)[4] == ((u8 *)event)[4]", 2).replace(
        "if (((u8 *)event)[0] == link->category)",
        "if (link->category == ((u8 *)event)[0])").replace(
        "        u8 *current = link->owner;\n\n"
        "        if (current == event->before) {",
        "        u8 *before = event->before;\n"
        "        u8 *current = link->owner;\n\n"
        "        if (before == current) {").replace(
        "        } else if (current == event->after) {",
        "        } else if (event->after == current) {")
    yield "retail-order", retail_order
    yield "retail-order-current-first", retail_order.replace(
        "        u8 *before = event->before;\n"
        "        u8 *current = link->owner;",
        "        u8 *current = link->owner;\n"
        "        u8 *before = event->before;")
    yield "byte-link", """void func_1519E1F4(u8 *record, s32 eventAddress, u8 command) {
    u8 *link;
    u8 *event;

    link = *(u8 **)(record + 0x98);
    event = (u8 *)eventAddress;
    if (command == 0) {
        if (*(s32 *)link == *(s32 *)event || link[4] == event[4]) {
            func_1519CFA0(record);
        }
    } else if (command == 6) {
        if (event[0] == link[0x4C]) {
            func_1519CFA0(record);
        }
    } else if (command == 7) {
        if (*(s32 *)link == *(s32 *)event || link[4] == event[4]) {
            func_1519CFA0(record);
        }
    } else if (command == 0x2D) {
        u8 *current = *(u8 **)link;

        if (current == *(u8 **)event) {
            *(u8 **)link = *(u8 **)(event + 4);
            link[4] = event[9];
        } else if (current == *(u8 **)(event + 4)) {
            *(u8 **)link = *(u8 **)event;
            link[4] = event[8];
        }
    }
}"""
    yield "byte-link-no-current", """void func_1519E1F4(u8 *record, s32 eventAddress, u8 command) {
    u8 *link;
    u8 *event;

    link = *(u8 **)(record + 0x98);
    event = (u8 *)eventAddress;
    if (command == 0) {
        if (*(s32 *)link == *(s32 *)event || link[4] == event[4]) {
            func_1519CFA0(record);
        }
    } else if (command == 6) {
        if (event[0] == link[0x4C]) {
            func_1519CFA0(record);
        }
    } else if (command == 7) {
        if (*(s32 *)link == *(s32 *)event || link[4] == event[4]) {
            func_1519CFA0(record);
        }
    } else if (command == 0x2D) {
        if (*(u8 **)event == *(u8 **)link) {
            *(u8 **)link = *(u8 **)(event + 4);
            link[4] = event[9];
        } else if (*(u8 **)(event + 4) == *(u8 **)link) {
            *(u8 **)link = *(u8 **)event;
            link[4] = event[8];
        }
    }
}"""
    yield "early-current", TYPED.replace(
        "    OwnerLinkEvent1519E1F4 *event;",
        "    OwnerLinkEvent1519E1F4 *event;\n    u8 *current;").replace(
        "    if (command == 0) {", "    current = link->owner;\n    if (command == 0) {").replace(
        "link->owner == event->before", "current == event->before").replace(
        "        u8 *current = link->owner;\n\n", "")


def compile_candidate(root, output, name, body, profile="o2g3"):
    output.mkdir(parents=True, exist_ok=True)
    with patch.multiple(
            compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        record, words = compiler.compile_candidate(
            root, output, name, body, profile)
    retail = struct.unpack_from(
        ">%dI" % WORDS, (root / "conker/conker.us.bin").read_bytes(), ROM)
    record["differences"] = sum(
        left != right for left, right in
        itertools.zip_longest(words, retail, fillvalue=0))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / "conker/build/game-owner-link-callback-1519E1F4-match"
    records = []
    for name, body in candidates():
        profiles = compiler.PROFILES if args.profiles else ("o2g3",)
        for profile in profiles:
            record = compile_candidate(
                root, output, name + "-" + profile, body, profile)
            records.append(record)
            print(name, profile, record["body_words"], hex(record["frame"]),
                  record["differences"], flush=True)
    (output / "candidate-measurements.json").write_text(
        json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
