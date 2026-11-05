"""Qualify func_150C2700's fixed effect-band packet callback as guarded C."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

from tools import pad_generated_object

sys.modules.setdefault("pad_generated_object", pad_generated_object)

from tools import pad_c_object
from tools.experiments import game_effect_band_packet_callback_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game_EF410.c.o"
ASM = "conker/asm/nonmatchings/game_EF410/func_150C2700.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22EF80.rodata.s"
LAYOUT = "conker/retail_layout.us.txt"
BUILD = "conker/build/game-effect-band-packet-callback-150C2700-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_SIZE = 66 * 4
NATURAL_FRAME = RETAIL_FRAME = 0x68
RAW_SHA256 = "b115a366a626904c2fa1722f2162ec22c78cb7cc89750f4a47f3c645f0ad12c8"
RETAIL_SHA256 = "f37e65e340eb33515ecba468408eb38f24eb250fa7407e22042fe7ae9e5105a4"
BINDINGS = {
    0x02C: [("R_MIPS_HI16", "D_800A0274")],
    0x030: [("R_MIPS_LO16", "D_800A0274")],
    0x034: [("R_MIPS_HI16", "D_800A0278")],
    0x038: [("R_MIPS_LO16", "D_800A0278")],
    0x048: [("R_MIPS_HI16", "D_800A027C")],
    0x050: [("R_MIPS_LO16", "D_800A027C")],
    0x0EC: [("R_MIPS_26", "func_15150178")],
}
RETAIL_BINDINGS = candidate.RETAIL_BINDINGS
PATCH_NOTE = (
    "Normalize fixed effect-band packet compiler scheduling and duplicate constant load"
)
PATCH_ROWS = (
    dict(offset="0x03C", expected="0x240E006B", replacement="0x240F0005"),
    dict(offset="0x040", expected="0x240F0046", replacement="0x2418006B"),
    dict(offset="0x044", expected="0x2418FFE1", replacement="0x3C010000",
         replacement_relocations="R_MIPS_HI16:D_800A027C"),
    dict(offset="0x048", expected="0x3C010000", replacement="0xC7A40078",
         expected_relocations="R_MIPS_HI16:D_800A027C"),
    dict(offset="0x04C", expected="0xC7A40078", replacement="0xC4320000",
         replacement_relocations="R_MIPS_LO16:D_800A027C"),
    dict(offset="0x050", expected="0xC4320000", replacement="0xA7AF0036",
         expected_relocations="R_MIPS_LO16:D_800A027C"),
    dict(offset="0x054", expected="0xA7AE0020", replacement="0xA7B80020"),
    dict(offset="0x058", expected="0xA7AF0022", replacement="0x240E0006"),
    dict(offset="0x05C", expected="0xA7B80024", replacement="0x24190046"),
    dict(offset="0x060", expected="0x2419002E", replacement="0x2408FFE1"),
    dict(offset="0x064", expected="0x24080006", replacement="0x2409002E"),
    dict(offset="0x068", expected="0x24090005", replacement="0x240A0064"),
    dict(offset="0x06C", expected="0x240A0064", replacement="0x240B009B"),
    dict(offset="0x070", expected="0x240B009B", replacement="0x240C0064"),
    dict(offset="0x074", expected="0x240C0064", replacement="0x240D0001"),
    dict(offset="0x078", expected="0x240D0001", replacement="0x240F0001"),
    dict(offset="0x07C", expected="0x240E0006", replacement="0x240E0006",
         omit="true"),
    dict(offset="0x080", expected="0x240F0001", replacement="0x24180001"),
    dict(offset="0x084", expected="0x24180001", replacement="0xE7AC0028"),
    dict(offset="0x088", expected="0xA7B90026", replacement="0xE7AE002C"),
    dict(offset="0x08C", expected="0xE7AC0028", replacement="0xA7AE0034"),
    dict(offset="0x090", expected="0xE7AE002C", replacement="0xA7B90022"),
    dict(offset="0x094", expected="0xA7A80034", replacement="0xA7A80024"),
    dict(offset="0x098", expected="0xA7A90036", replacement="0xA7A90026"),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def complete_row(row):
    return {
        "filename": FILENAME,
        "function": FUNCTION,
        "offset": row["offset"],
        "expected": row["expected"],
        "replacement": row["replacement"],
        "expected_relocations": row.get("expected_relocations", "-"),
        "replacement_relocations": row.get("replacement_relocations", "-"),
        "note": PATCH_NOTE,
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": row.get("omit", "false"),
    }


def relocation_spec(value):
    if not value or value == "-":
        return []
    return [tuple(item.split(":", 1)) for item in value.split(";")]


def normalized_payload(raw, bindings):
    rows = {int(row["offset"], 0): complete_row(row) for row in PATCH_ROWS}
    if len(rows) != len(PATCH_ROWS):
        raise ValueError("Effect-band packet guard offsets overlap")
    output = bytearray()
    output_bindings = {}
    applied = set()
    for offset in range(0, len(raw), 4):
        word = struct.unpack_from(">I", raw, offset)[0]
        relocations = bindings.get(offset, [])
        row = rows.get(offset)
        if row is not None:
            if (word != int(row["expected"], 0) or
                    relocations != relocation_spec(row["expected_relocations"])):
                raise ValueError(
                    "Effect-band packet guard preimage changed at 0x%X" % offset
                )
            applied.add(offset)
            if row["omit"] == "true":
                if relocations:
                    raise ValueError("Effect-band packet omitted a relocation")
                continue
            word = int(row["replacement"], 0)
            relocations = relocation_spec(row["replacement_relocations"])
        if relocations:
            output_bindings[len(output)] = relocations
        output.extend(struct.pack(">I", word))
    if applied != set(rows):
        raise ValueError("Effect-band packet guard closure changed")
    if len(output) != SIZE:
        raise ValueError("Effect-band packet normalized size changed")
    return bytes(output), output_bindings


def source_states(live):
    declarations = candidate.DECLARATIONS + "\n"
    marker = "extern f32 D_800A026C;\n"
    if live.count(candidate.PLACEHOLDER_BLOCK) == 1:
        if (candidate.SELECTED in live or declarations in live or
                live.count(candidate.OLD_PROTOTYPE) != 1 or
                candidate.PROTOTYPE in live):
            raise ValueError("Effect-band packet predecessor source changed")
        qualified = live.replace(
            candidate.OLD_PROTOTYPE, candidate.PROTOTYPE, 1
        ).replace(marker, marker + declarations, 1).replace(
            candidate.PLACEHOLDER_BLOCK, candidate.SELECTED, 1
        )
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if (live.count(declarations) != 1 or
                live.count(candidate.PROTOTYPE) != 1 or
                candidate.PLACEHOLDER_BLOCK in live):
            raise ValueError("Installed effect-band packet source changed")
        predecessor = live.replace(
            candidate.PROTOTYPE, candidate.OLD_PROTOTYPE, 1
        ).replace(declarations, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER_BLOCK, 1
        )
        return predecessor, live, True
    raise ValueError("Effect-band packet source state changed")


def checked_candidate(root, obj):
    raw, bindings = harness.function_blob(obj)
    if len(raw) != NATURAL_SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Effect-band packet natural candidate changed")
    if ((-struct.unpack_from(">I", raw)[0]) & 0xFFFF) != NATURAL_FRAME:
        raise ValueError("Effect-band packet natural frame changed")
    if bindings != BINDINGS:
        raise ValueError("Effect-band packet natural bindings changed")
    if normalized_payload(raw, bindings) != (
            harness.retail_object_bytes(root), RETAIL_BINDINGS):
        raise ValueError("Effect-band packet normalized payload differs from retail")
    return raw, bindings


def assemble_owner(root, output, compact, rows, fields, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    patch_file = owner_dir / "retail-word-patches.csv"
    harness.write_patches(patch_file, fields, rows)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(pad_c_object.emit_padded_assembly(
        compact, root / LAYOUT, FILENAME,
        word_patches_path=patch_file,
    ))
    obj = owner_dir / (FILENAME + ".c.o")
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(obj),
        str(assembly),
    ], check=True, capture_output=True)
    return obj


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_8008AA00\n", 1)[1].split(
        "enddlabel D_8008AA00", 1
    )[0]
    entries = [line.split(".word", 1)[1].strip()
               for line in block.splitlines() if ".word" in line]
    if (calls or pointers != [0x22F4CC] or len(entries) != 28 or
            entries[3] != FUNCTION or block.count(FUNCTION) != 1):
        raise ValueError("Effect-band packet callback registry evidence changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x22f4cc"],
        "registry": "D_8008AA00[3]",
        "abi": (
            "f32 x/y/z in arguments 2/3/4 and unsigned-byte channel in "
            "argument 14; submits one fixed effect-band packet and returns one"
        ),
    }


def prepare(root, output=None):
    replacements = {
        "candidate": candidate,
        "FUNCTION": FUNCTION,
        "FILENAME": FILENAME,
        "SOURCE": SOURCE,
        "OBJECT": OBJECT,
        "ASM": ASM,
        "GUARDS": GUARDS,
        "ELF": ELF,
        "LINKER": LINKER,
        "ROM_IMAGE": ROM_IMAGE,
        "REGISTRY": REGISTRY,
        "BUILD": BUILD,
        "ENTRY": ENTRY,
        "ROM": ROM,
        "WORDS": WORDS,
        "SIZE": SIZE,
        "NATURAL_FRAME": NATURAL_FRAME,
        "RETAIL_FRAME": RETAIL_FRAME,
        "RAW_SHA256": RAW_SHA256,
        "RETAIL_SHA256": RETAIL_SHA256,
        "BINDINGS": BINDINGS,
        "RETAIL_BINDINGS": RETAIL_BINDINGS,
        "PATCH_ROWS": PATCH_ROWS,
        "complete_row": complete_row,
        "source_states": source_states,
        "checked_candidate": checked_candidate,
        "assemble_owner": assemble_owner,
        "registry_evidence": registry_evidence,
    }
    saved = {name: getattr(harness, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(harness, name, value)
        result = harness.prepare(root, output or Path(root) / BUILD)
    finally:
        for name, value in saved.items():
            setattr(harness, name, value)
    report = result["report"]
    if (report["raw_sha256"] != RAW_SHA256 or
            report["retail_sha256"] != RETAIL_SHA256 or
            report["natural_positional_differences"] != len(PATCH_ROWS) or
            report["guards"] != len(PATCH_ROWS) or
            report["changed_bodies"] != [FUNCTION]):
        raise ValueError("Effect-band packet qualification report changed")
    report.update({
        "natural_words": NATURAL_SIZE // 4,
        "retail_words": WORDS,
        "omissions": 1,
        "natural_relocations": len(BINDINGS),
        "retail_relocations": len(RETAIL_BINDINGS),
    })
    (Path(output or Path(root) / BUILD) / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
