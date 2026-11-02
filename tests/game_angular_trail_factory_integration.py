"""Original caller and O32 ABI qualification for the angular trail factory."""
from dataclasses import dataclass
from pathlib import Path
import csv
import json
import struct

from tools.tests import game_oriented_effect_factory_integration as helpers
from tools.match_progress import load_elf_functions


TARGET = 0x15153F18
ROM_BASE = 0x2D4B0
VA_BASE = 0x15000000
JAL_WORD = 0x0D454FC6
J_WORD = 0x09544FC6
LOCALIZED_REQUIRED = set(range(68)) - {0x35, 0x36, 0x37}
DESCRIPTOR_REQUIRED = set(range(8)) | {8 + offset for offset in LOCALIZED_REQUIRED}


@dataclass(frozen=True)
class Site:
    call: int
    parent: str
    start: int
    end: int
    descriptor: int
    proofs: tuple[tuple[int, int, str], ...]


SITES = (
    Site(0x151422A8, "func_15142180", 0x15142180, 0x151422C0, 0x24, (
        (0x1514218C, 0x27A5002C, "A1 = descriptor+8 localized view"),
        (0x15142290, 0x27A40024, "A0 = descriptor angular view"),
        (0x15142294, 0x00003025, "A2 = zero category"),
        (0x15142298, 0x240700FF, "A3 = channel 255"),
        (0x1514228C, 0xAFAD0010, "fifth argument = one"),
    )),
    Site(0x151AEDD0, "func_151AECA0", 0x151AECA0, 0x151AF270, 0xF0, (
        (0x151AEDAC, 0x27A400F0, "A0 = descriptor angular view"),
        (0x151AEDB0, 0x27A500F8, "A1 = descriptor+8 localized view"),
        (0x151AEDB4, 0x27A6013C, "A2 = parent local pointer word"),
        (0x151AEDB8, 0x240700FF, "A3 = channel 255"),
        (0x151AEDA8, 0xAFB80010, "fifth argument = one"),
    )),
    Site(0x151B04FC, "func_151B03B8", 0x151B03B8, 0x151B09BC, 0x12C, (
        (0x151B04D8, 0x27A4012C, "A0 = descriptor angular view"),
        (0x151B04DC, 0x27A50134, "A1 = descriptor+8 localized view"),
        (0x151B04E0, 0x02003025, "A2 = saved category"),
        (0x151B04E4, 0x240700FF, "A3 = channel 255"),
        (0x151B04D4, 0xAFB80010, "fifth argument = one"),
    )),
    Site(0x151DC374, "func_151DC260", 0x151DC260, 0x151DC484, 0x6C, (
        (0x151DC268, 0x27A50074, "A1 = descriptor+8 localized view"),
        (0x151DC354, 0x27A4006C, "A0 = descriptor angular view"),
        (0x151DC350, 0x8FA600BC, "A2 = forwarded category"),
        (0x151DC34C, 0x93A700C7, "A3 = forwarded low byte"),
        (0x151DC378, 0xAFAC0010, "fifth argument = forwarded word"),
    )),
    Site(0x151DC594, "func_151DC484", 0x151DC484, 0x151DC6A0, 0x6C, (
        (0x151DC48C, 0x27A50074, "A1 = descriptor+8 localized view"),
        (0x151DC574, 0x27A4006C, "A0 = descriptor angular view"),
        (0x151DC570, 0x8FA600BC, "A2 = forwarded category"),
        (0x151DC56C, 0x93A700C7, "A3 = forwarded low byte"),
        (0x151DC598, 0xAFAB0010, "fifth argument = forwarded word"),
    )),
)


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
    functions, _, addresses = load_elf_functions(str(root / "conker/build/conker.us.elf"), "mips-linux-gnu-objdump")
    aligned = []
    jumps = []
    for name, words in functions.items():
        start = addresses[name]
        for index, word in enumerate(words):
            if word == JAL_WORD:
                aligned.append((start + index * 4, name))
            elif word == J_WORD:
                jumps.append((start + index * 4, name))
    expected = [(site.call, site.parent) for site in SITES]
    assert aligned == expected, (aligned, expected)
    assert not jumps

    progress = []
    with (root / "conker/progress.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            try:
                start, length = int(row["offset"]), int(row["length"])
            except ValueError:
                continue
            progress.append((row["function"], start, start + length, row["language"], row["filename"]))

    rows = []
    for site in SITES:
        owner = [row for row in progress if row[1] <= site.call < row[2]]
        assert len(owner) == 1 and owner[0][:3] == (site.parent, site.start, site.end), owner
        assert word_at(rom, site.call) == JAL_WORD
        proof_rows = []
        for va, wanted, meaning in site.proofs:
            actual = word_at(rom, va)
            assert actual == wanted, (site.parent, hex(va), hex(actual), hex(wanted))
            proof_rows.append({"va": hex(va), "word": f"0x{actual:08X}", "meaning": meaning})
        covered = stores(rom, site)
        assert DESCRIPTOR_REQUIRED <= covered, (site.parent, sorted(DESCRIPTOR_REQUIRED - covered))
        assert sorted(set(range(76)) - covered) == [0x3D, 0x3E, 0x3F]
        rows.append({
            "call_va": hex(site.call), "parent": site.parent,
            "parent_range": [hex(site.start), hex(site.end)],
            "parent_words": (site.end - site.start) // 4,
            "parent_language": owner[0][3], "owner": owner[0][4],
            "argument_proofs": proof_rows, "required_descriptor_store_bytes": len(DESCRIPTOR_REQUIRED),
            "private_padding_bytes": ["0x3D", "0x3E", "0x3F"],
            "return_taint": return_proof(rom, site),
        })

    source = (root / "conker/src/game_16EE20.c").read_text()
    assert "func_15153F18(&descriptor, &descriptor.point, 0, 255, 1);" in source
    assert "s16 value0, value2, value4, value6;\n    struct17 point;" in source
    report = {
        "success": True, "private_only": True, "matching_credit": 0,
        "target": "func_15153F18", "target_va": hex(TARGET),
        "original_callers": len(SITES), "unique_parents": len({site.parent for site in SITES}),
        "aligned_ELF_JALs": [hex(value) for value, _ in aligned], "aligned_ELF_Js": [],
        "descriptor_natural_bytes": 76, "descriptor_required_bytes": len(DESCRIPTOR_REQUIRED),
        "angular_required_bytes": 8, "localized_input_required_bytes": len(LOCALIZED_REQUIRED),
        "private_padding_bytes": ["0x3D", "0x3E", "0x3F"],
        "all_callers_initialize_required_descriptor_bytes": True,
        "typed_exact_C_caller_confirms_overlapping_root_and_plus8_views": True,
        "argument_contract": {
            "arg0": "pointer to the 8-byte angular prefix",
            "arg1": "arg0+8 pointer to the 68-byte localized configuration",
            "arg2": "full s32 category or pointer-sized payload",
            "arg3": "logical u8 channel reloaded from the big-endian low home byte",
            "arg4": "full s32 fifth argument in the O32 outgoing stack slot",
            "return": "void; conservative V0 taint reaches no post-call read",
        },
        "caller_sites": rows, "full_parent_execution_claimed": False,
        "alternate_source_used_for_ABI_proof": False,
    }
    (output / "private-caller-v1.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    root = Path.cwd()
    output = root / "conker/build/game-angular-trail-factory-15153F18-match"
    print(json.dumps(qualify(root, output), indent=2))
