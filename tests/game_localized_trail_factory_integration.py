from dataclasses import dataclass
from pathlib import Path
import csv
import json
import struct

from tools.tests import game_oriented_effect_factory_integration as helpers


TARGET = 0x15153CCC
WRAPPER = 0x15153C84
TRIANGLE = 0x1514F640
ROM_BASE = 0x2D4B0
VA_BASE = 0x15000000
JAL_WORD = 0x0D454F33
J_WORD = 0x09544F33
WRAPPER_JAL = 0x0D454F21
INPUT_REQUIRED = set(range(68)) - {0x35, 0x36, 0x37}
TRANSFORM_REQUIRED = {0} | set(range(4, 44))


@dataclass(frozen=True)
class Site:
    call: int
    parent: str
    start: int
    end: int
    config: int | None
    transform: int | None
    proofs: tuple[tuple[int, int, str], ...]


SITES = (
    Site(0x150DAC0C, "func_150DA67C", 0x150DA67C, 0x150DAE70, 0xF8, 0xA8, (
        (0x150DAA80, 0x27B200F8, "config = SP+0xF8"),
        (0x150DAC00, 0x27A400A8, "transform = SP+0xA8"),
        (0x150DAC04, 0x02402825, "A1 = config"),
        (0x150DAC08, 0x02003025, "A2 = saved integer argument"),
        (0x150DABFC, 0x9267000C, "A3 = caller byte"),
        (0x150DAC10, 0xAFAC0010, "fifth argument = caller byte promoted to word"),
    )),
    Site(0x15153CB4, "func_15153C84", 0x15153C84, 0x15153CCC, None, 0x24, (
        (0x15153C98, 0x0D453D90, "matched triangle-record builder supplies transform"),
        (0x15153C9C, 0x27A50024, "builder output = SP+0x24"),
        (0x15153CA4, 0x27A40024, "A0 = helper-produced transform"),
        (0x15153CA8, 0x8FA50054, "A1 = forwarded config pointer"),
        (0x15153CAC, 0x8FA60058, "A2 = forwarded integer argument"),
        (0x15153CB0, 0x93A7005F, "A3 = low byte of forwarded word"),
        (0x15153CB8, 0xAFAE0010, "fifth argument = forwarded full word"),
    )),
    Site(0x151D0CA0, "func_151D09A8", 0x151D09A8, 0x151D0ED8, 0xEC, 0x180, (
        (0x151D0BCC, 0x27A500EC, "config = SP+0xEC"),
        (0x151D0AC0, 0x27B60180, "transform = SP+0x180"),
        (0x151D0C80, 0x02C02025, "A0 = transform"),
        (0x151D0C84, 0x02203025, "A2 = saved integer argument"),
        (0x151D0C88, 0x324700FF, "A3 = low byte of saved argument"),
        (0x151D0C7C, 0xAFB30010, "fifth argument = saved full word"),
    )),
)


def word_at(rom, va):
    return struct.unpack_from(">I", rom, ROM_BASE + va - VA_BASE)[0]


def stores(rom, site, base):
    row = helpers.Callsite(site.call, site.parent, site.start, site.end, base, ())
    return helpers.descriptor_store_bytes(rom, row)


def return_proof(rom, site):
    row = helpers.Callsite(site.call, site.parent, site.start, site.end, 0, ())
    return helpers.return_value_is_unconsumed(rom, row)


def qualify(root, output):
    rom = (root / "conker/conker.us.bin").read_bytes()
    words = struct.unpack(f">{len(rom) // 4}I", rom[:len(rom) & ~3])
    jal_rom = [index * 4 for index, word in enumerate(words) if word == JAL_WORD]
    jump_rom = [index * 4 for index, word in enumerate(words) if word == J_WORD]
    pointer_rom = [index * 4 for index, word in enumerate(words) if word == TARGET]
    expected = [ROM_BASE + site.call - VA_BASE for site in SITES]
    assert jal_rom == expected, (jal_rom, expected)
    assert not jump_rom and not pointer_rom

    wrapper_jals = [index * 4 for index, word in enumerate(words) if word == WRAPPER_JAL]
    assert wrapper_jals == [ROM_BASE + 0x150DACD4 - VA_BASE]
    assert word_at(rom, 0x150DACD4) == WRAPPER_JAL
    assert word_at(rom, 0x150DACC8) == 0x27A40084
    assert word_at(rom, 0x150DACCC) == 0x02402825
    assert word_at(rom, 0x150DACD0) == 0x02003025
    assert word_at(rom, 0x150DACD8) == 0xAFAB0010

    progress = []
    with (root / "conker/progress.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            try:
                start = int(row["offset"])
                end = start + int(row["length"])
            except ValueError:
                continue
            progress.append((row["function"], start, end, row["language"]))

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
        config_covered = stores(rom, site, site.config) if site.config is not None else set()
        transform_covered = stores(rom, site, site.transform) if site.transform is not None and site.parent != "func_15153C84" else set()
        if site.config is not None:
            assert INPUT_REQUIRED <= config_covered
            assert sorted(set(range(68)) - config_covered) == [0x35, 0x36, 0x37]
        if transform_covered:
            assert TRANSFORM_REQUIRED <= transform_covered
            assert sorted(set(range(44)) - transform_covered) == [1, 2, 3]
        rows.append({
            "call_va": hex(site.call),
            "call_rom": hex(ROM_BASE + site.call - VA_BASE),
            "parent": site.parent,
            "parent_range": [hex(site.start), hex(site.end)],
            "parent_words": (site.end - site.start) // 4,
            "parent_language": owner[0][3],
            "argument_proofs": proof_rows,
            "config_required_store_bytes": len(INPUT_REQUIRED) if site.config is not None else "forwarded from sole original wrapper caller",
            "transform_required_store_bytes": len(TRANSFORM_REQUIRED) if transform_covered else "matched helper contract",
            "return_taint": return_proof(rom, site),
        })

    # The wrapper's sole original caller forwards the same fully initialized
    # SP+0xF8 config used by the neighboring direct target call.
    upstream = SITES[0]
    upstream_wrapper = Site(0x150DACD4, upstream.parent, upstream.start, upstream.end, 0xF8, None, ())
    upstream_config = stores(rom, upstream_wrapper, 0xF8)
    assert INPUT_REQUIRED <= upstream_config
    assert sorted(set(range(68)) - upstream_config) == [0x35, 0x36, 0x37]

    source = (root / "conker/src/game/generated_17CAF0.c").read_text()
    helper_contract = (
        "output[0] = 2;",
        "*(f32 *)(output + 0x28)",
        "(f32 *)(output + 0x10)",
        "(f32 *)(output + 0x1C)",
        "(f32 *)(output + 4)",
    )
    assert all(token in source for token in helper_contract)

    report = {
        "success": True,
        "private_only": True,
        "matching_credit": 0,
        "target": "func_15153CCC",
        "target_va": hex(TARGET),
        "original_callers": len(SITES),
        "aligned_ROM_JALs": [hex(value) for value in jal_rom],
        "aligned_ROM_Js": [],
        "aligned_ROM_pointer_literals": [],
        "unique_parents": len({site.parent for site in SITES}),
        "wrapper_original_callers": 1,
        "wrapper_upstream_call_va": hex(0x150DACD4),
        "input_natural_bytes": 68,
        "input_required_bytes": len(INPUT_REQUIRED),
        "input_private_padding_bytes": ["0x35", "0x36", "0x37"],
        "transform_natural_bytes": 44,
        "transform_required_bytes": len(TRANSFORM_REQUIRED),
        "transform_private_padding_bytes": ["0x1", "0x2", "0x3"],
        "direct_callers_initialize_all_required_config_and_transform_bytes": True,
        "wrapper_forwards_fully_initialized_config_from_sole_original_caller": True,
        "wrapper_uses_byte_exact_triangle_builder_for_required_transform_bytes": True,
        "argument_contract": {
            "transform": "pointer to 0x2C-byte record; byte 0 and bytes 4..43 are required, bytes 1..3 are private padding",
            "config": "pointer to 0x44-byte record; all named fields are initialized, bytes 0x35..0x37 are private padding",
            "arg2": "full s32 forwarded unchanged",
            "arg3": "u8 logical channel supplied by LBU or ANDI and reloaded from the big-endian low home byte",
            "arg4": "full s32 fifth argument supplied in the O32 outgoing stack slot",
            "return": "void contract; conservative V0 taint reaches no read on any post-call path",
        },
        "caller_sites": rows,
        "full_parent_execution_claimed": False,
        "alternate_source_used_for_ABI_proof": False,
    }
    (output / "private-caller-v3.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(qualify(Path.cwd(), Path(__file__).parent), indent=2), flush=True)
