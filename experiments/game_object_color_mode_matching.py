"""Closed object-mode register/lifetime recipe, not a retail-body replacement."""
import struct

from tools.experiments import game_object_color_mode_candidates as recovery
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = recovery.ENTRY, recovery.ROM, recovery.WORDS
FUNCTION, SOURCE = recovery.FUNCTION, recovery.SOURCE
SELECTED = recovery.SELECTED.replace('    s32 reserved0, reserved1;',
    '    /* Retain retail scratch extent; these reserved words are not accessed. */\n    s32 reserved0, reserved1;')
ORIGINAL = 's32 func_1502EC34() {\n    return 0;\n}'
RAW = tuple(int(word, 16) for word in '''
27BDFFD8 AFBF0014 908E00A4 25CFFFFF 2DE10007 1020008A 000F7880 3C010000
002F0821 8C2F0000 01E00008 00000000 909800A5 ACB80000 909900A6 ACD90000
908900A7 ACE90000 8C8200A0 8FA30038 2C410100 1420001C 00000000 44801000
C4400000 3C01437F 4602003C 00000000 45020004 44816000 1000000B 46001006
44816000 00000000 4600603C 00000000 45020004 46000086 10000002 46006086
46000086 46001006 3C010000 C4240000 8FA30038 46040182 4600320D 440B4000
1000005F AC6B0000 1000005D AC620000 8FA30038 ACA00000 ACC00000 ACE00000
908200A5 24010003 240800FF AC620000 908C00A4 01026823 55810052 8FBF0014
1000004F AC6D0000 8C8200A0 3C014F80 00027603 31CF00FF 0002C403 AFAF001C
331900FF ACB90000 8C8900A0 00095203 314B00FF ACCB0000 8C8C00A0 318D00FF
ACED0000 908E00A5 448E5000 05C10004 46805420 44819000 00000000 46128400
3C010000 C4240000 AFA40028 46048302 0C000000 00000000 3C013F80 44813000
3C013F00 44815000 46060200 8FAF001C 3C014280 44818000 460A4482 448F3000
8FA30038 8FA40028 240800FF 46803220 46128102 46044280 4600540D 44028000
00000000 AC620000 909900A7 01025023 01194823 012A0019 00005812 000B6203
01826821 10000016 AC6D0000 8C8200A0 8FA30038 240800FF 00027403 31CF00FF
ACAF0000 8C9800A0 00026E03 31AE00FF 0018CA03 332900FF ACC90000 8C8A00A0
314B00FF ACEB0000 908C00A5 018E0019 00007812 000FC203 0118C823 AC790000
8FBF0014 27BD0028 03E00008 00000000
'''.split())
RENAMES = (
    (16,16,9,10), (17,16,9,10), (19,16,3,8), (44,16,3,8), (47,16,11,12),
    (49,21,3,8), (49,16,11,12), (51,21,3,8), (52,16,3,8), (56,16,2,13),
    (58,16,8,9), (59,21,3,8), (59,16,2,13), (60,16,12,14), (61,21,8,9),
    (61,16,2,13), (61,11,13,24), (62,21,12,14), (65,21,3,8), (65,16,13,24),
    (68,11,14,25), (69,21,14,25), (69,16,15,10), (70,11,24,11), (71,16,15,10),
    (72,21,24,11), (72,16,25,12), (73,16,25,12), (74,16,9,13), (75,16,9,13),
    (75,11,10,14), (76,21,10,14), (76,16,11,15), (77,16,11,15), (78,16,12,24),
    (79,21,12,24), (79,16,13,25), (80,16,13,25), (81,16,14,10), (82,16,14,10),
    (83,21,14,10), (99,16,15,11), (103,16,15,11), (104,16,3,8), (106,16,8,9),
    (113,21,3,8), (114,16,25,14), (115,21,8,9), (115,11,10,13), (116,21,8,9),
    (116,16,25,14), (116,11,9,15), (117,21,10,13), (117,16,9,15), (118,11,11,24),
    (119,16,11,24), (119,11,12,25), (120,16,12,25), (120,11,13,10),
    (122,21,3,8), (122,16,13,10), (124,16,3,8), (125,16,8,9), (126,11,14,12),
    (127,21,14,12), (127,16,15,14), (128,16,15,14), (129,16,24,13), (130,11,13,3),
    (131,21,13,3), (131,16,14,11), (132,16,24,13), (132,11,25,15), (133,21,25,15),
    (133,16,9,24), (134,16,9,24), (135,16,10,25), (136,21,10,25), (136,16,11,10),
    (137,16,11,10), (138,16,12,11), (139,21,12,11), (139,16,14,3), (140,11,15,12),
    (141,16,15,12), (141,11,24,14), (142,21,8,9), (142,16,24,14), (142,11,25,13),
    (143,21,3,8), (143,16,25,13),
)
BRANCHES = {5:0x8C, 48:0x61, 50:0x5F, 62:0x54, 64:0x51, 121:0x18}
RELOCATIONS = {28:[('R_MIPS_HI16','.rodata')], 36:[('R_MIPS_LO16','.rodata')],
    168:[('R_MIPS_HI16','D_80096F38')], 172:[('R_MIPS_LO16','D_80096F38')],
    352:[('R_MIPS_HI16','D_80096F3C')], 356:[('R_MIPS_LO16','D_80096F3C')],
    368:[('R_MIPS_26','cosf')]}


def recipe(words, owner=False):
    expected = list(RAW)
    expected[9] |= 0x100 if owner else 0
    if list(words) != expected:
        raise ValueError('stale complete object color-mode body')
    changed = list(words)
    # Only commutative low-product and wrapping-add operand order changes.
    for index in (117,120):
        word = changed[index]
        changed[index] = word & ~((31 << 21) | (31 << 16)) | (word >> 16 & 31) << 21 | (word >> 21 & 31) << 16
    for index, shift, old, new in RENAMES:
        if changed[index] >> shift & 31 != old:
            raise ValueError('stale object-mode producer role')
        changed[index] = changed[index] & ~(31 << shift) | new << shift
    for index, displacement in BRANCHES.items():
        changed[index] = changed[index] & 0xFFFF0000 | displacement
    # Relocate directly to the protected table instead of the compact-owner pool.
    changed[9] &= 0xFFFF0000
    replacements = list(changed)
    replacements[121] = changed[122]
    replacements[122] = 0x8FBF0014
    replacements[123:126] = changed[124:126] + changed[123:124]
    inserted = {121:changed[121], 135:0x01601825}
    fitted = []
    for index, word in enumerate(replacements):
        fitted.append(word)
        if index in inserted: fitted.append(inserted[index])
    assert len(fitted) == 150
    return fitted, replacements, inserted


def guard_rows(path, owner=False):
    text, functions, relocations = parse_object(path)
    target = functions[FUNCTION]
    if target['size'] != 592:
        raise ValueError('expected complete 148-word object mode body')
    words = struct.unpack_from('>148I', text, target['value'])
    relative = {offset - target['value']: uses for offset, uses in relocations.items()
        if target['value'] <= offset < target['value'] + target['size']}
    if relative != RELOCATIONS:
        raise ValueError('stale complete object-mode relocations')
    _, replacements, inserted = recipe(words, owner)
    spec = lambda uses: ';'.join(kind + ':' + name for kind, name in uses) or '-'
    rows = []
    for index, word in enumerate(words):
        uses = relative.get(index * 4, ())
        after = [(kind, 'jtbl_80096F1C_game') for kind, _ in uses] if index in (7,9) else uses
        rows.append(dict(filename='generated_58F80', function=FUNCTION, offset='0x%X' % (index * 4),
            expected='0x%08X' % word, replacement='0x%08X' % replacements[index],
            expected_relocations=spec(uses), replacement_relocations=spec(after),
            note='Normalize certified object-mode lifetimes and protected table relocation',
            insert_after='0x%08X' % inserted[index] if index in inserted else '',
            insert_after_relocations='-' if index in inserted else '', omit='false'))
    return rows


def install(before):
    if before.count(ORIGINAL) != 1:
        raise ValueError('expected one original object mode placeholder')
    return before.replace('#include <ultra64.h>', '#include <ultra64.h>\n' + recovery.DECLARATIONS, 1).replace(ORIGINAL, SELECTED)
