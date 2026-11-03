"""Develop and qualify func_15035714's reflected projection probe."""

from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import re
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, same_functions, symbol_rows)
from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout


FUNCTION = "func_15035714"
FILENAME = "generated_61D10"
SOURCE = "conker/src/game/generated_61D10.c"
OBJECT = "conker/build/src/game/generated_61D10.c.o"
ASM = "conker/asm/61D10.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-projection-probe-15035714-match"
ENTRY, ROM, NATURAL_WORDS, WORDS, FRAME = 0x15035714, 0x62BC4, 61, 61, 0x40
SIZE = WORDS * 4
RAW_SHA256 = "7737dcd1956bd0849c341aa7652325e9123d1d60fa0de4877d19baa689be868a"
RETAIL_SHA256 = "d21bbfe78a3f986521fae1730e3d828ad77e65e5bda98f6716bf6fddf4aeb760"
RAW_BINDINGS = {
    0x010: [("R_MIPS_HI16", "D_800BE628")],
    0x014: [("R_MIPS_LO16", "D_800BE628")],
    0x018: [("R_MIPS_HI16", "D_800D1C90")],
    0x034: [("R_MIPS_LO16", "D_800D1C90")],
    0x0AC: [("R_MIPS_HI16", "D_80097D70")],
    0x0B0: [("R_MIPS_LO16", "D_80097D70")],
    0x0B4: [("R_MIPS_HI16", "D_800D9C10")],
    0x0BC: [("R_MIPS_LO16", "D_800D9C10")],
    0x0D0: [("R_MIPS_26", "func_150A6360")],
}
RETAIL_BINDINGS = RAW_BINDINGS
GUARD_ROWS = (
    (0x000, 0x27BDFFD0, 0x27BDFFC0, None),
    (0x00C, 0xAFA60038, 0xAFA60048, None),
    (0x020, 0xAFAE002C, 0xAFAE0028, None),
    (0x028, 0x8FA80038, 0x8FA80048, None),
    (0x064, 0x46004402, 0x46080402, None),
    (0x06C, 0x46001482, 0x46020482, None),
    (0x084, 0xC4A40018, 0xC4AA0018, None),
    (0x090, 0x460E4281, 0x460E4001, None),
    (0x098, 0x460A7081, 0x46007081, None),
    (0x09C, 0xC4A40018, 0xC4AA0018, None),
    (0x0A0, 0x460C2080, 0x460C5080, None),
    (0x0A4, 0xC5060038, 0xC5040038, None),
    (0x0B0, 0xC4280000, 0xC4260000, "R_MIPS_LO16:D_80097D70"),
    (0x0C8, 0x8FA4002C, 0x8FA40028, None),
    (0x0CC, 0xE7A60010, 0xE7A40010, None),
    (0x0D4, 0xE7A8001C, 0xE7A6001C, None),
    (0x0F0, 0x27BD0030, 0x27BD0040, None),
)

DECLARATIONS = """\
extern u8 *D_800BE628;
extern u8 *D_800D1C90[];
extern f32 D_800D9C10[4][4];
extern f32 D_80097D70;
s32 func_150A6360(u8 *, f32 [4][4], f32, f32, f32, f32, f32, f32);
"""

SELECTED = """\
/* Test an actor's reflected projection against the current view. */
s32 func_15035714(s32 mode, u8 *actor, u8 *projection, f32 reflectionY) {
    u8 *view;
    u8 *descriptor;
    s32 identity;
    f32 scale;
    f32 actorScale;
    f32 halfWidth;
    f32 halfHeight;
    f32 verticalRadius;

    view = D_800BE628;
    identity = actor[4];
    descriptor = D_800D1C90[identity];
    scale = (f32)*(u16 *)(descriptor + 0xE);
    actorScale = *(f32 *)(actor + 0x150);
    halfWidth = *(f32 *)(actor + 0x14C) * scale;
    halfHeight = actorScale * scale;
    verticalRadius = actorScale * (f32)*(s16 *)(descriptor + 0x10);
    if (mode == 1 || mode == 0) {
        actorScale = reflectionY -
            ((*(f32 *)(actor + 0x18) + verticalRadius) - reflectionY);
    } else {
        actorScale = *(f32 *)(actor + 0x18) + verticalRadius;
    }
    if (func_150A6360(view, D_800D9C10,
        *(f32 *)(projection + 0x30), actorScale,
        *(f32 *)(projection + 0x38),
        halfWidth, halfHeight, D_80097D70) == 0) {
        return 1;
    }
    return 0;
}"""


def candidate_source(live):
    lo, hi = function_span(live, FUNCTION)
    expected = "s32 func_15035714() {\n    return 0;\n}"
    if live[lo:hi] != expected:
        raise ValueError("Projection-probe source state changed")
    anchor = "/* Non-matching placeholders for the text-only asm slice asm/61D10.s. */\n"
    if live.count(anchor) != 1:
        raise ValueError("Projection-probe declaration anchor changed")
    live = live.replace(anchor, anchor + "\n" + DECLARATIONS, 1)
    lo, hi = function_span(live, FUNCTION)
    return live[:lo] + SELECTED + live[hi:]


ORIGINAL = "s32 func_15035714() {\n    return 0;\n}"
ANCHOR = "/* Non-matching placeholders for the text-only asm slice asm/61D10.s. */\n"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostic_counts(text):
    rows = []
    for line in text.splitlines():
        match = re.match(r"cfe: Warning (\d+): .*?: (.*)", line)
        if match:
            rows.append((match.group(1), match.group(2)))
        elif line.startswith("cfe:") and "Warning" not in line:
            raise ValueError("Unexpected projection-probe diagnostic: " + line)
    return Counter(rows)


def source_states(live):
    lo, hi = function_span(live, FUNCTION)
    body = live[lo:hi]
    if body == ORIGINAL:
        return live, candidate_source(live), False
    if body == SELECTED.split("\n", 1)[1]:
        purpose = SELECTED.split("\n", 1)[0] + "\n"
        if live.count(DECLARATIONS) != 1 or live.count(purpose) != 1:
            raise ValueError("Installed projection-probe source changed")
        predecessor = live.replace(DECLARATIONS, "", 1)
        lo, hi = function_span(predecessor, FUNCTION)
        predecessor = predecessor[:lo] + ORIGINAL + predecessor[hi:]
        return predecessor.replace(purpose, "", 1), live, True
    raise ValueError("Projection-probe source state changed")


def write_guards(source, destination, include):
    with Path(source).open(newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        rows = [row for row in reader if not
                (row["filename"] == FILENAME and row["function"] == FUNCTION)]
    if include:
        for offset, expected, replacement, relocation in GUARD_ROWS:
            rows.append({
                "filename": FILENAME, "function": FUNCTION,
                "offset": "0x%03X" % offset,
                "expected": "0x%08X" % expected,
                "replacement": "0x%08X" % replacement,
                "expected_relocations": relocation or "-",
                "replacement_relocations": relocation or "-",
                "note": "Normalize reflected projection probe compiler allocation and frame",
                "insert_after": "", "insert_after_relocations": "",
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
        raise ValueError("Projection-probe retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    for offset, rows in RETAIL_BINDINGS.items():
        word = struct.unpack_from(">I", data, offset)[0]
        word = word & (0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000)
        struct.pack_into(">I", data, offset, word)
    return bytes(data)


def checked_candidate(obj):
    raw, bindings = payload(obj, FUNCTION)
    if len(raw) != NATURAL_WORDS * 4 or digest(raw) != RAW_SHA256:
        raise ValueError("Projection-probe natural candidate changed")
    if bindings != RAW_BINDINGS:
        raise ValueError("Projection-probe natural bindings changed")
    words = struct.unpack(">%dI" % NATURAL_WORDS, raw)
    if ((-words[0]) & 0xFFFF) != 0x30:
        raise ValueError("Projection-probe natural frame changed")
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
        raise ValueError("Projection-probe linker owner reference changed")
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
        raise ValueError("Projection-probe predecessor symbol extent changed")
    struct.pack_into(">I", result, rows[0][0] + 8, SIZE)
    return bytes(result)


def check_image(predecessor, actual, retail):
    if actual != expected_image(predecessor, retail):
        raise ValueError("Projection-probe image differs from literal prediction")


def function_blob(obj, name):
    text, functions, relocations = parse_object(obj)
    info = functions[name]
    start, end = info["value"], info["value"] + info["size"]
    bindings = {offset - start: rows for offset, rows in relocations.items()
                if start <= offset < end}
    return text[start:end], bindings


def reference_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    if calls != [0x62FBC] or pointers:
        raise ValueError("Projection-probe reference census changed")
    caller = struct.unpack_from(">8I", image, 0x62FAC)
    required = {2: 0x8FA700E4, 3: 0x8FA600C0, 4: jal,
                5: 0x8FA400D8, 6: 0x10400005}
    if any(caller[index] != word for index, word in required.items()):
        raise ValueError("Projection-probe caller setup changed")
    return {
        "direct_jal_calls": [hex(at) for at in calls],
        "aligned_pointer_literals": [hex(at) for at in pointers],
        "caller": "func_15035808", "actor_argument": "s4",
        "result": "nonzero retires the provisional projection record",
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
    with (root / GUARDS).open(newline="") as stream:
        selected = [row for row in csv.DictReader(stream)
                    if row["filename"] == FILENAME and row["function"] == FUNCTION]
    if installed and len(selected) != len(GUARD_ROWS):
        raise ValueError("Installed projection-probe guards changed")
    if not installed and selected:
        raise ValueError("Projection-probe predecessor guards already exist")

    predecessor_compact, before_diagnostics = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after_diagnostics = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostic_counts(before_diagnostics) != diagnostic_counts(after_diagnostics):
        raise ValueError("Projection-probe owner diagnostics changed")
    raw, bindings = checked_candidate(qualified_compact)
    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_guards, "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, qualified_guards, "qualified-owner")
    live_owner = qualified_owner if installed else predecessor_owner
    if live_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Projection-probe selected owner differs from production")
    if function_blob(qualified_owner, FUNCTION) != (
            retail_object_bytes(root), RETAIL_BINDINGS):
        raise ValueError("Projection-probe guarded owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Projection-probe normalized pools changed")

    predecessor_elf = link_image(root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner, "qualified-image")
    retail = retail_bytes(root)
    check_image(predecessor_elf.read_bytes(), qualified_elf.read_bytes(), retail)
    live_elf = (root / ELF).read_bytes()
    expected_elf = qualified_elf if installed else predecessor_elf
    if live_elf != expected_elf.read_bytes():
        raise ValueError("Projection-probe selected image differs from production")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Projection-probe full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Projection-probe protected data changed")

    (output / "proposed-owner.c").write_text(qualified_source)
    report = {
        "function": FUNCTION, "installed": installed,
        "natural_words": NATURAL_WORDS, "words": WORDS, "frame": FRAME,
        "guards": len(GUARD_ROWS), "insertions": 0,
        "relocations": len(RETAIL_BINDINGS), "neighbors": neighbors,
        "raw_sha256": digest(raw), "retail_sha256": digest(retail),
        "qualified_owner_sha256": digest(qualified_owner.read_bytes()),
        "predecessor_elf_sha256": digest(predecessor_elf.read_bytes()),
        "qualified_elf_sha256": digest(qualified_elf.read_bytes()),
        "functions": len(new), "changed_bodies": changed,
        "all_addresses_fixed": True, "strict_exclusions": 0,
        "references": reference_evidence(root), "game_data": data,
    }
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report, predecessor_owner, qualified_owner, predecessor_elf, qualified_elf


def main():
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)[0], indent=2))


if __name__ == "__main__":
    main()
