"""Closed frame, constant, register-lifetime and scheduling normalization."""
import csv
import io
import struct

from tools.experiments import game_animation_scratch_prepare_candidates as recovery
from tools.experiments import game_animation_scratch_prepare_shape as shape
from tools.experiments.game_actor_attachment_update_matching import register
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = recovery.ENTRY, recovery.ROM, recovery.WORDS
FUNCTION, SOURCE, SELECTED = recovery.FUNCTION, recovery.SOURCE, shape.SELECTED
RAW = tuple(int(word, 16) for word in '''
27BDFFB0 AFBE0040 AFB10024 AFB00020 00A08025 00C08825 0080F025 AFBF0044
AFB7003C AFB60038 AFB50034 AFB40030 AFB3002C AFB20028 F7B40018 240E0001
12000008 AFAE004C 960F0084 3401FFFF 55E10004 8E1E02D0 0C000000 02002025
8E1E02D0 53C00095 8FBF0044 87D8003C 3C013F80 5B000004 8FA8004C 24190002
AFB9004C 8FA8004C 0000A825 5900008B 8FBF0044 4481A000 03C0B825 92F30045
00155080 0000B025 16600004 015EA021 03D54821 1000007B A1200038 8E850028
50A00079 8FA8004C C68C0008 C6800018 2631000F 4600610D 00115902 000B6100
01808825 44032000 00138040 03D54821 44833000 24070001 46803220 4608003E
00000000 45020006 92E20048 46140281 4600540D 44038000 00000000 92E20048
24420001 28410002 14200020 00000000 44839000 46140081 46809120 4604103E
00000000 4500000C 00000000 244FFFFF 448F3000 44828000 46803220 468084A0
46081280 46125103 4600218D 44033000 1000000E 00000000 0062001A 14400002
00000000 0007000D 2401FFFF 14410004 3C018000 14610002 00000000 0006000D
00001812 00000000 00000000 02630019 46146200 4608003E 0000C812 00B92021
30820003 304800FF 305200FF 45000004 00882023 24160001 10000002 02608025
A1330038 02128021 02515021 2E0100C8 10200006 AE8A0030 02202825 0C000000
02003025 10000007 00000000 2606000F 2401FFF0 00C15824 01603025 0C000000
02202825 12C0001F 02308821 8E840028 2631000F 00116102 30820001 304300FF
00738021 000C6900 2E0100C8 01A08825 305200FF 03D5B021 10200006 00832023
01A02825 0C000000 02003025 10000009 8E980030 2606000F 2401FFF0 00C17024
01C03025 02202825 0C000000 24070001 8E980030 02327821 02308821 01F8C823
A2D90038 8FA8004C 26B50001 26F701D0 56A8FF7B 92F30045 8FBF0044 D7B40018
8FB00020 8FB10024 8FB20028 8FB3002C 8FB40030 8FB50034 8FB60038 8FB7003C
8FBE0040 03E00008 27BD0050
'''.split())
RELOCATIONS = {88: [('R_MIPS_26', 'func_1505DFDC')],
    508: [('R_MIPS_26', 'func_1000480C')], 540: [('R_MIPS_26', 'func_10004514')],
    612: [('R_MIPS_26', 'func_1000480C')], 648: [('R_MIPS_26', 'func_10004514')]}
INSERTIONS = {108: 0x44814000, 109: 0x46086400, 110: 0x00007812, 123: 0x00A09025}


def recipe(words):
    if tuple(words) != RAW:
        raise ValueError('stale complete animation scratch body')
    out = list(words)
    out[0] = (out[0] & 0xFFFF0000) | ((out[0] - 24) & 0xFFFF)
    out[186] += 24
    for i in (17, 30, 32, 33, 49, 169):
        out[i] -= 4
    out[43] = register(register(out[43], 21, 30), 16, 10)

    # Source stays in A2; T0/T1 align scratch, while T9 holds the byte destination.
    out[47] = register(out[47], 16, 6)
    out[48] = register(out[48], 21, 6)
    out[49] = register(out[49], 16, 9)
    out[54] = register(out[54], 11, 8)
    out[55] = register(register(out[55], 16, 8), 11, 9)
    out[56] = words[58]
    out[58] = register(words[59], 11, 25)
    out[59] = register(words[56], 21, 9)
    for i in (83, 84):
        out[i] = register(out[i], 16, 13)

    # Materialize the same 1.0 in F8, then move the first offset to S2 before calls.
    out[108], out[109], out[110] = 0x3C013F80, 0, 0x4610003E
    out[111] = register(register(out[111], 21, 6), 16, 15)
    out[113] = register(out[113], 16, 24)
    out[114] = register(out[114], 16, 5)
    out[116] = register(out[116], 16, 24)
    out[120] = register(out[120], 21, 25)
    out[121] = register(out[121], 16, 5)
    out[122] = register(register(out[122], 21, 5), 16, 9)
    out[126] = register(out[126], 21, 9)

    # Keep the second offset in S2 across its call; T6 is the aligned source skip.
    out[143] = register(out[143], 16, 18)
    out[144] = register(out[144], 21, 18)
    out[146], out[147], out[148] = register(words[148], 16, 14), words[146], words[147]
    out[151] = register(out[151], 16, 14)
    out[156] = register(out[156], 16, 25)
    out[159] = register(out[159], 11, 15)
    out[160] = register(out[160], 21, 15)
    out[164] = register(out[164], 16, 25)
    out[165] = register(out[165], 11, 24)
    out[167] = register(register(register(out[167], 21, 24), 16, 25), 11, 8)
    out[168] = register(out[168], 16, 8)
    out[169] = register(out[169], 16, 9)
    out[172] = register(out[172], 16, 9)

    positions = {i: i + sum(j < i for j in INSERTIONS) for i in range(len(words) + 1)}
    for i, word in enumerate(words):
        opcode = word >> 26
        if opcode in (1, 4, 5, 6, 7, 20, 21, 22, 23) or (opcode == 17 and word >> 21 & 31 == 8):
            displacement = (word & 0x7FFF) - (word & 0x8000)
            target = i + 1 + displacement
            if target not in positions:
                raise ValueError('animation scratch branch leaves the body')
            out[i] = (out[i] & 0xFFFF0000) | ((positions[target] - positions[i] - 1) & 0xFFFF)
    fitted = []
    for i, word in enumerate(out):
        fitted.append(word)
        if i in INSERTIONS:
            fitted.append(INSERTIONS[i])
    assert len(fitted) == WORDS
    return out, fitted


def guard_rows(path):
    text, functions, relocations = parse_object(path)
    target = functions[FUNCTION]
    if target['size'] != 748:
        raise ValueError('unexpected complete animation scratch extent')
    start = target['value']
    relative = {o - start: uses for o, uses in relocations.items() if start <= o < start + target['size']}
    if relative != RELOCATIONS:
        raise ValueError('stale complete animation scratch relocations')
    words = struct.unpack_from('>187I', text, start)
    replacements, _ = recipe(words)
    rows = []
    for i, (old, new) in enumerate(zip(words, replacements)):
        uses = ';'.join(kind + ':' + symbol for kind, symbol in relative.get(i * 4, ())) or '-'
        rows.append(dict(filename='generated_58F80', function=FUNCTION, offset='0x%X' % (i * 4),
            expected='0x%08X' % old, replacement='0x%08X' % new,
            expected_relocations=uses, replacement_relocations=uses,
            note='Check complete scratch body; normalize closed frame constant register schedule',
            insert_after='0x%08X' % INSERTIONS[i] if i in INSERTIONS else '',
            insert_after_relocations='-' if i in INSERTIONS else '', omit='false'))
    return rows


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    return recovery.compile_candidate(root, out, name, body, profile)


def append_guards(path, before, obj):
    if path.read_bytes() != before or not before.endswith(b'\n'):
        raise ValueError('stale animation scratch guard manifest')
    reader = csv.DictReader(io.StringIO(before.decode('ascii')))
    if any(row['function'] == FUNCTION for row in reader):
        raise ValueError('animation scratch guards already published')
    output = io.StringIO(newline='')
    csv.DictWriter(output, fieldnames=reader.fieldnames, lineterminator='\n').writerows(guard_rows(obj))
    path.write_bytes(before + output.getvalue().encode('ascii'))
