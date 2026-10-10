"""Certify the complete dispatcher's private homes and closed emitted schedule."""
import struct

from tools.experiments import game_actor_render_dispatch_candidates as recovery
from tools.experiments import game_actor_render_dispatch_layout as layout
from tools.experiments.game_actor_segment_selector_matching import fields
from tools.pad_generated_object import parse_object

ENTRY,ROM,WORDS=recovery.ENTRY,recovery.ROM,recovery.WORDS
FUNCTION,SOURCE=recovery.FUNCTION,recovery.SOURCE
SELECTED=dict(layout.lifetime_candidates())['ternary-flag']
RAW=tuple(int(word,16) for word in '''
27BDFFA0 AFBF0024 AFA40060 AFA50064 AFA60068 AFA7006C 3C0F0000 91EF0000
8FAE0060 3C180000 11E00015 AFAE005C 93180000 8FB90064 3C090000 17000010
00194080 01194023 00084080 01194021 00084080 01194023 00084080 01194023
00084080 25290000 0C000000 01092021 54400004 8FAD0064 1000008E 8FA20060
8FAD0064 3C0F0000 8FAA0068 000D7080 01CD7023 000E7080 01CD7021 000E7080
01CD7023 000E7080 01CD7023 000E7080 25EF0000 01CF3821 90F80074 240C0001
314B001F 016C1004 0302C824 14590003 00E02025 10000077 8FA20060 8FA50068
0C000000 AFA70030 14400003 8FA70030 10000070 8FA20060 8CE801D4 8FA6006C
24010004 15000003 00000000 10000069 8FA20060 10C1000D 00E02025 24010005
10C1000A 24010003 10C10008 87A5006A 8FA40064 0C000000 AFA70030 8FA70030
90E901C8 10000005 AFA90040 27A50040 0C000000 AFA70030 8FA70030 8FA40064
27A50044 0C000000 AFA70030 3C0A0000 8D4A0000 8FA70030 27A50044 854C003E
8FA60068 240B00FF 11800005 00E02025 0C000000 AFA70030 10000002 8FA70030
AFAB0050 00E02025 8FA50068 0C000000 AFA70030 284100FF 8FA70030 1020000D
00401825 8CE20318 5040000B 8FB8006C 8C4D002C 24010100 8FAE0068 55A10006
8FB8006C 90EF0127 51CF0003 8FB8006C 240300FF 8FB8006C 24010004 3C080000
1701000A 27AC0044 91080000 3C190000 8F390000 01030019 AFB90054 00001812
00034A03 10000003 01201825 8CEA01D4 AFAA0054 8FAB006C 8FAD0070 8FA40060
8FA50064 8FA60068 8FA70054 AFA30010 AFAC0014 AFAB0018 0C000000 AFAD001C
3C0F0000 91EF0000 3C190000 3C0E0000 000FC080 0338C821 8F390000 8DCE0000
00401825 00594023 000848C3 01C9082A 10200003 00001025 10000001 24020001
54400004 8FA2005C 10000002 00601025 8FA2005C 8FBF0024 27BD0060 03E00008
00000000
'''.split())
RELOCATIONS={24:[('R_MIPS_HI16','D_800C3638')],28:[('R_MIPS_LO16','D_800C3638')],
    36:[('R_MIPS_HI16','D_800C3656')],48:[('R_MIPS_LO16','D_800C3656')],
    56:[('R_MIPS_HI16','D_800CC2D0')],100:[('R_MIPS_LO16','D_800CC2D0')],
    104:[('R_MIPS_26','func_150229E4')],132:[('R_MIPS_HI16','D_800CC2D0')],
    176:[('R_MIPS_LO16','D_800CC2D0')],224:[('R_MIPS_26','func_1506196C')],
    308:[('R_MIPS_26','func_1502C6E8')],336:[('R_MIPS_26','func_150849CC')],
    356:[('R_MIPS_26','func_1502D54C')],364:[('R_MIPS_HI16','D_800B0DF0')],
    368:[('R_MIPS_LO16','D_800B0DF0')],400:[('R_MIPS_26','func_1502D630')],
    428:[('R_MIPS_26','func_1506196C')],524:[('R_MIPS_HI16','D_800DF7C0')],
    528:[('R_MIPS_LO16','D_800DF7C0')],508:[('R_MIPS_HI16','D_800DF7C4')],
    520:[('R_MIPS_LO16','D_800DF7C4')],600:[('R_MIPS_26','func_1502CCFC')],
    620:[('R_MIPS_HI16','D_800BEBA4')],636:[('R_MIPS_LO16','D_800BEBA4')],
    608:[('R_MIPS_HI16','D_800BE9C0')],612:[('R_MIPS_LO16','D_800BE9C0')],
    616:[('R_MIPS_HI16','D_800BE9C8')],632:[('R_MIPS_LO16','D_800BE9C8')]}
OMIT=48
TEMPORARIES=dict(zip((8,9,10,11,12,13,14,15,24,25),(25,8,9,10,11,12,13,14,15,24)))
HOMES={0x30:0x2C,0x40:0x54,0x44:0x40,0x50:0x4C,0x54:0x38,0x5C:0x34,
    0x60:0x58,0x64:0x5C,0x68:0x60,0x6A:0x62,0x6C:0x64,0x70:0x68}
OUTPUT_RELOCATIONS={(136 if offset==176 else offset-4 if offset>OMIT*4 else offset):uses
    for offset,uses in RELOCATIONS.items()}


def recipe(words):
    if tuple(words)!=RAW:
        raise ValueError('stale complete actor render dispatch')
    out=[]
    for index,word in enumerate(words):
        op,rs,rt=word>>26,word>>21&31,word>>16&31
        if index>=29 and index!=34:
            mapping=TEMPORARIES
            if 127<=index<=138:
                # The mode-four factor, matrix and product temporaries close a second cycle.
                mapping=dict(TEMPORARIES)
                mapping.update({8:24,25:8,9:25})
            moved=lambda register:mapping.get(register,register)
            if op==0:
                word=fields(word,rs=moved(rs),rt=moved(rt),rd=moved(word>>11&31))
            elif op in (4,5,9,10,12,20,21,33,35,36,43):
                word=fields(word,rs=moved(rs),rt=moved(rt))
            elif op==15:
                word=fields(word,rt=moved(rt))
            elif op!=3:
                raise ValueError('unqualified dispatcher opcode')
        if rs==29 and op in (9,33,35,43) and word&65535 in HOMES:
            word=fields(word,imm=HOMES[word&65535])
        if op in (4,5,20,21):
            displacement=(word&65535)^32768
            target=index+1+displacement-32768
            if target==OMIT:
                raise ValueError('branch targets omitted view mask')
            new_index=index-(index>OMIT)
            new_target=target-(target>OMIT)
            word=fields(word,imm=new_target-new_index-1)
        out.append(word)
    out[0]=fields(out[0],imm=-0x58)
    out[174]=fields(out[174],imm=0x58)
    # The base low-half and saved view read are independent before actor construction.
    out[34],out[44]=out[44],out[34]
    # MIPS sllv already masks its count to five bits; keep the portable C source mask.
    out[49]=fields(out[49],rs=10)
    # Invert the likely return branch and preserve both delay-slot result producers.
    out[168]=fields(out[168],op=20)
    out[169],out[171]=out[171],out[169]
    out[172]=out[169]
    del out[OMIT]
    assert len(out)==WORDS
    return out


def guard_rows(path):
    text,functions,relocations=parse_object(path)
    target=functions[FUNCTION]
    if target['size']!=708:
        raise ValueError('expected complete 177-word actor render dispatcher')
    words=struct.unpack_from('>177I',text,target['value'])
    relative={offset-target['value']:uses for offset,uses in relocations.items()
        if target['value']<=offset<target['value']+target['size']}
    if relative!=RELOCATIONS:
        raise ValueError('stale complete actor render relocations')
    fitted=recipe(words)
    uses=lambda items:';'.join(kind+':'+symbol for kind,symbol in items) or '-'
    rows=[]
    emitted=0
    for index,word in enumerate(words):
        omitted=index==OMIT
        rows.append(dict(filename='generated_58F80',function=FUNCTION,offset='0x%X'%(index*4),
            expected='0x%08X'%word,replacement='0x%08X'%(word if omitted else fitted[emitted]),
            expected_relocations=uses(relative.get(index*4,())),
            replacement_relocations=uses(() if omitted else OUTPUT_RELOCATIONS.get(emitted*4,())),
            note='Normalize certified render dispatch homes, temporary cycle and branch schedule',
            insert_after='',insert_after_relocations='',omit='true' if omitted else 'false'))
        if not omitted:
            emitted+=1
    assert emitted==WORDS
    return rows


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    return recovery.compile_candidate(root,out,name,body,profile)


def install(before):
    if before.count(recovery.ORIGINAL)!=1:
        raise ValueError('expected untouched render dispatch placeholder')
    declarations=recovery.DECLARATIONS.replace('extern u8 D_800CC2D0[],','extern u8 ').replace(
        's32 func_1506196C(u8 *,s32);','').replace('void func_1502C6E8(s32,s16,s32);','').replace(
        'void func_1502D54C(s32,s32 *);','s32 func_1502D54C();').replace(
        'void func_1502D630(u8 *,s32 *,s32);','s32 func_1502D630();').replace(
        'Gfx *func_1502CCFC(Gfx *,s32,s32,u8 *,s32,s32 *,s32,s32);','s32 func_1502CCFC();')
    body=SELECTED.replace('func_1506196C(actor, view)',
        'func_1506196C((ActorDisplay58F80 *)actor, view)').replace(
        'commands = func_1502CCFC(commands,','commands = (Gfx *)func_1502CCFC(commands,')
    return before.replace(recovery.ORIGINAL,declarations+'\n'+body)
