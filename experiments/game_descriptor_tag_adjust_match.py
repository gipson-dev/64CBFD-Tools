"""Qualify the descriptor tag adjuster for a guarded retail match."""

import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset,
    same_functions,
    symbol_rows,
)
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import body, compile_owner
from tools.match_progress import load_elf_functions
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = "func_150174C0"
OWNER = "game_447B0"
ENTRY = 0x150174C0
ROM = 0x44970
SIZE = 184
BUILD = "conker/build/game-descriptor-tag-adjust-150174C0-guard-match"

RAW_SHA = "8e57209dd5813886c604aa2b29a938ddc3e8629b4052c3387b7b431d976ecea7"
RETAIL_SHA = "af19389bcf0550852cf32e581d96bc8bab3e1ded574db01cede8ef7e31afaf0d"
RETAIL_TEMPLATE_SHA = "27fbaa90d618da4e80e23cdaf8c5fca9d52eb079186ac48923577ea973bfd34f"
OLD_LINKED_SLOT_SHA = "33b7e0067d518a2a347cf88a97b482aec4be48fd2878d9a7b6bead6bd6188e2f"
QUALIFIED_OWNER_SHA = "284a4a47018cfd190f45b5a68748e16a206dba847e2bc56fe8ffdf3c881b7a7c"
EXPECTED_ELF_SHA = "4e2f6b37c94c63806e8400c1cf95012ff941ce3dbe559d0ed6b3b5666d353234"

PATHS = {
    "source": "conker/src/game_447B0.c",
    "header": "conker/include/variables.h",
    "object": "conker/build/src/game_447B0.c.o",
    "elf": "conker/build/conker.us.elf",
    "map": "conker/build/conker.us.map",
    "linker": "conker/build/conker.ld",
    "guards": "conker/retail_word_patches.us.csv",
    "layout": "conker/retail_layout.us.txt",
    "progress": "conker/progress.csv",
    "rom": "conker/conker.us.bin",
}

BASELINE = {
    "source": "df7b0b6f491ca5ada6e8db80c52ccde5a5899b88c94fed9f975e67a5e7ab679d",
    "header": "29d34e5a04fe5b2575ae94dfe5365a80256122d68984c60cf7c6a43d7d686785",
    "object": "0a616990fdcf10af26288908ba3b33e4231df410858b2ea15545807a36e8e642",
    "elf": "0e1cc15dcf288623c7ad505aad3b4cd4ad8b1af762b5221f90c3578c398b32ca",
    "map": "4ceeb40962070eb01cdc286937fdd209862def2bee87dbe33b6f8b7bd6912b38",
    "linker": "6479ca7cef48dc77d746c16afcc244de6bfb80c6789ba79a03d6f110e42a98d5",
    "guards": "b92ad7d866adb3d8af5fce60fd33a8f365d73b50c0bc8e914f8ca98b4eaae699",
    "layout": "1eb1e705545ec2e19f6b68ef5025d816f4d513684518968a6806008b6dc17612",
    "progress": "96a7f15ab5207027a204f795e91b8f9f3453482ce4ec4d47bd8bcb4b5a305502",
    "rom": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
}

BINDINGS = {
    0x00C: [("R_MIPS_HI16", "D_80087380")],
    0x010: [("R_MIPS_LO16", "D_80087380")],
    0x018: [("R_MIPS_HI16", "D_800D23C0")],
    0x024: [("R_MIPS_LO16", "D_800D23C0")],
    0x074: [("R_MIPS_HI16", "D_800D23C0")],
    0x078: [("R_MIPS_LO16", "D_800D23C0")],
    0x090: [("R_MIPS_HI16", "D_80087380")],
    0x094: [("R_MIPS_LO16", "D_80087380")],
}

ROW_TYPE = (
    "typedef struct {\n"
    "    u16 unused;\n"
    "    u16 count;\n"
    "    u32 reserved;\n"
    "    u16 entries[8];\n"
    "} DescriptorTagRow;\n"
)

SELECTED = """/* Adjust tag-2 entries while retaining live descriptor table/count reloads. */
void func_150174C0(s32 adjustment) {
    s32 descriptorIndex;
    s32 entryIndex;

    for (descriptorIndex = 0; descriptorIndex < (s32)D_80087380; descriptorIndex++) {
        for (entryIndex = 0; entryIndex < ((DescriptorTagRow *)D_800D23C0)[descriptorIndex].count; entryIndex++) {
            u16 *entry = &((DescriptorTagRow *)D_800D23C0)[descriptorIndex].entries[entryIndex];
            u16 value = *entry;
            if ((value >> 12) == 2) {
                *entry = (u32)value + (u32)adjustment;
            }
        }
    }
}
"""


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
            raise ValueError("Changed descriptor-adjust baseline: " + repr(hashes))
        for key, data in values.items():
            before_path(output, key).write_bytes(data)
        manifest.write_text(json.dumps(BASELINE, indent=2) + "\n")
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError("Modified descriptor-adjust baseline manifest")
    for key, expected in BASELINE.items():
        if digest(before_path(output, key).read_bytes()) != expected:
            raise ValueError("Modified descriptor-adjust frozen input: " + key)
    return {key: before_path(output, key) for key in PATHS}


def proposed_header(before):
    old = "extern s32 D_800D23C0;"
    if before.count(old) != 1:
        raise ValueError("Unknown descriptor table declaration")
    return before.replace(old, "extern u8 *D_800D23C0;", 1)


def proposed_source(before, private_header="variables-private.h"):
    old_declaration = "s32 func_150174C0(s32 arg0);"
    old_assignment = "D_800D23C0 = (s32)func_1502B5C8"
    if before.count(old_declaration) != 1 or before.count(old_assignment) != 1:
        raise ValueError("Unknown descriptor source declarations")
    result = before.replace('#include "variables.h"',
        '#include "%s"\n\n%s' % (private_header, ROW_TYPE.rstrip()), 1)
    result = result.replace(old_declaration, "void func_150174C0(s32 adjustment);", 1)
    result = result.replace(body(result, FUNCTION), SELECTED.rstrip(), 1)
    result = result.replace(old_assignment, "D_800D23C0 = func_1502B5C8", 1)
    return result


def guard_rows():
    note = "Normalize closed descriptor entry loop register allocation and scheduling"
    specs = (
        (0x03C, 0x00004825, 0x59000017),
        (0x040, 0x19000015, 0x24420001),
        (0x044, 0x00027080, 0x00001825),
        (0x048, 0x01C27023, 0x00027080),
        (0x04C, 0x000E70C0, 0x01C27023),
        (0x050, 0x00AE7821, 0x000E70C0),
        (0x054, 0x01E91821, 0x00AE7821),
        (0x058, 0x946A0008, 0x01E34821),
        (0x05C, 0x24840001, 0x952A0008),
        (0x060, 0x24630008, 0x24840001),
        (0x070, 0xA4790000, 0xA5390008),
        (0x088, 0x1420FFEE, 0x1420FFEF),
        (0x08C, 0x25290002, 0x24630002),
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
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    } for offset, expected, replacement in specs]


def retail_template(rom):
    linked = rom[ROM:ROM + SIZE]
    if (len(linked), digest(linked)) != (SIZE, RETAIL_SHA):
        raise ValueError("Descriptor-adjust retail slot changed")
    template = bytearray(linked)
    for offset in BINDINGS:
        word = struct.unpack_from(">I", template, offset)[0]
        struct.pack_into(">I", template, offset, word & 0xFFFF0000)
    if digest(template) != RETAIL_TEMPLATE_SHA:
        raise ValueError("Descriptor-adjust retail template changed")
    return linked, bytes(template)


def normalized_payload(raw, bindings):
    if (len(raw), digest(raw), bindings) != (SIZE, RAW_SHA, BINDINGS):
        raise ValueError("Descriptor-adjust compiler payload changed")
    rows = {int(row["offset"], 0): row for row in guard_rows()}
    words = list(struct.unpack(">46I", raw))
    for offset, row in rows.items():
        index = offset // 4
        if words[index] != int(row["expected"], 0) or offset in bindings:
            raise ValueError("Descriptor-adjust guard input changed")
        words[index] = int(row["replacement"], 0)
    result = struct.pack(">46I", *words)
    if digest(result) != RETAIL_TEMPLATE_SHA:
        raise ValueError("Descriptor-adjust guards do not reproduce retail")
    return result


def guard_manifest(before, raw, bindings):
    normalized_payload(raw, bindings)
    reader = csv.DictReader(io.StringIO(before.decode(), newline=""))
    fields = reader.fieldnames
    expected_fields = ["filename", "function", "offset", "expected", "replacement",
        "expected_relocations", "replacement_relocations", "note", "insert_after",
        "insert_after_relocations", "omit"]
    existing = list(reader)
    if fields != expected_fields or any(row["function"] == FUNCTION for row in existing):
        raise ValueError("Descriptor-adjust guard predecessor changed")
    newline = "\r\n" if before.endswith(b"\r\n") else "\n"
    output = io.StringIO(newline="")
    csv.DictWriter(output, fieldnames=fields, lineterminator=newline).writerows(guard_rows())
    return before + output.getvalue().encode()


def compile_candidate(root, output, baseline):
    before_header = baseline["header"].read_text()
    (output / "variables-before.h").write_text(before_header)
    header = proposed_header(baseline["header"].read_text())
    (output / "variables-private.h").write_text(header)
    baseline_source = baseline["source"].read_text()
    old_source = baseline_source.replace('#include "variables.h"',
                                         '#include "variables-before.h"', 1)
    source = proposed_source(baseline_source)
    (output / "proposed-source.c").write_text(source)
    old, old_diagnostics = compile_owner(root, output, old_source, "compact-before")
    new, new_diagnostics = compile_owner(root, output, source, "compact-candidate")
    if old_diagnostics or new_diagnostics:
        raise ValueError("Descriptor-adjust owner compiler diagnostics changed")
    if same_functions(old, new, (FUNCTION,)) != 4:
        raise ValueError("Descriptor-adjust changed a raw owner neighbor")
    if normalized_pools(old) != normalized_pools(new):
        raise ValueError("Descriptor-adjust changed owner pools")
    raw, bindings = payload(new, FUNCTION)
    normalized_payload(raw, bindings)
    return new, raw, bindings


def build_owner(root, output, baseline, compact, guards):
    padded = output / "qualified-owner.s"
    qualified = output / "qualified-owner.o"
    subprocess.run(["python3", str(root / "tools/pad_c_object.py"), str(compact),
        str(baseline["layout"]), OWNER, str(padded), "--word-patches", str(guards)],
        cwd=root / "conker", check=True, capture_output=True, text=True)
    subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(qualified),
        str(padded)], check=True, capture_output=True, text=True)
    retail, template = retail_template(baseline["rom"].read_bytes())
    raw, bindings = payload(qualified, FUNCTION)
    if raw != template or bindings != BINDINGS:
        raise ValueError("Descriptor-adjust qualified owner differs from retail template")
    if same_functions(baseline["object"], qualified, (FUNCTION,)) != 4:
        raise ValueError("Descriptor-adjust changed a padded owner neighbor")
    if normalized_pools(baseline["object"]) != normalized_pools(qualified):
        raise ValueError("Descriptor-adjust changed padded owner pools")
    if QUALIFIED_OWNER_SHA and digest(qualified.read_bytes()) != QUALIFIED_OWNER_SHA:
        raise ValueError("Descriptor-adjust qualified owner identity changed")
    return qualified, retail


def expected_image(before, retail):
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    if digest(result[at:at + SIZE]) != OLD_LINKED_SLOT_SHA:
        raise ValueError("Descriptor-adjust linked predecessor changed")
    result[at:at + SIZE] = retail
    rows = [position for position, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 152) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError("Descriptor-adjust predecessor symbol extent changed")
    struct.pack_into(">I", result, rows[0] + 8, SIZE)
    if digest(result) != EXPECTED_ELF_SHA:
        raise ValueError("Descriptor-adjust expected image identity changed")
    return bytes(result)


def link_image(root, output, baseline, qualified, retail):
    old = "build/src/game_447B0.c.o"
    new = str(qualified.relative_to(root / "conker")).replace("\\", "/")
    script_text = baseline["linker"].read_text()
    if script_text.count(old) != 1:
        raise ValueError("Descriptor-adjust linker owner reference changed")
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
        raise ValueError("Descriptor-adjust private link differs from prediction")
    old_functions, _, old_addresses = load_elf_functions(str(baseline["elf"]),
                                                          "mips-linux-gnu-objdump")
    new_functions, _, new_addresses = load_elf_functions(str(elf), "mips-linux-gnu-objdump")
    changed = [name for name in new_functions if old_functions[name] != new_functions[name]]
    if set(old_functions) != set(new_functions) or old_addresses != new_addresses:
        raise ValueError("Descriptor-adjust function inventory or addresses changed")
    if changed != [FUNCTION]:
        raise ValueError("Descriptor-adjust executable closure changed: " + repr(changed))
    closure = {"functions": len(new_functions), "changed_bodies": changed,
        "all_addresses_fixed": True, "strict_exclusions": 0}
    (output / "closure.json").write_text(json.dumps(closure, indent=2) + "\n")
    return elf, map_path, expected, closure


def prepare(root):
    root = Path(root)
    output = root / BUILD
    baseline = freeze(root, output)
    compact, raw, bindings = compile_candidate(root, output, baseline)
    guards = output / "proposed-guards.csv"
    guards.write_bytes(guard_manifest(baseline["guards"].read_bytes(), raw, bindings))
    qualified, retail = build_owner(root, output, baseline, compact, guards)
    elf, map_path, expected, closure = link_image(root, output, baseline, qualified, retail)
    return baseline, guards, qualified, elf, map_path, expected, closure


def main():
    root = Path(__file__).resolve().parents[2]
    values = prepare(root)
    print(json.dumps({"function": FUNCTION, "slot_words": 46, "frame": 8,
        "guards": 13, "insertions": 0, "omissions": 0, "relocations": 8,
        "qualified_owner_sha256": digest(values[2].read_bytes()),
        "expected_elf_sha256": digest(values[5].read_bytes()),
        "closure": values[6]}, indent=2))


if __name__ == "__main__":
    main()
