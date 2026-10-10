"""Close the full shading caller's constant lifetime and branch-side setup."""
import struct

from tools.experiments import game_actor_alpha_shading_candidates as recovery
from tools.experiments.game_actor_segment_selector_matching import fields
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = recovery.ENTRY, recovery.ROM, recovery.WORDS
FUNCTION, SOURCE = recovery.FUNCTION, recovery.SOURCE
SELECTED = dict(recovery.candidates())['ordered-private-homes']
RAW = tuple(int(word, 16) for word in '''
27BDFFA8 44809000 AFBF0024 AFA40058 AFA5005C AFA60060 3C010000 C4200000
8FB80060 3C080000 46009032 25080000 0018C980 3C0E0000 45010005 03282021
3C013F80 44812000 10000003 46002383 3C010000 C42E0000 3C010000 C4200000
3C010000 8FA90058 46009032 27AA0040 27AB003C 27AC0038 45010005 27AD0034
3C013F80 44813000 10000002 46003083 C4220000 46027201 95CE0000 3C010000
C42A0000 448E2000 3C014F80 460A4002 05C10004 468021A0 44814000 00000000
46083180 46003282 3C0F0000 95EF0000 3C014F80 448F2000 46025400 05E10004
46802220 44813000 00000000 46064200 46004282 8D250014 8D260018 8D27001C
E7B00050 AFAD001C AFAC0018 46025300 AFAB0014 AFAA0010 0C000000 E7AC0054
C7A20034 44809000 3C013F80 44817000 46121032 C7AC0054 C7B00050 3C010000
45010003 00000000 10000002 46027083 C4220000 4612103C 3C01437F 45020005
4602603E E7A20034 10000013 46009006 4602603E 00000000 45020005 4610103E
E7A20034 1000000C 46009006 4610103E 00000000 45020005 460C1101 E7A20034
10000005 46007006 460C1101 E7A20034 460C8181 46062003 46007201 44815000
8FB8005C 460A4102 4600218D 440F3000 00000000 AF0F000C 8FBF0024 03E00008
27BD0058
'''.split())
RELOCATIONS = {
    24: [('R_MIPS_HI16', 'D_800D9B1C')], 28: [('R_MIPS_LO16', 'D_800D9B1C')],
    36: [('R_MIPS_HI16', 'D_800D2CA8')], 44: [('R_MIPS_LO16', 'D_800D2CA8')],
    52: [('R_MIPS_HI16', 'D_800DD2E8')], 152: [('R_MIPS_LO16', 'D_800DD2E8')],
    80: [('R_MIPS_HI16', 'D_80096DE8')], 84: [('R_MIPS_LO16', 'D_80096DE8')],
    88: [('R_MIPS_HI16', 'D_800D9B20')], 92: [('R_MIPS_LO16', 'D_800D9B20')],
    96: [('R_MIPS_HI16', 'D_80096DEC')], 144: [('R_MIPS_LO16', 'D_80096DEC')],
    156: [('R_MIPS_HI16', 'D_80096DF0')], 160: [('R_MIPS_LO16', 'D_80096DF0')],
    200: [('R_MIPS_HI16', 'D_800DD2EC')], 204: [('R_MIPS_LO16', 'D_800DD2EC')],
    280: [('R_MIPS_26', 'func_150A7A00')],
    316: [('R_MIPS_HI16', 'D_80096DF4')], 336: [('R_MIPS_LO16', 'D_80096DF4')]}
OUTPUT_RELOCATIONS = {o: uses for o, uses in RELOCATIONS.items() if o < 316}
OUTPUT_RELOCATIONS.update({312: RELOCATIONS[316], 340: RELOCATIONS[336]})
INSERT_AFTER = (73, 80, 83, 84)


def recipe(words):
    if tuple(words) != RAW:
        raise ValueError('stale complete shading body')
    w = words
    out = list(w[:74])
    # Split zero from one; place copies of existing one producers in each reciprocal arm.
    out += [fields(w[73], rd=14), w[77], w[76], w[78], w[79],
        fields(w[80], imm=5), w[81], w[74], fields(w[75], rd=18),
        fields(w[82], imm=5), fields(w[83], rd=18), w[84],
        w[74], fields(w[75], rd=18), w[81]]
    out += list(w[85:])
    for index in (85, 91, 98):
        if index == 85:
            out[index + 4] = fields(w[index], rt=14)
        else:
            out[index + 4] = fields(w[index], rd=14)
    for index in (105, 110):
        out[index + 4] = fields(w[index], rd=18)
    assert len(out) == WORDS
    return out


def guard_rows(path):
    text, functions, relocations = parse_object(path)
    target = functions[FUNCTION]
    if target['size'] != 484:
        raise ValueError('expected complete 121-word shading body')
    words = struct.unpack_from('>121I', text, target['value'])
    relative = {o - target['value']: uses for o, uses in relocations.items()
        if target['value'] <= o < target['value'] + target['size']}
    if relative != RELOCATIONS:
        raise ValueError('stale complete shading relocations')
    fitted, rows, emitted = recipe(words), [], 0
    spec = lambda uses: ';'.join(kind + ':' + symbol for kind, symbol in uses) or '-'
    for i, word in enumerate(words):
        row = dict(filename='generated_58F80', function=FUNCTION, offset='0x%X' % (i * 4),
            expected='0x%08X' % word, replacement='0x%08X' % fitted[emitted],
            expected_relocations=spec(relative.get(i * 4, ())),
            replacement_relocations=spec(OUTPUT_RELOCATIONS.get(emitted * 4, ())),
            note='Normalize complete shading zero/one lifetime and reciprocal branch setup',
            insert_after='', insert_after_relocations='', omit='false')
        emitted += 1
        if i in INSERT_AFTER:
            row['insert_after'] = '0x%08X' % fitted[emitted]
            row['insert_after_relocations'] = spec(OUTPUT_RELOCATIONS.get(emitted * 4, ()))
            emitted += 1
        rows.append(row)
    assert emitted == WORDS
    return rows


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    return recovery.compile_candidate(root, out, name, body, profile)


def install(before):
    if before.count(recovery.ORIGINAL) != 1 or before.count('s32 func_1502D630();') != 1:
        raise ValueError('stale shading owner or declaration')
    return before.replace('s32 func_1502D630();', 'void func_1502D630(u8 *, s32 *, s32);').replace(
        recovery.ORIGINAL, recovery.DECLARATIONS + '\n' + SELECTED)
