"""Original caller and O32 ABI qualification for the directional-effect factory."""
from dataclasses import dataclass
from pathlib import Path
import csv
import json
import struct

from tools.tests import game_oriented_effect_factory_integration as helpers


TARGET = 0x15154684
ROM_BASE = 0x2D4B0
VA_BASE = 0x15000000
JAL_WORD = 0x0D4551A1
J_WORD = 0x094551A1
PRIVATE = {0x08, 0x09, 0x0C, 0x0D, 0x2A, 0x2B}
REQUIRED = set(range(60)) - PRIVATE


@dataclass(frozen=True)
class Site:
    call: int
    parent: str
    start: int
    end: int
    descriptor: int
    proofs: tuple[tuple[int, int, str], ...]


SITE = Site(0x151C6278, "func_151C61A0", 0x151C61A0, 0x151C6290, 0x1C, (
    (0x151C6250, 0x27A4001C, "A0 = SP+0x1C descriptor"),
    (0x151C6254, 0x93A50063, "A1 = caller byte at SP+0x63"),
    (0x151C6258, 0x00E03025, "A2 = forwarded fourth parent argument"),
    (0x151C627C, 0xAFAE0054, "delay slot stores final descriptor requestValue"),
))


def word_at(rom, va):
    return struct.unpack_from(">I", rom, ROM_BASE + va - VA_BASE)[0]


def stores(rom, site):
    row = helpers.Callsite(site.call, site.parent, site.start, site.end, site.descriptor, ())
    return helpers.descriptor_store_bytes(rom, row)


def return_proof(rom, site):
    row = helpers.Callsite(site.call, site.parent, site.start, site.end, 0, ())
    return helpers.return_value_is_unconsumed(rom, row)


def qualify(root, output):
    rom = (root / "conker/conker.us.bin").read_bytes()
    all_words = struct.unpack(f">{len(rom) // 4}I", rom[:len(rom) & ~3])
    aligned = [index * 4 for index, word in enumerate(all_words) if word == JAL_WORD]
    jumps = [index * 4 for index, word in enumerate(all_words) if word == J_WORD]
    pointers = [index * 4 for index, word in enumerate(all_words) if word == TARGET]
    expected_rom = ROM_BASE + SITE.call - VA_BASE
    assert aligned == [expected_rom], aligned
    assert not jumps
    assert not pointers

    progress = []
    with (root / "conker/progress.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            try:
                start, length = int(row["offset"]), int(row["length"])
            except ValueError:
                continue
            progress.append((row["function"], start, start + length, row["language"], row["filename"]))

    owner = [row for row in progress if row[1] <= SITE.call < row[2]]
    assert len(owner) == 1 and owner[0][:3] == (SITE.parent, SITE.start, SITE.end), owner
    assert word_at(rom, SITE.call) == JAL_WORD
    proof_rows = []
    for va, wanted, meaning in SITE.proofs:
        actual = word_at(rom, va)
        assert actual == wanted, (hex(va), hex(actual), hex(wanted))
        proof_rows.append({"va": hex(va), "word": f"0x{actual:08X}", "meaning": meaning})

    covered = stores(rom, SITE)
    assert REQUIRED <= covered, sorted(REQUIRED - covered)
    missing = sorted(set(range(60)) - covered)
    assert missing == [0x2A, 0x2B], missing
    taint = return_proof(rom, SITE)
    report = {
        "success": True, "private_only": True, "matching_credit": 0,
        "target": "func_15154684", "target_va": hex(TARGET),
        "original_callers": 1, "unique_parents": 1,
        "aligned_ROM_JALs": [hex(value) for value in aligned], "aligned_ROM_Js": [],
        "aligned_ROM_pointer_literals": [],
        "input_natural_bytes": 60, "input_required_bytes": len(REQUIRED),
        "private_bytes": [f"0x{value:02X}" for value in sorted(PRIVATE)],
        "caller_written_bytes": len(covered & set(range(60))),
        "caller_unwritten_bytes": [f"0x{value:02X}" for value in missing],
        "all_required_input_bytes_have_pre_call_store_evidence": True,
        "argument_contract": {
            "arg0": "pointer to the 60-byte SP+0x1C descriptor",
            "arg1": "logical u8 channel loaded from the caller's low byte",
            "arg2": "full s32 fourth parent argument forwarded in A2",
            "return": "void; conservative V0 taint reaches no post-call read",
        },
        "caller_site": {
            "call_va": hex(SITE.call), "parent": SITE.parent,
            "parent_range": [hex(SITE.start), hex(SITE.end)],
            "parent_words": (SITE.end - SITE.start) // 4,
            "parent_language": owner[0][3], "owner": owner[0][4],
            "argument_proofs": proof_rows,
            "required_input_store_bytes": len(REQUIRED),
            "return_taint": taint,
        },
        "full_parent_execution_claimed": False,
        "alternate_source_used_for_ABI_proof": False,
    }
    (output / "private-caller-v1.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    root = Path.cwd()
    output = root / "conker/build/game-direction-effect-factory-15154684-match"
    print(json.dumps(qualify(root, output), indent=2))
