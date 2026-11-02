from __future__ import annotations

import csv
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path


TARGET = 0x15152F70
ROM_BASE = 0x2D4B0
VA_BASE = 0x15000000
JAL_WORD = 0x0D454BDC
J_WORD = 0x09544BDC


@dataclass(frozen=True)
class Callsite:
    call: int
    parent: str
    parent_start: int
    parent_end: int
    descriptor: int
    proofs: tuple[tuple[int, int, str], ...]


CALLS = (
    Callsite(0x150B2BD4, "func_150B2740", 0x150B2740, 0x150B2EB4, 0xF4, (
        (0x150B2BB8, 0x02002025, "input = saved SP+0xF4"),
        (0x150B2BBC, 0x326500FF, "mode = low byte of S3"),
    )),
    Callsite(0x150B2C0C, "func_150B2740", 0x150B2740, 0x150B2EB4, 0xF4, (
        (0x150B2C08, 0x02002025, "input = saved SP+0xF4"),
        (0x150B2C10, 0x326500FF, "mode = low byte of S3 (delay)"),
    )),
    Callsite(0x150DBB10, "func_150DB9E0", 0x150DB9E0, 0x150DBC60, 0x78, (
        (0x150DBAEC, 0x27A40078, "input = SP+0x78"),
        (0x150DBAF0, 0x320500FF, "mode = low byte of S0"),
    )),
    Callsite(0x150DBD58, "func_150DBC60", 0x150DBC60, 0x150DBD70, 0x18, (
        (0x150DBD54, 0x90C5000C, "mode = LBU owner+0x0C"),
        (0x150DBD5C, 0x27A40018, "input = SP+0x18 (delay)"),
    )),
    Callsite(0x1514B6A4, "func_1514B364", 0x1514B364, 0x1514B844, 0xBC, (
        (0x1514B6A0, 0x27A400BC, "input = SP+0xBC"),
        (0x1514B6A8, 0x240500FF, "mode = 0xFF (delay)"),
    )),
)


def word_at(rom: bytes, va: int) -> int:
    return struct.unpack_from(">I", rom, ROM_BASE + va - VA_BASE)[0]


def words(rom: bytes, start: int, end: int) -> list[int]:
    return [word_at(rom, va) for va in range(start, end, 4)]


def reads_register(word: int, reg: int) -> bool:
    op = word >> 26
    rs = word >> 21 & 31
    rt = word >> 16 & 31
    fn = word & 63
    if op == 0:
        if fn in (0, 2, 3):
            return rt == reg
        if fn in (8, 9, 16, 17, 18, 19):
            return rs == reg
        if fn in (24, 25, 26, 27):
            return rs == reg or rt == reg
        return rs == reg or rt == reg
    if op in (2, 3, 15):
        return False
    if op in (4, 5, 20, 21):
        return rs == reg or rt == reg
    if op in (6, 7, 22, 23):
        return rs == reg
    if op in (40, 41, 42, 43, 46, 47, 56, 57, 61):
        return rs == reg or rt == reg
    return rs == reg


def writes_register(word: int, reg: int) -> bool:
    op = word >> 26
    rt = word >> 16 & 31
    rd = word >> 11 & 31
    fn = word & 63
    if reg == 0:
        return False
    if op == 0:
        if fn in (8, 24, 25, 26, 27, 48, 49, 50, 51):
            return False
        if fn == 9:
            return (rd or 31) == reg
        if fn in (16, 18):
            return rd == reg
        if fn in (17, 19):
            return False
        return rd == reg
    if op == 3:
        return reg == 31
    if op in (1,):
        return reg == 31 and rt in (16, 17, 18, 19)
    if op in (2, 4, 5, 6, 7, 16, 17, 18, 20, 21, 22, 23):
        return False
    if op in (40, 41, 42, 43, 46, 47, 56, 57, 61):
        return False
    return rt == reg


def return_value_is_unconsumed(rom: bytes, site: Callsite) -> dict[str, object]:
    # Conservative control-flow taint: V0 starts as the target's return value.
    # A later call clears the taint only after its delay slot has executed.
    pending = [(site.call + 8, True)]
    seen: set[tuple[int, bool]] = set()
    exits = 0
    overwrites = 0
    while pending:
        pc, tainted = pending.pop()
        state = (pc, tainted)
        if state in seen:
            continue
        seen.add(state)
        if pc < site.parent_start or pc >= site.parent_end:
            exits += 1
            continue
        word = word_at(rom, pc)
        op = word >> 26
        rs = word >> 21 & 31
        rt = word >> 16 & 31
        fn = word & 63
        if tainted and reads_register(word, 2):
            raise AssertionError(f"{site.parent}: V0 consumed at {pc:#x}")
        if op == 3 or (op == 0 and fn == 9):
            delay = word_at(rom, pc + 4)
            if tainted and reads_register(delay, 2):
                raise AssertionError(f"{site.parent}: V0 consumed in call delay at {pc + 4:#x}")
            overwrites += int(tainted)
            pending.append((pc + 8, False))
            continue
        if tainted and writes_register(word, 2):
            tainted = False
            overwrites += 1
        if op == 0 and fn == 8:  # JR: function exit or an indirect tail transfer.
            exits += 1
            continue
        if op == 2:  # J
            target = ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
            pending.append((target, tainted))
            continue
        signed = ((word & 0xFFFF) ^ 0x8000) - 0x8000
        if op in (1, 4, 5, 6, 7, 20, 21, 22, 23):
            pending.append((pc + 8 + signed * 4, tainted))
            pending.append((pc + 8, tainted))
            continue
        pending.append((pc + 4, tainted))
    return {"states": len(seen), "exits": exits, "later_overwrites": overwrites}


def descriptor_store_bytes(rom: bytes, site: Callsite) -> set[int]:
    # Linear provenance is sufficient for this write census. Calls invalidate
    # volatile pointers; callee-saved SP-derived pointers remain valid.
    stack_pointer: dict[int, int] = {29: 0}
    covered: set[int] = set()
    for pc in range(site.parent_start, site.call + 8, 4):
        word = word_at(rom, pc)
        op = word >> 26
        rs = word >> 21 & 31
        rt = word >> 16 & 31
        rd = word >> 11 & 31
        fn = word & 63
        imm = ((word & 0xFFFF) ^ 0x8000) - 0x8000
        if op in (40, 41, 43, 57, 61) and rs in stack_pointer:
            width = {40: 1, 41: 2, 43: 4, 57: 4, 61: 8}[op]
            absolute = stack_pointer[rs] + imm
            for offset in range(absolute - site.descriptor, absolute - site.descriptor + width):
                if 0 <= offset < 0x58:
                    covered.add(offset)
        if op == 9 and rs in stack_pointer:
            if rs == 29 and rt == 29:
                # Descriptor offsets are expressed against the post-prologue SP.
                stack_pointer[29] = 0
            else:
                stack_pointer[rt] = stack_pointer[rs] + imm
        elif op == 0 and fn in (32, 33, 36, 37, 38, 39, 42, 43):
            if rt == 0 and rs in stack_pointer:
                stack_pointer[rd] = stack_pointer[rs]
            elif rs == 0 and rt in stack_pointer:
                stack_pointer[rd] = stack_pointer[rt]
            else:
                stack_pointer.pop(rd, None)
        elif op == 0 and writes_register(word, rd):
            stack_pointer.pop(rd, None)
        elif writes_register(word, rt):
            stack_pointer.pop(rt, None)
        if op == 3 or (op == 0 and fn == 9):
            for reg in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 24, 25):
                stack_pointer.pop(reg, None)
    return covered


def qualify(root: Path, output: Path) -> dict[str, object]:
    rom = (root / "conker/conker.us.bin").read_bytes()
    all_words = struct.unpack(f">{len(rom) // 4}I", rom[: len(rom) & ~3])
    jal_rom = [index * 4 for index, word in enumerate(all_words) if word == JAL_WORD]
    jump_rom = [index * 4 for index, word in enumerate(all_words) if word == J_WORD]
    pointer_rom = [index * 4 for index, word in enumerate(all_words) if word == TARGET]
    expected_jals = [ROM_BASE + site.call - VA_BASE for site in CALLS]
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

    required = set(range(0x00, 0x3A)) | set(range(0x3C, 0x56))
    sites = []
    all_required_written = True
    for site in CALLS:
        owner = [row for row in progress_rows if row[1] <= site.call < row[2]]
        assert len(owner) == 1 and owner[0][:3] == (site.parent, site.parent_start, site.parent_end), owner
        assert word_at(rom, site.call) == JAL_WORD
        proof_rows = []
        for va, expected, meaning in site.proofs:
            actual = word_at(rom, va)
            assert actual == expected, (site.parent, va, actual, expected)
            proof_rows.append({"va": hex(va), "word": f"0x{actual:08X}", "meaning": meaning})
        covered = descriptor_store_bytes(rom, site)
        missing = sorted(required - covered)
        all_required_written &= not missing
        sites.append({
            "call_va": hex(site.call),
            "call_rom": hex(ROM_BASE + site.call - VA_BASE),
            "parent": site.parent,
            "parent_range": [hex(site.parent_start), hex(site.parent_end)],
            "parent_words": (site.parent_end - site.parent_start) // 4,
            "parent_language": owner[0][3],
            "descriptor": f"SP+0x{site.descriptor:X}",
            "argument_proofs": proof_rows,
            "descriptor_bytes_written_by_static_union": len(covered),
            "required_input_bytes_missing_from_static_union": [hex(value) for value in missing],
            "return_taint": return_value_is_unconsumed(rom, site),
        })

    prologue = words(rom, TARGET, TARGET + 0x1C)
    expected_prologue = [0x27BDFEF8, 0xAFB70088, 0xAFB60084, 0xAFB0006C, 0x00808025, 0x30B600FF, 0x27B700EC]
    assert prologue == expected_prologue
    assert all_required_written, [(row["parent"], row["required_input_bytes_missing_from_static_union"]) for row in sites]
    report = {
        "success": True,
        "private_only": True,
        "matching_credit": 0,
        "target": "func_15152F70",
        "target_va": hex(TARGET),
        "original_callers": len(CALLS),
        "aligned_ROM_JALs": [hex(value) for value in jal_rom],
        "aligned_ROM_Js": [],
        "aligned_ROM_pointer_literals": [],
        "unique_parents": len({site.parent for site in CALLS}),
        "argument_contract": {
            "input": "pointer to a 0x58-byte stack descriptor",
            "mode": "u8: byte loads/constants at every caller and ANDI 0xFF in callee prologue",
            "return": "void: conservative V0 taint reaches no read on any post-call control-flow path",
        },
        "required_input_bytes": len(required),
        "all_required_input_bytes_have_pre_call_store_evidence": all_required_written,
        "caller_sites": sites,
        "full_parent_execution_claimed": False,
        "alternate_source_used_for_ABI_proof": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "private-caller-v7.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path.cwd()
    print(json.dumps(qualify(root, output), indent=2))
