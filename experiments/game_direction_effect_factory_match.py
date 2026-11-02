"""Directional-effect factory bytes and complete qualification gates."""
from collections import Counter
import hashlib
import json
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions


BUILD = "conker/build/game-direction-effect-factory-15154684-match"
BASELINE = "17ad20e1a039f88b9008b1b694447978cc68502dab29f74a51d17d47b5401c4c"
LINKED = "752feb861f0a37a4ce3ee397f1a52952a048048aff9c3521ad2b3ff3d9b122da"
FUNCTION = "func_15154684"
OWNER = "generated_17CAF0"
ENTRY = 0x15154684
ROM = 0x181B34
WORDS = 128
SIZE = WORDS * 4
FRAME = 144
RAW_FRAME = 152
GUARDS = 31
RAW_SHA = "65f8717db56dd0fe17874adab0d163cd4834e2ce5a0313ad2ee664e2e875a621"
NORMALIZED_SHA = "3e1ea91a5ac5d8dbab21726da74374f5b34d7d5699677b7304993664d88a1b8a"
RAW_BINDINGS = {
    56: [("R_MIPS_26", "func_150ADA20")],
    116: [("R_MIPS_26", "func_150ADA20")], 124: [("R_MIPS_26", "func_150ADA20")],
    132: [("R_MIPS_26", "func_150ADA68")], 220: [("R_MIPS_26", "func_15143794")],
    228: [("R_MIPS_26", "func_150ADA68")], 236: [("R_MIPS_26", "func_150ADA20")],
    244: [("R_MIPS_26", "func_150ADA20")], 252: [("R_MIPS_26", "func_150ADA68")],
    260: [("R_MIPS_26", "func_150ADA68")], 444: [("R_MIPS_26", "func_151C5F44")],
}
RETAIL_BINDINGS = dict(RAW_BINDINGS)
RETAIL_BINDINGS[60] = RETAIL_BINDINGS.pop(56)

TYPE_DECL = """typedef struct {
    s16 countBase;
    s16 countRange;
    void *providerType;
    u8 private8[2];
    s16 secondAngleBase;
    s16 privateC;
    s16 secondAngleRange;
    f32 radiusBase;
    f32 radiusRange;
    f32 scaleBase;
    f32 scaleRange;
    f32 *mode;
    u8 selectorBase;
    u8 selectorRange;
    s16 durationBase;
    s16 durationRange;
    u8 private2A[2];
    f32 timeBase;
    f32 timeRange;
    f32 opaqueChance;
    s32 requestValue;
} DirectionEffectInput;
void func_151C5F44(void *, f32 *, f32, f32 *, s32, s32, f32, s32,
                  s32, s32, s32);

"""

HEADERS = """#include <ultra64.h>

""" + TYPE_DECL + """s32 func_150ADA20(void);
f32 func_150ADA68(void);
void func_15143794(s16, s16, f32, f32 *);
"""

SELECTED = """void func_15154684(DirectionEffectInput *arg0, s32 arg1, s32 arg2) {
    f32 direction[3];
    f32 scaleRandom;
    f32 timeRandom;
    s32 remaining;
    u32 secondAngleRandom;
    u32 durationRandom;
    u32 firstAngleRandom;
    u32 selectorRandom;

    remaining = (u32)func_150ADA20() % ((u32)arg0->countRange + 1U)
                + arg0->countBase;
    if (remaining > 0) {
        do {
            firstAngleRandom = (u32)func_150ADA20();
            secondAngleRandom = (u32)func_150ADA20();
            func_15143794(
                (s16)(firstAngleRandom & 0xFF),
                (s16)(secondAngleRandom % ((u32)arg0->secondAngleRange + 1U)
                      + arg0->secondAngleBase),
                func_150ADA68() * arg0->radiusRange + arg0->radiusBase,
                direction);
            scaleRandom = func_150ADA68();
            selectorRandom = (u32)func_150ADA20();
            durationRandom = (u32)func_150ADA20();
            timeRandom = func_150ADA68();
            func_151C5F44(
                arg0->providerType,
                direction,
                scaleRandom * arg0->scaleRange + arg0->scaleBase,
                arg0->mode,
                selectorRandom % ((u32)arg0->selectorRange + 1U)
                    + arg0->selectorBase,
                durationRandom % ((u32)arg0->durationRange + 1U)
                    + arg0->durationBase,
                timeRandom * arg0->timeRange + arg0->timeBase,
                func_150ADA68() < arg0->opaqueChance,
                arg0->requestValue,
                arg1 & 0xFF,
                arg2);
            remaining--;
        } while (remaining > 0);
    }
}

"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_payload(raw, bindings):
    if len(raw) != SIZE or sha(raw) != RAW_SHA or bindings != RAW_BINDINGS:
        raise ValueError("Directional-effect factory payload or bindings changed")
    return raw, bindings


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != "s32 func_15154684() {\n    return 0;\n}":
        raise ValueError("Directional-effect factory predecessor body changed")
    comment = "/* Emit randomized directional effects from a complete live configuration. */\n"
    return before[:lo] + TYPE_DECL + comment + SELECTED.rstrip() + before[hi:]


def predict(before, rom):
    if sha(before) != BASELINE:
        raise ValueError("Directional-effect factory image predecessor changed")
    out = bytearray(before)
    row, = [value for value in symbol_rows(before) if value[1] == FUNCTION]
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError("Directional-effect factory predecessor extent changed")
    at = elf_slot_offset(before, ENTRY, SIZE)
    out[at:at + SIZE] = rom[ROM:ROM + SIZE]
    struct.pack_into(">I", out, row[0] + 8, SIZE)
    return bytes(out)


def check_image(before, actual, rom):
    if actual != predict(before, rom):
        raise ValueError("Directional-effect factory entire image differs")


def expected_map(output):
    data = (output / "private-joint-linked.map").read_bytes()
    private = (BUILD.removeprefix("conker/") + f"/make-shadow-{OWNER}/src/game/{OWNER}.c.o").encode()
    if data.count(private) != 9:
        raise ValueError("Directional-effect factory map owner path changed")
    data = data.replace(private, f"build/src/game/{OWNER}.c.o".encode())
    private = (BUILD.removeprefix("conker/") + "/private-joint-linked.elf").encode()
    if data.count(private) != 1:
        raise ValueError("Directional-effect factory map output changed")
    return data.replace(private, b"build/conker.us.elf")


def verify_prepared(output):
    q = json.loads((output / "private-layout-v1.json").read_text())
    values = (q["words"], q["retail_frame"], q["raw_frame"], q["proposed_closed_normalizations"],
              q["raw_SHA256"], q["normalized_SHA256"], len(q["layouts"]))
    if values != (WORDS, FRAME, RAW_FRAME, GUARDS, RAW_SHA, NORMALIZED_SHA, 3):
        raise ValueError("Directional-effect layout receipt changed")
    raw, refs = checked_payload(*payload(output / "screen-v1.o", FUNCTION))
    original, original_refs = payload(output / ("original-" + FUNCTION + ".o"), FUNCTION)
    normalized, normalized_refs = payload(output / "normalized.o", FUNCTION)
    if original != normalized or original_refs != normalized_refs or original_refs != RETAIL_BINDINGS:
        raise ValueError("Directional-effect normalized payload changed")
    if refs != RAW_BINDINGS:
        raise ValueError("Directional-effect raw bindings changed")
    if sum(a != b for a, b in zip(struct.unpack(">128I", raw), struct.unpack(">128I", original))) != GUARDS:
        raise ValueError("Directional-effect closed-word count changed")
    if (output / "proposed-guards.csv").read_bytes().count(b"," + FUNCTION.encode() + b",") != GUARDS:
        raise ValueError("Directional-effect guard rows changed")
    for name in ("private-guest-v1.json", "private-native-v1.json", "private-caller-v1.json",
                 "native_harness_v1.c", f"qualified-{OWNER}.o", "private-joint-linked.elf"):
        if not (output / name).is_file():
            raise ValueError("Directional-effect prepared artifact missing: " + name)
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
        changes["conker/build/conker.us.elf"] = predict(
            baseline["conker/build/conker.us.elf"], (root / "conker/conker.us.bin").read_bytes())
        changes["conker/build/conker.us.map"] = expected_map(output)
        changes["conker/retail_word_patches.us.csv"] = (output / "proposed-guards.csv").read_bytes()
    for name, data in baseline.items():
        if (root / name).read_bytes() != changes.get(name, data):
            raise ValueError("Directional-effect live input changed: " + name)
    return baseline


def audit(root, output, installed=False):
    from tools.check_game_data_layout import audit_layout
    values = check_inputs(root, output, installed)
    path = root / "conker/build/conker.us.elf" if installed else output / "private-joint-linked.elf"
    actual, rom = path.read_bytes(), (root / "conker/conker.us.bin").read_bytes()
    check_image(values["conker/build/conker.us.elf"], actual, rom)
    if sha(actual) != LINKED:
        raise ValueError("Directional-effect linked image changed")
    protected = audit_layout(path, root / "conker")
    if not protected["exact"] or protected["bytes"] != 189088 or protected["owner_count"] != 720:
        raise ValueError("Directional-effect protected data changed")
    old, _, old_other = load_elf_functions(
        str(output / "before-conker_build_conker.us.elf"), "mips-linux-gnu-objdump")
    new, _, new_other = load_elf_functions(str(path), "mips-linux-gnu-objdump")
    if old.keys() != new.keys() or old_other != new_other or {
            name for name in old if old[name] != new[name]} != {FUNCTION}:
        raise ValueError("Directional-effect factory changed another body")
    expected = Counter((name, fields[1], SIZE if name == FUNCTION else fields[2], *fields[3:])
                       for _, name, fields, _ in symbol_rows(values["conker/build/conker.us.elf"]))
    if expected != Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(actual)):
        raise ValueError("Directional-effect named definition changed")
    q = json.loads((output / "private-owner-build-v1.json").read_text())
    q.update(private_only=not installed, installed=installed, matching_credit=1 if installed else 0,
             strict_whole_image_prediction=True, strict_exclusions=0,
             functions=len(old), other_bodies_fixed=len(old) - 1,
             all_function_addresses_fixed=True, entire_named_definition_multiset_verified=True,
             protected_data=protected)
    q.pop("strict_whole_image_pending", None)
    q.pop("guest_native_caller_gates_pending", None)
    if installed:
        (output / "installed-audit.json").write_text(json.dumps(q, indent=2) + "\n")
    else:
        (output / "private-owner-image-v1.json").write_text(json.dumps(q, indent=2) + "\n")
    return q


if __name__ == "__main__":
    from pathlib import Path
    root = Path.cwd()
    print(json.dumps(audit(root, root / BUILD), indent=2))
