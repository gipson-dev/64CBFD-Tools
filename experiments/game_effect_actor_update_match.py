"""Effect-actor update callback: direct C bytes and complete qualification gates."""
from collections import Counter
import hashlib
import json
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset, same_functions, symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions


FUNCTION = "func_15154A88"
OWNER = "generated_17CAF0"
ENTRY = 0x15154A88
ROM = 0x181F38
BODY = SIZE = 520
WORDS = 130
FRAME = 24
SOURCE = "conker/src/game/generated_17CAF0.c"
OBJECT = "conker/build/src/game/generated_17CAF0.c.o"
ASM = "conker/asm/17CAF0.s"
BUILD = "conker/build/game-effect-actor-update-15154A88-match"
RAW_SHA = "91be33265a4774f1628ef1270a0b65f738e4cda19b54893d56ce2af3468daee5"
TRUTH_SHA = "d578acd5448e5f5d9ce53a5cc2a6326ae48702fb27acce539fc0889a516770e0"
BINDINGS = {
    12: [("R_MIPS_26", "sinf")],
    28: [("R_MIPS_HI16", "D_800BE9A4")],
    40: [("R_MIPS_LO16", "D_800BE9A4")],
}

DECLARATIONS = """extern f32 D_800BE9A4;
f32 sinf(f32);

"""
HEADERS = "#include <ultra64.h>\n\n" + DECLARATIONS
SELECTED = """/* Update a sine-scaled effect actor and report whether its lifetime remains active. */
s32 func_15154A88(u8 *actor) {
    f32 *payload = (f32 *)(actor + 0x170);
    f32 wave = sinf(*(f32 *)(actor + 0x17C));
    f32 scale = payload[1] * wave;

    *(f32 *)(actor + 0x18) = *(f32 *)(actor + 0x1C) = scale;
    actor[0x70] = (u8)((u8)payload[2] * wave);
    payload[0] -= D_800BE9A4;
    if (payload[0] <= 0.0f) {
        return 0;
    }
    payload[3] += payload[4] * D_800BE9A4;
    *(f32 *)(actor + 0x20) += *(f32 *)(actor + 0x50) * D_800BE9A4;
    *(f32 *)(actor + 0x24) += *(f32 *)(actor + 0x54) * D_800BE9A4;
    *(f32 *)(actor + 0x28) += *(f32 *)(actor + 0x58) * D_800BE9A4;
    return 1;
}
"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def payload(obj):
    return function_payload(obj, FUNCTION)


def checked_payload(raw, bindings):
    if len(raw) != BODY or sha(raw) != RAW_SHA or bindings != BINDINGS:
        raise ValueError("Effect-actor update payload or bindings changed")
    return raw, bindings


def recovered_owner(before):
    pragma = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_17CAF0/func_15154A88.s")'
    if before.count(pragma) != 1:
        raise ValueError("Effect-actor update predecessor changed")
    return before.replace(pragma, DECLARATIONS + SELECTED.rstrip(), 1)


def predict_image(before, truth):
    if len(truth) != SIZE or sha(truth) != TRUTH_SHA:
        raise ValueError("Effect-actor update retail payload changed")
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    if before[at:at + SIZE] != truth:
        raise ValueError("Effect-actor update predecessor image changed")
    result[at:at + SIZE] = truth
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predict_image(before, truth):
        raise ValueError("Effect-actor update complete image differs")
    expected = Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(before))
    observed = Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(actual))
    if expected != observed:
        raise ValueError("Effect-actor update named definitions changed")


NEW_GUARDS = []


def guard_manifest(before):
    prefix = (OWNER + "," + FUNCTION + ",").encode()
    if any(line.startswith(prefix) for line in before.splitlines()):
        raise ValueError("Effect-actor update unexpectedly has guards")
    return before


def before_path(output, name):
    return output / ("before-" + name.replace("/", "_"))


def verify_prepared(output):
    report = json.loads((output / "private-preparation.json").read_text())
    expected = (True, 0, WORDS, FRAME, 0, 3, True, 40, True, True)
    observed = (report["success"], report["matching_credit"], report["words"],
                report["frame"], report["guards"], report["bindings"],
                report["raw_C_byte_exact"], report["neighbors"],
                report["padded_owner_object_byte_identical"],
                report["entire_linked_image_byte_identical"])
    if observed != expected:
        raise ValueError("Effect-actor update preparation changed")
    selected = output / "selected-final.o"
    checked_payload(*payload(selected))
    if selected.read_bytes() == b"" or not (output / "qualified-padded.o").is_file():
        raise ValueError("Effect-actor update prepared objects missing")
    for name in ("private-guest-v1.json", "private-native-v1.json", "private-caller-v1.json"):
        if not json.loads((output / name).read_text())["success"]:
            raise ValueError("Effect-actor update qualification failed: " + name)
    return report


def check_inputs(root, output, installed=False):
    verify_prepared(output)
    names = (SOURCE, OBJECT, "conker/build/conker.us.elf",
             "conker/build/conker.us.map", "conker/retail_word_patches.us.csv")
    changes = {}
    if installed:
        changes = {SOURCE: (output / "proposed-generated_17CAF0.c").read_bytes(),
                   OBJECT: (output / "qualified-padded.o").read_bytes()}
    for name in names:
        expected = changes.get(name, before_path(output, name).read_bytes())
        if (root / name).read_bytes() != expected:
            raise ValueError("Effect-actor update live input changed: " + name)
    return {name: before_path(output, name).read_bytes() for name in names}


def audit(root, output, installed=False):
    from tools.check_game_data_layout import audit_layout
    values = check_inputs(root, output, installed)
    actual = (root / "conker/build/conker.us.elf").read_bytes()
    truth = before_path(output, "conker/conker.us.bin").read_bytes()[ROM:ROM + SIZE]
    check_image(values["conker/build/conker.us.elf"], actual, truth)
    old, _, old_other = load_elf_functions(str(before_path(output, "conker/build/conker.us.elf")),
                                            "mips-linux-gnu-objdump")
    new, _, new_other = load_elf_functions(str(root / "conker/build/conker.us.elf"),
                                            "mips-linux-gnu-objdump")
    if old != new or old_other != new_other:
        raise ValueError("Effect-actor update changed linked functions or addresses")
    protected = audit_layout(root / "conker/build/conker.us.elf", root / "conker")
    if (protected["exact"], protected["bytes"], protected["owner_count"],
            protected["different_bytes"]) != (True, 189088, 720, 0):
        raise ValueError("Effect-actor update protected data changed")
    report = {"success": True, "private_only": not installed,
              "installed": installed, "matching_credit": 1 if installed else 0,
              "words": WORDS, "frame": FRAME, "guards": 0, "neighbors": 40,
              "actual_Make_commands": 5, "actual_Make_object_equals_qualified": True,
              "entire_linked_image_byte_identical": True, "strict_exclusions": 0,
              "functions": len(old), "other_bodies_fixed": len(old) - 1,
              "all_function_addresses_fixed": True, "protected_data": protected}
    if installed:
        (output / "installed-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
