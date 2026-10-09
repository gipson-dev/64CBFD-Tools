"""Closed ribbon GP/save/factor normalization; no retail-word lookup."""

import hashlib
import struct

from tools.experiments import game_record_ring_renderer_candidates as screen
from tools.experiments import game_record_ring_renderer_proof as proof

SOURCE_SHA256 = "8fafaaa5a9f93eb1636fb25571e4fd8dee30d6d82fb83d4c9191680a9bd0e242"
RELOCATIONS = {
    0x8C: [('R_MIPS_26','func_151D5D60')],
    0xB0: [('R_MIPS_HI16','D_80090CD4')],
    0xC8: [('R_MIPS_LO16','D_80090CD4')],
    0xEC: [('R_MIPS_26','func_15142E24')],
    0x104: [('R_MIPS_26','func_15142B7C')],
    0x114: [('R_MIPS_26','func_1513F4E4')],
    0x11C: [('R_MIPS_HI16','D_800A4AC8')],
    0x120: [('R_MIPS_HI16','D_800D2C9C')],
    0x124: [('R_MIPS_LO16','D_800D2C9C')],
    0x128: [('R_MIPS_LO16','D_800A4AC8')],
    0x148: [('R_MIPS_26','func_15142FBC')],
    0x23C: [('R_MIPS_HI16','D_800DD1E8')],
    0x244: [('R_MIPS_LO16','D_800DD1E8')],
    0x24C: [('R_MIPS_HI16','D_800DD1D8')],
    0x258: [('R_MIPS_LO16','D_800DD1D8')],
    0x56C: [('R_MIPS_26','memcpy')],
}

# Per-instruction live roles certified by the whole-CFG congruence checker.
GP_REWRITES = (
    (0x18, ((11, 19, 18),)),
    (0x68, ((21, 19, 18),)),
    (0x6C, ((16, 6, 25),)),
    (0x78, ((16, 6, 25), (11, 25, 9))),
    (0x7C, ((21, 25, 9),)),
    (0xA4, ((16, 9, 10),)),
    (0xAC, ((21, 19, 18),)),
    (0xB4, ((16, 10, 11),)),
    (0xB8, ((16, 11, 12),)),
    (0xBC, ((16, 9, 10),)),
    (0xC0, ((16, 11, 12),)),
    (0xC4, ((16, 10, 11),)),
    (0xCC, ((21, 19, 18),)),
    (0x12C, ((16, 14, 9),)),
    (0x130, ((16, 15, 10),)),
    (0x138, ((11, 12, 24),)),
    (0x13C, ((21, 12, 24),)),
    (0x14C, ((21, 14, 9), (16, 15, 10))),
    (0x150, ((16, 24, 11),)),
    (0x158, ((11, 19, 18),)),
    (0x15C, ((21, 24, 11), (16, 25, 12))),
    (0x160, ((21, 25, 12),)),
    (0x168, ((16, 18, 19),)),
    (0x16C, ((21, 18, 19), (16, 18, 19))),
    (0x170, ((21, 18, 19),)),
    (0x178, ((16, 18, 19),)),
    (0x17C, ((21, 18, 19), (16, 18, 19))),
    (0x184, ((16, 9, 13),)),
    (0x188, ((11, 6, 4),)),
    (0x18C, ((21, 9, 13),)),
    (0x190, ((16, 11, 15),)),
    (0x194, ((21, 9, 13), (16, 11, 15))),
    (0x19C, ((21, 9, 13),)),
    (0x1B4, ((16, 18, 19),)),
    (0x1C0, ((16, 18, 19),)),
    (0x1C4, ((21, 18, 19),)),
    (0x1C8, ((11, 12, 24),)),
    (0x1CC, ((16, 18, 19),)),
    (0x1D0, ((21, 18, 19), (16, 18, 19))),
    (0x1D4, ((21, 12, 24), (11, 13, 24))),
    (0x1D8, ((16, 13, 24), (11, 14, 24))),
    (0x1DC, ((21, 14, 8), (16, 8, 24))),
    (0x1E4, ((16, 15, 25),)),
    (0x1E8, ((21, 15, 25),)),
    (0x1EC, ((16, 25, 10),)),
    (0x1F0, ((21, 15, 25), (16, 25, 10))),
    (0x1F8, ((21, 15, 25),)),
    (0x1FC, ((16, 6, 4),)),
    (0x204, ((16, 18, 19), (11, 10, 11))),
    (0x208, ((21, 10, 11), (16, 18, 19), (11, 9, 11))),
    (0x210, ((16, 9, 11),)),
    (0x218, ((21, 11, 8), (16, 8, 11))),
    (0x224, ((11, 4, 3),)),
    (0x22C, ((16, 14, 13),)),
    (0x230, ((16, 14, 13),)),
    (0x240, ((16, 4, 3),)),
    (0x254, ((16, 4, 3),)),
    (0x25C, ((16, 24, 15),)),
    (0x268, ((21, 24, 15), (16, 15, 24))),
    (0x274, ((16, 12, 13),)),
    (0x278, ((21, 15, 24),)),
    (0x284, ((11, 25, 9),)),
    (0x288, ((21, 25, 9), (11, 25, 9))),
    (0x28C, ((16, 25, 9), (11, 25, 9))),
    (0x294, ((21, 25, 9),)),
    (0x29C, ((16, 13, 12),)),
    (0x2A0, ((21, 3, 4), (16, 6, 3))),
    (0x2A8, ((21, 12, 13), (16, 13, 12))),
    (0x2B0, ((16, 15, 9),)),
    (0x2B4, ((16, 4, 6),)),
    (0x2CC, ((11, 6, 4),)),
    (0x2D0, ((16, 6, 4), (11, 9, 10))),
    (0x2D4, ((21, 15, 9),)),
    (0x2DC, ((21, 9, 10), (11, 6, 4))),
    (0x2E0, ((16, 9, 11),)),
    (0x30C, ((21, 9, 11),)),
    (0x310, ((16, 13, 12),)),
    (0x314, ((21, 13, 12), (16, 4, 6))),
    (0x318, ((16, 12, 13),)),
    (0x31C, ((21, 12, 13),)),
    (0x320, ((16, 14, 15),)),
    (0x324, ((21, 14, 15),)),
    (0x330, ((16, 15, 9),)),
    (0x334, ((21, 15, 9),)),
    (0x33C, ((16, 6, 4),)),
    (0x34C, ((16, 9, 11),)),
    (0x354, ((21, 9, 11), (16, 11, 14))),
    (0x358, ((16, 11, 14),)),
    (0x360, ((16, 12, 13),)),
    (0x368, ((21, 11, 14), (16, 12, 13))),
    (0x370, ((16, 15, 9),)),
    (0x380, ((21, 15, 9),)),
    (0x388, ((16, 9, 11),)),
    (0x39C, ((21, 9, 11),)),
    (0x3A0, ((16, 13, 12),)),
    (0x3A4, ((21, 13, 12), (16, 4, 6))),
    (0x3A8, ((16, 12, 13),)),
    (0x3AC, ((21, 12, 13),)),
    (0x3B0, ((16, 11, 14),)),
    (0x3B4, ((21, 11, 14),)),
    (0x3B8, ((16, 14, 15),)),
    (0x3BC, ((21, 14, 15),)),
    (0x3C8, ((16, 15, 9),)),
    (0x3CC, ((21, 15, 9), (16, 6, 4))),
    (0x3DC, ((16, 9, 11),)),
    (0x3E0, ((16, 9, 11),)),
    (0x3F8, ((21, 19, 18),)),
    (0x404, ((16, 14, 15),)),
    (0x40C, ((11, 13, 12),)),
    (0x410, ((16, 14, 15),)),
    (0x41C, ((21, 13, 12),)),
    (0x438, ((16, 12, 13),)),
    (0x448, ((16, 13, 12),)),
    (0x450, ((21, 12, 13), (16, 13, 12))),
    (0x454, ((16, 14, 15),)),
    (0x458, ((21, 14, 15),)),
    (0x464, ((16, 15, 9),)),
    (0x468, ((21, 15, 9),)),
    (0x47C, ((16, 9, 11),)),
    (0x480, ((21, 9, 11),)),
    (0x484, ((16, 13, 12),)),
    (0x488, ((21, 13, 12),)),
    (0x490, ((16, 12, 13),)),
    (0x498, ((21, 12, 13), (16, 11, 14))),
    (0x49C, ((16, 11, 14),)),
    (0x4AC, ((21, 11, 14),)),
    (0x4CC, ((16, 12, 13),)),
    (0x4D8, ((16, 13, 12),)),
    (0x4E0, ((21, 12, 13), (16, 13, 12))),
    (0x4E4, ((16, 14, 15),)),
    (0x4E8, ((21, 14, 15),)),
    (0x4F4, ((16, 11, 14),)),
    (0x4F8, ((21, 11, 14),)),
    (0x4FC, ((16, 15, 9),)),
    (0x500, ((21, 15, 9),)),
    (0x514, ((16, 9, 11),)),
    (0x518, ((21, 9, 11),)),
    (0x51C, ((16, 13, 12),)),
    (0x520, ((21, 13, 12), (16, 12, 13))),
    (0x524, ((16, 12, 13),)),
    (0x52C, ((16, 14, 15),)),
    (0x530, ((21, 19, 18), (16, 19, 18))),
    (0x534, ((21, 19, 18),)),
    (0x538, ((21, 14, 15),)),
    (0x540, ((21, 19, 18), (16, 19, 18))),
    (0x54C, ((21, 19, 18),)),
    (0x558, ((21, 19, 18), (16, 19, 18))),
    (0x574, ((16, 11, 14),)),
    (0x580, ((21, 11, 14), (16, 15, 9))),
    (0x584, ((21, 15, 9),)),
    (0x588, ((21, 11, 14),)),
    (0x590, ((16, 9, 11),)),
    (0x594, ((16, 9, 11),)),
    (0x598, ((21, 9, 11), (16, 13, 12))),
    (0x59C, ((21, 13, 12), (11, 12, 13))),
    (0x5A0, ((21, 9, 11), (16, 12, 13))),
    (0x5A4, ((16, 14, 15),)),
    (0x5A8, ((21, 14, 15),)),
    (0x5B0, ((21, 18, 19),)),
    (0x5B4, ((21, 18, 19), (16, 18, 19))),
    (0x5B8, ((21, 18, 19),)),
    (0x5C0, ((16, 18, 19),)),
    (0x5C4, ((21, 18, 19), (16, 18, 19))),
    (0x5C8, ((16, 18, 19), (11, 15, 9))),
    (0x5CC, ((21, 15, 9), (16, 18, 19), (11, 25, 9))),
    (0x5D0, ((16, 25, 9), (11, 11, 9))),
    (0x5D4, ((21, 11, 8), (16, 8, 9))),
    (0x5DC, ((16, 10, 25),)),
    (0x5E0, ((11, 9, 12),)),
    (0x5E4, ((21, 10, 25),)),
    (0x5E8, ((16, 12, 10),)),
    (0x5EC, ((21, 9, 12), (11, 14, 12))),
    (0x5F0, ((16, 14, 12), (11, 24, 12))),
    (0x5F4, ((21, 10, 25), (16, 12, 10))),
    (0x5FC, ((21, 24, 8), (16, 8, 12), (11, 15, 13))),
    (0x600, ((21, 10, 25),)),
    (0x604, ((16, 25, 11),)),
    (0x60C, ((21, 15, 13),)),
    (0x610, ((16, 25, 11),)),
    (0x618, ((21, 19, 18),)),
)
SAVE_REWRITES = ((0x14, 19, 18, 0x54, 0x50), (0x34, 18, 19, 0x50, 0x54))


def canonical_words(words):
    if len(words) != screen.WORDS:
        raise ValueError('wrong complete ribbon extent')
    result = list(words)
    for offset, records in RELOCATIONS.items():
        kind, _ = records[0]
        mask = 0x3FFFFFF if kind == 'R_MIPS_26' else 65535
        result[offset // 4] &= ~mask
    return result


def normalize(words):
    canonical = canonical_words(words)
    digest = hashlib.sha256(struct.pack('>405I', *canonical)).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError('stale complete ribbon candidate')
    result = proof.factor_order(words)
    for offset, fields in GP_REWRITES:
        index = offset // 4
        for shift, before, after in fields:
            if result[index] >> shift & 31 != before:
                raise ValueError('stale ribbon GP role +0x%X' % offset)
            mask = 31 << shift
            if proof.gp_mask(result[index]) & mask != mask:
                raise ValueError('non-GP ribbon rewrite +0x%X' % offset)
            result[index] = result[index] & ~mask | after << shift
    for offset, before, after, old_slot, new_slot in SAVE_REWRITES:
        index = offset // 4
        expected = (43 << 26) | (29 << 21) | (before << 16) | old_slot
        if result[index] != expected:
            raise ValueError('stale ribbon entry save +0x%X' % offset)
        result[index] = result[index] & ~0x1FFFFF | after << 16 | new_slot
    return result


def owner_guards(words, relocations):
    if relocations != RELOCATIONS:
        raise ValueError('stale complete ribbon relocations')
    if list(words) != canonical_words(words):
        raise ValueError('owner guards require unlinked zero-addend ribbon words')
    derived = normalize(words)
    rows = []
    for index, (before, after) in enumerate(zip(words, derived)):
        if before == after:
            continue
        offset = index * 4
        records = RELOCATIONS.get(offset, [])
        relocation = ';'.join(kind + ':' + symbol for kind, symbol in records) or '-'
        note = ('Normalize closed ribbon factor predicate arms and non-annulled delay'
            if 0x278 <= offset <= 0x298 else
            'Normalize paired ribbon entry saves with closed live GP allocation'
            if offset in (0x14, 0x34) else
            'Normalize proven whole-CFG ribbon GP live-value allocation')
        rows.append(dict(filename='generated_204660', function=screen.FUNCTION,
            offset='0x%X' % offset, expected='0x%08X' % before, replacement='0x%08X' % after,
            expected_relocations=relocation, replacement_relocations=relocation, note=note,
            insert_after='', insert_after_relocations='', omit='false'))
    if len(rows) != 185:
        raise ValueError('incomplete ribbon guard closure')
    return rows
