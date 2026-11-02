"""Qualify the recovered matrix-pair resolver for a guarded retail match."""

import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset,
    symbol_rows,
)
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.match_progress import load_elf_functions


FUNCTION = "func_15031070"
OWNER = "generated_5D2C0"
RODATA_SYMBOL = "jtbl_80096F40_game"
ENTRY = 0x15031070
ROM = 0x5E520
SIZE = 340
RAW_SIZE = 336
BUILD = "conker/build/game-matrix-pair-resolver-15031070-match"

RAW_OBJECT_SHA = "c819f3f1a29e2d52da2745a090d37037ee51515f3cc9f0eaf16469022b9c04cf"
RAW_SLOT_SHA = "ed3686a43ce4b38e18ca8bb89056c19b06dcac9c203b705ee6cd98e888e38ea0"
RAW_LINKED_SHA = "3bce84735473b6d019c5ccf1fce00fa628d5247b7e2c91cc8b6b5b5c8ab4e07d"
RETAIL_SHA = "35fc6072ee135716bf0fe7ddf7154f23df68fb1532333e84d01e88a01d6b62ac"
RETAIL_TEMPLATE_SHA = "13f433101420fbed109a4f5d42a908755920562889737e19f45418451f77e26f"
QUALIFIED_OWNER_SHA = "717f411f525b93365de5cc2302afe2923ba990fea6ee93ba6e09bcce164f1d7c"
EXPECTED_ELF_SHA = "0e1cc15dcf288623c7ad505aad3b4cd4ad8b1af762b5221f90c3578c398b32ca"

PATHS = {
    "source": "conker/src/game/generated_5D2C0.c",
    "object": "conker/build/src/game/generated_5D2C0.c.o",
    "elf": "conker/build/conker.us.elf",
    "map": "conker/build/conker.us.map",
    "linker": "conker/build/conker.ld",
    "guards": "conker/retail_word_patches.us.csv",
    "asm": "conker/asm/5D2C0.s",
    "progress": "conker/progress.csv",
    "rom": "conker/conker.us.bin",
}

BASELINE = {
    "source": "5123677fb6b17a9ab2d56787c03406ebaa0783d83d0a26e98b7815424388f34c",
    "object": "7926648ac7ebef6535b10eaf0348a14c4c967f537099677f832f369a7f5d2619",
    "elf": "f930a85c4640fb0f36cac1750284d15863164fd5d4140010a99dd94a9f6ceb04",
    "map": "4ceeb40962070eb01cdc286937fdd209862def2bee87dbe33b6f8b7bd6912b38",
    "linker": "6479ca7cef48dc77d746c16afcc244de6bfb80c6789ba79a03d6f110e42a98d5",
    "guards": "6f57886c6dc2b3e55ff910d65423c74e65223d9a1154753d2edf11f7db14f780",
    "asm": "fae7f4cef62e47f676f42bfc5998932f92f0b807b6fb694a3000d7a15ae2074d",
    "progress": "96a7f15ab5207027a204f795e91b8f9f3453482ce4ec4d47bd8bcb4b5a305502",
    "rom": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
}

CANDIDATE_BINDINGS = {
    0x02C: [("R_MIPS_HI16", "D_800BE9C0")],
    0x030: [("R_MIPS_LO16", "D_800BE9C0")],
    0x07C: [("R_MIPS_HI16", "D_800BE9C0")],
    0x080: [("R_MIPS_LO16", "D_800BE9C0")],
    0x0C4: [("R_MIPS_26", "func_1503195C")],
    0x0E4: [("R_MIPS_26", FUNCTION)],
}

RETAIL_BINDINGS = {
    0x02C: [("R_MIPS_HI16", "D_800BE9C0")],
    0x030: [("R_MIPS_LO16", "D_800BE9C0")],
    0x07C: [("R_MIPS_HI16", "D_800BE9C0")],
    0x080: [("R_MIPS_LO16", "D_800BE9C0")],
    0x0C8: [("R_MIPS_26", "func_1503195C")],
    0x0E8: [("R_MIPS_26", FUNCTION)],
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def before_path(output, key):
    return output / ("before-" + key)


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    manifest = output / "baseline.json"
    if not manifest.exists():
        values = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: digest(data) for key, data in values.items()}
        if hashes != BASELINE:
            raise ValueError("Changed matrix-pair baseline: " + repr(hashes))
        for key, data in values.items():
            before_path(output, key).write_bytes(data)
        manifest.write_text(json.dumps(BASELINE, indent=2) + "\n")
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError("Modified matrix-pair baseline manifest")
    for key, expected in BASELINE.items():
        if digest(before_path(output, key).read_bytes()) != expected:
            raise ValueError("Modified matrix-pair frozen input: " + key)
    return {key: before_path(output, key) for key in PATHS}


def source_slot(obj):
    raw, bindings = payload(obj, FUNCTION)
    if (len(raw), digest(raw), bindings) != (RAW_SIZE, RAW_OBJECT_SHA, CANDIDATE_BINDINGS):
        raise ValueError("Matrix-pair compiler payload changed")
    slot = raw + bytes(SIZE - len(raw))
    if digest(slot) != RAW_SLOT_SHA:
        raise ValueError("Matrix-pair compiler slot changed")
    return raw, bindings


def retail_slots(rom):
    linked = rom[ROM:ROM + SIZE]
    if (len(linked), digest(linked)) != (SIZE, RETAIL_SHA):
        raise ValueError("Matrix-pair retail slot changed")
    template = bytearray(linked)
    for offset, rows in RETAIL_BINDINGS.items():
        word = struct.unpack_from(">I", template, offset)[0]
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", template, offset, word & mask)
    if digest(template) != RETAIL_TEMPLATE_SHA:
        raise ValueError("Matrix-pair retail relocation template changed")
    return linked, bytes(template)


def guard_rows():
    note = "Normalize matrix-pair resolver key lifetime and recursive success schedule"
    specs = (
        (0x03C, 0x1000003F, 0x10000040, None, False),
        (0x06C, 0x10000032, 0x10000033, None, False),
        (0x0A8, 0x10000023, 0x10000024, None, False),
        (0x0B0, 0x9625001E, 0x9622001E, None, False),
        (0x0B4, 0x50A00019, 0x5040001A, None, False),
        (0x0BC, 0x8FA40024, 0x8FA40024, 0x00402825, False),
        (0x104, 0x24020001, 0x24020001, None, True),
        (0x110, 0x1000000A, 0xAE0F0000, None, False),
        (0x114, 0xAE0F0000, 0x1000000A, 0x24020001, False),
    )
    return [{
        "filename": OWNER,
        "function": FUNCTION,
        "offset": "0x%03X" % offset,
        "expected": "0x%08X" % expected,
        "replacement": "0x%08X" % replacement,
        "expected_relocations": "-",
        "replacement_relocations": "-",
        "note": note,
        "insert_after": "" if inserted is None else "0x%08X" % inserted,
        "insert_after_relocations": "" if inserted is None else "-",
        "omit": "true" if omit else "false",
    } for offset, expected, replacement, inserted, omit in specs]


def normalized_payload(raw, bindings):
    if (len(raw), digest(raw), bindings) != (RAW_SIZE, RAW_OBJECT_SHA, CANDIDATE_BINDINGS):
        raise ValueError("Matrix-pair raw payload changed")
    by_offset = {int(row["offset"], 0): row for row in guard_rows()}
    words = struct.unpack(">84I", raw)
    output = []
    relocations = {}
    for index, word in enumerate(words):
        offset = index * 4
        row = by_offset.get(offset)
        if row is not None:
            if word != int(row["expected"], 0) or bindings.get(offset):
                raise ValueError("Matrix-pair expected guard word or binding changed")
            if row["omit"] == "true":
                continue
            word = int(row["replacement"], 0)
        emitted = len(output) * 4
        output.append(word)
        if offset in bindings:
            relocations[emitted] = bindings[offset]
        if row is not None and row["insert_after"]:
            output.append(int(row["insert_after"], 0))
    result = struct.pack(">85I", *output)
    if digest(result) != RETAIL_TEMPLATE_SHA or relocations != RETAIL_BINDINGS:
        raise ValueError("Matrix-pair normalization differs from retail template")
    return result, relocations


def guard_manifest(before, raw, bindings):
    normalized_payload(raw, bindings)
    stream = io.StringIO(before.decode(), newline="")
    reader = csv.DictReader(stream)
    fields = reader.fieldnames
    expected_fields = ["filename", "function", "offset", "expected", "replacement",
        "expected_relocations", "replacement_relocations", "note", "insert_after",
        "insert_after_relocations", "omit"]
    existing = list(reader)
    if fields != expected_fields or any(row["function"] == FUNCTION for row in existing):
        raise ValueError("Matrix-pair guard predecessor changed")
    newline = "\r\n" if before.endswith(b"\r\n") else "\n"
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator=newline)
    writer.writerows(guard_rows())
    return before + output.getvalue().encode()


def build_owner(root, output, baseline, guards):
    compact, _ = compile_owner(root, output, baseline["source"].read_text(),
                               "compact-owner")
    source_slot(compact)
    padded = output / "qualified-owner.s"
    qualified = output / "qualified-owner.o"
    subprocess.run(["python3", str(root / "tools/pad_generated_object.py"),
        str(compact), str(baseline["asm"]), str(padded),
        "--word-patches", str(guards), "--filename", OWNER,
        "--rodata-symbol", RODATA_SYMBOL],
        cwd=root / "conker", check=True, capture_output=True, text=True)
    subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(qualified),
        str(padded)], check=True, capture_output=True, text=True)
    raw, bindings = payload(qualified, FUNCTION)
    _, template = retail_slots(baseline["rom"].read_bytes())
    if raw != template or bindings != RETAIL_BINDINGS:
        raise ValueError("Matrix-pair qualified owner differs from retail template")
    if QUALIFIED_OWNER_SHA and digest(qualified.read_bytes()) != QUALIFIED_OWNER_SHA:
        raise ValueError("Matrix-pair qualified owner identity changed")
    return qualified


def expected_image(before, retail):
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    if digest(result[at:at + SIZE]) != RAW_LINKED_SHA:
        raise ValueError("Matrix-pair linked predecessor changed")
    result[at:at + SIZE] = retail
    rows = [position for position, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, RAW_SIZE) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError("Matrix-pair original symbol extent changed")
    struct.pack_into(">I", result, rows[0] + 8, SIZE)
    if digest(result) != EXPECTED_ELF_SHA:
        raise ValueError("Matrix-pair expected complete-image identity changed")
    return bytes(result)


def link_image(root, output, baseline, qualified, retail):
    old = "build/src/game/generated_5D2C0.c.o"
    new = str(qualified.relative_to(root / "conker")).replace("\\", "/")
    script_text = baseline["linker"].read_text()
    if script_text.count(old) != 1:
        raise ValueError("Matrix-pair linker owner reference changed")
    script = output / "first-link.ld"
    script.write_text(script_text.replace(old, new))
    elf = output / "first-linked.elf"
    map_path = output / "first-linked.map"
    subprocess.run(["mips-linux-gnu-ld", "-T", str(script.relative_to(root / "conker")),
        "-Map", str(map_path.relative_to(root / "conker")), "-T", "undefined_syms.us.txt",
        "-T", "undefined_funcs.us.txt", "-T", "undefined_syms_auto.txt", "-T",
        "undefined_funcs_auto.txt", "--no-check-sections", "--no-warn-mismatch", "-o",
        str(elf.relative_to(root / "conker"))], cwd=root / "conker", check=True,
        capture_output=True, text=True)
    expected = output / "expected-conker.us.elf"
    expected.write_bytes(expected_image(baseline["elf"].read_bytes(), retail))
    if elf.read_bytes() != expected.read_bytes():
        raise ValueError("Matrix-pair private link differs from independent prediction")
    return elf, map_path, expected


def closure_audit(before_path_, after_path):
    old, _, old_addresses = load_elf_functions(str(before_path_), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(str(after_path), "mips-linux-gnu-objdump")
    if set(old) != set(new) or old_addresses != new_addresses:
        raise ValueError("Matrix-pair function inventory or addresses changed")
    changed = [name for name in new if old[name] != new[name]]
    if changed != [FUNCTION]:
        raise ValueError("Matrix-pair executable closure changed: " + repr(changed))
    return {"functions": len(new), "changed_bodies": changed,
            "all_addresses_fixed": True, "strict_exclusions": 0}


def prepare(root):
    root = Path(root)
    output = root / BUILD
    baseline = freeze(root, output)
    raw, bindings = source_slot(baseline["object"])
    retail, _ = retail_slots(baseline["rom"].read_bytes())
    guards = output / "proposed-guards.csv"
    guards.write_bytes(guard_manifest(baseline["guards"].read_bytes(), raw, bindings))
    qualified = build_owner(root, output, baseline, guards)
    elf, map_path, expected = link_image(root, output, baseline, qualified, retail)
    closure = closure_audit(baseline["elf"], elf)
    (output / "closure.json").write_text(json.dumps(closure, indent=2) + "\n")
    return baseline, guards, qualified, elf, map_path, expected


def main():
    root = Path(__file__).resolve().parents[2]
    values = prepare(root)
    print(json.dumps({"function": FUNCTION, "slot_words": 85, "raw_body_words": 84,
        "retail_body_words": 85, "guards": 9, "insertions": 2, "omissions": 1,
        "relocations": 6, "qualified_owner_sha256": digest(values[2].read_bytes()),
        "expected_elf_sha256": digest(values[5].read_bytes()),
        "closure": json.loads((root / BUILD / "closure.json").read_text())}, indent=2))


if __name__ == "__main__":
    main()
