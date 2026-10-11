"""Closed transition register lives and equivalent common-epilogue schedule."""
import struct
from tools.experiments import game_actor_resource_transition_candidates as recovery
from tools.experiments.game_actor_segment_selector_matching import fields
from tools.pad_generated_object import parse_object

ENTRY,ROM,WORDS=recovery.ENTRY,recovery.ROM,recovery.WORDS
FUNCTION,SOURCE=recovery.FUNCTION,recovery.SOURCE
SELECTED=dict(recovery.candidates())['mask-after-store']
RAW=tuple(int(word,16) for word in '''27BDFFD0 AFBF001C AFB00018 AFA60038 00A03825 00047080 01C47023 000E7080 01C47021 000E7080 01C47023 000E7080 01C47023 3C0F0000 25EF0000 000E7080 01CF8021 240100FF 14E1000C A2070004 44802000 24020046 A60000E4 A60000E6 A60000E8 A60200D2 A60200D4 A60000D6 A6000160 10000014 E60400C8 3C190000 27390000 0007C080 03191021 8C480000 02002025 8E05014C 85090006 AFA20020 8E060150 44893000 00000000 46803220 0C000000 E60800C8 8FA20020 8C4A0000 914B0012 A20B0005 0C000000 02002025 304700FF 00076040 3C0D0000 A2020006 01AC6821 95AD0000 00002025 24050002 51A00005 8FBF001C 0C000000 24060002 AE020058 8FBF001C 8FB00018 27BD0030 03E00008 00000000'''.split())
RELOCATIONS={52:[('R_MIPS_HI16','D_800CC2D0')],56:[('R_MIPS_LO16','D_800CC2D0')],
    124:[('R_MIPS_HI16','D_800D1C90')],128:[('R_MIPS_LO16','D_800D1C90')],
    176:[('R_MIPS_26','func_15062BDC')],200:[('R_MIPS_26','func_15084D00')],
    216:[('R_MIPS_HI16','D_800C5A90')],228:[('R_MIPS_LO16','D_800C5A90')],
    248:[('R_MIPS_26','func_1502B020')]}


def recipe(words):
    if tuple(words)!=RAW:raise ValueError('stale complete actor resource transition')
    output=list(words)
    for index in (34,):output[index]=fields(words[index],rd=3)
    for index in (35,):output[index]=fields(words[index],rs=3)
    for index in (39,46):output[index]=fields(words[index],rt=3)
    output[47]=fields(words[47],rs=3,rt=2)
    output[48]=fields(words[48],rs=2,rt=10)
    output[49]=fields(words[49],rt=10)
    output[52]=fields(words[52],rt=3)
    output[53]=fields(words[53],rt=3,rd=11)
    output[54]=fields(words[54],rt=12)
    output[56]=fields(words[56],rs=12,rt=11,rd=12)
    output[57]=fields(words[57],rs=12,rt=12)
    # The annulled zero-count RA load and nonzero-count RA load are alternatives.
    # Merge them at the existing common epilogue, moving a2's emitted constant
    # earlier and copying the emitted move with the renamed canonical-ID source.
    output[60]=fields(words[60],op=4,rs=12,imm=4)
    output[61]=words[63]
    output[63]=fields(words[4],rs=3)
    return output


def guard_rows(path):
    text,functions,relocations=parse_object(path)
    target=functions[FUNCTION];start=target['value']
    if target['size'] not in (280,288) or any(text[start+280:start+target['size']]):
        raise ValueError('unexpected actor resource transition extent')
    words=struct.unpack_from('>70I',text,start)
    relative={offset-start:uses for offset,uses in relocations.items()
        if start<=offset<start+target['size']}
    if relative!=RELOCATIONS:raise ValueError('stale actor resource transition relocations')
    rows=[]
    for index,(word,fitted) in enumerate(zip(words,recipe(words))):
        if word==fitted:continue
        uses=relative.get(index*4,[])
        names=';'.join(kind+':'+symbol for kind,symbol in uses) or '-'
        rows.append(dict(filename='generated_AEB40',function=FUNCTION,offset='0x%X'%(index*4),
            expected='0x%08X'%word,replacement='0x%08X'%fitted,
            expected_relocations=names,replacement_relocations=names,
            note='Normalize closed actor resource register lives and equivalent common epilogue schedule',
            insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==15
    return rows


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    return recovery.compile_candidate(root,out,name,body,profile)


def install(before):return recovery.copied_owner(before,SELECTED)
