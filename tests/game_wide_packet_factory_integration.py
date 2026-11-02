from pathlib import Path
import csv
import json
import struct

from tools.tests import game_oriented_effect_factory_integration as helpers

TARGET = 0x151539B4
ROM_BASE = 0x2D4B0
VA_BASE = 0x15000000
JAL_WORD = 0x0D454E6D
J_WORD = 0x09544E6D

def word_at(rom, va):
    return struct.unpack_from(">I", rom, ROM_BASE + va - VA_BASE)[0]


def qualify(root: Path, output: Path):
    sites = (
        helpers.Callsite(
            0x150B2AD0, "func_150B2740", 0x150B2740, 0x150B2EB4, 0x14C,
            (
                (0x150B2AB4, 0x27A4014C, "input = SP+0x14C"),
                (0x150B2AB8, 0x326500FF, "mode = low byte of S3"),
            ),
        ),
        helpers.Callsite(
            0x15156A14, "func_151568F8", 0x151568F8, 0x15156B54, 0x98,
            (
                (0x15156914, 0x27A40098, "input = SP+0x98"),
                (0x15156940, 0x93A500E7, "mode = caller argument byte from SP+0xE7"),
            ),
        ),
    )
    rom = (root / "conker/conker.us.bin").read_bytes()
    all_words = struct.unpack(f">{len(rom) // 4}I", rom[:len(rom) & ~3])
    jal_rom = [index * 4 for index, word in enumerate(all_words) if word == JAL_WORD]
    jump_rom = [index * 4 for index, word in enumerate(all_words) if word == J_WORD]
    pointer_rom = [index * 4 for index, word in enumerate(all_words) if word == TARGET]
    expected_jals = [ROM_BASE + site.call - VA_BASE for site in sites]
    assert jal_rom == expected_jals, (jal_rom, expected_jals)
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
            progress_rows.append((row["function"], start, start + length, row["language"]))

    required = set(range(0x47)) - {0x31}
    report_sites = []
    all_required_written = True
    for site in sites:
        owner = [row for row in progress_rows if row[1] <= site.call < row[2]]
        assert len(owner) == 1 and owner[0][:3] == (site.parent, site.parent_start, site.parent_end), owner
        assert word_at(rom, site.call) == JAL_WORD
        proof_rows = []
        for va, expected, meaning in site.proofs:
            actual = word_at(rom, va)
            assert actual == expected, (site.parent, va, actual, expected)
            proof_rows.append({"va": hex(va), "word": f"0x{actual:08X}", "meaning": meaning})
        covered = helpers.descriptor_store_bytes(rom, site)
        missing = sorted(required - covered)
        all_required_written &= not missing
        report_sites.append({
            "call_va": hex(site.call),
            "call_rom": hex(ROM_BASE + site.call - VA_BASE),
            "parent": site.parent,
            "parent_range": [hex(site.parent_start), hex(site.parent_end)],
            "parent_words": (site.parent_end - site.parent_start) // 4,
            "parent_language": owner[0][3],
            "input": f"SP+0x{site.descriptor:X}",
            "argument_proofs": proof_rows,
            "input_bytes_written_by_static_union": len(covered & required),
            "required_input_bytes_missing_from_static_union": [hex(value) for value in missing],
            "return_taint": helpers.return_value_is_unconsumed(rom, site),
        })

    prologue = [word_at(rom, TARGET + 4 * index) for index in range(7)]
    assert prologue == [
        0x27BDFF48, 0xAFB40054, 0xAFB00044, 0x00808025,
        0x30B400FF, 0xAFBF005C, 0xAFB50058,
    ]
    assert all_required_written, [
        (row["parent"], row["required_input_bytes_missing_from_static_union"])
        for row in report_sites
    ]
    report = {
        "success": True,
        "private_only": True,
        "matching_credit": 0,
        "target": "func_151539B4",
        "target_va": hex(TARGET),
        "original_callers": len(sites),
        "aligned_ROM_JALs": [hex(value) for value in jal_rom],
        "aligned_ROM_Js": [],
        "aligned_ROM_pointer_literals": [],
        "unique_parents": len({site.parent for site in sites}),
        "argument_contract": {
            "input": "pointer to a 0x47-byte live extent in a 0x48-byte natural object; byte 0x31 and tail byte 0x47 are private/unread",
            "mode": "u8: both callers provide one byte and the callee repeats ANDI 0xFF",
            "return": "void: conservative V0 taint reaches no read on any post-call control-flow path",
        },
        "required_input_bytes": len(required),
        "private_unread_input_bytes": ["0x31", "0x47"],
        "all_required_input_bytes_have_pre_call_store_evidence": all_required_written,
        "caller_sites": report_sites,
        "full_parent_execution_claimed": False,
        "alternate_source_used_for_ABI_proof": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "private-caller-v3.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(qualify(Path.cwd(), Path.cwd()), indent=2))
