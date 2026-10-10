"""Close compiler-derived selector homes, arithmetic producers and branch delays."""
import struct

from tools.experiments import game_actor_segment_selector_layout as layout
from tools.pad_generated_object import parse_object

recovery=layout.recovery
ENTRY, ROM, WORDS = layout.ENTRY,layout.ROM,layout.WORDS
FUNCTION, SOURCE = layout.FUNCTION,layout.SOURCE
SELECTED=dict(layout.scoped_shapes())['shift-sub-original']
RAW=tuple(int(word,16) for word in '''
27BDFF78 AFB60030 0080B025 AFBF003C AFBE0038 AFB70034 AFB5002C AFB40028
AFB30024 AFB20020 AFB1001C AFB00018 00057080 01C57023 000E7080 01C57021
000E7080 01C57023 000E7080 01C57023 3C0F0000 25EF0000 000E7080 01CFA021
3C1E0000 92950004 00003025 02809825 27DE0000 00008025 27B10074 24170002
9262006C 0015C880 03D99021 2841000A 14200004 00104080 2458FFF6 10000024
A2380000 8E4B0000 00484821 01305023 9285006F 014B6021 918D0008 10A00006
A22D0000 14C00004 00000000 0C000000 02802025 00403025 50C00016 26100001
90CE0000 00101080 AFAE0068 90CF0001 10C0000F AFAF006C 8E580000 03A21821
8C630068 0302C821 03304023 9109000A 54690004 926A006C 10000005 A2230000
926A006C 55400003 26100001 A2230000 26100001 26310001 1617FFD1 26730001
92830004 3C020000 3C0CDB06 00035880 004B1021 8C420000 2407000C 02C01825
1040002A 358C0018 AC6C0000 93AD0074 26D60008 3C19DB06 01A70019 3C0CDB06
3739001C 02C02025 358C0028 00007012 004E7821 8DF80000 AC780004 AC990000
93A80075 26D60008 3C19DB06 01070019 02C02825 3739002C 00004812 00495021
8D4B0000 AC8B0004 ACAC0000 928D0068 26D60008 02C03025 01A70019 00007012
004E7821 8DF80000 ACB80004 ACD90000 92880069 26D60008 01070019 00004812
00495021 8D4B0000 ACCB0004 02C01025 8FBF003C 8FB00018 8FB1001C 8FB20020
8FB30024 8FB40028 8FB5002C 8FB60030 8FB70034 8FBE0038 03E00008 27BD0088
'''.split())
RELOCATIONS={80:[('R_MIPS_HI16','D_800CC2D0')],84:[('R_MIPS_LO16','D_800CC2D0')],
    96:[('R_MIPS_HI16','D_800D1C90')],112:[('R_MIPS_LO16','D_800D1C90')],
    204:[('R_MIPS_26','func_1507E908')],324:[('R_MIPS_HI16','D_800C5338')],
    340:[('R_MIPS_LO16','D_800C5338')]}
OUTPUT_RELOCATIONS={80:RELOCATIONS[80],84:RELOCATIONS[84],96:RELOCATIONS[96],
    108:RELOCATIONS[112],208:RELOCATIONS[204],332:RELOCATIONS[324],348:RELOCATIONS[340]}
INSERT_AFTER=(36,52,60)
OMIT=50


def fields(word,rs=None,rt=None,rd=None,op=None,imm=None):
    for shift,width,value in ((21,5,rs),(16,5,rt),(11,5,rd),(26,6,op),(0,16,imm)):
        if value is not None: word=word&~(((1<<width)-1)<<shift)|(value&((1<<width)-1))<<shift
    return word


def recipe(words):
    if tuple(words)!=RAW: raise ValueError('stale complete actor-segment body')
    w=words
    out=list(w[:32])
    out[27],out[28]=w[28],w[27]
    out[30]=fields(w[30],imm=0x80)
    out+=list(w[32:37])
    # Split the existing mode and selector producers; preserve their original ABI values.
    out+=[fields(w[53],rd=3),fields(w[38],rs=3),fields(w[39],imm=38),w[40]]
    # Reassociate mode + 4*i - i + table as table + (4*i - i) + mode.
    out+=[fields(w[41],rt=8),fields(w[37],rd=9),fields(w[43],rd=9),
        fields(w[45],rs=8,rt=9,rd=10),fields(w[44],rt=3),
        fields(w[42],rs=10,rt=2,rd=11),fields(w[46],rs=11,rt=12),
        fields(w[47],rs=3),fields(w[48],rt=12),w[49],w[52],w[51],
        fields(w[52],rs=3,rd=5),w[53],fields(w[54],imm=23),w[55]]
    # Keep distinct pair-index and table-index producers around the two physical stores.
    out+=[fields(w[56],rt=13),fields(w[57],rd=15),fields(w[63],rt=15,rd=2),
        fields(w[58],rt=13),fields(w[59],rt=14),fields(w[57],rd=25),
        fields(w[60],imm=14),fields(w[61],rt=14),w[62],
        fields(w[66],rs=25,rd=25),fields(w[64],rs=2,rt=2),
        fields(w[65],rt=25,rd=8),w[67]]
    # Invert the equality branch and move the emitted store into its likely delay.
    out+=[fields(w[68],op=20,rs=2,imm=7),fields(w[71],rt=2),w[69],
        fields(w[73],imm=5),w[74],fields(w[70],imm=2),fields(w[75],rt=2),
        fields(w[75],rt=2),w[76],w[77],fields(w[78],imm=-49),w[79]]
    out+=list(w[80:])
    for i in (93,106): out[i]=fields(out[i],imm=(out[i]&65535)+12)
    assert len(out)==146 and w[OMIT]==0
    return out


def guard_rows(path):
    text,functions,relocations=parse_object(path)
    target=functions[FUNCTION]
    if target['size']!=576: raise ValueError('expected complete 144-word actor-segment body')
    words=struct.unpack_from('>144I',text,target['value'])
    relative={o-target['value']:r for o,r in relocations.items()
        if target['value']<=o<target['value']+target['size']}
    if relative!=RELOCATIONS: raise ValueError('stale complete actor-segment relocations')
    fitted=recipe(words)
    spec=lambda uses:';'.join(kind+':'+symbol for kind,symbol in uses) or '-'
    rows=[]
    emitted=0
    for index,word in enumerate(words):
        omit=index==OMIT
        row=dict(filename='generated_58F80',function=FUNCTION,offset='0x%X'%(index*4),
            expected='0x%08X'%word,replacement='0x%08X'%(word if omit else fitted[emitted]),
            expected_relocations=spec(relative.get(index*4,())),
            replacement_relocations=spec(() if omit else OUTPUT_RELOCATIONS.get(emitted*4,())),
            note='Normalize closed selector homes, arithmetic producers and branch-delay stores',
            insert_after='',insert_after_relocations='',omit='true' if omit else 'false')
        if not omit: emitted+=1
        if index in INSERT_AFTER:
            row['insert_after']='0x%08X'%fitted[emitted]
            row['insert_after_relocations']=spec(OUTPUT_RELOCATIONS.get(emitted*4,()))
            emitted+=1
        rows.append(row)
    assert emitted==146
    return rows


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    return recovery.compile_candidate(root,out,name,body,profile)


def install(before):
    return recovery.install(before,SELECTED)
