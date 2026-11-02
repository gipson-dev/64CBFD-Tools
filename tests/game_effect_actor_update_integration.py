"""Original pointer-table registration and dispatcher contract for func_15154A88."""
import json
import struct


def qualify(root, output):
    rom = (root / "conker/conker.us.bin").read_bytes()
    entry = 0x15154A88
    words = struct.unpack(">{}I".format(len(rom) // 4), rom)
    jal = 0x0C000000 | ((entry >> 2) & 0x03FFFFFF)
    jump = 0x08000000 | ((entry >> 2) & 0x03FFFFFF)
    report = {
        "success": True,
        "private_only": True,
        "matching_credit": 0,
        "target": "func_15154A88",
        "aligned_ROM_JALs": [hex(i * 4) for i, word in enumerate(words) if word == jal],
        "aligned_ROM_Js": [hex(i * 4) for i, word in enumerate(words) if word == jump],
        "aligned_ROM_pointer_literals": [hex(i * 4) for i, word in enumerate(words) if word == entry],
        "registration_table": "D_800898B0",
        "registration_index": 18,
        "registration_ROM": "0x22e3b8",
        "selector_field": "actor+0x71",
        "dispatcher": "func_151321D0",
        "dispatcher_window": ["0x15132244", "0x15132278"],
        "ABI": "s32(u8 *actor)",
        "nonzero_result_keeps_actor": True,
        "zero_result_requests_expiration": True,
        "complete_parent_execution_claimed": False,
    }
    assert report["aligned_ROM_JALs"] == []
    assert report["aligned_ROM_Js"] == []
    assert report["aligned_ROM_pointer_literals"] == ["0x22e3b8"]
    assert struct.unpack_from(">I", rom, 0x22E3B8)[0] == entry
    window = struct.unpack_from(">13I", rom, 0x15F6F4)
    assert window == (
        0x92020071, 0x3C198009, 0x1040000A, 0x00026080,
        0x032CC821, 0x8F3998B0, 0x02002025, 0xA3A50023,
        0x0320F809, 0x00000000, 0x14400002, 0x93A50023,
        0x24050001,
    )
    (output / "private-caller-v1.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
