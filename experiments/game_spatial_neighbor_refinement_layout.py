"""Closed spatial-refinement lifetimes, local coefficient and five-step loop recipe."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_spatial_neighbor_refinement_fitting as source
from tools.experiments.game_route_projection_layout_normalizer import fields as shared_fields

RAW_SHA='42926261351a97b64a3293f7f2e93db283fe1db84c512b9cf1a9e70549321c85'
NORMALIZED_SHA='2a5e43a59df60d6015c1653cebc7cb0842f641681c3a2d3db3a23eb0d218620a'
BINDINGS={0x3C:[('R_MIPS_26','func_15085DA8')],0x54:[('R_MIPS_26','func_15085DF8')],
    0x78:[('R_MIPS_26','func_15086C70')],0xA4:[('R_MIPS_26','func_150A32B4')],
    0xC8:[('R_MIPS_26','func_15086364')],0xD8:[('R_MIPS_HI16','D_800D2350')],
    0xDC:[('R_MIPS_LO16','D_800D2350')],0x118:[('R_MIPS_HI16','D_8009D9D0')],
    0x11C:[('R_MIPS_LO16','D_8009D9D0')],0x14C:[('R_MIPS_26','func_15086364')],
    0x26C:[('R_MIPS_26','func_15086364')]}
OMITTED=(0x15C,0x160)
INSERTED={'minimum-copy':0x46006686,'dead-minimum-copy':0x46006686,
    'multiply-hazard':0,'negative-base':0x46008407,'loop-test-copy':0x28C10005}


def origins():
    result=[*range(0,0x24,4),0x28,0x2C,0x24,*range(0x30,0xE4,4),
        0x118,0xE8,0xEC,0x11C,0xE4,0xF8,0xF0,*range(0x100,0x118,4),
        0x120,0x128,0x12C,0x124,0xFC,0xF4,0x134,0x138,0x13C,'minimum-copy',
        *range(0x144,0x15C,4),'dead-minimum-copy',*range(0x164,0x178,4),
        0x17C,0x178,0x184,0x180,*range(0x188,0x19C,4),0x130,0x140,0x1A0,
        0x1A4,0x19C,0x1AC,0x1B0,0x1B4,0x1A8,0x1BC,0x1B8,
        *range(0x1C0,0x1D4,4),0x1E4,0x1E8,0x1EC,'multiply-hazard',
        0x1D4,0x1D8,0x1DC,0x1F0,0x1F4,'negative-base',0x1E0,
        *range(0x1F8,0x248,4),'loop-test-copy',*range(0x248,0x2C0,4)]
    retained={x for x in result if isinstance(x,int)}
    if len(result)!=179 or len(set(result))!=179 or retained!=set(range(0,704,4))-set(OMITTED):
        raise ValueError('Changed refinement source-origin accounting')
    return result


def fields(word):
    op,rs,fn=word>>26,word>>21&31,word&63
    if op in (1,22,23):return (21,),()
    if op==10:return (21,16),()
    if op in (53,61):return (21,),(16,)
    if op==0 and fn==35:return (21,16,11),()
    if op==17:
        if rs==0:return (16,),(11,)
        if rs==16 and fn in (7,13):return (),(11,6)
    return shared_fields(word)


def gp_mapping(old):
    result={12:11,11:10}
    if old in (0xB4,0xCC):result[14]=13
    elif old in (0xE0,0xE8):result[15]=14
    elif old in (0xEC,0xF8,0x100):result[24]=15
    elif old in (0x12C,0x150):result[25]=24
    elif old==0xF4:result[6]=7
    elif old in (0xFC,0x168):result[7]=6
    elif old in (0x164,0x24C):result[6]=7
    elif old in (0x170,0x174):result[13]=25
    elif old==0x17C:result[14]=12
    elif old==0x184:result[24]=14
    elif old in (0x188,0x18C):result.update({14:12,15:13})
    elif old in (0x190,0x194):result.update({24:14,25:15})
    elif old in (0x258,0x270):result[13]=24
    return result


def fp_mapping(old):
    if old>=0x28C:return {}
    result={26:28,28:30,24:26,22:24,16:18,18:20}
    local={0x24:{30:22},0x104:{0:2},0x110:{0:2},0x114:{0:2},
        0x11C:{24:12},0x134:{24:12},0x140:{30:8},0x1C0:{30:8},
        0x19C:{8:10},0x1B0:{8:10,16:18},0x1A8:{10:4},0x1B8:{10:4,18:20},
        0x1E4:{10:6,16:18},0x1EC:{4:8,18:20},0x1D4:{4:10,26:28},
        0x1DC:{6:4,28:30},0x1F0:{6:16,10:6,4:8},0x1F4:{10:8},
        0x1E0:{8:6,4:10,6:4},0x1F8:{22:24,8:6,6:16},0x1FC:{10:8,22:24},
        0x20C:{4:10,22:24},0x210:{8:4,4:10,16:18},0x218:{26:28,8:4},
        0x21C:{10:8,18:20},0x220:{4:10},0x224:{28:30,10:8},
        0x228:{8:4},0x22C:{4:10,8:4}}
    result.update(local.get(old,{}));return result


def normalize(raw,bindings):
    if len(raw)!=704 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown refinement source or bindings')
    words=list(struct.unpack('>176I',raw));order=origins();destination={x:i for i,x in enumerate(order)}
    if words[0x15C//4]!=0x4481F000 or words[0x160//4]!=0x240A0005:
        raise ValueError('Changed dead coefficient copy or loop bound')
    result=[];moved={}
    for new,old in enumerate(order):
        if isinstance(old,str):result.append(INSERTED[old]);continue
        initial=word=words[old//4];op,rs=word>>26,word>>21&31
        if op in (1,4,5,6,7,20,21,22,23) or op==17 and rs==8:
            target=old+4+(((word&65535)^32768)-32768)*4
            # Only the distance-test false edge executes its duplicated test in the delay slot.
            if old in (0x16C,0x204):target='loop-test-copy'
            elif target==0x160:target=0x164
            if target not in destination:raise ValueError('Removed refinement branch destination')
            offset=destination[target]-new-1
            if not -32768<=offset<32768:raise ValueError('Refinement branch out of range')
            word=word&0xFFFF0000|offset&65535
        for shifts,colors in zip(fields(initial),(gp_mapping(old),fp_mapping(old))):
            for shift in shifts:
                reg=initial>>shift&31;word=word&~(31<<shift)|colors.get(reg,reg)<<shift
        if old==0:word=word&0xFFFF0000|0xFF90
        elif old==0x2BC:word=word&0xFFFF0000|0x70
        elif old in (0x4,0x8,0x24,0x28,0x2C):
            word=word&0xFFFF0000|{4:0x48,8:0x40,0x24:0x28,0x28:0x38,0x2C:0x30}[old]
        elif op in (32,35,43) and rs==29:
            home=initial&65535
            if home==0x74:word=word&0xFFFF0000|0x60
            elif home>=0x84:word=word&0xFFFF0000|(home-8)
        if old==0x114:word=word&~(31<<6)  # Radius F2 is doubled into the distinct diameter F0.
        if old==0x174:
            a,b=word>>21&31,word>>16&31;word=word&~((31<<21)|(31<<16))|b<<21|a<<16
        if old in (0x210,0x21C):
            a,b=word>>11&31,word>>16&31;word=word&~((31<<11)|(31<<16))|b<<11|a<<16
        if old==0x1F8:word=word&~63  # Dot + negative base-dot, retaining both rounded operations.
        if old==0x238:word=word&~(3<<16)|2<<16
        if old==0x23C:word=0x28C10005  # Zero-initialized counter reaches exactly 1..5, with no loop helper.
        if old==0x248:word=word&0xFFFF|0x14200000
        if old in bindings:moved[new*4]=bindings[old]
        result.append(word)
    normalized=struct.pack('>179I',*result)
    if len(moved)!=11 or hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA:
        raise ValueError('Changed refinement lifetime recipe or bindings')
    return normalized,moved


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings);old=struct.unpack('>176I',raw);new=struct.unpack('>179I',normalized)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if not before.endswith(b'\n') or any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):
        raise ValueError('Unknown refinement guard predecessor')
    spec=lambda entries:';'.join(k+':'+n for k,n in entries) or '-'
    rows=[];cursor=0;order=origins()
    for i,word in enumerate(old):
        at=i*4;omit=at in OMITTED
        insert=not omit and cursor+1<len(order) and isinstance(order[cursor+1],str)
        origin=None if omit else order[cursor]
        rows.append(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%at,
            expected='0x%08X'%word,replacement='0x%08X'%(0 if omit else new[cursor]),
            expected_relocations=spec(bindings.get(at,[])),replacement_relocations='-' if omit else spec(moved.get(cursor*4,[])),
            note='Omit dead coefficient copy or rematerialized loop bound' if omit else
                'Normalize proven refinement private/FP/loop lifetime; source word 0x%X'%origin,
            insert_after='0x%08X'%new[cursor+1] if insert else '',insert_after_relocations='-' if insert else '',
            omit='true' if omit else 'false'))
        if not omit:cursor+=2 if insert else 1
    if cursor!=179 or sum(r['omit']=='true' for r in rows)!=2 or sum(bool(r['insert_after']) for r in rows)!=5:
        raise ValueError('Changed refinement guard accounting')
    output=io.StringIO(newline='');csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+output.getvalue().encode()
