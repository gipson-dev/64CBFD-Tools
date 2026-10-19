"""Explicit private homes, closed GP lifetimes and clear-loop edge normalization."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_balanced_target_assignment_candidates as source
from tools.experiments.game_actor_sine_selector_layout import gp_fields as shared_fields

RAW_SHA='c31e39062a3c82931d51d574c1106272083e651bfc04b8e796c6b31490009795'
NORMALIZED_SHA='530c11d19d950b3b016f6a5af8a62b0f9d7acd34759eac10434384b8d1818217'
BINDINGS={0x2C:[('R_MIPS_HI16','D_800D23B0')],0x30:[('R_MIPS_LO16','D_800D23B0')]}
OMITTED=(0x74,0x1EC)
SAVED={18:19,19:20,20:21,21:18}
CURSORS={9:10,10:9}
SCAN={2:4,3:2,4:3}
TEMPS={14:24,15:25,24:14,25:15}
HOMES={0x48:0x6C,0x50:0x68,0x64:0x64,0x68:0x60,0xCC:0xA4,
    0xE0:0x6C,0x108:0xA4,0x118:0xA4,0x138:0x64,0x13C:0x60,
    0x154:0x68,0x23C:0xA4,0x248:0xA4}


def gp_fields(word):
    if word>>26==13:return (21,16)
    if word>>26 in (22,23):return (21,)
    return shared_fields(word)


def origins():
    order=[*range(0,0x38,4),0xC8,*range(0x3C,0x74,4),
        *range(0x78,0x8C,4),'remainder-copy',0x8C,'clear-pointer-copy',
        *range(0x90,0xC8,4),0xCC,0x38,*range(0xD0,0x124,4),
        0x124,0x128,0x134,0x130,0x12C,*range(0x138,0x1EC,4),
        *range(0x1F0,0x21C,4),0x238,*range(0x21C,0x230,4),
        0x234,0x230,*range(0x23C,0x280,4)]
    if len(order)!=160 or len(set(order))!=160 or {x for x in order if isinstance(x,int)}!=set(range(0,640,4))-set(OMITTED):
        raise ValueError('Changed balanced-assignment source origins')
    return order


def mapping(old):
    if old<0x2C or 0x250<=old<0x278:return {}
    result={**SAVED,**CURSORS}
    if old in (0x84,0x88):result[2]=4
    elif old==0x8C:result[3]=24
    elif 0x90<=old<=0x9C:result.update({2:3,3:2})
    elif old==0xA4:result[21]=25
    elif old in (0xA8,0xAC):result.update({2:3,3:2,21:25})
    elif 0xB0<=old<=0xC4:result.update({2:3,3:2})
    elif 0xD0<=old<=0x210:result.update({**SCAN,**TEMPS})
    elif 0x218<=old<=0x220:result.update({14:15,15:24,24:14})
    elif old==0x238:result[4]=3
    elif 0x23C<=old<=0x248:result.update({4:3,14:24,24:25,25:14})
    return result


def normalize(raw,bindings):
    if len(raw)!=640 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown balanced-assignment source or bindings')
    words=list(struct.unpack('>160I',raw));order=origins()
    if words[0x74//4]!=0xA3A0008C or words[0x1EC//4]!=0x3319001F:
        raise ValueError('Changed native backing initializer or low-five-bit mask')
    destination={old:new for new,old in enumerate(order)};result=[];moved={}
    for new,old in enumerate(order):
        if old=='remainder-copy':
            result.append(0x00801825)  # Preserve the remainder across the clear pointer's V0 lifetime.
            continue
        if old=='clear-pointer-copy':
            result.append(0x00181021)  # Split the clear address definition from its incremented cursor.
            continue
        original=word=words[old//4];op=word>>26
        if op in (1,4,5,6,7,20,21,22,23):
            target=old+4+(((word&65535)^32768)-32768)*4
            # Positive count with remainder0 cannot equal the zero clear index.
            target=0xA4 if old==0x88 else 0xCC if target==0xC8 else target
            if target not in destination:raise ValueError('Removed assignment branch destination')
            offset=destination[target]-new-1
            if not -32768<=offset<32768:raise ValueError('Assignment branch out of range')
            word=word&0xFFFF0000|offset&65535
        colors=mapping(old)
        for shift in gp_fields(original):
            reg=original>>shift&31;word=word&~(31<<shift)|colors.get(reg,reg)<<shift
        if old==0:word=word&0xFFFF0000|0xFF50
        elif old==0x27C:word=word&0xFFFF0000|0xB0
        elif old in HOMES:word=word&0xFFFF0000|HOMES[old]
        elif old in (0x8C,0xA4,0xC8):word=word&0xFFFF0000|0x7C
        if old in (0x98,0xA8,0xAC):
            rs,rt=word>>21&31,word>>16&31
            word=word&~((31<<21)|(31<<16))|rt<<21|rs<<16
        if old==0x1F0:
            # SLLV itself consumes only the signed byte's low five bits.
            word=word&~(31<<21)|14<<21
        if old in bindings:moved[new*4]=bindings[old]
        result.append(word)
    normalized=struct.pack('>160I',*result)
    if hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA or len(moved)!=2:
        raise ValueError('Changed assignment lifetime recipe or bindings')
    return normalized,moved


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings);old=struct.unpack('>160I',raw);new=struct.unpack('>160I',normalized)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if not before.endswith(b'\n') or any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):
        raise ValueError('Unknown assignment guard predecessor')
    spec=lambda entries:';'.join(k+':'+n for k,n in entries) or '-'
    order=origins();rows=[];cursor=0
    for i,word in enumerate(old):
        at=i*4;omit=at in OMITTED
        insert=not omit and cursor+1<len(order) and isinstance(order[cursor+1],str)
        origin=None if omit else order[cursor]
        rows.append(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%at,
            expected='0x%08X'%word,replacement='0x%08X'%(0 if omit else new[cursor]),
            expected_relocations=spec(bindings.get(at,[])),
            replacement_relocations='-' if omit else spec(moved.get(cursor*4,[])),
            note='Omit native-only miss-cell initializer or redundant SLLV mask' if omit else
                'Normalize proven assignment private homes and GP lifetimes; source word 0x%X'%origin,
            insert_after='0x%08X'%new[cursor+1] if insert else '',
            insert_after_relocations='-' if insert else '',omit='true' if omit else 'false'))
        if not omit:cursor+=2 if insert else 1
    if cursor!=160 or sum(r['omit']=='true' for r in rows)!=2 or sum(bool(r['insert_after']) for r in rows)!=2:
        raise ValueError('Changed assignment guard accounting')
    output=io.StringIO(newline='');csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+output.getvalue().encode()
