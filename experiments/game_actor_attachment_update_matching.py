"""Close two commutative additions and one leaf temporary-register cycle."""
import struct

from tools.experiments import game_actor_attachment_update_candidates as recovery
from tools.pad_generated_object import parse_object

ENTRY,ROM,WORDS=recovery.ENTRY,recovery.ROM,recovery.WORDS
FUNCTION,SOURCE=recovery.FUNCTION,recovery.SOURCE
SELECTED=dict(recovery.candidates())['ordered-u32-volatile-stores']
RAW=tuple(int(word,16) for word in '''
3C050000 24A50000 2406032C 00860019 00007012 00AE1021 90430065 1060004F
00000000 00660019 90580101 24010002 33190002 00007812 01E52021 13210047
2484FCD4 8C8301D4 3C01C080 54600009 8C48005C C4840014 E4440014 C4860018
E4460018 C488001C 1000000A E448001C 8C48005C 00084980 01231821 C46A0030
E44A0014 C4700034 E4500018 C4720038 E452001C 90430101 C4840180 44813000
306A0020 E4440180 1540000E E4460020 94850076 90430101 A4450076 C488003C
E448003C C48A0040 E44A0040 948B0076 A44B0076 948C007A A44C007A 948D0078
A44D0078 306E0040 15C0001C 00000000 908F0007 3C070000 24E70000 A04F0007
90980008 00001825 00802825 A0580008 90990009 00403025 A0590009 9088000A
A048000A 9089000F A049000F 8CEA0000 0540000A 00000000 90AB000B 24630001
24A50001 A0CB000B 8CEC0000 24C60001 0183082A 5020FFF9 90AB000B 03E00008
00000000
'''.split())
RELOCATIONS={0:[('R_MIPS_HI16','D_800CC2D0')],4:[('R_MIPS_LO16','D_800CC2D0')],
    244:[('R_MIPS_HI16','D_80082FA0')],248:[('R_MIPS_LO16','D_80082FA0')]}


def register(word,shift,value):
    return word&~(31<<shift)|value<<shift


def recipe(words):
    if tuple(words)!=RAW: raise ValueError('stale complete attachment updater')
    out=list(words)
    for index in (14,30):
        word=out[index]
        out[index]=register(register(word,21,word>>16&31),16,word>>21&31)
    for index in (44,46): out[index]=register(out[index],16,11)
    for index in range(51,58): out[index]=register(out[index],16,(out[index]>>16&31)+1)
    out[58]=register(out[58],21,15)
    mapping={15:24,24:25,25:8,8:9,9:10,10:11,11:12,12:13}
    for index in (60,63,64,67,68,70,71,72,73,74,75,78,81,82,86):
        out[index]=register(out[index],16,mapping[out[index]>>16&31])
    for index in (76,84): out[index]=register(out[index],21,mapping[out[index]>>21&31])
    return out


def guard_rows(path):
    text,functions,relocations=parse_object(path)
    target=functions[FUNCTION]
    if target['size']!=356: raise ValueError('expected complete 89-word attachment updater')
    words=struct.unpack_from('>89I',text,target['value'])
    relative={offset-target['value']:uses for offset,uses in relocations.items()
        if target['value']<=offset<target['value']+target['size']}
    if relative!=RELOCATIONS: raise ValueError('stale complete attachment relocations')
    fitted=recipe(words)
    rows=[]
    for index,(before,after) in enumerate(zip(words,fitted)):
        uses=';'.join(kind+':'+symbol for kind,symbol in relative.get(index*4,())) or '-'
        rows.append(dict(filename='generated_58F80',function=FUNCTION,offset='0x%X'%(index*4),
            expected='0x%08X'%before,replacement='0x%08X'%after,
            expected_relocations=uses,replacement_relocations=uses,
            note='Normalize closed attachment temporary-register cycle and commutative additions',
            insert_after='',insert_after_relocations='',omit='false'))
    return rows


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    return recovery.compile_candidate(root,out,name,body,profile)


def install(before):
    return recovery.install(before,SELECTED)
