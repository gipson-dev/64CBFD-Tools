"""Short-packet factory bytes, closed normalizations and strict image qualification."""
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

BUILD = "conker/build/game-short-packet-factory-15153298-match"
BASELINE = "e62447ad4dc113aa5633ac7639ccc34eba9ef21104d56fe48b48c8027e790c31"
LINKED = "c96781392ff30f96aea42f93ef2ec8c5aa9c19964aa3688694ce7a0aa4f495e2"
FUNCTION = "func_15153298"
OWNER = "generated_17CAF0"
ENTRY = 0x15153298
ROM = 0x180748
SIZE = 924
WORDS = 231
FRAME = 192
GUARDS = 103
RAW_SHA = "5b93e16561cb70b6553e717752618e7fc83d2d03bbb9fc041670b7320ab4fa69"
NORMALIZED_SHA = "b2ac88679486f7a4480a273566bac6d278e652762bd9c936d3f200c50a7f9a10"
BINDINGS = {
    288: [("R_MIPS_26", "func_150ADA20")],
    344: [("R_MIPS_26", "func_150ADA20")],
    396: [("R_MIPS_26", "func_150ADA20")],
    452: [("R_MIPS_26", "func_151423D8")],
    472: [("R_MIPS_26", "func_151423D8")],
    484: [("R_MIPS_26", "func_151423D8")],
    504: [("R_MIPS_26", "func_151423D8")],
    512: [("R_MIPS_26", "func_150ADA68")],
    532: [("R_MIPS_26", "func_150ADA20")],
    632: [("R_MIPS_26", "func_150ADA20")],
    680: [("R_MIPS_26", "func_150ADA20")],
    728: [("R_MIPS_26", "func_150ADA20")],
    776: [("R_MIPS_26", "func_150ADA20")],
    844: [("R_MIPS_26", "func_15167D84")],
}
HEADERS = """#include <ultra64.h>

typedef struct {
    f32 x;
    f32 y;
    f32 z;
    s16 countBase;
    s16 countRange;
    s16 firstAngleBase;
    s16 firstAngleRange;
    s16 secondAngleBase;
    s16 secondAngleRange;
    f32 speedBase;
    f32 speedRange;
    s16 magnitudeBase;
    s16 magnitudeRange;
    s16 field22Base;
    s16 field22Range;
    s8 fixed1F;
    u8 fixed34;
    s16 field2ABase;
    s16 field2ARange;
    s16 fixed0E;
    s16 field24Base;
    s16 field24Range;
    s16 field26Base;
    s16 field26Range;
    s32 owner;
    u8 color;
    u8 alpha;
    u8 privateTail3E[2];
} ShortPacketInput;

typedef struct {
    s32 owner;
    u8 private04[8];
    s16 zero0C;
    s16 fixed0E;
    s16 positionX;
    s16 positionY;
    s16 positionZ;
    s16 directionX;
    s16 directionZ;
    u8 private1A[2];
    s8 scaledX;
    s8 scaledY;
    s8 scaledZ;
    s8 fixed1F;
    s16 directionY;
    s16 field22;
    s16 field24;
    s16 field26;
    s16 magnitude;
    s8 field2A;
    u8 private2B;
    u8 color0;
    u8 color1;
    u8 color2;
    u8 alpha;
    s8 zero30;
    s8 zero31;
    s8 zero32;
    u8 private33;
    u16 fixed34;
    u8 privateTail36[2];
} ShortPacket;

s32 func_150ADA20(void);
f32 func_150ADA68(void);
f32 func_151423D8(s32 angle);
void func_15167D84(void *packet, s32 kind, s32 offset, s8 marker, u8 mode, s32 owner);

"""
SELECTED = """void func_15153298(ShortPacketInput *input, u8 mode, s32 owner) {
    ShortPacket packet;
    f32 speed;
    f32 secondPrimary;
    f32 secondQuarter;
    f32 firstPrimary;
    f32 firstQuarter;
    f32 product;
    s16 firstAngle;
    s16 secondAngle;
    s32 remaining;

    packet.positionX = (s16)input->x;
    packet.positionY = (s16)input->y;
    packet.positionZ = (s16)input->z;
    packet.scaledX = (s8)(input->x * 256.0f);
    packet.scaledY = (s8)(input->y * 256.0f);
    packet.scaledZ = (s8)(input->z * 256.0f);
    packet.color0 = input->color;
    packet.color1 = input->color;
    packet.zero30 = 0;
    packet.zero31 = 0;
    packet.zero32 = 0;
    packet.color2 = input->color;
    packet.alpha = input->alpha;
    packet.fixed1F = input->fixed1F;
    packet.zero0C = 0;
    packet.fixed34 = input->fixed34;
    packet.fixed0E = input->fixed0E;
    packet.owner = input->owner;
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
            product = speed * secondPrimary;
            packet.magnitude = (u32)func_150ADA20() % ((u32)input->magnitudeRange + 1U) + input->magnitudeBase;
            packet.directionX = (s16)(product * firstQuarter);
            packet.directionY = (s16)(-speed * secondQuarter);
            packet.directionZ = (s16)(product * firstPrimary);
            packet.field22 = (u32)func_150ADA20() % ((u32)input->field22Range + 1U) + input->field22Base;
            packet.field2A = (u32)func_150ADA20() % ((u32)input->field2ARange + 1U) + input->field2ABase;
            packet.field24 = (u32)func_150ADA20() % ((u32)input->field24Range + 1U) + input->field24Base;
            packet.field26 = (u32)func_150ADA20() % ((u32)input->field26Range + 1U) + input->field26Base;
            func_15167D84(&packet, 0, 0, -1, mode, owner);
            remaining--;
        } while (remaining != 0);
    }
}

"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_payload(raw, bindings):
    if len(raw) != SIZE or sha(raw) != RAW_SHA or bindings != BINDINGS:
        raise ValueError("Short-packet factory payload or bindings changed")
    return raw, bindings


def recovered_owner(before):
    before = before.replace("\r\n", "\n")
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != f"s32 {FUNCTION}() {{\n    return 0;\n}}":
        raise ValueError("Short-packet factory predecessor changed")
    header = HEADERS.replace("#include <ultra64.h>\n", "").rstrip() + "\n"
    comment = "/* Emit randomized short-form effect packets from a complete live input record. */\n"
    return before[:lo] + header + comment + SELECTED.rstrip() + before[hi:]


def predict(before, rom):
    if sha(before) != BASELINE:
        raise ValueError("Short-packet factory image predecessor changed")
    out = bytearray(before)
    row, = [value for value in symbol_rows(before) if value[1] == FUNCTION]
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError("Short-packet factory predecessor extent changed")
    truth = rom[ROM:ROM + SIZE]
    if len(truth) != SIZE:
        raise ValueError("Short-packet factory retail slot missing")
    at = elf_slot_offset(before, ENTRY, SIZE)
    out[at:at + SIZE] = truth
    struct.pack_into(">I", out, row[0] + 8, SIZE)
    return bytes(out)


def check_image(before, actual, rom):
    if actual != predict(before, rom):
        raise ValueError("Short-packet factory entire image differs")


def expected_map(output):
    data = (output / "private-joint-linked.map").read_bytes()
    private = (BUILD.removeprefix("conker/") + f"/make-shadow-{OWNER}/src/game/{OWNER}.c.o").encode()
    if not data.count(private):
        raise ValueError("Short-packet factory map owner path changed")
    data = data.replace(private, f"build/src/game/{OWNER}.c.o".encode())
    private = (BUILD.removeprefix("conker/") + "/private-joint-linked.elf").encode()
    if data.count(private) != 1:
        raise ValueError("Short-packet factory map output changed")
    return data.replace(private, b"build/conker.us.elf")


def verify_prepared(output):
    q = json.loads((output / "private-layout-v3.json").read_text())
    values = (q["words"], q["retail_frame"], q["raw_frame"], q["proposed_closed_normalizations"], q["raw_SHA256"], q["normalized_SHA256"], len(q["layouts"]))
    if values != (WORDS, FRAME, FRAME, GUARDS, RAW_SHA, NORMALIZED_SHA, 3):
        raise ValueError("Short-packet factory layout receipt changed")
    raw, refs = payload(output / "screen-mode-u8.o", FUNCTION)
    checked_payload(raw, refs)
    original, original_refs = payload(output / ("original-" + FUNCTION + ".o"), FUNCTION)
    normalized, normalized_refs = payload(output / "normalized.o", FUNCTION)
    if original != normalized or original_refs != normalized_refs or refs != original_refs:
        raise ValueError("Short-packet factory normalized payload changed")
    if sum(left != right for left, right in zip(struct.unpack(">231I", raw), struct.unpack(">231I", original))) != GUARDS:
        raise ValueError("Short-packet factory closed-word count changed")
    if (output / "proposed-guards.csv").read_bytes().count(b"," + FUNCTION.encode() + b",") != GUARDS:
        raise ValueError("Short-packet factory guard rows changed")
    for name in (
        "private-guest-v4.json", "private-native-v6.json", "private-caller-v5.json",
        "private-owner-image-v7.json", f"qualified-{OWNER}.o", "private-joint-linked.elf",
    ):
        if not (output / name).is_file():
            raise ValueError("Short-packet factory prepared artifact missing: " + name)
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
            raise ValueError("Short-packet factory live input changed: " + name)
    return baseline


def audit(root, output, installed=False):
    from tools.check_game_data_layout import audit_layout
    values = check_inputs(root, output, installed)
    path = root / "conker/build/conker.us.elf" if installed else output / "private-joint-linked.elf"
    actual = path.read_bytes()
    rom = (root / "conker/conker.us.bin").read_bytes()
    check_image(values["conker/build/conker.us.elf"], actual, rom)
    if sha(actual) != LINKED:
        raise ValueError("Short-packet factory linked image changed")
    data = audit_layout(path, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Short-packet factory protected data changed")
    old, _, old_other = load_elf_functions(str(output / "before-conker_build_conker.us.elf"), "mips-linux-gnu-objdump")
    new, _, new_other = load_elf_functions(str(path), "mips-linux-gnu-objdump")
    if old.keys() != new.keys() or old_other != new_other or {name for name in old if old[name] != new[name]} != {FUNCTION}:
        raise ValueError("Short-packet factory changed another body")
    expected = Counter((name, fields[1], SIZE if name == FUNCTION else fields[2], *fields[3:]) for _, name, fields, _ in symbol_rows(values["conker/build/conker.us.elf"]))
    if expected != Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(actual)):
        raise ValueError("Short-packet factory named definition changed")
    q = json.loads((output / "private-owner-image-v7.json").read_text())
    q.update(private_only=not installed, installed=installed, matching_credit=1 if installed else 0, protected_data=data)
    if installed:
        (output / "installed-audit.json").write_text(json.dumps(q, indent=2) + "\n")
    return q


