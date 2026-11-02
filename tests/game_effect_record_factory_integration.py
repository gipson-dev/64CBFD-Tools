"""Complete retail caller census and seven-argument stack ABI for func_1515548C."""

import json
import struct


CALLS = [
    0xDCE50, 0xDD068, 0xEB5B0, 0xFCC84, 0xFCFD0, 0x114B68, 0x114E2C,
    0x1285DC, 0x1297E0, 0x162DC8, 0x163048, 0x188DD8, 0x1ECC28,
    0x1ECC7C, 0x1F7878, 0x1F7B24, 0x1F7CD8, 0x1F7D50, 0x1F7DBC,
    0x1F7E34, 0x1F7F2C, 0x1F81AC, 0x1F8354, 0x1F83D0, 0x1F8440,
    0x1F84BC, 0x1F8C94, 0x1F8CDC, 0x1F8D54, 0x1F8D9C, 0x1F9B6C,
    0x1F9C00, 0x1F9E58, 0x1F9ED0, 0x1F9F34, 0x1F9FA0, 0x1FA000,
    0x1FA074, 0x1FA0DC, 0x1FA138, 0x1FA1A0, 0x1FA318, 0x1FA654,
]


def qualify(root, output):
    rom = (root / "conker/conker.us.bin").read_bytes()
    entry = 0x1515548C
    words = struct.unpack(">{}I".format(len(rom) // 4), rom)
    jal = 0x0C000000 | ((entry >> 2) & 0x03FFFFFF)
    jump = 0x08000000 | ((entry >> 2) & 0x03FFFFFF)
    calls = [i * 4 for i, word in enumerate(words) if word == jal]
    jumps = [i * 4 for i, word in enumerate(words) if word == jump]
    pointers = [i * 4 for i, word in enumerate(words) if word == entry]
    assert calls == CALLS and not jumps and not pointers

    stack_sites = {}
    for call in calls:
        window = [(at, struct.unpack_from(">I", rom, at)[0])
                  for at in range(call - 128, call + 8, 4)]
        sites = {}
        for at, word in window:
            opcode = word >> 26
            base = (word >> 21) & 31
            offset = ((word & 0xFFFF) ^ 0x8000) - 0x8000
            if base == 29 and opcode in (40, 41, 43, 57, 61) and offset in (0x10, 0x14, 0x18):
                sites[offset] = at
        assert set(sites) == {0x10, 0x14, 0x18}, hex(call)
        stack_sites[hex(call)] = {hex(offset): hex(at) for offset, at in sites.items()}

    source = (root / "conker/src/game/generated_113D60.c").read_text()
    assert "s32 func_1515548C(void *descriptor, s32 arg1, s32 *pair, s32 mode," in source
    assert "s32 arg4, u8 slot, s32 context);" in source
    source = (root / "conker/src/game/generated_FC5F0.c").read_text()
    assert "void *func_1515548C(void *, s32, s32 *, s32, s32, u8, s32);" in source

    report = {
        "success": True, "private_only": True, "matching_credit": 0,
        "target": "func_1515548C", "original_callers": len(calls),
        "aligned_ROM_JALs": [hex(value) for value in calls],
        "aligned_ROM_Js": [], "aligned_ROM_pointer_literals": [],
        "seven_argument_O32_ABI": True,
        "all_callers_materialize_stack_arguments_5_6_7": True,
        "stack_argument_store_sites": stack_sites,
        "matching_C_prototypes_checked": ["generated_113D60.c", "generated_FC5F0.c"],
        "complete_parent_execution_claimed": False,
    }
    (output / "private-caller-v1.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
