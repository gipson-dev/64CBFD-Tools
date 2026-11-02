"""Qualify the existing queued-segment writer for a guarded retail match."""

import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_four_head_lookup_match import payload
from tools.match_progress import load_elf_functions


FUNCTION = "func_1510D8C0"
OWNER = "generated_139FC0"
ENTRY = 0x1510D8C0
ROM = 0x13AD70
SIZE = 176
RAW_SIZE = 160
BUILD = "conker/build/game-queued-segment-writer-1510D8C0-match"
RAW_OBJECT_SHA = "3986629e75f287d39f4c2a364a01d3bbe5af41932cb1ed8b8f9d52bfd0c29ccd"
RAW_SLOT_SHA = "9dc27827e280f34681915bc97b25cf04c22654a0b068625bfc5f48d868416e89"
RAW_LINKED_SHA = "f3a227545fc8d35dd017430e12f6fd1da0512c5746e400423358eee3a9566feb"
RETAIL_SHA = "d4909fd2c5d0fa9df7bc1118c01ae806110cd3e919d69f1799daa6286337bd70"
RETAIL_TEMPLATE_SHA = "23e63d547626daa4d1112b89e5fe932f77a9d6579e16dd890c0c1a151c0ff4df"
QUALIFIED_OWNER_SHA = "f6479404609b3524685973edab6063d618fef0556866e3443ec1abdec13e522c"
EXPECTED_ELF_SHA = "f930a85c4640fb0f36cac1750284d15863164fd5d4140010a99dd94a9f6ceb04"

PATHS = {
    "source": "conker/src/game/generated_139FC0.c",
    "object": "conker/build/src/game/generated_139FC0.c.o",
    "elf": "conker/build/conker.us.elf",
    "map": "conker/build/conker.us.map",
    "linker": "conker/build/conker.ld",
    "guards": "conker/retail_word_patches.us.csv",
    "asm": "conker/asm/139FC0.s",
    "progress": "conker/progress.csv",
    "rom": "conker/conker.us.bin",
}

BASELINE = {
    "source": "92acd2ba087d8762add65d1d93d9960a91f9cca7c544eaa695b99fa15aab23e0",
    "object": "19e5fd54979992c36e2f2be10669b6f3f4ae3112e8dee36c72886e1250e17f36",
    "elf": "9073a15c16751d7488d87c18d53fa5971fcce573dcfaf26f805fb4890165ef5a",
    "map": "4ceeb40962070eb01cdc286937fdd209862def2bee87dbe33b6f8b7bd6912b38",
    "linker": "6479ca7cef48dc77d746c16afcc244de6bfb80c6789ba79a03d6f110e42a98d5",
    "guards": "495a93b5f7a63abdf16ad2393c9acffe05703b018dfc56bf9c18d7e9f43237b6",
    "asm": "bff80847aaa7145696f6e95b1a54559e67f6bcdb371482b674e6908a73198bd7",
    "progress": "96a7f15ab5207027a204f795e91b8f9f3453482ce4ec4d47bd8bcb4b5a305502",
    "rom": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
}

CANDIDATE_BINDINGS = {
    0x00: [("R_MIPS_HI16", "D_800D9ED0")],
    0x04: [("R_MIPS_LO16", "D_800D9ED0")],
    0x0C: [("R_MIPS_HI16", "D_800D9ED8")],
    0x10: [("R_MIPS_LO16", "D_800D9ED8")],
}
RETAIL_BINDINGS = {
    0x04: [("R_MIPS_HI16", "D_800D9ED0")],
    0x08: [("R_MIPS_LO16", "D_800D9ED0")],
    0x0C: [("R_MIPS_HI16", "D_800D9ED8")],
    0x10: [("R_MIPS_LO16", "D_800D9ED8")],
    0x84: [("R_MIPS_HI16", "D_800D9ED0")],
    0x88: [("R_MIPS_LO16", "D_800D9ED0")],
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
            raise ValueError("Changed queued-writer baseline: " + repr(hashes))
        for key, data in values.items():
            before_path(output, key).write_bytes(data)
        manifest.write_text(json.dumps(BASELINE, indent=2) + "\n")
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError("Modified queued-writer baseline manifest")
    for key, expected in BASELINE.items():
        if digest(before_path(output, key).read_bytes()) != expected:
            raise ValueError("Modified queued-writer frozen input: " + key)
    return {key: before_path(output, key) for key in PATHS}


def relocation_text(rows):
    if not rows:
        return "-"
    if len(rows) != 1:
        raise ValueError("Unexpected queued-writer relocation list: " + repr(rows))
    return rows[0][0] + ":" + rows[0][1]


def source_slot(obj):
    raw, bindings = payload(obj, FUNCTION)
    if (len(raw), digest(raw), bindings) != (RAW_SIZE, RAW_OBJECT_SHA, CANDIDATE_BINDINGS):
        raise ValueError("Queued-writer compiler payload changed")
    return raw + bytes(SIZE - len(raw)), bindings


def retail_slots(rom):
    linked = rom[ROM:ROM + SIZE]
    if (len(linked), digest(linked)) != (SIZE, RETAIL_SHA):
        raise ValueError("Queued-writer retail slot changed")
    template = bytearray(linked)
    for offset in RETAIL_BINDINGS:
        word = struct.unpack_from(">I", template, offset)[0] & 0xFFFF0000
        struct.pack_into(">I", template, offset, word)
    if digest(template) != RETAIL_TEMPLATE_SHA:
        raise ValueError("Queued-writer retail relocation template changed")
    return linked, bytes(template)


def guard_manifest(before, raw, raw_bindings, retail, retail_bindings=RETAIL_BINDINGS):
    source_slot_bytes(raw)
    if (digest(raw), raw_bindings, digest(retail), retail_bindings) != (
            RAW_SLOT_SHA, CANDIDATE_BINDINGS, RETAIL_TEMPLATE_SHA, RETAIL_BINDINGS):
        raise ValueError("Queued-writer guard source slot changed")
    stream = io.StringIO(before.decode(), newline="")
    reader = csv.DictReader(stream)
    fields = reader.fieldnames
    expected_fields = ["filename", "function", "offset", "expected", "replacement",
        "expected_relocations", "replacement_relocations", "note", "insert_after",
        "insert_after_relocations", "omit"]
    rows = list(reader)
    if fields != expected_fields or any(row["function"] == FUNCTION for row in rows):
        raise ValueError("Queued-writer guard predecessor changed")
    old_words = struct.unpack(">44I", raw)
    new_words = struct.unpack(">44I", retail)
    newline = "\r\n" if before.endswith(b"\r\n") else "\n"
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator=newline)
    count = 0
    for index, (old, new) in enumerate(zip(old_words, new_words)):
        offset = index * 4
        old_relocations = raw_bindings.get(offset, [])
        new_relocations = retail_bindings.get(offset, [])
        if old == new and old_relocations == new_relocations:
            continue
        writer.writerow({"filename": OWNER, "function": FUNCTION,
            "offset": "0x%03X" % offset, "expected": "0x%08X" % old,
            "replacement": "0x%08X" % new,
            "expected_relocations": relocation_text(old_relocations),
            "replacement_relocations": relocation_text(new_relocations),
            "note": "Normalize queued segment writer register allocation and scheduling",
            "insert_after": "", "insert_after_relocations": "", "omit": "false"})
        count += 1
    if count != 38:
        raise ValueError("Queued-writer guard count changed: %d" % count)
    return before + output.getvalue().encode()


def source_slot_bytes(raw):
    if len(raw) != SIZE:
        raise ValueError("Queued-writer source slot extent changed")
    return raw


def compiler_command(root, source, obj):
    includes = [".", "include", "include/2.0L", "include/2.0L/PR", "include/libc",
                "src/libultra/os", "src/libultra/audio", "src/libultra/io"]
    return [str(root / "ido/ido5.3_recomp/cc"), "-c", "-32", "-G", "0",
        "-Xfullwarn", "-Xcpluscomm", "-signed", "-nostdinc", "-non_shared",
        "-Wab,-r4300_mul", "-D_LANGUAGE_C", "-D_FINALROM", "-DF3DEX_GBI_2",
        "-D_MIPS_SZLONG=32", "-woff", "649,838",
        *[item for path in includes for item in ("-I", path)],
        "-O2", "-g3", "-mips2", "-o32", "-o", str(obj), str(source)]


def build_owner(root, output, baseline, guards):
    candidate_source = output / "candidate-generated_139FC0.c"
    compact = output / "generated_139FC0.c.o.compact"
    padded = output / "qualified-owner.s"
    qualified = output / "qualified-owner.o"
    candidate_source.write_bytes(baseline["source"].read_bytes())
    command = compiler_command(root, candidate_source.relative_to(root / "conker"),
                               compact.relative_to(root / "conker"))
    result = subprocess.run(command, cwd=root / "conker", capture_output=True, text=True)
    diagnostics = result.stdout + result.stderr
    (output / "compiler-diagnostics.txt").write_text(diagnostics)
    if result.returncode or "Error:" in diagnostics:
        raise ValueError("Queued-writer owner compile failed: " + diagnostics)
    source_slot(compact)
    subprocess.run(["python3", str(root / "tools/pad_generated_object.py"), str(compact),
        str(baseline["asm"]), str(padded), "--word-patches", str(guards),
        "--filename", OWNER], cwd=root / "conker", check=True,
        capture_output=True, text=True)
    subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(qualified),
        str(padded)], check=True, capture_output=True, text=True)
    raw, bindings = payload(qualified, FUNCTION)
    linked, template = retail_slots(baseline["rom"].read_bytes())
    if raw != template[:RAW_SIZE] or bindings != RETAIL_BINDINGS:
        raise ValueError("Queued-writer qualified owner payload differs from retail template")
    if QUALIFIED_OWNER_SHA and digest(qualified.read_bytes()) != QUALIFIED_OWNER_SHA:
        raise ValueError("Queued-writer qualified owner identity changed")
    return qualified, linked


def expected_image(before, retail):
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    old = bytes(result[at:at + SIZE])
    if digest(old) != RAW_LINKED_SHA:
        raise ValueError("Queued-writer linked predecessor changed")
    result[at:at + SIZE] = retail
    return bytes(result)


def link_image(root, output, baseline, qualified, retail):
    old = "build/src/game/generated_139FC0.c.o"
    new = str(qualified.relative_to(root / "conker")).replace("\\", "/")
    script_text = baseline["linker"].read_text()
    if script_text.count(old) != 1:
        raise ValueError("Queued-writer linker owner reference changed")
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
    expected = expected_image(baseline["elf"].read_bytes(), retail)
    expected_path = output / "expected-conker.us.elf"
    expected_path.write_bytes(expected)
    if digest(expected) != EXPECTED_ELF_SHA:
        raise ValueError("Queued-writer expected complete-image identity changed")
    if elf.read_bytes() != expected:
        raise ValueError("Queued-writer private link differs from independent prediction")
    return elf, map_path, expected_path


def closure_audit(before_path, after_path):
    old, _, old_addresses = load_elf_functions(str(before_path), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(str(after_path), "mips-linux-gnu-objdump")
    if set(old) != set(new) or old_addresses != new_addresses:
        raise ValueError("Queued-writer function inventory or addresses changed")
    changed = []
    for name, words in new.items():
        if old[name] != words:
            changed.append(name)
    if changed != [FUNCTION]:
        raise ValueError("Queued-writer executable closure changed: " + repr(changed))
    return {"functions": len(new), "changed_bodies": changed,
            "all_addresses_fixed": True, "strict_exclusions": 0}


def prepare(root):
    root = Path(root)
    output = root / BUILD
    baseline = freeze(root, output)
    raw, raw_bindings = source_slot(baseline["object"])
    retail, template = retail_slots(baseline["rom"].read_bytes())
    guards = output / "proposed-guards.csv"
    guards.write_bytes(guard_manifest(baseline["guards"].read_bytes(), raw,
                                      raw_bindings, template))
    qualified, retail = build_owner(root, output, baseline, guards)
    elf, map_path, expected = link_image(root, output, baseline, qualified, retail)
    closure = closure_audit(baseline["elf"], elf)
    (output / "closure.json").write_text(json.dumps(closure, indent=2) + "\n")
    return baseline, guards, qualified, elf, map_path, expected


def main():
    root = Path(__file__).resolve().parents[2]
    values = prepare(root)
    print(json.dumps({"function": FUNCTION, "slot_words": 44, "raw_body_words": 40,
        "retail_body_words": 41, "guards": 38, "relocations": 6,
        "qualified_owner_sha256": digest(values[2].read_bytes()),
        "expected_elf_sha256": digest(values[5].read_bytes()),
        "closure": json.loads((root / BUILD / "closure.json").read_text())}, indent=2))


if __name__ == "__main__":
    main()
