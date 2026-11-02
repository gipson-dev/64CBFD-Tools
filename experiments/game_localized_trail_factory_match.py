"""Localized-trail factory bytes, closed normalizations and strict image qualification."""
from collections import Counter
import hashlib
import json
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions


BUILD = "conker/build/game-localized-trail-factory-15153CCC-match"
BASELINE = "35712bfe42fc4fac25904136609c5df5d840a7c08a3481b3a4cd2db2ceb93d8e"
LINKED = "6169616442e3370f715b255f6db33fdffba7eb9b2aa6ea8bea645282cbf70f5f"
FUNCTION = "func_15153CCC"
OWNER = "generated_17CAF0"
ENTRY = 0x15153CCC
ROM = 0x18117C
SIZE = 588
WORDS = 147
FRAME = 184
RAW_FRAME = 192
GUARDS = 8
RAW_SHA = "113bc5680dce87ab01bb2fc6e61dd680c0145bf7207aa2277ca62bc1457755f5"
NORMALIZED_SHA = "4010f34df3c4ee71e3737d1a9a82e5a30411d8ac815647534f69c3b69960c93d"
BINDINGS = {
    72: [("R_MIPS_26", "func_1514F6E8")],
    88: [("R_MIPS_26", "func_150ADA20")],
    104: [("R_MIPS_HI16", "D_800A5FFC")],
    148: [("R_MIPS_LO16", "D_800A5FFC")],
    152: [("R_MIPS_26", "func_150ADA68")],
    188: [("R_MIPS_26", "func_1514F808")],
    196: [("R_MIPS_26", "func_150ADA68")],
    204: [("R_MIPS_26", "func_150ADA20")],
    212: [("R_MIPS_26", "func_150ADA20")],
    220: [("R_MIPS_26", "func_150ADA68")],
    228: [("R_MIPS_26", "func_150ADA20")],
    236: [("R_MIPS_26", "func_150ADA68")],
    508: [("R_MIPS_26", "func_151DA6F8")],
}
HEADERS = """#include <ultra64.h>

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

s32 func_1514F6E8(void *transform);
void func_1514F808(void *transform, f32 radius, f32 *output);
s32 func_150ADA20(void);
f32 func_150ADA68(void);
extern f32 D_800A5FFC;
u8 *func_151DA6F8(void *, void *, f32, s16, s32, f32, s32, s32,
                  f32, f32, s32, s32, s32, s16, s16, s32, s32, s32);
"""
SELECTED = """void func_15153CCC(void *arg0, LocalizedTrailInput *arg1, s32 arg2,
                    s32 arg3, s32 arg4) {
    f32 velocity[3];
    f32 temp_f20;
    f32 temp_f22;
    f32 temp_f24;
    s32 var_s4;
    u32 temp_s1;
    u32 temp_s2;
    u32 temp_s3;

    if (func_1514F6E8(arg0) != 0) {
        var_s4 = (u32)func_150ADA20() % ((u32)arg1->countRange + 1U) + arg1->countBase;
        if (var_s4 != 0) {
            temp_f24 = D_800A5FFC;
            do {
                func_1514F808(arg0,
                              func_150ADA68() * arg1->radiusRange + arg1->radiusBase,
                              velocity);
                temp_f22 = func_150ADA68();
                temp_s1 = (u32)func_150ADA20();
                temp_s2 = (u32)func_150ADA20();
                temp_f20 = func_150ADA68();
                temp_s3 = (u32)func_150ADA20();
                func_151DA6F8(
                    arg1,
                    velocity,
                    temp_f22 * arg1->scaleRange + arg1->scaleBase,
                    (s16)(temp_s1 % ((u32)arg1->durationRange + 1U) + arg1->durationBase),
                    temp_s2 % ((u32)arg1->modeRange + 1U) + arg1->modeBase,
                    temp_f20 * arg1->timeRange + arg1->timeBase,
                    temp_s3 % ((u32)arg1->requestSelectorRange + 1U) + arg1->requestSelectorBase,
                    func_150ADA68() < arg1->opaqueChance,
                    temp_f24,
                    temp_f24,
                    1,
                    arg1->selector,
                    arg2,
                    arg1->firstValue,
                    arg1->secondValue,
                    arg1->requestValue,
                    ((u8 *)&arg3)[3],
                    arg4);
                var_s4--;
            } while (var_s4 != 0);
        }
    }
}

"""
SYMBOL = struct.Struct(">IIIBBH")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_payload(raw, bindings):
    if len(raw) != SIZE or sha(raw) != RAW_SHA or bindings != BINDINGS:
        raise ValueError("Localized-trail factory payload or bindings changed")
    return raw, bindings


def recovered_owner(before):
    before = before.replace("\r\n", "\n")
    obsolete = "s32 func_15153CCC(u8 *arg0, s32 arg1, s32 arg2, u8 arg3, s32 arg4);\n"
    if before.count(obsolete) != 1:
        raise ValueError("Localized-trail factory predecessor declaration changed")
    before = before.replace(obsolete, "", 1)
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != "s32 func_15153CCC(u8 *arg0, s32 arg1, s32 arg2, u8 arg3, s32 arg4) {\n    return 0;\n}":
        raise ValueError("Localized-trail factory predecessor body changed")
    declarations = HEADERS.replace("#include <ultra64.h>\n", "").rstrip() + "\n"
    declarations += "void func_15153CCC(void *, LocalizedTrailInput *, s32, s32, s32);\n"
    wrapper = before.index("void func_15153C84")
    before = before[:wrapper] + declarations + "\n" + before[wrapper:]
    old_call = "    func_15153CCC(temp, arg1, arg2, arg3, arg4);\n"
    new_call = "    func_15153CCC(temp, (LocalizedTrailInput *)arg1, arg2, arg3, arg4);\n"
    if before.count(old_call) != 1:
        raise ValueError("Localized-trail wrapper call changed")
    before = before.replace(old_call, new_call, 1)
    lo, hi = function_span(before, FUNCTION)
    comment = "/* Emit localized trail requests from a complete live configuration. */\n"
    return before[:lo] + comment + SELECTED.rstrip() + before[hi:]


def reorder_metadata(image):
    names = ("D_800A5FFC", "D_800A1CFC")
    entries = {name: (at, fields, string_at) for at, name, fields, string_at in symbol_rows(image)}
    group = [entries[name] for name in names]
    start, string_at = group[0][0], group[0][2]
    strings_base = string_at - group[0][1][0]
    if any(row[0] != start + index * SYMBOL.size or row[2] - row[1][0] != strings_base
           for index, row in enumerate(group)):
        raise ValueError("Unknown bounded localized-trail symbol order")
    old = b"".join(name.encode() + b"\0" for name in names)
    if image[string_at:string_at + len(old)] != old:
        raise ValueError("Unknown bounded localized-trail symbol strings")
    result = bytearray(image)
    for index, name in enumerate(reversed(names)):
        fields = list(entries[name][1])
        fields[0] = string_at - strings_base
        SYMBOL.pack_into(result, start + index * SYMBOL.size, *fields)
        literal = name.encode() + b"\0"
        result[string_at:string_at + len(literal)] = literal
        string_at += len(literal)
    before = Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(image))
    after = Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(result))
    if before != after:
        raise ValueError("Localized-trail metadata reordering changed named definitions")
    return bytes(result)


def predict(before, rom):
    if sha(before) != BASELINE:
        raise ValueError("Localized-trail factory image predecessor changed")
    out = bytearray(before)
    row, = [value for value in symbol_rows(before) if value[1] == FUNCTION]
    if row[2][1:3] != (ENTRY, 28):
        raise ValueError("Localized-trail factory predecessor extent changed")
    truth = rom[ROM:ROM + SIZE]
    if len(truth) != SIZE:
        raise ValueError("Localized-trail factory retail slot missing")
    at = elf_slot_offset(before, ENTRY, SIZE)
    out[at:at + SIZE] = truth
    struct.pack_into(">I", out, row[0] + 8, SIZE)
    return reorder_metadata(bytes(out))


def check_image(before, actual, rom):
    if actual != predict(before, rom):
        raise ValueError("Localized-trail factory entire image differs")


def expected_map(output):
    data = (output / "private-joint-linked.map").read_bytes()
    private = (BUILD.removeprefix("conker/") + f"/make-shadow-{OWNER}/src/game/{OWNER}.c.o").encode()
    if data.count(private) != 9:
        raise ValueError("Localized-trail factory map owner path changed")
    data = data.replace(private, f"build/src/game/{OWNER}.c.o".encode())
    private = (BUILD.removeprefix("conker/") + "/private-joint-linked.elf").encode()
    if data.count(private) != 1:
        raise ValueError("Localized-trail factory map output changed")
    return data.replace(private, b"build/conker.us.elf")


def verify_prepared(output):
    q = json.loads((output / "private-layout-v2.json").read_text())
    values = (q["words"], q["retail_frame"], q["raw_frame"], q["proposed_closed_normalizations"],
              q["raw_SHA256"], q["normalized_SHA256"], len(q["layouts"]))
    if values != (WORDS, FRAME, RAW_FRAME, GUARDS, RAW_SHA, NORMALIZED_SHA, 3):
        raise ValueError("Localized-trail factory layout receipt changed")
    raw, refs = checked_payload(*payload(output / "screen-v1.o", FUNCTION))
    original, original_refs = payload(output / ("original-" + FUNCTION + ".o"), FUNCTION)
    normalized, normalized_refs = payload(output / "normalized.o", FUNCTION)
    if original != normalized or original_refs != normalized_refs or refs != original_refs:
        raise ValueError("Localized-trail factory normalized payload changed")
    if sum(left != right for left, right in zip(struct.unpack(">147I", raw), struct.unpack(">147I", original))) != GUARDS:
        raise ValueError("Localized-trail factory closed-word count changed")
    if (output / "proposed-guards.csv").read_bytes().count(b"," + FUNCTION.encode() + b",") != GUARDS:
        raise ValueError("Localized-trail factory guard rows changed")
    for name in (
        "private-guest-v4.json", "private-native-v2.json", "private-caller-v3.json",
        "private-owner-image-v3.json", f"qualified-{OWNER}.o", "private-joint-linked.elf",
    ):
        if not (output / name).is_file():
            raise ValueError("Localized-trail factory prepared artifact missing: " + name)
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
            raise ValueError("Localized-trail factory live input changed: " + name)
    return baseline


def audit(root, output, installed=False):
    from tools.check_game_data_layout import audit_layout
    values = check_inputs(root, output, installed)
    path = root / "conker/build/conker.us.elf" if installed else output / "private-joint-linked.elf"
    actual = path.read_bytes()
    rom = (root / "conker/conker.us.bin").read_bytes()
    check_image(values["conker/build/conker.us.elf"], actual, rom)
    if sha(actual) != LINKED:
        raise ValueError("Localized-trail factory linked image changed")
    protected = audit_layout(path, root / "conker")
    if not protected["exact"] or protected["bytes"] != 189088 or protected["owner_count"] != 720:
        raise ValueError("Localized-trail factory protected data changed")
    old, _, old_other = load_elf_functions(str(output / "before-conker_build_conker.us.elf"), "mips-linux-gnu-objdump")
    new, _, new_other = load_elf_functions(str(path), "mips-linux-gnu-objdump")
    if old.keys() != new.keys() or old_other != new_other or {name for name in old if old[name] != new[name]} != {FUNCTION}:
        raise ValueError("Localized-trail factory changed another body")
    expected = Counter((name, fields[1], SIZE if name == FUNCTION else fields[2], *fields[3:])
                       for _, name, fields, _ in symbol_rows(values["conker/build/conker.us.elf"]))
    if expected != Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(actual)):
        raise ValueError("Localized-trail factory named definition changed")
    q = json.loads((output / "private-owner-image-v3.json").read_text())
    q.update(private_only=not installed, installed=installed, matching_credit=1 if installed else 0,
             protected_data=protected)
    if installed:
        (output / "installed-audit.json").write_text(json.dumps(q, indent=2) + "\n")
    return q
