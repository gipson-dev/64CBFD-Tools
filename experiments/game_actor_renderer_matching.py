"""Certify the complete renderer's emitted register cycles and branch-side count reload."""
import struct

from tools.experiments import game_actor_renderer_candidates as recovery
from tools.experiments import game_actor_renderer_layout as layout
from tools.experiments.game_actor_segment_selector_matching import fields
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = recovery.ENTRY, recovery.ROM, recovery.WORDS
FUNCTION, SOURCE = recovery.FUNCTION, recovery.SOURCE
SELECTED = layout.SELECTED
RAW = tuple(int(word, 16) for word in '''
27BDFEB0 AFB3004C AFB20048 AFB10044 AFB00040 00808025 8FB10168 00A09025
00E09825 AFBF005C AFB60058 AFB50054 AFB40050 AFA60158 00127080 01D27023
000E7080 01D27021 000E7080 01D27023 000E7080 01D27023 3C0F0000 25EF0000
000E7080 01CFA821 92B80004 24010003 12210005 AFB80140 24010004 12210002
24010005 16210006 02A02025 0C000000 27A50144 AFA20140 10000003 8FB10168
92B901C8 AFB90144 24010003 16210003 02A02025 10000002 00003825 24070001
8FA50140 0C000000 8FA60144 10400003 3C140000 100001D3 02001025 8FAE0144
26940000 92820000 000E78C0 02AFC021 00028880 0311C821 8F2E028C 8FAF016C
02402825 15C00003 00000000 100001C5 02001025 11E00009 3C16DE00 02001025
3C180000 27180000 AC580004 AC560000 26100008 10000007 00000000 3C1FE700
02001025 AC5F0000 AC400004 26100008 3C16DE00 0C000000 02002025 00402025
0C000000 02402825 3C19DB06 3739000C AC590000 AC530004 3C0EDB06 35CE0004
AC4E0008 8FAF0144 24500010 02A02025 000FC0C0 02B8C821 03317021 8DCF028C
27AE0124 27B90128 25F8FFC8 AC58000C AFB90010 AFAE0014 27AE0114 27B90118
27AF0120 27B8011C AFB8001C AFAF0018 AFB90020 AFAE0024 27AE0104 27B90108
27AF0110 27B8010C AFB8002C AFAF0028 AFB90030 AFAE0034 8FA50158 8FA60160
0C000000 8FA70164 8FA60168 24010005 3C1FE700 14C1000A 02001025 3C0FDB06
3C180000 27180000 35EF0020 AC4F0000 AC580004 26100008 10000023 02001025
24010003 14C1000B 8FAF0160 02001025 3C19DB06 3C0E0000 25CE0000 37390020
AC590000 AC4E0004 26100008 10000016 02001025 29E100FF 1020000B 02001025
02001025 3C18DB06 3C190000 27390000 37180020 AC580000 AC590004 26100008
10000009 02001025 3C0EDB06 3C0F0000 25EF0000 35CE0020 AC4E0000 AC4F0004
26100008 02001025 3C18D9FF 3718F9FF AC580000 AC400004 26100008 14C0000A
3C0F0000 3C05D9FF 34A5FFFF 02001025 24190200 AC590004 AC450000 26100008
10000008 00000000 3C05D9FF 34A5FFFF 02001025 240E0400 AC4E0004 AC450000
26100008 8DEF0000 2401000C 24040001 85F8003E 3C0E0002 AFB80130 92A20066
3059000C 1721000D 03201025 02001025 AC450000 AC4E0004 26100008 02001825
3C0FD9BF 35EFFFFF AC6F0000 AC600004 26100008 1000001D 24010003 24010008
10410009 3C190000 02001025 3C18D9BD 3718FFFF AC580000 AC400004 26100008
10000011 00002025 8F390000 3C0FD9BD 35EFFFFF 13200008 02001025 02001025
3C0E0042 AC4E0004 AC450000 26100008 10000006 24010003 26100008 AC4F0000
AC400004 00002025 24010003 14C10007 02001025 3C18D9BD 3718FFFF AC580000
26100008 AC400004 00002025 10800032 3C0E0000 92B902FE 24020002 17200003
00000000 10000001 2402000A 91CE0000 344F0008 51C00003 C6B0001C 01E01025
C6B0001C C6A40014 C6A80018 4600848D 8FA50158 02002025 4600218D 44199000
00057880 4600428D AFB90010 8EAE0184 02AFC821 44075000 AFAE0014 8F2E0304
92990000 44063000 AFAE0018 92B80301 001970C0 26B90302 AFB8001C 8EAF0314
AFA20030 AFB90024 01EEC021 AFB80020 3C180000 27180000 26AE01DD 240F0002
AFAF0028 AFAE002C 0C000000 AFB80034 3C1FE700 00408025 8FB90140 3C0E0000
25CE0000 00197840 01EE5021 95440000 2407FFFF 00008825 188000AC 240D00FF
3C0BFA00 3C090000 25290000 356BF200 3C0CFB00 3C08F800 8EAF0094 3238001F
24190001 03191004 01E27024 15C0009B 8FA60140 8EB80098 0006C880 03203025
03027824 15E0004D 24010001 10E0005D 02001025 26100008 AC5F0000 AC400004
8FA40160 8FB90130 00003825 308E00FF 17200014 01C02025 02001025 AC480000
8FB9010C 8FAF0110 26100008 333800FF 000F7600 00187C00 8FB80108 01CFC825
330E00FF 000E7A00 8FAE0104 032FC025 31D900FF 03197825 AC4F0004 10000011
02001025 02001025 AC480000 91380002 912E0000 26100008 0018CA00 000EC600
03387825 91390001 0019C400 8FB90104 01F87025 332F00FF 01CFC025 AC580004
02001025 AC4B0000 8FB80124 8FAE0128 26100008 331900FF 000E7E00 00197400
8FB90120 01EEC025 02001825 332F00FF 000F7200 030EC825 AC590004 AC6C0000
8FB90118 8FB8011C 26100008 332F00FF 00187600 000FC400 8FAF0114 01D8C825
31EE00FF 000EC200 03387825 01E47025 AC6E0004 10000014 8FB90168 10E10011
02001025 26100008 AC5F0000 AC400004 02001825 AC680000 AC6D0004 26100008
02002025 AC8B0000 AC800004 26100008 02002825 ACAC0000 ACAD0004 26100008
24070001 8FB90168 24010003 3C040000 17210011 24840000 3C180000 27180000
00D81821 8C6F0000 02001025 11E00008 00000000 AC560000 8C6E0000 0011C880
26100008 01D9C021 8F0F0000 AC4F0004 10000022 95440000 3C0E0000 25CE0000
3C130000 26730000 00CEA021 00119080 AFA7013C 0C000000 AFAA0078 3C090000
3C0BFA00 356BF200 25290000 8FA7013C 3C08F800 8FAA0078 3C0CFB00 240D00FF
3C1FE700 02001025 3C19DA38 37390003 AC590000 AC530004 26100008 02001825
AC760000 8E980000 26100008 03127821 8DEE0000 AC6E0004 95440000 26310001
0224082A 5420FF5D 8EAF0094 0C000000 02A02025 24190001 A2B902FE 8FB80168
8FA60158 02002025 17000004 02A02825 0C000000 24070001 00408025 8FAF016C
3C0E0000 25CE0000 11E00004 02001025 26100008 AC560000 AC4E0004 8FB90168
3C18D9FF 3718FDFF 17200005 02001025 240F0400 AC4F0004 26100008 AC580000
02001025 8FBF005C 8FB00040 8FB10044 8FB20048 8FB3004C 8FB40050 8FB50054
8FB60058 03E00008 27BD0150
'''.split())
RELOCATIONS = {
    88: [('R_MIPS_HI16', 'D_800CC2D0')],
    92: [('R_MIPS_LO16', 'D_800CC2D0')],
    140: [('R_MIPS_26', 'func_150849CC')],
    196: [('R_MIPS_26', 'func_1503DA9C')],
    208: [('R_MIPS_HI16', 'D_800BE9C0')],
    224: [('R_MIPS_LO16', 'D_800BE9C0')],
    288: [('R_MIPS_HI16', 'D_80084160')],
    292: [('R_MIPS_LO16', 'D_80084160')],
    340: [('R_MIPS_26', 'func_1502F01C')],
    352: [('R_MIPS_26', 'func_1502F9FC')],
    512: [('R_MIPS_26', 'func_1502CC34')],
    544: [('R_MIPS_HI16', 'D_800832C0')],
    548: [('R_MIPS_LO16', 'D_800832C0')],
    596: [('R_MIPS_HI16', 'D_800832C0')],
    600: [('R_MIPS_LO16', 'D_800832C0')],
    648: [('R_MIPS_HI16', 'D_80082FC0')],
    652: [('R_MIPS_LO16', 'D_80082FC0')],
    684: [('R_MIPS_HI16', 'D_80083140')],
    688: [('R_MIPS_LO16', 'D_80083140')],
    736: [('R_MIPS_HI16', 'D_800B0DF0')],
    804: [('R_MIPS_LO16', 'D_800B0DF0')],
    900: [('R_MIPS_HI16', 'D_800DCD7C')],
    936: [('R_MIPS_LO16', 'D_800DCD7C')],
    1040: [('R_MIPS_HI16', 'D_800D9900')],
    1068: [('R_MIPS_LO16', 'D_800D9900')],
    1200: [('R_MIPS_HI16', 'D_800D9E28')],
    1204: [('R_MIPS_LO16', 'D_800D9E28')],
    1224: [('R_MIPS_26', 'func_1515D914')],
    1244: [('R_MIPS_HI16', 'D_800C4778')],
    1248: [('R_MIPS_LO16', 'D_800C4778')],
    1284: [('R_MIPS_HI16', 'D_800DD2E4')],
    1288: [('R_MIPS_LO16', 'D_800DD2E4')],
    1740: [('R_MIPS_HI16', 'D_800C3E98')],
    1748: [('R_MIPS_LO16', 'D_800C3E98')],
    1752: [('R_MIPS_HI16', 'D_800C48F0')],
    1756: [('R_MIPS_LO16', 'D_800C48F0')],
    1816: [('R_MIPS_HI16', 'D_800C4488')],
    1820: [('R_MIPS_LO16', 'D_800C4488')],
    1824: [('R_MIPS_HI16', 'D_C3E98')],
    1828: [('R_MIPS_LO16', 'D_C3E98')],
    1844: [('R_MIPS_26', 'func_151EFE88')],
    1852: [('R_MIPS_HI16', 'D_800DD2E4')],
    1864: [('R_MIPS_LO16', 'D_800DD2E4')],
    1964: [('R_MIPS_26', 'func_1502FD70')],
    2000: [('R_MIPS_26', 'func_15030F94')],
    2016: [('R_MIPS_HI16', 'D_80084190')],
    2020: [('R_MIPS_LO16', 'D_80084190')],
}
OMIT = 327
INSERT_AFTER = (452, 453)
LOOP_REGISTERS = {8: 9, 9: 10, 10: 8, 14: 15, 15: 25, 25: 14}
BRANCH_OPS = (4, 5, 6, 7, 20, 21, 22, 23)


def recipe_items(words):
    if tuple(words) != RAW:
        raise ValueError('stale complete actor renderer body')
    changed = list(words)
    for index in range(314, len(words)):
        word = words[index]
        op = word >> 26
        mapping = {register: destination for register, destination in LOOP_REGISTERS.items()
            if (register in (8, 9, 10) and index <= 490)
            or (register in (14, 15, 25) and index >= 326)}
        moved = lambda register: mapping.get(register, register)
        if op == 0:
            word = fields(word, rs=moved(word >> 21 & 31), rt=moved(word >> 16 & 31),
                rd=moved(word >> 11 & 31))
        elif op in (*BRANCH_OPS, 9, 12, 13, 15, 35, 36, 37, 40, 43):
            word = fields(word, rs=moved(word >> 21 & 31), rt=moved(word >> 16 & 31))
        elif op != 3:
            raise ValueError('unqualified renderer loop opcode')
        changed[index] = word
    # SLLV supplies the low-five-bit mask itself; retain the defined mask in C.
    changed[328] = fields(changed[328], rt=24)
    changed[329] = fields(changed[329], rs=17, rt=24)
    order = list(range(len(words)))
    # Hoist two independent geometry constants without moving any memory access.
    order[205:218] = [216, 205, 206, 207, 217, *range(208, 216)]
    # The count-pointer reload and fog-opcode producer have independent registers.
    order[468], order[469] = order[469], order[468]
    items = []
    for origin in order:
        if origin == OMIT:
            continue
        items.append((origin, origin, changed[origin]))
        if origin == 453:
            # Split the existing common branch/read exit into its two retail arms.
            items.extend((('null-branch', 452, changed[452]), ('null-read', 453, changed[453])))
    positions = {label: index for index, (label, _, _) in enumerate(items)}
    output = []
    for index, (label, origin, word) in enumerate(items):
        if word >> 26 in BRANCH_OPS:
            immediate = words[origin] & 65535
            target = origin + 1 + (immediate ^ 32768) - 32768
            if target == OMIT:
                if origin != 489:
                    raise ValueError('unexpected branch into redundant renderer mask')
                target = 328
            destination = positions['null-branch' if origin == 443 else target]
            word = fields(word, imm=destination - index - 1)
        output.append((label, origin, word))
    assert len(output) == WORDS
    return output


def recipe(words):
    return [word for _, _, word in recipe_items(words)]


OUTPUT_RELOCATIONS = {index * 4: RELOCATIONS[origin * 4]
    for index, (_, origin, _) in enumerate(recipe_items(RAW)) if origin * 4 in RELOCATIONS}


def guard_rows(path):
    text, functions, relocations = parse_object(path)
    target = functions[FUNCTION]
    if target['size'] != 2124:
        raise ValueError('expected complete 531-word actor renderer')
    words = struct.unpack_from('>531I', text, target['value'])
    relative = {offset - target['value']: uses for offset, uses in relocations.items()
        if target['value'] <= offset < target['value'] + target['size']}
    if relative != RELOCATIONS:
        raise ValueError('stale complete actor renderer relocations')
    fitted, rows, emitted = recipe(words), [], 0
    spec = lambda uses: ';'.join(kind + ':' + symbol for kind, symbol in uses) or '-'
    for index, word in enumerate(words):
        omitted = index == OMIT
        row = dict(filename='generated_58F80', function=FUNCTION, offset='0x%X' % (index * 4),
            expected='0x%08X' % word,
            replacement='0x%08X' % (word if omitted else fitted[emitted]),
            expected_relocations=spec(relative.get(index * 4, ())),
            replacement_relocations=spec(() if omitted else OUTPUT_RELOCATIONS.get(emitted * 4, ())),
            note='Normalize complete renderer loop register cycles and branch-side count reload',
            insert_after='', insert_after_relocations='', omit='true' if omitted else 'false')
        if not omitted:
            emitted += 1
        if index in INSERT_AFTER:
            row['insert_after'] = '0x%08X' % fitted[emitted]
            row['insert_after_relocations'] = spec(OUTPUT_RELOCATIONS.get(emitted * 4, ()))
            emitted += 1
        rows.append(row)
    assert emitted == WORDS
    return rows


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    return recovery.compile_candidate(root, out, name, body, profile)
