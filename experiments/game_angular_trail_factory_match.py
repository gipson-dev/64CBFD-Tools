"""Angular localized-trail factory bytes and complete qualification gates."""
from collections import Counter
import hashlib
import json
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions


BUILD = "conker/build/game-angular-trail-factory-15153F18-match"
BASELINE = "6169616442e3370f715b255f6db33fdffba7eb9b2aa6ea8bea645282cbf70f5f"
LINKED = "17ad20e1a039f88b9008b1b694447978cc68502dab29f74a51d17d47b5401c4c"
FUNCTION = "func_15153F18"
OWNER = "generated_17CAF0"
ENTRY = 0x15153F18
ROM = 0x1813C8
WORDS = 168
SIZE = WORDS * 4
FRAME = 184
RAW_FRAME = 200
GUARDS = 16
RAW_SHA = "842db97e986a881744d8c94aa402debbcabcfade28518ece6246a2a35c7e8d9b"
NORMALIZED_SHA = "820ec0ad3cdc593311eb877d8f12192740dd57f49c5127d91ee81e98b71ed161"
BINDINGS = {
    72: [("R_MIPS_26", "func_150ADA20")], 88: [("R_MIPS_HI16", "D_800A6000")],
    132: [("R_MIPS_LO16", "D_800A6000")], 136: [("R_MIPS_26", "func_150ADA20")],
    144: [("R_MIPS_26", "func_150ADA20")], 152: [("R_MIPS_26", "func_150ADA68")],
    272: [("R_MIPS_26", "func_15143794")], 280: [("R_MIPS_26", "func_150ADA68")],
    288: [("R_MIPS_26", "func_150ADA20")], 296: [("R_MIPS_26", "func_150ADA20")],
    304: [("R_MIPS_26", "func_150ADA68")], 312: [("R_MIPS_26", "func_150ADA20")],
    320: [("R_MIPS_26", "func_150ADA68")], 592: [("R_MIPS_26", "func_151DA6F8")],
}
HEADERS = """#include <ultra64.h>

typedef struct {
    s16 firstAngleBase;
    s16 firstAngleRange;
    s16 secondAngleBase;
    s16 secondAngleRange;
} AngularTrailInput;

typedef struct {
    f32 position[3];
    f32 timeBase;
    f32 timeRange;
    f32 scaleBase;
    f32 scaleRange;
    f32 radiusBase;
    f32 radiusRange;
    s16 countBase;
    s16 countRange;
    s16 requestSelectorBase;
    s16 requestSelectorRange;
    s16 durationBase;
    s16 durationRange;
    s16 modeBase;
    s16 modeRange;
    u8 selector;
    u8 private35[3];
    f32 opaqueChance;
    s16 firstValue;
    s16 secondValue;
    s32 requestValue;
} LocalizedTrailInput;

void func_15143794(s16, s16, f32, f32 *);
s32 func_150ADA20(void);
f32 func_150ADA68(void);
extern f32 D_800A6000;
u8 *func_151DA6F8(void *, void *, f32, s16, s32, f32, s32, s32,
                  f32, f32, s32, s32, s32, s16, s16, s32, s32, s32);
"""
SELECTED = """void func_15153F18(AngularTrailInput *arg0, LocalizedTrailInput *arg1,
                    s32 arg2, s32 arg3, s32 arg4) {
    f32 velocity[3];
    f32 temp_f20;
    f32 temp_f22;
    f32 temp_f24;
    s32 remaining;
    u32 secondRandom;
    u32 firstRandom;
    u32 requestRandom;
    u32 modeRandom;
    u32 durationRandom;

    remaining = (u32)func_150ADA20() % ((u32)arg1->countRange + 1U)
                + arg1->countBase;
    if (remaining != 0) {
        temp_f24 = D_800A6000;
        do {
            firstRandom = (u32)func_150ADA20();
            secondRandom = (u32)func_150ADA20();
            func_15143794(
                (s16)(firstRandom % ((u32)arg0->firstAngleRange + 1U)
                      + arg0->firstAngleBase),
                (s16)(secondRandom % ((u32)arg0->secondAngleRange + 1U)
                      + arg0->secondAngleBase),
                func_150ADA68() * arg1->radiusRange + arg1->radiusBase,
                velocity);
            temp_f22 = func_150ADA68();
            durationRandom = (u32)func_150ADA20();
            modeRandom = (u32)func_150ADA20();
            temp_f20 = func_150ADA68();
            requestRandom = (u32)func_150ADA20();
            func_151DA6F8(
                arg1, velocity,
                temp_f22 * arg1->scaleRange + arg1->scaleBase,
                (s16)(durationRandom % ((u32)arg1->durationRange + 1U) + arg1->durationBase),
                modeRandom % ((u32)arg1->modeRange + 1U) + arg1->modeBase,
                temp_f20 * arg1->timeRange + arg1->timeBase,
                requestRandom % ((u32)arg1->requestSelectorRange + 1U) + arg1->requestSelectorBase,
                func_150ADA68() < arg1->opaqueChance,
                temp_f24, temp_f24, 1, arg1->selector, arg2,
                arg1->firstValue, arg1->secondValue, arg1->requestValue,
                ((u8 *)&arg3)[3], arg4);
            remaining--;
        } while (remaining != 0);
    }
}

"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_payload(raw, bindings):
    if len(raw) != SIZE or sha(raw) != RAW_SHA or bindings != BINDINGS:
        raise ValueError("Angular-trail factory payload or bindings changed")
    return raw, bindings


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != "s32 func_15153F18() {\n    return 0;\n}":
        raise ValueError("Angular-trail factory predecessor body changed")
    anchor = "} LocalizedTrailInput;\n"
    if before.count(anchor) != 1:
        raise ValueError("Localized-trail type anchor changed")
    angular = ("\ntypedef struct {\n    s16 firstAngleBase;\n    s16 firstAngleRange;\n"
               "    s16 secondAngleBase;\n    s16 secondAngleRange;\n} AngularTrailInput;\n"
               "extern f32 D_800A6000;\nvoid func_15143794(s16, s16, f32, f32 *);\n")
    before = before.replace(anchor, anchor + angular, 1)
    lo, hi = function_span(before, FUNCTION)
    comment = "/* Emit angular localized trails from a complete live configuration. */\n"
    return before[:lo] + comment + SELECTED.rstrip() + before[hi:]


def predict(before, rom):
    if sha(before) != BASELINE:
        raise ValueError("Angular-trail factory image predecessor changed")
    out = bytearray(before)
    row, = [value for value in symbol_rows(before) if value[1] == FUNCTION]
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError("Angular-trail factory predecessor extent changed")
    at = elf_slot_offset(before, ENTRY, SIZE)
    out[at:at + SIZE] = rom[ROM:ROM + SIZE]
    struct.pack_into(">I", out, row[0] + 8, SIZE)
    return bytes(out)


def check_image(before, actual, rom):
    if actual != predict(before, rom):
        raise ValueError("Angular-trail factory entire image differs")


def expected_map(output):
    data = (output / "private-joint-linked.map").read_bytes()
    private = (BUILD.removeprefix("conker/") + f"/make-shadow-{OWNER}/src/game/{OWNER}.c.o").encode()
    if data.count(private) != 9:
        raise ValueError("Angular-trail factory map owner path changed")
    data = data.replace(private, f"build/src/game/{OWNER}.c.o".encode())
    private = (BUILD.removeprefix("conker/") + "/private-joint-linked.elf").encode()
    if data.count(private) != 1:
        raise ValueError("Angular-trail factory map output changed")
    return data.replace(private, b"build/conker.us.elf")


def verify_prepared(output):
    q = json.loads((output / "private-layout-v1.json").read_text())
    values = (q["words"], q["retail_frame"], q["raw_frame"], q["proposed_closed_normalizations"],
              q["raw_SHA256"], q["normalized_SHA256"], len(q["layouts"]))
    if values != (WORDS, FRAME, RAW_FRAME, GUARDS, RAW_SHA, NORMALIZED_SHA, 3):
        raise ValueError("Angular-trail layout receipt changed")
    raw, refs = checked_payload(*payload(output / "screen-v1.o", FUNCTION))
    original, original_refs = payload(output / ("original-" + FUNCTION + ".o"), FUNCTION)
    normalized, normalized_refs = payload(output / "normalized.o", FUNCTION)
    if original != normalized or original_refs != normalized_refs or refs != original_refs:
        raise ValueError("Angular-trail normalized payload changed")
    if sum(a != b for a, b in zip(struct.unpack(">168I", raw), struct.unpack(">168I", original))) != GUARDS:
        raise ValueError("Angular-trail closed-word count changed")
    if (output / "proposed-guards.csv").read_bytes().count(b"," + FUNCTION.encode() + b",") != GUARDS:
        raise ValueError("Angular-trail guard rows changed")
    for name in ("private-guest-v1.json", "private-native-v1.json", "private-caller-v1.json",
                 f"qualified-{OWNER}.o", "private-joint-linked.elf"):
        if not (output / name).is_file():
            raise ValueError("Angular-trail prepared artifact missing: " + name)
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
        changes["conker/build/conker.us.elf"] = predict(baseline["conker/build/conker.us.elf"],
                                                        (root / "conker/conker.us.bin").read_bytes())
        changes["conker/build/conker.us.map"] = expected_map(output)
        changes["conker/retail_word_patches.us.csv"] = (output / "proposed-guards.csv").read_bytes()
    for name, data in baseline.items():
        if (root / name).read_bytes() != changes.get(name, data):
            raise ValueError("Angular-trail live input changed: " + name)
    return baseline


def audit(root, output, installed=False):
    from tools.check_game_data_layout import audit_layout
    values = check_inputs(root, output, installed)
    path = root / "conker/build/conker.us.elf" if installed else output / "private-joint-linked.elf"
    actual, rom = path.read_bytes(), (root / "conker/conker.us.bin").read_bytes()
    check_image(values["conker/build/conker.us.elf"], actual, rom)
    if sha(actual) != LINKED:
        raise ValueError("Angular-trail linked image changed")
    protected = audit_layout(path, root / "conker")
    if not protected["exact"] or protected["bytes"] != 189088 or protected["owner_count"] != 720:
        raise ValueError("Angular-trail protected data changed")
    old, _, old_other = load_elf_functions(str(output / "before-conker_build_conker.us.elf"), "mips-linux-gnu-objdump")
    new, _, new_other = load_elf_functions(str(path), "mips-linux-gnu-objdump")
    if old.keys() != new.keys() or old_other != new_other or {name for name in old if old[name] != new[name]} != {FUNCTION}:
        raise ValueError("Angular-trail factory changed another body")
    expected = Counter((name, fields[1], SIZE if name == FUNCTION else fields[2], *fields[3:])
                       for _, name, fields, _ in symbol_rows(values["conker/build/conker.us.elf"]))
    if expected != Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(actual)):
        raise ValueError("Angular-trail named definition changed")
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
