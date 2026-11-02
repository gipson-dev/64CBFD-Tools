from pathlib import Path
import csv
import json
import struct

from tools.tests import game_oriented_effect_factory_integration as helpers

TARGET = 0x15153298
ROM_BASE = 0x2D4B0
VA_BASE = 0x15000000
JAL_WORD = 0x0D454CA6
J_WORD = 0x09544CA6


def word_at(rom, va):
    return struct.unpack_from(">I", rom, ROM_BASE + va - VA_BASE)[0]


def qualify(root: Path, output: Path):
    site = helpers.Callsite(
        0x150DBC30, "func_150DB9E0", 0x150DB9E0, 0x150DBC60, 0x38,
        (
            (0x150DBC14, 0x27A40038, "input = SP+0x38"),
            (0x150DBC18, 0x320500FF, "mode = low byte of S0"),
            (0x150DBC1C, 0x24060001, "owner/extra argument = 1"),
        ),
    )
    rom = (root / "conker/conker.us.bin").read_bytes()
    all_words = struct.unpack(f">{len(rom) // 4}I", rom[:len(rom) & ~3])
    jal_rom = [index * 4 for index, word in enumerate(all_words) if word == JAL_WORD]
    jump_rom = [index * 4 for index, word in enumerate(all_words) if word == J_WORD]
    pointer_rom = [index * 4 for index, word in enumerate(all_words) if word == TARGET]
    expected_jal = ROM_BASE + site.call - VA_BASE
    assert jal_rom == [expected_jal], (jal_rom, expected_jal)
    assert not jump_rom
    assert not pointer_rom

    progress_rows = []
    with (root / "conker/progress.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            try:
                start = int(row["offset"])
                length = int(row["length"])
            except ValueError:
                continue
            progress_rows.append((row["function"], start, start + length, row["language"] ))
    owner = [row for row in progress_rows if row[1] <= site.call < row[2]]
    assert len(owner) == 1 and owner[0][:3] == (site.parent, site.parent_start, site.parent_end), owner

    proof_rows = []
    for va, expected, meaning in site.proofs:
        actual = word_at(rom, va)
        assert actual == expected, (va, actual, expected)
        proof_rows.append({"va": hex(va), "word": f"0x{actual:08X}", "meaning": meaning})

    required = set(range(0x3E))
    covered = helpers.descriptor_store_bytes(rom, site)
    missing = sorted(required - covered)
    assert not missing, missing
    taint = helpers.return_value_is_unconsumed(rom, site)

    prologue = [word_at(rom, TARGET + 4 * index) for index in range(9)]
    assert prologue == [
        0x27BDFF40, 0x3C014380, 0xAFB5005C, 0xAFB40058, 0xAFB00048,
        0x44810000, 0x00808025, 0x30B400FF, 0x00C0A825,
    ]

    report = {
        "success": True,
        "private_only": True,
        "matching_credit": 0,
        "target": "func_15153298",
        "target_va": hex(TARGET),
        "original_callers": 1,
        "aligned_ROM_JALs": [hex(value) for value in jal_rom],
        "aligned_ROM_Js": [],
        "aligned_ROM_pointer_literals": [],
        "unique_parents": 1,
        "argument_contract": {
            "input": "pointer to a 0x3E-byte stack input record",
            "mode": "u8: caller masks to one byte and callee repeats ANDI 0xFF",
            "owner": "s32: caller passes constant 1 and callee preserves the full word",
            "return": "void: conservative V0 taint reaches no read on any post-call control-flow path",
        },
        "required_input_bytes": len(required),
        "all_required_input_bytes_have_pre_call_store_evidence": True,
        "caller_sites": [{
            "call_va": hex(site.call),
            "call_rom": hex(expected_jal),
            "parent": site.parent,
            "parent_range": [hex(site.parent_start), hex(site.parent_end)],
            "parent_words": (site.parent_end - site.parent_start) // 4,
            "parent_language": owner[0][3],
            "input": "SP+0x38",
            "argument_proofs": proof_rows,
            "input_bytes_written_by_static_union": len(covered & required),
            "required_input_bytes_missing_from_static_union": [],
            "return_taint": taint,
        }],
        "full_parent_execution_claimed": False,
        "alternate_source_used_for_ABI_proof": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "private-caller-v5.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(qualify(Path.cwd(), Path.cwd()), indent=2))

