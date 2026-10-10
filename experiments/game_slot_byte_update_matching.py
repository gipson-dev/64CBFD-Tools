"""Closed saved-role permutation; the semantic C already has the retail extent."""
import struct

from tools.experiments import game_slot_byte_update_candidates as recovery
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = recovery.ENTRY, recovery.ROM, recovery.WORDS
FUNCTION, SOURCE, ORIGINAL, SELECTED = recovery.FUNCTION,recovery.SOURCE,recovery.ORIGINAL,recovery.SELECTED
RAW = tuple(int(word,16) for word in '''
27BDFFD0 AFB50028 0080A825 AFBF002C AFB40024 AFB30020 AFB2001C AFB10018
AFB00014 00157080 01D57023 000E7080 01D57021 000E7080 01D57023 000E7080
01D57023 3C0F0000 25EF0000 000E7080 01CF8021 00008825 24140001 24130001
24120002 9218006C 02A02025 2B01000A 50200015 26310001 0C000000 02202825
304300FF 14600006 00000000 9202006C 1840000C 2459FFFF 1000000A A219006C
56630008 A214006C 9202006C 28410002 10200004 24480001 10000002 A208006C
A214006C 26310001 1632FFE6 26100001 00154880 01354823 00094880 01354821
00094880 01354823 00094880 01354823 3C0B0000 256B0000 00095080 0C000000
014B2021 8FBF002C 8FB00014 8FB10018 8FB2001C 8FB30020 8FB40024 8FB50028
03E00008 27BD0030
'''.split())
RENAMES = [(2,11,21,18),(22,16,20,21),(23,16,19,20),(24,16,18,19),
    (40,21,19,20),(41,16,20,21),(48,16,20,21),(50,16,18,19),
    (60,16,11,10),(61,21,11,10),(61,16,11,10),(62,11,10,9),
    (64,21,10,9),(64,16,11,10)]
for index in (9,10,12,14,16,26,52,53,55,57,59):
    RENAMES.append((index,21 if index==26 else 16,21,18))
RELOCATIONS = {68:[('R_MIPS_HI16','D_800CC2D0')],72:[('R_MIPS_LO16','D_800CC2D0')],
    120:[('R_MIPS_26','func_1502EE8C')],240:[('R_MIPS_HI16','D_800CC2D0')],
    244:[('R_MIPS_LO16','D_800CC2D0')],252:[('R_MIPS_26','func_1507E3C0')]}


def recipe(words):
    if tuple(words)!=RAW:
        raise ValueError('stale complete slot-byte updater body')
    result = list(words)
    for index,shift,old,new in RENAMES:
        if result[index]>>shift&31 != old:
            raise ValueError('stale slot-byte producer role')
        result[index] = result[index]&~(31<<shift) | new<<shift
    # Preserve physical saved homes; permute only the independent opening stores.
    result[1],result[4],result[5],result[6] = words[6],words[1],words[4],words[5]
    return result


def guard_rows(path):
    text,functions,relocations = parse_object(path)
    target = functions[FUNCTION]
    if target['size']!=296:
        raise ValueError('expected complete 74-word slot-byte body')
    words = struct.unpack_from('>74I',text,target['value'])
    relative = {offset-target['value']:uses for offset,uses in relocations.items()
        if target['value']<=offset<target['value']+target['size']}
    if relative != RELOCATIONS:
        raise ValueError('stale complete slot-byte relocations')
    replacements = recipe(words)
    spec = lambda uses: ';'.join(kind+':'+name for kind,name in uses) or '-'
    return [dict(filename='generated_58F80',function=FUNCTION,offset='0x%X'%(index*4),
        expected='0x%08X'%word,replacement='0x%08X'%replacements[index],
        expected_relocations=spec(relative.get(index*4,())),
        replacement_relocations=spec(relative.get(index*4,())),
        note='Normalize certified slot-byte saved roles and independent save order',
        insert_after='',insert_after_relocations='',omit='false') for index,word in enumerate(words)]


def install(before):
    prototype = 's32 func_1502EEF4();'
    if before.count(ORIGINAL)!=1 or before.count(prototype)!=1:
        raise ValueError('expected unique slot-byte placeholder and prototype')
    return before.replace('#include <ultra64.h>', '#include <ultra64.h>\nvoid func_1507E3C0(u8 *);',1).replace(
        prototype,'void func_1502EEF4(s32 slot);').replace(ORIGINAL,SELECTED)
