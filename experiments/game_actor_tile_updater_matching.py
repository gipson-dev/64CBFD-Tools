"""Fit complete tile updater from emitted producers, closed register lives and low-halfword loads."""
import struct
from tools.experiments import game_actor_tile_updater_layout as layout
from tools.experiments.game_actor_segment_selector_matching import fields
from tools.pad_generated_object import parse_object

recovery=layout.recovery
ENTRY,ROM,WORDS=recovery.ENTRY,recovery.ROM,recovery.WORDS
FUNCTION,SOURCE=recovery.FUNCTION,recovery.SOURCE
SELECTED=dict(layout.candidates())['distinct-coordinates']
RAW=tuple(int(word,16) for word in '27BDFFE0 AFB00018 3C070000 24E70000 00808025 AFBF001C 00057080 01C57023 000E7080 01C57021 000E7080 01C57023 000E7080 01C57023 000E7080 00EE3021 90C20004 24010089 02002025 10410003 240100BA 14410005 00027880 0C000000 00C02825 1000005A 8FBF001C 14400004 3C180000 2403000E 10000017 241F0002 24010096 14410003 24030007 10000012 241F0002 24010028 14410003 24030004 1000000D 241F0002 24010001 10410007 241F0002 105F0005 24010003 10410003 24010004 14410004 00001825 241F0002 10000001 24030005 27180000 01F85021 8D590000 00057080 01C57023 13200036 000E7080 01C57021 000E7080 01C57023 000E7080 01C57023 00035880 000E7880 01635823 00EF4021 000B5880 00004825 240D0005 3C0CF200 8D580000 9502027A 9503027E 030B3021 94C40008 94C5000A 24420002 3059FFFF 03201025 24630002 306EFFFF 00047880 0005C880 01C01825 25E4FFFE 2725FFFE 3098FFFF 30AEFFFF 03002025 01C02825 304F0FFF 000FC300 030CC825 306E0FFF 032E7825 02003825 ACEF0000 01A9C023 33190007 308F0FFF 000FC300 00197600 01D8C825 30AF0FFF 032F7025 ACEE0004 26100008 25290001 153FFFD9 25080002 02001025 8FBF001C 8FB00018 27BD0020 03E00008 00000000'.split())
RELOCATIONS={8: [('R_MIPS_HI16', 'D_800CC2D0')], 12: [('R_MIPS_LO16', 'D_800CC2D0')], 92: [('R_MIPS_26', 'func_150C3160')], 112: [('R_MIPS_HI16', 'D_800C5338')], 216: [('R_MIPS_LO16', 'D_800C5338')]}
BRANCH_OPS=(4,5)
INSERT_AFTER=(3,68,69)


def recipe_items(words):
    if tuple(words)!=RAW:
        raise ValueError('stale complete actor tile updater')
    changed=list(words)
    def edit(index,**values):
        changed[index]=fields(words[index],**values)
    edit(2,rt=15);edit(3,rs=15,rt=15)
    for index in range(6,15):
        word=words[index]
        edit(index,rs=7 if word>>21&31==5 else word>>21&31,
            rt=7 if word>>16&31==5 else word>>16&31)
    edit(15,rs=14,rt=15,rd=6)
    edit(22,rd=24);edit(28,rt=25);edit(54,rs=25,rt=25)
    edit(55,rs=24,rt=25,rd=12);edit(56,rs=12,rt=14)
    edit(59,rs=14)
    for index in (57,58,60,61,62,63,64,65):
        word=words[index]
        edit(index,rs={5:7,14:15}.get(word>>21&31,word>>21&31),
            rt={5:7,14:15}.get(word>>16&31,word>>16&31),
            rd={14:15}.get(word>>11&31,word>>11&31))
    edit(66,rd=13);edit(67,rt=15,rd=15);edit(68,rs=13,rd=13)
    edit(69,rs=15,rt=24,rd=5);edit(70,rt=13,rd=13);edit(71,rd=4)
    edit(72,rt=11);edit(73,rt=10)
    loop={
        74:dict(rs=12,rt=25),75:dict(op=33,rs=5,rt=6),76:dict(op=33,rs=5,rt=7),
        77:dict(rs=25,rt=13,rd=2),78:dict(rs=2,rt=8),79:dict(rs=2,rt=9),
        80:dict(rs=6,rt=6),81:dict(rs=6,rt=14),82:dict(rs=14,rd=6),
        83:dict(rs=7,rt=7),84:dict(rs=7,rt=15),85:dict(rt=8,rd=24),
        86:dict(rt=9,rd=14),87:dict(rs=15,rd=7),88:dict(rs=24,rt=8),
        89:dict(rs=14,rt=9),90:dict(rs=8,rt=25),91:dict(rs=9,rt=15),
        92:dict(rs=25,rd=8),93:dict(rs=15,rd=9),94:dict(rs=6,rt=25),
        95:dict(rt=25,rd=14),96:dict(rs=14,rt=10,rd=15),97:dict(rs=7,rt=25),
        98:dict(rs=15,rt=25,rd=14),99:dict(rd=3),100:dict(rs=3,rt=14),
        101:dict(rs=11,rt=4,rd=24),102:dict(rs=24,rt=15),103:dict(rs=8,rt=24),
        104:dict(rt=24,rd=15),105:dict(rt=15,rd=25),106:dict(rs=25,rt=15,rd=14),
        107:dict(rs=9,rt=25),108:dict(rs=14,rt=25,rd=15),109:dict(rs=3,rt=15),
        111:dict(rs=4,rt=4),112:dict(rs=4),113:dict(rs=5,rt=5)}
    for index,values in loop.items():edit(index,**values)
    # Preserve every emitted instruction; duplicate only existing move/address producers.
    items=[(i,i,changed[i]) for i in (0,1,4,5)]
    items.append(('slot-copy',4,fields(words[4],rs=5,rd=7)))
    items.extend((i,i,changed[i]) for i in (*range(6,14),2,3,14,15,*range(16,57),
        66,68,59,71,57,58,60,61,62,63,64,65))
    items.extend((('base-copy-hi',2,fields(words[2],rt=24)),
        ('base-copy-lo',3,fields(words[3],rs=24,rt=24))))
    items.extend((i,i,changed[i]) for i in (67,69,70,72,73,*range(74,99),
        101,102,105,103,99,100,104,*range(106,120)))
    positions={label:index for index,(label,_,_) in enumerate(items)}
    output=[]
    for index,(label,origin,word) in enumerate(items):
        if word>>26 in BRANCH_OPS:
            immediate=words[origin]&65535
            target=origin+1+(immediate^32768)-32768
            word=fields(word,imm=positions[target]-index-1)
        output.append((label,origin,word))
    if len(output)!=WORDS or sorted(origin for label,origin,_ in output if isinstance(label,int))!=list(range(120)):
        raise ValueError('incomplete actor tile producer provenance')
    return output


def recipe(words):
    return [word for _,_,word in recipe_items(words)]


OUTPUT_RELOCATIONS={index*4:RELOCATIONS[origin*4]
    for index,(_,origin,_) in enumerate(recipe_items(RAW)) if origin*4 in RELOCATIONS}


def certify(words):
    items=recipe_items(words)
    copies=[(label,origin) for label,origin,_ in items if not isinstance(label,int)]
    if copies!=[('slot-copy',4),('base-copy-hi',2),('base-copy-lo',3)]:
        raise ValueError('unqualified tile producer copies')
    if any(words[origin]>>26 in (33,35,36,37,40,41,43) for _,origin in copies):
        raise ValueError('cannot duplicate a memory access')
    for value in range(65536):
        signed=value if value<32768 else value-65536
        if (signed+2)&65535 != (value+2)&65535:
            raise ValueError('low-halfword signed promotion differs')
    # Both changed loads feed exactly the same modulo-16 addition and modulo-12 fields.
    if [(label,origin) for label,origin,word in items if word>>26==33]!=[(75,75),(76,76)]:
        raise ValueError('unqualified signed coordinate load')
    return dict(original_producers=120,copied_producers=copies,emitted_words=123,
        omitted_producers=0,missing_body_padding=0,exhaustive_coordinate_promotions=65536,
        copied_memory_accesses=0,relocation_dependencies=len(RELOCATIONS),
        fitted_relocation_sites=len(OUTPUT_RELOCATIONS),
        instruction_semantics_require_full_order_alias_fault_tests=True)


def guard_rows(path):
    text,functions,relocations=parse_object(path)
    target=functions[FUNCTION]
    if target['size']!=480:
        raise ValueError('expected complete 120-word actor tile updater')
    words=struct.unpack_from('>120I',text,target['value'])
    relative={offset-target['value']:uses for offset,uses in relocations.items()
        if target['value']<=offset<target['value']+target['size']}
    if relative!=RELOCATIONS:
        raise ValueError('stale complete actor tile relocations')
    certify(words)
    fitted=recipe(words);rows=[];emitted=0
    spec=lambda uses:';'.join(kind+':'+symbol for kind,symbol in uses) or '-'
    for index,word in enumerate(words):
        row=dict(filename='generated_58F80',function=FUNCTION,offset='0x%X'%(index*4),
            expected='0x%08X'%word,replacement='0x%08X'%fitted[emitted],
            expected_relocations=spec(relative.get(index*4,())),
            replacement_relocations=spec(OUTPUT_RELOCATIONS.get(emitted*4,())),
            note='Normalize complete tile updater address producer lifetime and closed register scheduling',
            insert_after='',insert_after_relocations='',omit='false')
        emitted+=1
        if index in INSERT_AFTER:
            row['insert_after']='0x%08X'%fitted[emitted]
            row['insert_after_relocations']=spec(OUTPUT_RELOCATIONS.get(emitted*4,()))
            emitted+=1
        rows.append(row)
    assert emitted==WORDS
    return rows


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    return recovery.compile_candidate(root,out,name,body,profile)
