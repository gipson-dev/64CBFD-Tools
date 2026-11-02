"""Wide-packet factory bytes, closed normalizations and strict image qualification."""
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

BUILD = "conker/build/game-wide-packet-factory-151539B4-match"
BASELINE = "c96781392ff30f96aea42f93ef2ec8c5aa9c19964aa3688694ce7a0aa4f495e2"
LINKED = "35712bfe42fc4fac25904136609c5df5d840a7c08a3481b3a4cd2db2ceb93d8e"
FUNCTION = "func_151539B4"
OWNER = "generated_17CAF0"
ENTRY = 0x151539B4
ROM = 0x180E64
SIZE = 720
WORDS = 180
FRAME = 184
GUARDS = 25
RAW_SHA = "6b604155f0f95c0b49cf459376fd966cebcde5e9217d863dc000d3b77c721f96"
NORMALIZED_SHA = "55fc20581320123f9891d01122a03b6926841dc87d0a705e000f10a3f7cd36cc"
BINDINGS = {
    64: [("R_MIPS_26", "func_150ADA20")],
    256: [("R_MIPS_26", "func_150ADA20")],
    308: [("R_MIPS_26", "func_150ADA20")],
    364: [("R_MIPS_26", "func_151423D8")],
    384: [("R_MIPS_26", "func_151423D8")],
    396: [("R_MIPS_26", "func_151423D8")],
    416: [("R_MIPS_26", "func_151423D8")],
    460: [("R_MIPS_26", "func_150ADA68")],
    484: [("R_MIPS_26", "func_150ADA68")],
    508: [("R_MIPS_26", "func_150ADA20")],
    556: [("R_MIPS_26", "func_150ADA68")],
    580: [("R_MIPS_26", "func_150ADA20")],
    644: [("R_MIPS_26", "func_15156190")],
}
HEADERS = """#include <ultra64.h>

typedef struct {
    s16 countBase;
    s16 countRange;
    f32 origin[3];
    s16 firstAngleBase;
    s16 secondAngleBase;
    s16 firstAngleRange;
    s16 secondAngleRange;
    f32 firstValueBase;
    f32 firstValueRange;
    f32 secondValueBase;
    f32 secondValueRange;
    u8 copiedBytes[9];
    u8 private31;
    s16 shortBase;
    s16 shortRange;
    u16 fixed36;
    f32 floatBase;
    f32 floatRange;
    u8 byteBase;
    u8 byteRange;
    s16 fixed42;
    s16 fixed44;
    u8 kind;
    u8 privateTail47;
} WidePacketInput;

typedef struct {
    f32 origin[3];
    f32 directionX;
    f32 directionY;
    f32 directionZ;
    f32 firstValue;
    f32 secondValue;
    u8 copiedBytes[9];
    u8 private29;
    s16 randomShort;
    u16 fixed2C;
    u8 private2E[2];
    f32 randomFloat;
    s8 randomByte;
    u8 private35;
    s16 fixed36;
    s16 fixed38;
    u8 privateTail3A[2];
} WidePacket;

s32 func_150ADA20(void);
f32 func_150ADA68(void);
f32 func_151423D8(s32 angle);
void func_15156190(void *packet, u8 kind, s32 zero, u8 mode, s32 owner);

"""
SELECTED = """void func_151539B4(WidePacketInput *input, u8 mode) {
    WidePacket packet;
    WidePacket *packetPtr;
    f32 secondPrimary;
    f32 secondQuarter;
    f32 firstPrimary;
    f32 directionScale;
    s16 firstAngle;
    s16 secondAngle;
    s32 remaining;

    remaining = (u32)func_150ADA20() % ((u32)input->countRange + 1U) + input->countBase;
    packetPtr = &packet;
    *(volatile u8 *)&input->copiedBytes[0];
    *(s32 *)&packetPtr->origin[0] = *(s32 *)&input->origin[0];
    *(s32 *)&packetPtr->origin[1] = *(s32 *)&input->origin[1];
    *(s32 *)&packetPtr->origin[2] = *(s32 *)&input->origin[2];
    packetPtr->copiedBytes[0] = input->copiedBytes[0];
    packetPtr->copiedBytes[1] = input->copiedBytes[1];
    packetPtr->copiedBytes[2] = input->copiedBytes[2];
    packetPtr->copiedBytes[3] = input->copiedBytes[3];
    packetPtr->copiedBytes[4] = input->copiedBytes[4];
    packetPtr->copiedBytes[5] = input->copiedBytes[5];
    packetPtr->copiedBytes[6] = input->copiedBytes[6];
    packetPtr->copiedBytes[7] = input->copiedBytes[7];
    packetPtr->copiedBytes[8] = input->copiedBytes[8];
    packetPtr->fixed2C = input->fixed36;
    packetPtr->fixed36 = input->fixed42;
    packetPtr->fixed38 = input->fixed44;
    if (remaining != 0) {
        do {
            firstAngle = (u32)func_150ADA20() % ((u32)input->firstAngleRange + 1U) + input->firstAngleBase;
            secondAngle = (u32)func_150ADA20() % ((u32)input->secondAngleRange + 1U) + input->secondAngleBase;
            secondPrimary = func_151423D8((u8)secondAngle);
            secondQuarter = func_151423D8((u8)(secondAngle - 0x40));
            firstPrimary = func_151423D8((u8)firstAngle);
            directionScale = 10.0f * secondPrimary;
            packetPtr->directionX = directionScale * func_151423D8((u8)(firstAngle - 0x40));
            packetPtr->directionY = -10.0f * secondQuarter;
            packetPtr->directionZ = directionScale * firstPrimary;
            packetPtr->firstValue = func_150ADA68() * input->firstValueRange + input->firstValueBase;
            packetPtr->secondValue = func_150ADA68() * input->secondValueRange + input->secondValueBase;
            packetPtr->randomShort = (u32)func_150ADA20() % ((u32)input->shortRange + 1U) + input->shortBase;
            packetPtr->randomFloat = func_150ADA68() * input->floatRange + input->floatBase;
            packetPtr->randomByte = (u32)func_150ADA20() % ((u32)input->byteRange + 1U) + input->byteBase;
            func_15156190(packetPtr, input->kind, 0, mode, 0);
            remaining--;
        } while (remaining != 0);
    }
}

"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_payload(raw, bindings):
    if len(raw) != SIZE or sha(raw) != RAW_SHA or bindings != BINDINGS:
        raise ValueError("Wide-packet factory payload or bindings changed")
    return raw, bindings


def recovered_owner(before):
    before = before.replace("\r\n", "\n")
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != f"s32 {FUNCTION}() {{\n    return 0;\n}}":
        raise ValueError("Wide-packet factory predecessor changed")
    header = HEADERS.replace("#include <ultra64.h>\n", "").rstrip() + "\n"
    comment = "/* Emit randomized wide effect packets from a complete live input record. */\n"
    return before[:lo] + header + comment + SELECTED.rstrip() + before[hi:]


def predict(before, rom):
    if sha(before) != BASELINE:
        raise ValueError("Wide-packet factory image predecessor changed")
    out = bytearray(before)
    row, = [value for value in symbol_rows(before) if value[1] == FUNCTION]
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError("Wide-packet factory predecessor extent changed")
    truth = rom[ROM:ROM + SIZE]
    if len(truth) != SIZE:
        raise ValueError("Wide-packet factory retail slot missing")
    at = elf_slot_offset(before, ENTRY, SIZE)
    out[at:at + SIZE] = truth
    struct.pack_into(">I", out, row[0] + 8, SIZE)
    return bytes(out)


def check_image(before, actual, rom):
    if actual != predict(before, rom):
        raise ValueError("Wide-packet factory entire image differs")


def expected_map(output):
    data = (output / "private-joint-linked.map").read_bytes()
    private = (BUILD.removeprefix("conker/") + f"/make-shadow-{OWNER}/src/game/{OWNER}.c.o").encode()
    if not data.count(private):
        raise ValueError("Wide-packet factory map owner path changed")
    data = data.replace(private, f"build/src/game/{OWNER}.c.o".encode())
    private = (BUILD.removeprefix("conker/") + "/private-joint-linked.elf").encode()
    if data.count(private) != 1:
        raise ValueError("Wide-packet factory map output changed")
    return data.replace(private, b"build/conker.us.elf")


def verify_prepared(output):
    q = json.loads((output / "private-layout-v2.json").read_text())
    values = (q["words"], q["retail_frame"], q["raw_frame"], q["proposed_closed_normalizations"], q["raw_SHA256"], q["normalized_SHA256"], len(q["layouts"]))
    if values != (WORDS, FRAME, FRAME, GUARDS, RAW_SHA, NORMALIZED_SHA, 3):
        raise ValueError("Wide-packet factory layout receipt changed")
    raw, refs = payload(output / "screen-mode-u8.o", FUNCTION)
    checked_payload(raw, refs)
    original, original_refs = payload(output / ("original-" + FUNCTION + ".o"), FUNCTION)
    normalized, normalized_refs = payload(output / "normalized.o", FUNCTION)
    if original != normalized or original_refs != normalized_refs or refs != original_refs:
        raise ValueError("Wide-packet factory normalized payload changed")
    if sum(left != right for left, right in zip(struct.unpack(">180I", raw), struct.unpack(">180I", original))) != GUARDS:
        raise ValueError("Wide-packet factory closed-word count changed")
    if (output / "proposed-guards.csv").read_bytes().count(b"," + FUNCTION.encode() + b",") != GUARDS:
        raise ValueError("Wide-packet factory guard rows changed")
    for name in (
        "private-guest-v3.json", "private-native-v3.json", "private-caller-v3.json",
        "private-owner-image-v4.json", f"qualified-{OWNER}.o", "private-joint-linked.elf",
    ):
        if not (output / name).is_file():
            raise ValueError("Wide-packet factory prepared artifact missing: " + name)
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
            raise ValueError("Wide-packet factory live input changed: " + name)
    return baseline


def audit(root, output, installed=False):
    from tools.check_game_data_layout import audit_layout
    values = check_inputs(root, output, installed)
    path = root / "conker/build/conker.us.elf" if installed else output / "private-joint-linked.elf"
    actual = path.read_bytes()
    rom = (root / "conker/conker.us.bin").read_bytes()
    check_image(values["conker/build/conker.us.elf"], actual, rom)
    if sha(actual) != LINKED:
        raise ValueError("Wide-packet factory linked image changed")
    data = audit_layout(path, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Wide-packet factory protected data changed")
    old, _, old_other = load_elf_functions(str(output / "before-conker_build_conker.us.elf"), "mips-linux-gnu-objdump")
    new, _, new_other = load_elf_functions(str(path), "mips-linux-gnu-objdump")
    if old.keys() != new.keys() or old_other != new_other or {name for name in old if old[name] != new[name]} != {FUNCTION}:
        raise ValueError("Wide-packet factory changed another body")
    expected = Counter((name, fields[1], SIZE if name == FUNCTION else fields[2], *fields[3:]) for _, name, fields, _ in symbol_rows(values["conker/build/conker.us.elf"]))
    if expected != Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(actual)):
        raise ValueError("Wide-packet factory named definition changed")
    q = json.loads((output / "private-owner-image-v4.json").read_text())
    q.update(private_only=not installed, installed=installed, matching_credit=1 if installed else 0, protected_data=data)
    if installed:
        (output / "installed-audit.json").write_text(json.dumps(q, indent=2) + "\n")
    return q


