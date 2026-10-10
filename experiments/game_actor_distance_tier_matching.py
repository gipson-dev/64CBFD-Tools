"""Certify private spill homes and one closed single-precision scheduling block."""
import struct

from tools.experiments import game_actor_distance_tier_candidates as recovery
from tools.pad_generated_object import parse_object

ENTRY,ROM,WORDS=recovery.ENTRY,recovery.ROM,recovery.WORDS
FUNCTION,SOURCE=recovery.FUNCTION,recovery.SOURCE
SELECTED=dict(recovery.candidates())['early-square-local']
RAW=tuple(int(word,16) for word in '''
27BDFFB0 AFA50054 00057400 000E2C03 AFBF0014 AFA40050 AFA60058 8FA80050
0005C080 0305C021 00084880 01284823 00094880 01284821 00094880 01284823
00094880 3C0A0000 01284823 0018C080 00094880 254A0000 0305C023 012A3821
90EB01C9 0018C080 3C190000 8F390000 0305C021 0018C140 15600080 03191821
90EC0005 24010007 1181007C 3C0143FA 44812000 3C010000 C4260000 3C010000
C4280000 3C0144FA 44815000 E7A40038 E7A6003C E7A80040 E7AA0044 90E502C8
2401FFFF 00E02025 24A5FFFF 50A1006C 8FBF0014 AFA30048 AFA50028 0C000000
AFA7001C 8FA30048 8FA7001C 8FA50028 C47002F8 C4F20014 C46402FC C4E60018
46128001 C46A0300 C4F0001C 3C0D0000 46000082 46062001 C7A40038 3C0E0000
46000202 46105001 46000482 C7A0003C 46081080 46042182 46121080 4606103C
00000000 45000003 00000000 10000019 00001825 46000202 C7A00040 4608103C
00000000 45000003 00000000 10000011 24030001 46000282 C7A00044 460A103C
00000000 45000003 00000000 10000009 24030002 46000402 24030004 4610103C
00000000 45000003 00000000 10000001 24030003 28610002 14200008 3C014040
44812000 C4F2003C 4604903C 00000000 45000002 00000000 2463FFFF 10400007
2401005A 14410009 00000000 14600007 00000000 10000005 24030001 91AD0000
11A00002 00000000 24030001 91CE0000 24010001 55C10003 00A3082A 00001825
00A3082A 50200005 2401FFFF 04A10002 00A01825 00001825 2401FFFF 50610010
8FBF0014 90EF01C8 506F000D 8FBF0014 8CF802C4 8FA40050 00003025 0303C821
93250000 AFA7001C 0C000000 AFA30020 8FA30020 8FA7001C A0E301C8 8FBF0014
27BD0050 03E00008 00000000
'''.split())
RELOCATIONS={68:[('R_MIPS_HI16','D_800CC2D0')],84:[('R_MIPS_LO16','D_800CC2D0')],
    104:[('R_MIPS_HI16','D_800DBFF0')],108:[('R_MIPS_LO16','D_800DBFF0')],
    148:[('R_MIPS_HI16','D_80096DE0')],152:[('R_MIPS_LO16','D_80096DE0')],
    156:[('R_MIPS_HI16','D_80096DE4')],160:[('R_MIPS_LO16','D_80096DE4')],
    220:[('R_MIPS_26','func_150849A0')],268:[('R_MIPS_HI16','D_800BE616')],
    284:[('R_MIPS_HI16','D_800C35EA')],508:[('R_MIPS_LO16','D_800BE616')],
    524:[('R_MIPS_LO16','D_800C35EA')],616:[('R_MIPS_26','func_150837D4')]}
FITTED_RELOCATIONS=dict(RELOCATIONS)
FITTED_RELOCATIONS[280]=FITTED_RELOCATIONS.pop(268)


def register(word,shift,value):
    return word&~(31<<shift)|value<<shift


def immediate(word,value):
    return word&0xFFFF0000|value&65535


def fp(destination,left,right,operation):
    return 0x46000000|right<<16|left<<11|destination<<6|operation


def recipe(words):
    if tuple(words)!=RAW: raise ValueError('stale complete distance tier updater')
    out=list(words)
    for index in range(43,47): out[index]=immediate(out[index],(out[index]&65535)-16)
    for index in (53,57): out[index]=immediate(out[index],0x4C)
    for index in (54,59): out[index]=immediate(out[index],0x3C)
    for index in (155,156): out[index]=immediate(out[index],0x40)
    # Keep the ordered coordinate reads and x*x + y*y + z*z rounding edges.
    out[65],out[66]=register(words[65],16,8),register(words[66],16,10)
    out[67]=immediate(register(words[70],16,16),0x28)
    out[70]=words[67]
    out[72]=fp(0,0,0,2)
    out[73]=fp(2,2,0,0)
    out[74]=fp(0,8,10,1)
    out[75]=fp(0,0,0,2)
    out[76]=fp(2,2,0,0)
    out[77]=fp(18,16,16,2)
    out[78]=immediate(words[75],0x2C)
    out[79]=fp(0,2,18,60)
    for multiply,load,compare,reg,home in ((85,86,87,4,0x30),(93,94,95,6,0x34)):
        out[multiply]=fp(reg,0,0,2)
        out[load]=immediate(out[load],home)
        out[compare]=fp(0,2,reg,60)
    out[101],out[103]=fp(8,0,0,2),fp(0,2,8,60)
    out[112]=register(words[112],11,16)
    out[113]=register(words[113],16,10)
    out[114]=fp(0,10,16,60)
    return out


def guard_rows(path):
    text,functions,relocations=parse_object(path)
    target=functions[FUNCTION]
    if target['size']!=652: raise ValueError('expected complete 163-word distance tier updater')
    words=struct.unpack_from('>163I',text,target['value'])
    relative={offset-target['value']:uses for offset,uses in relocations.items()
        if target['value']<=offset<target['value']+target['size']}
    if relative!=RELOCATIONS: raise ValueError('stale complete distance tier relocations')
    fitted=recipe(words)
    uses=lambda rs,offset:';'.join(kind+':'+symbol for kind,symbol in rs.get(offset,())) or '-'
    return [dict(filename='generated_58F80',function=FUNCTION,offset='0x%X'%(index*4),
        expected='0x%08X'%before,replacement='0x%08X'%after,
        expected_relocations=uses(relative,index*4),replacement_relocations=uses(FITTED_RELOCATIONS,index*4),
        note='Normalize certified distance tier private homes and closed floating schedule',
        insert_after='',insert_after_relocations='',omit='false')
        for index,(before,after) in enumerate(zip(words,fitted))]


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    return recovery.compile_candidate(root,out,name,body,profile)


def install(before):
    return recovery.install(before,SELECTED)
