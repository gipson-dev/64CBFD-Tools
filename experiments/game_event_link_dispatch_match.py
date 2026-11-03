"""Qualify func_151CD3CC's linked-effect event dispatcher as guarded C."""

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.check_game_data_layout import audit_layout
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, same_functions, symbol_rows)
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span)
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = "func_151CD3CC"
FILENAME = "generated_1FA770"
SOURCE = "conker/src/game/generated_1FA770.c"
OBJECT = "conker/build/src/game/generated_1FA770.c.o"
ASM = "conker/asm/1FA770.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-event-link-dispatch-151CD3CC-match"
ENTRY, ROM, NATURAL_WORDS, WORDS, FRAME = 0x151CD3CC, 0x1FA87C, 60, 61, 0x40
SIZE = WORDS * 4
REGISTRY_ROM = 0x22F410
DISPATCH_ROM = 0x1768E4
RAW_SHA256 = "7863f7af254e8fa0cb310b3f72b827ea999bc29b56050868fb61847ac1211902"
RETAIL_SHA256 = "ae92b1d194f2d66b8d470f3f726594e3a5c5fddbd963b801b5ee9170c66d32ff"
RAW_BINDINGS = {
    0x05C: [("R_MIPS_26", "func_151CD4C0")],
    0x0A0: [("R_MIPS_26", "func_151CE47C")],
}
RETAIL_BINDINGS = {
    0x05C: [("R_MIPS_26", "func_151CD4C0")],
    0x0A4: [("R_MIPS_26", "func_151CE47C")],
}
GUARD_ROWS = (
    (0x000, 0x27BDFFD0, 0x27BDFFC0, None),
    (0x008, 0xAFA60038, 0xAFA60048, None),
    (0x020, 0x14C10015, 0x14C10016, None),
    (0x034, 0x54CF002A, 0x54CF002B, None),
    (0x040, 0x57000027, 0x57000028, None),
    (0x058, 0xAFA30028, 0xAFA3002C, None),
    (0x064, 0x8FA30028, 0x8FA3002C, None),
    (0x070, 0x1000001A, 0xA1000014, None),
    (0x074, 0xA1000014, 0x1000001B, 0x8FBF0024),
    (0x0E4, 0x27BD0030, 0x27BD0040, None),
)

ORIGINAL = "s32 func_151CD3CC() {\n    return 0;\n}"
TYPE_ANCHOR = """} EffectRecordPayload;
void *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);
void *memcpy(void *, const void *, u32);
"""
TYPES = """
typedef struct {
    u8 *source;
    s32 identity;
    u8 *effect;
    u8 variant;
    u8 reservedD[3];
} EffectLinkRecord151CD3CC;
typedef struct {
    u8 reserved0;
    u8 sourceKind;
    u8 reserved2[10];
    u8 ownerMode;
    u8 reservedD[27];
    EffectLinkRecord151CD3CC link;
} EffectLinkOwner151CD3CC;
void *func_151CD4C0();
void func_151CE47C(u8 *);
"""
SELECTED = """/* Create, retire or detach the linked effect selected by an event command. */
void func_151CD3CC(EffectLinkOwner151CD3CC *owner, s32 *identity, u8 command) {
    EffectLinkRecord151CD3CC *link = &owner->link;

    if (command == 0x17) {
        if (link->identity == *identity && link->effect == 0) {
            link->effect = func_151CD4C0(
                link->source, link->variant, link->identity,
                owner->ownerMode, owner->sourceKind);
            link->source[0x14] = 0;
        }
    } else if (command == 0x18) {
        if (link->identity == *identity && link->effect != 0) {
            func_151CE47C(link->effect);
        }
    } else if (command == 0x23 && link->identity == *identity) {
        link->effect = 0;
        link->source[0x14] = 1;
    }
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostic_counts(text):
    rows = []
    for line in text.splitlines():
        match = re.match(r"cfe: Warning (\d+): .*?: (.*)", line)
        if match:
            rows.append((match.group(1), match.group(2)))
        elif line.startswith("cfe:") and "Warning" not in line:
            raise ValueError("Unexpected event-link diagnostic: " + line)
    return Counter(rows)


def source_states(live):
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    if body == ORIGINAL:
        if TYPES in live or live.count(TYPE_ANCHOR) != 1:
            raise ValueError("Event-link predecessor source changed")
        qualified = live.replace(TYPE_ANCHOR, TYPE_ANCHOR + TYPES, 1)
        qualified = qualified.replace(
            "s32 func_151CD4C0() {", "void *func_151CD4C0() {", 1)
        start2, end2 = function_span(qualified, FUNCTION)
        qualified = qualified[:start2] + SELECTED + qualified[end2:]
        return live, qualified, False
    if body == SELECTED.split("\n", 1)[1]:
        purpose = SELECTED.split("\n", 1)[0] + "\n"
        if live.count(TYPES) != 1 or live.count(purpose) != 1 or live.count(
                "void *func_151CD4C0() {") != 1:
            raise ValueError("Installed event-link source changed")
        predecessor = live.replace(TYPES, "", 1).replace(
            "void *func_151CD4C0() {", "s32 func_151CD4C0() {", 1)
        start2, end2 = function_span(predecessor, FUNCTION)
        predecessor = predecessor[:start2] + ORIGINAL + predecessor[end2:]
        return predecessor.replace(purpose, "", 1), live, True
    raise ValueError("Event-link source state changed")


def write_guards(source, destination, include):
    with Path(source).open(newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        rows = [row for row in reader if not
                (row["filename"] == FILENAME and row["function"] == FUNCTION)]
    if include:
        for offset, expected, replacement, inserted in GUARD_ROWS:
            rows.append({
                "filename": FILENAME, "function": FUNCTION,
                "offset": "0x%03X" % offset,
                "expected": "0x%08X" % expected,
                "replacement": "0x%08X" % replacement,
                "expected_relocations": "-", "replacement_relocations": "-",
                "note": "Normalize linked-effect event dispatcher compiler layout",
                "insert_after": "" if inserted is None else "0x%08X" % inserted,
                "insert_after_relocations": "" if inserted is None else "-",
                "omit": "false",
            })
    destination = Path(destination)
    with destination.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return destination


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Event-link retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    for offset in RETAIL_BINDINGS:
        struct.pack_into(">I", data, offset, 0x0C000000)
    return bytes(data)


def checked_candidate(obj):
    raw, bindings = payload(obj, FUNCTION)
    if len(raw) != NATURAL_WORDS * 4 or digest(raw) != RAW_SHA256:
        raise ValueError("Event-link natural candidate changed")
    if bindings != RAW_BINDINGS:
        raise ValueError("Event-link natural bindings changed")
    words = struct.unpack(">%dI" % NATURAL_WORDS, raw)
    if ((-words[0]) & 0xFFFF) != 0x30:
        raise ValueError("Event-link natural frame changed")
    return raw, bindings


def assemble_owner(root, output, compact, guards, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=guards, filename=FILENAME))
    obj = owner_dir / (FILENAME + ".c.o")
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(obj),
        str(assembly)], check=True, capture_output=True)
    return obj


def link_image(root, output, owner, label):
    old = OBJECT.replace("conker/", "")
    new = str(owner.relative_to(root / "conker")).replace("\\", "/")
    linker = (root / LINKER).read_text()
    if linker.count(old) != 1:
        raise ValueError("Event-link linker owner reference changed")
    link_dir = output / label
    link_dir.mkdir(parents=True, exist_ok=True)
    script = link_dir / "conker.ld"
    script.write_text(linker.replace(old, new))
    elf = link_dir / "conker.us.elf"
    subprocess.run([
        "mips-linux-gnu-ld", "-T", str(script.relative_to(root / "conker")),
        "-T", "undefined_syms.us.txt", "-T", "undefined_funcs.us.txt",
        "-T", "undefined_syms_auto.txt", "-T", "undefined_funcs_auto.txt",
        "--no-check-sections", "--no-warn-mismatch", "-o",
        str(elf.relative_to(root / "conker"))], cwd=root / "conker",
        check=True, capture_output=True)
    return elf


def expected_image(predecessor, retail):
    result = bytearray(predecessor)
    offset = elf_slot_offset(predecessor, ENTRY, SIZE)
    result[offset:offset + SIZE] = retail
    rows = [(at, fields) for at, name, fields, _ in symbol_rows(predecessor)
            if name == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 12):
        raise ValueError("Event-link predecessor symbol extent changed")
    struct.pack_into(">I", result, rows[0][0] + 8, SIZE)
    return bytes(result)


def check_image(predecessor, actual, retail):
    if actual != expected_image(predecessor, retail):
        raise ValueError("Event-link image differs from literal prediction")


def function_blob(obj, name):
    text, functions, relocations = parse_object(obj)
    info = functions[name]
    start, end = info["value"], info["value"] + info["size"]
    bindings = {offset - start: rows for offset, rows in relocations.items()
                if start <= offset < end}
    return text[start:end], bindings


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    dispatcher = struct.unpack_from(">23I", image, DISPATCH_ROM)
    required = {
        2: 0x30CE00FF, 14: 0x8C63A8D8,
        17: 0x0060F809, 18: 0x00000000,
    }
    if calls or pointers != [REGISTRY_ROM] or any(
            dispatcher[index] != word for index, word in required.items()):
        raise ValueError("Event-link registry evidence changed")
    return {
        "table": "D_8008A8D8", "index": 30,
        "registry_rom": hex(REGISTRY_ROM), "direct_jal_calls": calls,
        "aligned_pointer_literals": [hex(at) for at in pointers],
        "dispatcher": "func_15149434",
        "arguments": ["owner", "event identity pointer", "low command byte"],
    }


def prepare(root, output=None):
    root = Path(root).resolve()
    output = Path(output or root / BUILD).resolve()
    output.mkdir(parents=True, exist_ok=True)
    predecessor_source, qualified_source, installed = source_states(
        (root / SOURCE).read_text())
    predecessor_guards = write_guards(root / GUARDS,
                                      output / "predecessor-guards.csv", False)
    qualified_guards = write_guards(root / GUARDS,
                                    output / "proposed-guards.csv", True)
    if installed:
        with (root / GUARDS).open(newline="") as stream:
            selected = [row for row in csv.DictReader(stream)
                        if row["filename"] == FILENAME and
                        row["function"] == FUNCTION]
        if len(selected) != len(GUARD_ROWS):
            raise ValueError("Installed event-link guards changed")
    else:
        with (root / GUARDS).open(newline="") as stream:
            if any(row["filename"] == FILENAME and row["function"] == FUNCTION
                   for row in csv.DictReader(stream)):
                raise ValueError("Event-link predecessor guards already exist")

    predecessor_compact, before_diagnostics = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after_diagnostics = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostic_counts(before_diagnostics) != diagnostic_counts(after_diagnostics):
        raise ValueError("Event-link owner diagnostics changed")
    raw, bindings = checked_candidate(qualified_compact)
    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_guards, "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, qualified_guards, "qualified-owner")
    live_owner = qualified_owner if installed else predecessor_owner
    if live_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Event-link selected owner differs from production")
    if function_blob(qualified_owner, FUNCTION) != (
            retail_object_bytes(root), RETAIL_BINDINGS):
        raise ValueError("Event-link guarded owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Event-link normalized pools changed")

    predecessor_elf = link_image(root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner, "qualified-image")
    retail = retail_bytes(root)
    check_image(predecessor_elf.read_bytes(), qualified_elf.read_bytes(), retail)
    live_elf = (root / ELF).read_bytes()
    expected_elf = qualified_elf if installed else predecessor_elf
    if live_elf != expected_elf.read_bytes():
        raise ValueError("Event-link selected image differs from production")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Event-link full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Event-link protected data changed")

    (output / "proposed-owner.c").write_text(qualified_source)
    report = {
        "function": FUNCTION, "installed": installed,
        "natural_words": NATURAL_WORDS, "words": WORDS, "frame": FRAME,
        "guards": len(GUARD_ROWS), "insertions": 1,
        "relocations": len(RETAIL_BINDINGS), "neighbors": neighbors,
        "raw_sha256": digest(raw), "retail_sha256": digest(retail),
        "qualified_owner_sha256": digest(qualified_owner.read_bytes()),
        "predecessor_elf_sha256": digest(predecessor_elf.read_bytes()),
        "qualified_elf_sha256": digest(qualified_elf.read_bytes()),
        "functions": len(new), "changed_bodies": changed,
        "all_addresses_fixed": True, "strict_exclusions": 0,
        "registry": registry_evidence(root), "game_data": data,
    }
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report, predecessor_owner, qualified_owner, predecessor_elf, qualified_elf


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)[0], indent=2))
