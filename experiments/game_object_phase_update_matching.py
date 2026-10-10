"""Closed leaf schedule and register recipe with separately certified owner pools."""
import struct

from tools.experiments import game_object_phase_update_candidates as recovery
from tools.experiments import game_object_color_mode_matching as color
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = recovery.ENTRY, recovery.ROM, recovery.WORDS
FUNCTION, SOURCE, ORIGINAL, SELECTED = recovery.FUNCTION, recovery.SOURCE, recovery.ORIGINAL, recovery.SELECTED
RAW = tuple(int(word, 16) for word in '''
908E00A4 25CFFFFE 2DE10006 10200045 000F7880 3C010000 002F0821 8C2F0000
01E00008 00000000 3C190000 8F390000 909800A6 908300A5 03190019 00001012
0043082A 10200003 00624023 03E00008 A08800A5 03E00008 A08000A5 3C020000
8C420000 908300A7 00024880 01224821 00094840 0123082A 10200003 00695023
10000002 A08A00A7 A08000A4 3C0C0000 8D8C0000 908B00A6 908E00A5 016C0019
00006812 01CD7821 03E00008 A08F00A5 3C190000 8F390000 909800A6 908300A5
240500FF 03190019 240A0007 00001012 00A24023 0068082A 10200003 00624821
10000002 A08900A5 A08500A5 03E00008 A08A00A4 3C0C0000 8D8C0000 908B00A6
908300A5 016C0019 00001012 0043082A 10200003 00627023 03E00008 A08E00A5
A08000A4 03E00008 00000000
'''.split())
RENAMES = ((48,16,5,8), (50,16,10,12), (52,21,5,8), (52,11,8,9),
    (53,16,8,9), (55,11,9,10), (57,16,9,10), (58,16,5,11), (60,16,10,12),
    (61,16,12,13), (62,21,12,13), (62,16,12,13), (63,16,11,14),
    (65,21,11,14), (65,16,12,13), (69,11,14,15), (71,16,14,15))
RELOCATIONS = {20:[('R_MIPS_HI16','.rodata')], 28:[('R_MIPS_LO16','.rodata')]}
for offset in (40,92,140,176,244):
    RELOCATIONS[offset] = [('R_MIPS_HI16','D_800BE9E4')]
    RELOCATIONS[offset+4] = [('R_MIPS_LO16','D_800BE9E4')]
TABLE = 'jtbl_80096F04_game'


def recipe(words, owner=False):
    expected = list(RAW)
    expected[7] |= 0x100 if owner else 0
    if list(words) != expected:
        raise ValueError('stale complete object phase-update body')
    changed = list(words)
    for index, shift, old, new in RENAMES:
        if changed[index] >> shift & 31 != old:
            raise ValueError('stale phase producer role')
        changed[index] = changed[index] & ~(31 << shift) | new << shift
    changed[3] = changed[3] & 0xFFFF0000 | 0x48
    changed[7] &= 0xFFFF0000
    # Retail has explicit stores before two returns and separate 255 producers.
    replacements = list(changed)
    replacements[21:23] = [changed[22], changed[21]]
    replacements[59:61] = [changed[60], changed[59]]
    inserted = {22:0, 49:0x240B00FF, 60:0}
    fitted = []
    for index, word in enumerate(replacements):
        fitted.append(word)
        if index in inserted:
            fitted.append(inserted[index])
    assert len(fitted) == WORDS
    return fitted, replacements, inserted


def guard_rows(path, owner=False):
    text, functions, relocations = parse_object(path)
    target = functions[FUNCTION]
    if target['size'] != 300:
        raise ValueError('expected complete 75-word phase body')
    words = struct.unpack_from('>75I', text, target['value'])
    relative = {offset-target['value']:uses for offset,uses in relocations.items()
        if target['value'] <= offset < target['value']+target['size']}
    if relative != RELOCATIONS:
        raise ValueError('stale complete phase relocations')
    _, replacements, inserted = recipe(words, owner)
    spec = lambda uses: ';'.join(kind+':'+name for kind,name in uses) or '-'
    return [dict(filename='generated_58F80', function=FUNCTION, offset='0x%X'%(index*4),
        expected='0x%08X'%word, replacement='0x%08X'%replacements[index],
        expected_relocations=spec(relative.get(index*4,())),
        replacement_relocations=spec([(kind,TABLE) for kind,_ in relative[index*4]]
            if index in (5,7) else relative.get(index*4,())),
        note='Normalize certified phase-update schedule and protected table relocation',
        insert_after='0x%08X'%inserted[index] if index in inserted else '',
        insert_after_relocations='-' if index in inserted else '', omit='false')
        for index,word in enumerate(words)]


def requalify_color(path, rows):
    text, functions, relocations = parse_object(path)
    target = functions[color.FUNCTION]
    if target['size'] != 592:
        raise ValueError('stale neighboring color extent')
    words = list(struct.unpack_from('>148I', text, target['value']))
    expected = list(color.RAW)
    expected[9] |= 0x118
    relative = {offset-target['value']:uses for offset,uses in relocations.items()
        if target['value'] <= offset < target['value']+target['size']}
    if words != expected or relative != color.RELOCATIONS:
        raise ValueError('stale complete neighboring color body or relocations')
    words[9] &= 0xFFFF0000
    color.recipe(words)
    result = [dict(row) for row in rows]
    selected = [row for row in result if row['filename']=='generated_58F80'
        and row['function']==color.FUNCTION and row['offset']=='0x24']
    if len(selected) != 1 or selected[0]['expected'] != '0x8C2F0100':
        raise ValueError('stale previously banked color addend guard')
    selected[0]['expected'] = '0x8C2F0118'
    return result


def install(before):
    prototype = 's32 func_1502EAFC();'
    call = '    func_1502EAFC(actor);'
    if any(before.count(part)!=1 for part in (ORIGINAL,prototype,call)):
        raise ValueError('expected unique phase placeholder, prototype and caller')
    return before.replace('#include <ultra64.h>', '#include <ultra64.h>\n'+recovery.DECLARATIONS.rstrip('\n'),1).replace(
        prototype,'void func_1502EAFC(u8 *object);').replace(call,'    func_1502EAFC((u8 *)actor);').replace(ORIGINAL,SELECTED)
