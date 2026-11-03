"""Screen semantic C forms for actor child-state finisher func_1507FEA0."""

import itertools
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler


ENTRY, ROM, WORDS = 0x1507FEA0, 0xAD350, 61
FUNCTION = "func_1507FEA0"
SYMBOLS = {
    "D_800BE9E4": 0x800BE9E4,
    "D_800C35EA": 0x800C35EA,
    "func_1507FC2C": 0x1507FC2C,
    "func_1507FF94": 0x1507FF94,
}
RECORD = ""
DECLARATIONS = """extern s32 D_800BE9E4;
extern u8 D_800C35EA;
void func_1507FC2C(u8 *);
void func_1507FF94(u8 *);
"""

SELECTED = """void func_1507FEA0(u8 *actor) {
    u8 *child = *(u8 **)(actor + 0x31C);
    u8 *state;
    s32 timer;
    s32 tick;
    u16 count;

    if (child == NULL || actor[0x127] == 0xFF) {
        return;
    }
    if (actor[0x13A] != 0) {
        actor[0x13A]--;
    }
    state = child + 0x58;
    if (state[0] == 1) {
        if (D_800C35EA == 1) {
            *(u16 *)(state + 2) = 0;
        } else {
            tick = D_800BE9E4;
            count = *(u16 *)(state + 2);
            if (count < 0xFFFF - tick) {
                *(u16 *)(state + 2) = count + tick;
            }
        }
    } else {
        *(u16 *)(state + 2) = 0;
        state[4] = 0;
        state[5] = 0;
        state[0xC] = 0;
        state[0xD] = 0;
    }
    child = *(u8 **)(actor + 0x31C);
    timer = *(s16 *)(child + 0x66);
    if (timer != 0) {
        tick = D_800BE9E4;
        if (tick < timer) {
            *(s16 *)(child + 0x66) = timer - tick;
        } else {
            func_1507FF94(actor);
            child = *(u8 **)(actor + 0x31C);
            *(s16 *)(child + 0x66) = 0;
        }
    }
    func_1507FC2C(actor);
}"""

COMBINED = """void func_1507FEA0(u8 *actor) {
    u8 *child = *(u8 **)(actor + 0x31C);
    u8 *state = child + 0x58;
    u8 countdown;
    s32 timer;
    s32 tick;
    u16 count;

    if (child == NULL || actor[0x127] == 0xFF) {
        return;
    }
    countdown = actor[0x13A];
    if (countdown != 0) {
        actor[0x13A] = countdown - 1;
    }
    if (state[0] == 1 && D_800C35EA != 1) {
        tick = D_800BE9E4;
        count = *(u16 *)(state + 2);
        if (count < 0xFFFF - tick) {
            *(u16 *)(state + 2) = count + tick;
        }
    } else {
        *(u16 *)(state + 2) = 0;
        state[4] = 0;
        state[5] = 0;
        state[0xC] = 0;
        state[0xD] = 0;
    }
    child = *(u8 **)(actor + 0x31C);
    timer = *(s16 *)(child + 0x66);
    if (timer != 0) {
        tick = D_800BE9E4;
        if (tick < timer) {
            *(s16 *)(child + 0x66) = timer - tick;
        } else {
            func_1507FF94(actor);
            child = *(u8 **)(actor + 0x31C);
            *(s16 *)(child + 0x66) = 0;
        }
    }
    func_1507FC2C(actor);
}"""


def candidates():
    yield "combined", COMBINED
    child_state = COMBINED.replace(
        "    u8 *state = child + 0x58;\n", "").replace(
        "    countdown = actor[0x13A];",
        "    child += 0x58;\n    countdown = actor[0x13A];").replace(
        "state[", "child[").replace("(state +", "(child +")
    yield "child-as-state", child_state
    yield "child-as-state-after-countdown", child_state.replace(
        "    child += 0x58;\n    countdown = actor[0x13A];",
        "    countdown = actor[0x13A];\n    child += 0x58;")
    yield "combined-countdown-first-declaration", COMBINED.replace(
        "    u8 *state = child + 0x58;\n    u8 countdown;",
        "    u8 countdown;\n    u8 *state = child + 0x58;")
    yield "combined-wide-countdown", COMBINED.replace(
        "    u8 countdown;", "    s32 countdown;")
    yield "combined-address-expression", COMBINED.replace(
        "    u8 *state = child + 0x58;", "    u8 *state = &child[0x58];")
    yield "combined-two-step-state", COMBINED.replace(
        "    u8 *state = child + 0x58;", "    u8 *state = child;").replace(
        "    countdown = actor[0x13A];",
        "    state += 0x58;\n    countdown = actor[0x13A];")
    yield "combined-countdown-before-state", COMBINED.replace(
        "    u8 *state = child + 0x58;", "    u8 *state;").replace(
        "    countdown = actor[0x13A];",
        "    countdown = actor[0x13A];\n    state = child + 0x58;")
    yield "combined-comma-state", COMBINED.replace(
        "    u8 *state = child + 0x58;", "    u8 *state;").replace(
        "    countdown = actor[0x13A];",
        "    countdown = (state = child + 0x58, actor[0x13A]);")
    yield "combined-direct-countdown", COMBINED.replace(
        "    u8 countdown;\n", "").replace(
        "    countdown = actor[0x13A];\n"
        "    if (countdown != 0) {\n"
        "        actor[0x13A] = countdown - 1;",
        "    if (actor[0x13A] != 0) {\n"
        "        actor[0x13A]--;")
    yield "combined-state-statement", COMBINED.replace(
        "    u8 *state = child + 0x58;", "    u8 *state;").replace(
        "    countdown = actor[0x13A];", "    state = child + 0x58;\n"
        "    countdown = actor[0x13A];")
    yield "combined-mode-nested", COMBINED.replace(
        "    if (state[0] == 1 && D_800C35EA != 1) {",
        "    if (state[0] == 1) {\n"
        "        if (D_800C35EA == 1) {\n"
        "            goto reset;\n"
        "        }").replace(
        "    } else {\n        *(u16 *)(state + 2) = 0;",
        "    } else {\nreset:\n        *(u16 *)(state + 2) = 0;")
    yield "selected", SELECTED
    yield "early-state", SELECTED.replace(
        "    u8 *state;", "    u8 *state = child + 0x58;").replace(
        "    state = child + 0x58;\n", "")
    yield "early-state-separate-exits", SELECTED.replace(
        "    u8 *state;", "    u8 *state = child + 0x58;").replace(
        "    state = child + 0x58;\n", "").replace(
        "    if (child == NULL || actor[0x127] == 0xFF) {\n"
        "        return;\n"
        "    }",
        "    if (child == NULL) {\n"
        "        return;\n"
        "    }\n"
        "    if (actor[0x127] == 0xFF) {\n"
        "        return;\n"
        "    }")
    yield "separate-early-exits", SELECTED.replace(
        "    if (child == NULL || actor[0x127] == 0xFF) {\n"
        "        return;\n"
        "    }",
        "    if (child == NULL) {\n"
        "        return;\n"
        "    }\n"
        "    if (actor[0x127] == 0xFF) {\n"
        "        return;\n"
        "    }")
    yield "post-decrement", SELECTED.replace(
        "        actor[0x13A]--;", "        actor[0x13A] = actor[0x13A] - 1;")
    yield "mode-not-one", SELECTED.replace(
        "    if (state[0] == 1) {\n"
        "        if (D_800C35EA == 1) {\n"
        "            *(u16 *)(state + 2) = 0;\n"
        "        } else {",
        "    if (state[0] != 1) {\n"
        "        *(u16 *)(state + 2) = 0;\n"
        "        state[4] = 0;\n"
        "        state[5] = 0;\n"
        "        state[0xC] = 0;\n"
        "        state[0xD] = 0;\n"
        "    } else {\n"
        "        if (D_800C35EA == 1) {\n"
        "            *(u16 *)(state + 2) = 0;\n"
        "        } else {").replace(
        "        }\n    } else {\n"
        "        *(u16 *)(state + 2) = 0;\n"
        "        state[4] = 0;\n"
        "        state[5] = 0;\n"
        "        state[0xC] = 0;\n"
        "        state[0xD] = 0;\n"
        "    }\n    child =",
        "        }\n    }\n    child =")
    yield "inline-count", SELECTED.replace(
        "    u16 count;\n", "").replace(
        "            count = *(u16 *)(state + 2);\n"
        "            if (count < 0xFFFF - tick) {\n"
        "                *(u16 *)(state + 2) = count + tick;",
        "            if (*(u16 *)(state + 2) < 0xFFFF - tick) {\n"
        "                *(u16 *)(state + 2) += tick;")
    yield "fresh-tick", SELECTED.replace(
        "            tick = D_800BE9E4;\n"
        "            count = *(u16 *)(state + 2);\n"
        "            if (count < 0xFFFF - tick) {\n"
        "                *(u16 *)(state + 2) = count + tick;",
        "            count = *(u16 *)(state + 2);\n"
        "            if (count < 0xFFFF - D_800BE9E4) {\n"
        "                *(u16 *)(state + 2) = count + D_800BE9E4;").replace(
        "        tick = D_800BE9E4;\n"
        "        if (tick < timer) {\n"
        "            *(s16 *)(child + 0x66) = timer - tick;",
        "        if (D_800BE9E4 < timer) {\n"
        "            *(s16 *)(child + 0x66) = timer - D_800BE9E4;")
    yield "short-timer", SELECTED.replace("    s32 timer;", "    s16 timer;")
    yield "signed-count", SELECTED.replace("    u16 count;", "    s16 count;")
    yield "wide-return", SELECTED.replace(
        "void func_1507FEA0(u8 *actor)", "s32 func_1507FEA0(u8 *actor)").replace(
        "        return;", "        return 0;").replace(
        "    func_1507FC2C(actor);\n}", "    func_1507FC2C(actor);\n    return 0;\n}")


def compile_candidate(root, output, name, body):
    output.mkdir(parents=True, exist_ok=True)
    with patch.multiple(
            compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        record, words = compiler.compile_candidate(
            root, output, name, body, "o2g3")
    retail = struct.unpack_from(
        ">%dI" % WORDS, (root / "conker/conker.us.bin").read_bytes(), ROM)
    pairs = list(itertools.zip_longest(words, retail, fillvalue=0))
    record["differences"] = sum(left != right for left, right in pairs)
    record["difference_offsets"] = [index * 4 for index, (left, right)
                                    in enumerate(pairs) if left != right]
    record["raw_sha256"] = hashlib.sha256(struct.pack(
        ">%dI" % len(words), *words)).hexdigest()
    return record


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / "conker/build/game-actor-child-state-finish-1507FEA0-candidates"
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
