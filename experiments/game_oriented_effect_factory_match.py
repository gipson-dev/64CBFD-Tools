"""Oriented-effect factory bytes, closed normalizations and strict image qualification."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions

BUILD = "conker/build/game-oriented-effect-factory-15152F70-match"
BASELINE = "c3ac9a148dfa49ed6fae2cd5c04a37eed443128c4250acf69aa102511233bde3"
LINKED = "e62447ad4dc113aa5633ac7639ccc34eba9ef21104d56fe48b48c8027e790c31"
FUNCTION = "func_15152F70"
OWNER = "generated_17CAF0"
ENTRY = 0x15152F70
ROM = 0x180420
SIZE = 808
WORDS = 202
FRAME = 264
GUARDS = 37
RAW_SHA = "07baa8548bb2a5b67b717eaa44d704390c5f4b52507d446c4d16afb099aaf7c9"
NORMALIZED_SHA = "25c67ac4d7109f3bc77eef9078d6893f57d0ecb108bd2b38aed2bf7691bebd16"
BINDINGS = {
    212: [("R_MIPS_26", "func_150ADA20")],
    272: [("R_MIPS_26", "func_150ADA20")],
    324: [("R_MIPS_26", "func_150ADA20")],
    380: [("R_MIPS_26", "func_151423D8")],
    400: [("R_MIPS_26", "func_151423D8")],
    412: [("R_MIPS_26", "func_151423D8")],
    432: [("R_MIPS_26", "func_151423D8")],
    440: [("R_MIPS_26", "func_150ADA68")],
    460: [("R_MIPS_26", "func_150ADA20")],
    508: [("R_MIPS_26", "func_150ADA20")],
    556: [("R_MIPS_26", "func_150ADA68")],
    580: [("R_MIPS_26", "func_150ADA68")],
    724: [("R_MIPS_26", "func_15147DA0")],
}
HEADERS = """#include <ultra64.h>

typedef struct { f32 x, y, z; } OrientedEffectPosition;
typedef struct {
    OrientedEffectPosition position;
    f32 fieldCBase, field10Range, field14Base, field18Range, speedBase, speedRange;
    s16 countBase, countRange, firstAngleBase, firstAngleRange;
    s16 secondAngleBase, secondAngleRange, byteBase, byteRange, shortBase, shortRange;
    u8 fixed38, fixed39, private3A[2];
    s32 argument3C, argument40, argument44, argument48, argument4C, argument50;
    u8 fixed54, fixed55, privateTail56[2];
} OrientedEffectInput;
typedef struct {
    s32 field0, field4, field8, fieldC, field10, field14, field18;
    u8 field1C, field1D, privateTail1E[6];
} OrientedEffectDescriptor;
typedef struct {
    f32 field0, direction[3], field10;
    u8 private14[4], fixed18, fixed19, fixed1A, fixed1B, privateTail1C[4];
} OrientedEffectMotion;
typedef struct {
    OrientedEffectPosition position;
    s16 randomC, constantE;
    s32 constant10;
    u8 private14;
    s8 random15;
    u8 privateTail16[2];
} OrientedEffectHeader;
typedef struct {
    OrientedEffectDescriptor descriptor;
    OrientedEffectMotion motion;
    OrientedEffectHeader header;
} OrientedEffectScratch;
s32 func_150ADA20(void);
f32 func_150ADA68(void);
f32 func_151423D8(s32 angle);
void func_15147DA0();
"""
SELECTED = """void func_15152F70(OrientedEffectInput *input, u8 mode) {
    OrientedEffectHeader header;
    OrientedEffectMotion motion;
    OrientedEffectDescriptor descriptor;
    f32 speed;
    f32 secondPrimary;
    f32 secondQuarter;
    f32 firstPrimary;
    f32 firstQuarter;
    f32 product;
    s16 firstAngle;
    s16 secondAngle;
    s32 remaining;

    header.constant10 = 1;
    header.constantE = 1;
    motion.fixed19 = input->fixed38;
    motion.fixed1A = input->fixed54;
    motion.fixed18 = input->fixed39;
    motion.fixed1B = input->fixed55;
    header.position = input->position;
    descriptor.field0 = 0;
    descriptor.field4 = 1;
    descriptor.field8 = 0x160600;
    descriptor.fieldC = 3;
    descriptor.field10 = 0x10;
    descriptor.field14 = 0x80;
    descriptor.field18 = 0x20;
    descriptor.field1C = 0;
    descriptor.field1D = 9;
    remaining = (u32)func_150ADA20() % ((u32)input->countRange + 1U) + input->countBase;
    if (remaining != 0) {
        do {
            firstAngle = (u32)func_150ADA20() % ((u32)input->firstAngleRange + 1U) + input->firstAngleBase;
            secondAngle = (u32)func_150ADA20() % ((u32)input->secondAngleRange + 1U) + input->secondAngleBase;
            secondPrimary = func_151423D8((u8)secondAngle);
            secondQuarter = func_151423D8((u8)(secondAngle - 0x40));
            firstPrimary = func_151423D8((u8)firstAngle);
            firstQuarter = func_151423D8((u8)(firstAngle - 0x40));
            speed = func_150ADA68() * input->speedRange + input->speedBase;
            header.random15 = (u32)func_150ADA20() % ((u32)input->byteRange + 1U) + input->byteBase;
            header.randomC = (u32)func_150ADA20() % ((u32)input->shortRange + 1U) + input->shortBase;
            motion.field0 = func_150ADA68() * input->field10Range + input->fieldCBase;
            product = speed * secondPrimary;
            motion.field10 = func_150ADA68() * input->field18Range + input->field14Base;
            motion.direction[0] = product * firstQuarter;
            motion.direction[1] = -speed * secondQuarter;
            motion.direction[2] = product * firstPrimary;
            func_15147DA0(&header.position, &motion.field0, 0,
                          input->argument3C, input->argument40, input->argument44,
                          input->argument48, input->argument4C, input->argument50,
                          0, 0, &descriptor, 0, mode, 1);
            remaining--;
        } while (remaining != 0);
    }
}
"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_payload(raw, bindings):
    if len(raw) != SIZE or sha(raw) != RAW_SHA or bindings != BINDINGS:
        raise ValueError("Oriented-effect factory payload or bindings changed")
    return raw, bindings


def recovered_owner(before):
    before = before.replace("\r\n", "\n")
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != f"s32 {FUNCTION}() {{\n    return 0;\n}}":
        raise ValueError("Oriented-effect factory predecessor changed")
    header = HEADERS.replace("#include <ultra64.h>\n", "").rstrip() + "\n"
    comment = "/* Emit oriented randomized effect packets from live input fields using complete private scratch extents. */\n"
    return before[:lo] + header + comment + SELECTED.rstrip() + before[hi:]


def predict(before, rom):
    if sha(before) != BASELINE:
        raise ValueError("Oriented-effect factory image predecessor changed")
    out = bytearray(before)
    row, = [value for value in symbol_rows(before) if value[1] == FUNCTION]
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError("Oriented-effect factory predecessor extent changed")
    truth = rom[ROM:ROM + SIZE]
    if len(truth) != SIZE:
        raise ValueError("Oriented-effect factory retail slot missing")
    at = elf_slot_offset(before, ENTRY, SIZE)
    out[at:at + SIZE] = truth
    struct.pack_into(">I", out, row[0] + 8, SIZE)
    return bytes(out)


def check_image(before, actual, rom):
    if actual != predict(before, rom):
        raise ValueError("Oriented-effect factory entire image differs")


def expected_map(output):
    data = (output / "private-joint-linked.map").read_bytes()
    private = (BUILD.removeprefix("conker/") + f"/make-shadow-{OWNER}/src/game/{OWNER}.c.o").encode()
    if not data.count(private):
        raise ValueError("Oriented-effect factory map owner path changed")
    data = data.replace(private, f"build/src/game/{OWNER}.c.o".encode())
    private = (BUILD.removeprefix("conker/") + "/private-joint-linked.elf").encode()
    if data.count(private) != 1:
        raise ValueError("Oriented-effect factory map output changed")
    return data.replace(private, b"build/conker.us.elf")


def verify_prepared(output):
    q = json.loads((output / "private-layout-v6.json").read_text())
    values = (q["words"], q["retail_frame"], q["raw_frame"], q["proposed_closed_normalizations"], q["raw_SHA256"], q["normalized_SHA256"], len(q["layouts"]))
    if values != (WORDS, FRAME, 272, GUARDS, RAW_SHA, NORMALIZED_SHA, 3):
        raise ValueError("Oriented-effect factory layout receipt changed")
    raw, refs = payload(output / "refine-alias-v0-p0-m0.o", FUNCTION)
    checked_payload(raw, refs)
    original, original_refs = payload(output / ("original-" + FUNCTION + ".o"), FUNCTION)
    normalized, normalized_refs = payload(output / "normalized.o", FUNCTION)
    if original != normalized or original_refs != normalized_refs or refs != original_refs:
        raise ValueError("Oriented-effect factory normalized payload changed")
    if sum(left != right for left, right in zip(struct.unpack(">202I", raw), struct.unpack(">202I", original))) != GUARDS:
        raise ValueError("Oriented-effect factory closed-word count changed")
    if (output / "proposed-guards.csv").read_bytes().count(b"," + FUNCTION.encode() + b",") != GUARDS:
        raise ValueError("Oriented-effect factory guard rows changed")
    for name in (
        "private-guest-v8.json", "private-native-v9.json", "private-caller-v7.json",
        "private-owner-image-v10.json", f"qualified-{OWNER}.o", "private-joint-linked.elf",
    ):
        if not (output / name).is_file():
            raise ValueError("Oriented-effect factory prepared artifact missing: " + name)
    return True


def check_inputs(root, output, installed=False):
    verify_prepared(output)
    baseline = {
        f"conker/src/game/{OWNER}.c": (output / f"before-conker_src_game_{OWNER}.c").read_bytes(),
        f"conker/build/src/game/{OWNER}.c.o": (output / f"before-conker_build_src_game_{OWNER}.c.o").read_bytes(),
        "conker/build/conker.us.elf": (output / "before-conker_build_conker.us.elf").read_bytes(),
        "conker/build/conker.us.map": (output / "before-conker_build_conker.us.map").read_bytes(),
        "conker/retail_word_patches.us.csv": (output / "before-conker_retail_word_patches.us.csv").read_bytes(),
    }
    changes = {}
    if installed:
        changes[f"conker/src/game/{OWNER}.c"] = (output / f"proposed-{OWNER}.c").read_bytes()
        changes[f"conker/build/src/game/{OWNER}.c.o"] = (output / f"qualified-{OWNER}.o").read_bytes()
        changes["conker/build/conker.us.elf"] = predict(baseline["conker/build/conker.us.elf"], (root / "conker/conker.us.bin").read_bytes())
        changes["conker/build/conker.us.map"] = expected_map(output)
        changes["conker/retail_word_patches.us.csv"] = (output / "proposed-guards.csv").read_bytes()
    for name, data in baseline.items():
        if (root / name).read_bytes() != changes.get(name, data):
            raise ValueError("Oriented-effect factory live input changed: " + name)
    return baseline


def audit(root, output, installed=False):
    from tools.check_game_data_layout import audit_layout
    values = check_inputs(root, output, installed)
    path = root / "conker/build/conker.us.elf" if installed else output / "private-joint-linked.elf"
    actual = path.read_bytes()
    rom = (root / "conker/conker.us.bin").read_bytes()
    check_image(values["conker/build/conker.us.elf"], actual, rom)
    if sha(actual) != LINKED:
        raise ValueError("Oriented-effect factory linked image changed")
    data = audit_layout(path, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Oriented-effect factory protected data changed")
    old, _, old_other = load_elf_functions(str(output / "before-conker_build_conker.us.elf"), "mips-linux-gnu-objdump")
    new, _, new_other = load_elf_functions(str(path), "mips-linux-gnu-objdump")
    if old.keys() != new.keys() or old_other != new_other or {name for name in old if old[name] != new[name]} != {FUNCTION}:
        raise ValueError("Oriented-effect factory changed another body")
    expected = Counter((name, fields[1], SIZE if name == FUNCTION else fields[2], *fields[3:]) for _, name, fields, _ in symbol_rows(values["conker/build/conker.us.elf"]))
    if expected != Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(actual)):
        raise ValueError("Oriented-effect factory named definition changed")
    q = json.loads((output / "private-owner-image-v10.json").read_text())
    q.update(private_only=not installed, installed=installed, matching_credit=1 if installed else 0, protected_data=data)
    if installed:
        (output / "installed-audit.json").write_text(json.dumps(q, indent=2) + "\n")
    return q
