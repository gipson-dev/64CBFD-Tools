"""Composite-effect factory direct bytes and strict whole-image qualification."""
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

BUILD = "conker/build/game-composite-effect-factory-15152B38-match"
BASELINE = "f459bd92845118fe65e9615347275c6b6a08821b21558c9546b87922a6e88b20"
LINKED = "c3ac9a148dfa49ed6fae2cd5c04a37eed443128c4250acf69aa102511233bde3"
FUNCTION = "func_15152B38"
OWNER = "generated_17CAF0"
ENTRY = 0x15152B38
ROM = 0x17FFE8
SIZE = 1080
RAW_SHA = "e0ec9c03e53dc37933fde31f8724b5903fc59e07babeab64894005606090736e"
BINDINGS = {
    60: [("R_MIPS_26", "func_150ADA20")],
    272: [("R_MIPS_26", "func_150ADA20")],
    320: [("R_MIPS_26", "func_150ADA20")],
    368: [("R_MIPS_26", "func_150ADA68")],
    392: [("R_MIPS_26", "func_150ADA68")],
    416: [("R_MIPS_26", "func_150ADA20")],
    424: [("R_MIPS_26", "func_150ADA20")],
    432: [("R_MIPS_26", "func_150ADA68")],
    552: [("R_MIPS_26", "func_15143794")],
    560: [("R_MIPS_26", "func_150ADA20")],
    608: [("R_MIPS_26", "func_150ADA20")],
    656: [("R_MIPS_26", "func_150ADA20")],
    704: [("R_MIPS_26", "func_150ADA20")],
    752: [("R_MIPS_26", "func_150ADA20")],
    800: [("R_MIPS_26", "func_150ADA20")],
    848: [("R_MIPS_26", "func_150ADA20")],
    896: [("R_MIPS_26", "func_150ADA20")],
    944: [("R_MIPS_26", "func_150ADA20")],
    1012: [("R_MIPS_26", "func_1515C2F0")],
}
HEADERS = """#include <ultra64.h>
typedef struct { f32 x, y, z; } CompositeEffectPosition;
typedef struct {
    s32 baseCount, countRange;
    CompositeEffectPosition position;
    f32 field14Base, field18Range, field1CBase, field20Range;
    f32 radiusBase, radiusRange;
    s16 firstBase, firstRange, secondBase, secondRange;
    s32 headerByteBase, headerByteRange;
    s16 headerShortBase, headerShortRange;
    u16 field40;
    u8 fixed42, fixed43, fixed44;
    u8 byteBase45, byteBase46, byteBase47, byteBase48;
    u8 byteRange49, byteRange4A, byteRange4B, byteRange4C;
    u8 byteBase4D, byteBase4E, byteBase4F, byteBase50;
    u8 byteRange51, byteRange52, byteRange53, byteRange54;
    u8 byteBase55, byteRange56, fixed57, fixed58, padding59[3];
    s32 field5C, field60;
    s16 field64, field66, field68;
    u8 field6A, padding6B;
    f32 field6C;
    s8 field70, field71;
    u8 privateTail72[2];
} CompositeEffectInput;
typedef struct {
    f32 field0, direction[3], field10;
    u8 fixed14, fixed15, fixed16;
    s8 random17, random18, random19, random1A, random1B, random1C, random1D, random1E, random1F;
    u8 fixed20, fixed21, private22[2];
    s32 field24, field28;
    s16 field2C, field2E, field30;
    u8 field32, private33;
    f32 field34;
    s8 field38, field39;
    u8 privateTail3A[2];
} CompositeEffectPacket;
typedef struct {
    CompositeEffectPosition position;
    s16 randomC;
    u16 fieldE;
    s32 constant10;
    u8 private14;
    s8 random15;
    u8 privateTail16[2];
} CompositeEffectHeader;
typedef struct { CompositeEffectPacket packet; CompositeEffectHeader header; u8 privateTail54[4]; } CompositeEffectScratch;
s32 func_150ADA20(void);
f32 func_150ADA68(void);
void func_15143794(s16, s16, f32, f32 *);
s32 func_1515C2F0(CompositeEffectHeader *, s32, CompositeEffectPacket *, s32, u8, s32);
"""
SELECTED = """void func_15152B38(CompositeEffectInput *input, u8 mode, s32 extra) {
    CompositeEffectScratch scratch;
    u32 remaining;
    u32 first;
    u32 second;

    first = (u32)func_150ADA20();
    remaining = first % ((u32)input->countRange + 1U) + (u32)input->baseCount;
    scratch.header.position = input->position;
    scratch.header.fieldE = input->field40;
    scratch.header.constant10 = 10;
    scratch.packet.fixed14 = input->fixed42;
    scratch.packet.fixed15 = input->fixed43;
    scratch.packet.fixed16 = input->fixed44;
    scratch.packet.fixed20 = input->fixed57;
    scratch.packet.fixed21 = input->fixed58;
    scratch.packet.field24 = input->field5C;
    scratch.packet.field28 = input->field60;
    scratch.packet.field2C = input->field64;
    scratch.packet.field2E = input->field66;
    scratch.packet.field38 = input->field70;
    scratch.packet.field39 = input->field71;
    scratch.packet.field30 = input->field68;
    scratch.packet.field32 = input->field6A;
    scratch.packet.field34 = input->field6C;
    while (remaining != 0) {
        first = (u32)func_150ADA20();
        scratch.header.random15 = (s8)(first % ((u32)input->headerByteRange + 1U) + (u32)input->headerByteBase);
        first = (u32)func_150ADA20();
        scratch.header.randomC = (s16)(first % ((u32)(input->headerShortRange + 1)) + input->headerShortBase);
        scratch.packet.field0 = func_150ADA68() * input->field18Range + input->field14Base;
        scratch.packet.field10 = func_150ADA68() * input->field20Range + input->field1CBase;
        first = (u32)func_150ADA20();
        second = (u32)func_150ADA20();
        func_15143794((s16)(first % (u32)(input->firstRange + 1) + input->firstBase),
                      (s16)(second % (u32)(input->secondRange + 1) + input->secondBase),
                      func_150ADA68() * input->radiusRange + input->radiusBase, scratch.packet.direction);
        first = (u32)func_150ADA20(); scratch.packet.random17 = (s8)(first % ((u32)input->byteRange49 + 1U) + input->byteBase45);
        first = (u32)func_150ADA20(); scratch.packet.random18 = (s8)(first % ((u32)input->byteRange4A + 1U) + input->byteBase46);
        first = (u32)func_150ADA20(); scratch.packet.random19 = (s8)(first % ((u32)input->byteRange4B + 1U) + input->byteBase47);
        first = (u32)func_150ADA20(); scratch.packet.random1A = (s8)(first % ((u32)input->byteRange4C + 1U) + input->byteBase48);
        first = (u32)func_150ADA20(); scratch.packet.random1B = (s8)(first % ((u32)input->byteRange51 + 1U) + input->byteBase4D);
        first = (u32)func_150ADA20(); scratch.packet.random1C = (s8)(first % ((u32)input->byteRange52 + 1U) + input->byteBase4E);
        first = (u32)func_150ADA20(); scratch.packet.random1D = (s8)(first % ((u32)input->byteRange53 + 1U) + input->byteBase4F);
        first = (u32)func_150ADA20(); scratch.packet.random1E = (s8)(first % ((u32)input->byteRange54 + 1U) + input->byteBase50);
        first = (u32)func_150ADA20(); scratch.packet.random1F = (s8)(first % ((u32)input->byteRange56 + 1U) + input->byteBase55);
        func_1515C2F0(&scratch.header, 0, &scratch.packet, 0, (u8)mode, extra);
        remaining--;
    }
}
"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_payload(raw, bindings):
    if len(raw) != SIZE or sha(raw) != RAW_SHA or bindings != BINDINGS:
        raise ValueError("Composite-effect factory payload or bindings changed")
    return raw, bindings


def recovered_owner(before):
    before = before.replace("\r\n", "\n")
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != f"s32 {FUNCTION}() {{\n    return 0;\n}}":
        raise ValueError("Composite-effect factory predecessor changed")
    header = HEADERS.replace("#include <ultra64.h>\n", "").rstrip() + "\n"
    comment = "/* Emit randomized composite-effect packets from live input fields using the complete private scratch extents. */\n"
    return before[:lo] + header + comment + SELECTED.rstrip() + before[hi:]


def predict(before, rom):
    if sha(before) != BASELINE:
        raise ValueError("Composite-effect factory image predecessor changed")
    out = bytearray(before)
    row, = [value for value in symbol_rows(before) if value[1] == FUNCTION]
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError("Composite-effect factory predecessor extent changed")
    truth = rom[ROM:ROM + SIZE]
    if len(truth) != SIZE:
        raise ValueError("Composite-effect factory retail slot missing")
    at = elf_slot_offset(before, ENTRY, SIZE)
    out[at:at + SIZE] = truth
    struct.pack_into(">I", out, row[0] + 8, SIZE)
    return bytes(out)


def check_image(before, actual, rom):
    if actual != predict(before, rom):
        raise ValueError("Composite-effect factory entire image differs")


def expected_map(output):
    data = (output / "private-joint-linked.map").read_bytes()
    private = (BUILD.removeprefix("conker/") + f"/make-shadow-{OWNER}/src/game/{OWNER}.c.o").encode()
    if not data.count(private):
        raise ValueError("Composite-effect factory map owner path changed")
    data = data.replace(private, f"build/src/game/{OWNER}.c.o".encode())
    private = (BUILD.removeprefix("conker/") + "/private-joint-linked.elf").encode()
    if data.count(private) != 1:
        raise ValueError("Composite-effect factory map output changed")
    return data.replace(private, b"build/conker.us.elf")


def verify_prepared(output):
    q = json.loads((output / "private-layout-v5.json").read_text())
    if (q["words"], q["frame"], q["guards"], q["raw_SHA256"], len(q["layouts"])) != (270, 176, 0, RAW_SHA, 3):
        raise ValueError("Composite-effect factory layout receipt changed")
    if payload(output / "selected-final.o", FUNCTION) != payload(output / f"original-{FUNCTION}.o", FUNCTION):
        raise ValueError("Composite-effect factory direct-exact payload changed")
    for name in ("private-guest-v6.json", "private-native-v7.json", "private-caller-v8.json", "private-owner-image-v9.json", f"qualified-{OWNER}.o", "private-joint-linked.elf"):
        if not (output / name).is_file():
            raise ValueError("Composite-effect factory prepared artifact missing: " + name)
    return True


def check_inputs(root, output, installed=False):
    verify_prepared(output)
    baseline = {
        f"conker/src/game/{OWNER}.c": (output / "before-conker_src_game_generated_17CAF0.c").read_bytes(),
        f"conker/build/src/game/{OWNER}.c.o": (output / "before-conker_build_src_game_generated_17CAF0.c.o").read_bytes(),
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
            raise ValueError("Composite-effect factory live input changed: " + name)
    return baseline


def audit(root, output, installed=False):
    from tools.check_game_data_layout import audit_layout
    values = check_inputs(root, output, installed)
    path = root / "conker/build/conker.us.elf" if installed else output / "private-joint-linked.elf"
    actual = path.read_bytes()
    rom = (root / "conker/conker.us.bin").read_bytes()
    check_image(values["conker/build/conker.us.elf"], actual, rom)
    if sha(actual) != LINKED:
        raise ValueError("Composite-effect factory linked image changed")
    data = audit_layout(path, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Composite-effect factory protected data changed")
    old, _, old_other = load_elf_functions(str(output / "before-conker_build_conker.us.elf"), "mips-linux-gnu-objdump")
    new, _, new_other = load_elf_functions(str(path), "mips-linux-gnu-objdump")
    if old.keys() != new.keys() or old_other != new_other or {name for name in old if old[name] != new[name]} != {FUNCTION}:
        raise ValueError("Composite-effect factory changed another body")
    expected = Counter((name, fields[1], SIZE if name == FUNCTION else fields[2], *fields[3:]) for _, name, fields, _ in symbol_rows(values["conker/build/conker.us.elf"]))
    if expected != Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(actual)):
        raise ValueError("Composite-effect factory named definition changed")
    q = json.loads((output / "private-owner-image-v9.json").read_text())
    q.update(private_only=not installed, installed=installed, matching_credit=1 if installed else 0, protected_data=data)
    if installed:
        (output / "installed-audit.json").write_text(json.dumps(q, indent=2) + "\n")
    return q
