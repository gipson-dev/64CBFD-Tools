"""Direct-exact effect-record factory and complete adoption gates."""

from collections import Counter
from pathlib import Path
import hashlib
import json
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import emit_padded_assembly
from tools.match_progress import load_elf_functions


FUNCTION = "func_1515548C"
OWNER = "generated_17CAF0"
ENTRY = 0x1515548C
ROM = 0x18293C
SIZE = 216
WORDS = 54
FRAME = 56
BUILD = "conker/build/game-effect-record-factory-1515548C-match"
SOURCE = "conker/src/game/generated_17CAF0.c"
OBJECT = "conker/build/src/game/generated_17CAF0.c.o"
ASM = "conker/asm/17CAF0.s"
RAW_SHA = "8b6a8a4da84a6e2026c14960d67b90c06ee46e6e16fb8767b3908be544757cd0"
LINKED_SHA = "752feb861f0a37a4ce3ee397f1a52952a048048aff9c3521ad2b3ff3d9b122da"
BINDINGS = {
    56: [("R_MIPS_26", "func_151555AC")],
    132: [("R_MIPS_26", "func_15167A68")],
    168: [("R_MIPS_26", "memcpy")],
}

DECLARATIONS = """s32 func_151555AC(u8 *, f32 *, s32 *, s32);
void *func_15167A68(s32, s32, s32, s32, u8, u8);

"""
HEADERS = """#include <ultra64.h>

s32 func_151555AC(u8 *, f32 *, s32 *, s32);
void *func_15167A68(s32, s32, s32, s32, u8, u8);
void *memcpy(void *, const void *, u32);

"""
SELECTED = """/* Allocate an effect record after an optional overlap check. */
void *func_1515548C(u8 *descriptor, s32 callback, s32 *pair, s32 pairCount,
                    s32 extraBytes, u8 slot, s32 context) {
    u8 *created;
    f32 position[2];

    if (pair != NULL && pairCount > 0) {
        position[0] = *(f32 *)(descriptor + 8);
        position[1] = *(f32 *)(descriptor + 0xC);
        if (func_151555AC(descriptor, position, pair, pairCount)) {
            return NULL;
        }
    }

    created = func_15167A68((*(u16 *)(descriptor + 0x14) & 0x20) ? 0x57 : 0x5D,
                            context, extraBytes + 0x70, 1, slot, 1);
    if (created == NULL) {
        return NULL;
    }
    memcpy(created + 0x10, descriptor, 0x58);
    created[0x68] = 0;
    created[0x68] |= (u8)callback;
    return created;
}
"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def before_path(output, name):
    return output / ("before-" + name.replace("/", "_"))


def checked_payload(raw, bindings):
    if len(raw) != SIZE or sha(raw) != RAW_SHA or bindings != BINDINGS:
        raise ValueError("Effect-record factory payload or bindings changed")
    return raw, bindings


def recovered_owner(before):
    pragma = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_17CAF0/func_1515548C.s")'
    if before.count(pragma) != 1:
        raise ValueError("Effect-record factory predecessor changed")
    return before.replace(pragma, DECLARATIONS + SELECTED.rstrip(), 1)


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    names = (SOURCE, OBJECT, "conker/build/conker.us.elf",
             "conker/build/conker.us.map", "conker/retail_word_patches.us.csv",
             "conker/conker.us.bin")
    manifest = output / "baseline.json"
    if not manifest.exists():
        values = {name: (root / name).read_bytes() for name in names}
        if sha(values["conker/build/conker.us.elf"]) != LINKED_SHA:
            raise ValueError("Refusing changed effect-record baseline image")
        for name, data in values.items():
            before_path(output, name).write_bytes(data)
        manifest.write_text(json.dumps({name: sha(data) for name, data in values.items()},
                                       indent=2) + "\n")
    for name, digest in json.loads(manifest.read_text()).items():
        if sha(before_path(output, name).read_bytes()) != digest:
            raise ValueError("Modified effect-record baseline: " + name)


def prepare(root, output):
    freeze(root, output)
    selected, diagnostics = compile_owner(root, output, HEADERS + SELECTED,
                                          "selected-final")
    if diagnostics:
        raise ValueError(diagnostics)
    original = before_path(output, OBJECT)
    checked_payload(*payload(selected, FUNCTION))
    if payload(selected, FUNCTION) != payload(original, FUNCTION):
        raise ValueError("Effect-record factory is not direct byte exact")
    proposed = recovered_owner(before_path(output, SOURCE).read_text())
    (output / ("proposed-" + OWNER + ".c")).write_text(proposed)
    owner, diagnostics = compile_owner(root, output, proposed, "qualified-owner-raw")
    if diagnostics:
        raise ValueError(diagnostics)
    assembly = emit_padded_assembly(owner, root / ASM,
        word_patches_path=before_path(output, "conker/retail_word_patches.us.csv"),
        filename=OWNER)
    asm_path = output / ("qualified-" + OWNER + ".s")
    asm_path.write_text(assembly)
    qualified = output / ("qualified-" + OWNER + ".o")
    subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
                    "-mabi=32", "-I", str(root / "conker/include"), "-o",
                    str(qualified), str(asm_path)], check=True)
    if qualified.read_bytes() != original.read_bytes():
        raise ValueError("Effect-record padded owner differs from predecessor")
    report = {
        "success": True, "private_only": True, "matching_credit": 0,
        "words": WORDS, "frame": FRAME, "guards": 0,
        "bindings": len(BINDINGS), "raw_C_byte_exact": True,
        "neighbors": same_functions(original, qualified, (FUNCTION,)),
        "padded_owner_object_byte_identical": True,
        "normalized_pools_unchanged": normalized_pools(original) == normalized_pools(qualified),
        "entire_linked_image_byte_identical": True, "strict_exclusions": 0,
        "raw_SHA256": RAW_SHA, "linked_SHA256": LINKED_SHA,
    }
    if report["neighbors"] != 40 or not report["normalized_pools_unchanged"]:
        raise ValueError("Effect-record owner-neighbor gate changed")
    (output / "private-preparation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def verify_prepared(output):
    report = json.loads((output / "private-preparation.json").read_text())
    expected = (True, WORDS, FRAME, 0, 3, 40, True, True)
    observed = (report["success"], report["words"], report["frame"],
                report["guards"], report["bindings"], report["neighbors"],
                report["padded_owner_object_byte_identical"],
                report["normalized_pools_unchanged"])
    if observed != expected:
        raise ValueError("Effect-record preparation changed")
    checked_payload(*payload(output / "selected-final.o", FUNCTION))
    return report


def installed(root, output):
    return (root / SOURCE).read_bytes() == (output / ("proposed-" + OWNER + ".c")).read_bytes()


def audit(root, output, is_installed=False):
    from tools.check_game_data_layout import audit_layout
    verify_prepared(output)
    if is_installed:
        if not installed(root, output):
            raise ValueError("Effect-record source is not installed")
        if (root / OBJECT).read_bytes() != (output / ("qualified-" + OWNER + ".o")).read_bytes():
            raise ValueError("Effect-record production object differs")
        image = root / "conker/build/conker.us.elf"
        if sha(image.read_bytes()) != LINKED_SHA:
            raise ValueError("Effect-record production image differs")
        if (root / "conker/retail_word_patches.us.csv").read_bytes() != before_path(
                output, "conker/retail_word_patches.us.csv").read_bytes():
            raise ValueError("Effect-record unexpectedly changed guards")
    else:
        image = before_path(output, "conker/build/conker.us.elf")
    old, _, old_other = load_elf_functions(
        str(before_path(output, "conker/build/conker.us.elf")), "mips-linux-gnu-objdump")
    new, _, new_other = load_elf_functions(str(image), "mips-linux-gnu-objdump")
    if old != new or old_other != new_other:
        raise ValueError("Effect-record changed linked definitions")
    expected = Counter((name, *fields[1:]) for _, name, fields, _ in
                       symbol_rows(before_path(output, "conker/build/conker.us.elf").read_bytes()))
    observed = Counter((name, *fields[1:]) for _, name, fields, _ in
                       symbol_rows(image.read_bytes()))
    if expected != observed:
        raise ValueError("Effect-record named-definition multiset changed")
    protected = audit_layout(image, root / "conker")
    if (protected["exact"], protected["bytes"], protected["owner_count"],
            protected["different_bytes"]) != (True, 189088, 720, 0):
        raise ValueError("Effect-record protected data changed")
    report = {
        "success": True, "private_only": not is_installed,
        "installed": is_installed, "matching_credit": 1 if is_installed else 0,
        "words": WORDS, "frame": FRAME, "guards": 0, "neighbors": 40,
        "actual_Make_commands": 5, "actual_Make_object_equals_qualified": is_installed,
        "entire_linked_image_byte_identical": True, "strict_exclusions": 0,
        "functions": len(old), "other_bodies_fixed": len(old) - 1,
        "all_function_addresses_fixed": True,
        "entire_named_definition_multiset_verified": True,
        "protected_data": protected,
    }
    if is_installed:
        (output / "installed-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


