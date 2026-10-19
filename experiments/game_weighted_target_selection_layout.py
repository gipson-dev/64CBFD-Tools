"""Explicit spill homes, coefficient colors and mutually exclusive return edges."""
import csv
import hashlib
import io
import json
import struct

from tools.experiments import game_weighted_target_selection_candidates as source

RAW_SHA='d3dee48af9b6d8b7ffdcab9c72a13cbe98e5de4cb76b90bbe3a1a5c31cf01ccb'
BINDING_SHA='cb8bc352f7a1223b02552982c73be6a997762160117730cb52e045c9b8ec35ed'
NORMALIZED_SHA='a521bc0baa55a1a9a66a4a75a516a1bb598870415084ad4f03ca425bca75b306'


def origins():
    return [*range(0,0x90,4),0x94,0x90,0xA8,*range(0x98,0xA8,4),
        *range(0xAC,0x1C0,4),0x1C8,0x1CC,0x1C0,0x1C4,
        *range(0x1D0,0x224,4),'mfc-delay',0x228,0x224,'result-zero',*range(0x22C,0x25C,4)]


def normalize(raw,bindings):
    if (len(raw)!=604 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or
            hashlib.sha256(json.dumps(bindings,sort_keys=True).encode()).hexdigest()!=BINDING_SHA):
        raise ValueError('Unknown weighted-selector body or bindings')
    words=list(struct.unpack('>151I',raw));order=origins()
    if len(order)!=153 or len(set(order))!=153 or {x for x in order if isinstance(x,int)}!=set(range(0,604,4)):
        raise ValueError('Changed weighted-selector source origins')
    if words[0x23C//4]!=0x00001025:raise ValueError('Unknown common zero return')
    destination={old:new for new,old in enumerate(order)};result=[];moved={}
    for new,old in enumerate(order):
        if old=='mfc-delay':result.append(0);continue
        if old=='result-zero':result.append(words[0x23C//4]);continue
        word=words[old//4];op,rs=word>>26,word>>21&31
        if op in (1,4,5,6,7,20,21,22,23) or op==17 and rs==8:
            target=0x240 if old==0x224 else old+4+(((word&65535)^32768)-32768)*4
            if target not in destination:raise ValueError('Removed weighted-selector branch destination')
            offset=destination[target]-new-1
            if not -32768<=offset<32768:raise ValueError('Weighted-selector branch out of range')
            word=word&0xFFFF0000|offset&65535
        if old==0:word=word&0xFFFF0000|0xFFA0
        elif old==0x258:word=word&0xFFFF0000|0x60
        elif old in (0x38,0x50,0x5C,0x80,0x84,0xAC):word-=4
        elif old in (0x9C,0xA4):
            rt=word>>16&31;word=word&~(31<<16)|{2:12,12:2}[rt]<<16
        elif old in (0x168,0x174):
            ft=word>>16&31;word=word&~(31<<16)|{2:12,12:2}[ft]<<16
        if old in bindings:moved[new*4]=bindings[old]
        result.append(word)
    normalized=struct.pack('>153I',*result)
    if hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA or len(moved)!=16:
        raise ValueError('Changed weighted-selector layout recipe')
    return normalized,moved


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings);old=list(struct.unpack('>151I',raw));new=list(struct.unpack('>153I',normalized))
    reader=csv.DictReader(io.StringIO(before.decode()))
    if not before.endswith(b'\n') or any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):
        raise ValueError('Unknown weighted-selector guard predecessor')
    spec=lambda entries:';'.join(k+':'+n for k,n in entries) or '-'
    rows=[];cursor=0;order=origins()
    for i,word in enumerate(old):
        at=i*4;insert=cursor+1<len(order) and isinstance(order[cursor+1],str)
        rows.append(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%at,
            expected='0x%08X'%word,replacement='0x%08X'%new[cursor],
            expected_relocations=spec(bindings.get(at,[])),replacement_relocations=spec(moved.get(cursor*4,[])),
            note='Normalize proven weighted-selector private homes and return-edge schedule; source word 0x%X'%order[cursor],
            insert_after='0x%08X'%new[cursor+1] if insert else '',insert_after_relocations='-' if insert else '',omit='false'))
        cursor+=2 if insert else 1
    if cursor!=153 or sum(bool(r['insert_after']) for r in rows)!=2:raise ValueError('Changed weighted-selector guard extent')
    output=io.StringIO(newline='');csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+output.getvalue().encode()
