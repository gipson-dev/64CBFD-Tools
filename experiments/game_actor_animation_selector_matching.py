"""Closed selector/phase register lives, retained spill slots and independent O32 schedule."""
import struct
from tools.experiments import game_actor_animation_selector_candidates as recovery
from tools.experiments.game_actor_segment_selector_matching import fields
from tools.pad_generated_object import parse_object

ENTRY,ROM,WORDS=recovery.ENTRY,recovery.ROM,recovery.WORDS
FUNCTION,SOURCE=recovery.FUNCTION,recovery.SOURCE
SELECTED=dict(recovery.candidates())['focused-reads-False-True']
RAW=tuple(int(word,16) for word in '''27BDFFC0 AFB00028 00808025 AFBF002C 920201C9 3C0A0000 254A0000 10400055 020A2023 920E0004 3C070000 240100FF 000E7880 00EF3821 14410004 8CE70000 A20001C9 10000008 00001025 921802C9 2442FFFF 0058082A 50200047 8FBF002C 921901C8 10590043 2401032C 0081001A 8E0802C4 00002012 00003025 01024821 91250000 AFA70034 AFA2003C 0C000000 AFA50030 8FA2003C 8FA50030 8FA70034 3C030000 A20201C8 90630000 24010001 3C0D0000 14610003 00056080 3C010000 A0200000 01AC6821 8DAD0000 00057040 3C0F0000 10ED0020 01EE7821 96020084 95EF0000 3419FFFF 02002025 004F082A 1420000F 3045FFFF 44800000 3418FFFF A6180084 44070000 AFA00018 02002025 00002825 3C063F80 E7A00014 0C000000 E7A00010 3C030000 1000000B 90630000 44800000 A6190084 AFA00018 44070000 3C063F80 E7A00014 0C000000 E7A00010 3C030000 90630000 24010001 14610003 24080001 3C010000 A0280000 0C000000 02002025 8FBF002C 8FB00028 27BD0040 03E00008 00000000'''.split())
RELOCATIONS={40:[('R_MIPS_HI16','D_800D1588')],60:[('R_MIPS_LO16','D_800D1588')],
    20:[('R_MIPS_HI16','D_800CC2D0')],24:[('R_MIPS_LO16','D_800CC2D0')],
    140:[('R_MIPS_26','func_150837D4')],160:[('R_MIPS_HI16','D_800C35EA')],
    168:[('R_MIPS_LO16','D_800C35EA')],188:[('R_MIPS_HI16','D_800C3638')],
    192:[('R_MIPS_LO16','D_800C3638')],176:[('R_MIPS_HI16','D_800D1588')],
    200:[('R_MIPS_LO16','D_800D1588')],208:[('R_MIPS_HI16','D_800C5A90')],
    224:[('R_MIPS_LO16','D_800C5A90')],284:[('R_MIPS_26','func_1505E650')],
    292:[('R_MIPS_HI16','D_800C35EA')],300:[('R_MIPS_LO16','D_800C35EA')],
    328:[('R_MIPS_26','func_1505E650')],336:[('R_MIPS_HI16','D_800C35EA')],
    340:[('R_MIPS_LO16','D_800C35EA')],356:[('R_MIPS_HI16','D_800C3638')],
    360:[('R_MIPS_LO16','D_800C3638')],364:[('R_MIPS_26','func_1507EABC')]}


def recipe(words):
    if tuple(words)!=RAW:raise ValueError('stale complete actor animation selector')
    output=list(words)
    for index in (4,):output[index]=fields(words[index],rt=3)
    for index in (7,14,20,59,61):output[index]=fields(words[index],rs=3)
    output[55]=fields(words[55],rt=3)
    for index,offset in ((33,0x38),(36,0x34),(38,0x34),(39,0x38)):
        output[index]=fields(words[index],imm=offset)
    # Only constant/address-independent producers move; memory access order is unchanged.
    output[77:81]=[words[index] for index in (80,77,79,78)]
    return output


def guard_rows(path):
    text,functions,relocations=parse_object(path)
    target=functions[FUNCTION];start=target['value']
    words=struct.unpack_from('>98I',text,start)
    if target['size'] not in (392,400) or any(text[start+392:start+target['size']]):
        raise ValueError('unexpected actor animation selector extent')
    relative={offset-start:uses for offset,uses in relocations.items()
        if start<=offset<start+target['size']}
    if relative!=RELOCATIONS:raise ValueError('stale actor animation selector relocations')
    rows=[]
    for index,(word,fitted) in enumerate(zip(words,recipe(words))):
        if word==fitted:continue
        assert index*4 not in relative
        rows.append(dict(filename='generated_58F80',function=FUNCTION,offset='0x%X'%(index*4),
            expected='0x%08X'%word,replacement='0x%08X'%fitted,
            expected_relocations='-',replacement_relocations='-',
            note='Normalize closed animation selector register lives, retained spills and independent call schedule',
            insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==14
    return rows


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    return recovery.compile_candidate(root,out,name,body,profile)


def install(before):
    return recovery.copied_owner(before,SELECTED)
