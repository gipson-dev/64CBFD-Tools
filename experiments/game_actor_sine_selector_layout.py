"""Qualified closed saved-mask/coefficient lifetime recipe for guarded matching."""
import csv
import hashlib
import io
import json
import struct

from tools.experiments import game_actor_sine_selector_candidates as source
from tools.experiments.game_route_projection_layout_normalizer import fields

RAW_SHA='9b36dd52ce1411f49bae251814c8a252900c479b10c8c7e22e2eed05d14afbc3'
BINDING_SHA='885fc708cec75e54e03fda9d05ab8e87bbb7c3dca3e777db5205faeabc05824b'
NORMALIZED_SHA='d700e03ab127756ccfcb925d990cc167c093674913bcda10b137db54785b3394'
OMITTED=(0xC4,0x19C,0x1B4)


def origins():
    # Rematerialize tau at its use; split the state cursor's entry and loop homes.
    result=[*range(0,0x5C,4),0xC8,0x60,0x64,0x68,*range(0x6C,0x80,4),
        0x5C,*range(0x80,0x94,4),0x98,0x94,0xBC,0xA4,0xA8,0xAC,0xB8,
        0x9C,0xB4,0xC0,0xA0,None,0xCC,0xD0,*range(0xD4,0x114,4),0xB0,
        *range(0x114,0x19C,4),*range(0x1A0,0x1B4,4),*range(0x1B8,0x228,4)]
    if len(result)!=136 or len(set(result))!=136 or set(result)-{None}!=set(range(0,552,4))-set(OMITTED):
        raise ValueError('Changed selector lifetime extent')
    return result


def gp_fields(word):
    op,fn=word>>26,word&63
    if op==0:
        if fn in (4,36):return (21,16,11)
        if fn==25:return (21,16)
        if fn==18:return (11,)
    if op in (53,61):return (21,)
    return fields(word)[0]


def normalize(raw,bindings):
    if (len(raw)!=552 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or
            hashlib.sha256(json.dumps(bindings,sort_keys=True).encode()).hexdigest()!=BINDING_SHA):
        raise ValueError('Unknown selector source body or bindings')
    words=list(struct.unpack('>138I',raw));order=origins()
    destination={old:new for new,old in enumerate(order)}
    expected={0xB0:[('R_MIPS_HI16','D_8009DA58')],0xC4:[('R_MIPS_LO16','D_8009DA58')]}
    if any(bindings.get(at)!=entries for at,entries in expected.items()):
        raise ValueError('Unknown coefficient relocation lifetime')
    if any(at in bindings for at in (0x114,0x19C,0x1B4)):
        raise ValueError('Unexpected relocated selector operand')
    result=[];moved={}
    for new,old in enumerate(order):
        if old is None:
            result.append(0x00608825)  # Move the early state base into its saved loop cursor.
            continue
        word=words[old//4];op,rs=word>>26,word>>21&31
        if op in (4,5,6,7,20,21) or op==17 and rs==8:
            # The else edge must enter its relocated LUI, not skip to its load.
            target=0x5C if old==0x64 else old+4+(((word&65535)^32768)-32768)*4
            if target not in destination:raise ValueError('Removed selector branch destination')
            offset=destination[target]-new-1
            if not -32768<=offset<32768:raise ValueError('Selector branch out of range')
            word=word&0xFFFF0000|offset&65535
        # The selected index and slot offset exchange saved colors, not save slots.
        initial=word
        if old not in (0x10,0x14,0x210,0x214):
            for shift in gp_fields(word):
                reg=initial>>shift&31
                word=word&~(31<<shift)|{21:22,22:21}.get(reg,reg)<<shift
        # Remove the dead mask spill area and preserve the incoming A0 home.
        # Saved GP/FP slots stay at their original frame-relative offsets.
        if old==0:word=word&0xFFFF0000|0xFF90
        elif old in (0x224,0x198,0x1B0):word=word&0xFFFF0000|0x70
        elif old==0x60:word=word&~(31<<16)|30<<16
        elif old==0xE4:word=word&~(31<<21)|30<<21
        elif old==0xC8:word=word&~(31<<16)|3<<16
        elif old==0xB0:word=word&~(31<<16)|1<<16
        elif old==0x114:word=word&~(31<<21)|1<<21
        if old in bindings:moved[new*4]=bindings[old]
        if old==0x114:moved[new*4]=bindings[0xC4]
        result.append(word)
    normalized=struct.pack('>136I',*result)
    if len(moved)!=len(bindings) or hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA:
        raise ValueError('Changed selector lifetime recipe or bindings')
    return normalized,moved


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings)
    old=list(struct.unpack('>138I',raw));new=list(struct.unpack('>136I',normalized))
    reader=csv.DictReader(io.StringIO(before.decode()))
    if not before.endswith(b'\n') or any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):
        raise ValueError('Unknown selector guard predecessor')
    spec=lambda entries:';'.join(k+':'+n for k,n in entries) or '-'
    rows=[];cursor=0;order=origins()
    for offset,word in enumerate(old):
        at=offset*4;omit=at in OMITTED;insert=not omit and cursor==48
        origin=None if omit else order[cursor]
        row=dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%at,
            expected='0x%08X'%word,replacement='0x%08X'%(0 if omit else new[cursor]),
            expected_relocations=spec(bindings.get(at,[])),
            replacement_relocations='-' if omit else spec(moved.get(cursor*4,[])),
            note='Omit recovered dead coefficient address or active-mask spill' if omit else
                'Normalize closed selector lifetime; source word 0x%X'%origin,
            insert_after='0x%08X'%new[49] if insert else '',
            insert_after_relocations='-' if insert else '',omit='true' if omit else 'false')
        rows.append(row)
        if not omit:cursor+=2 if insert else 1
    if cursor!=136 or sum(r['omit']=='true' for r in rows)!=3 or sum(bool(r['insert_after']) for r in rows)!=1:
        raise ValueError('Changed selector guard contraction')
    output=io.StringIO(newline='');writer=csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n');writer.writerows(rows)
    return before+output.getvalue().encode()
