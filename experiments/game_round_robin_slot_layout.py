"""Restore a closed state/count/result GPR cycle and independent opening work."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_round_robin_slot_candidates as source
from tools.experiments.game_packed_peer_lookup_layout import fields as shared_fields

RAW_SHA='2399eb522cb25f9ae26d3fa6f5cc64db50b1007bd0f2525f9eb007ffc7060dd7'
GP={3:5,5:6,6:3}
BINDINGS={0:[('R_MIPS_HI16','D_800D23B0')],4:[('R_MIPS_LO16','D_800D23B0')],
    8:[('R_MIPS_HI16','D_8008FD8C')],12:[('R_MIPS_HI16','D_800D18A0')],
    16:[('R_MIPS_HI16','D_800CC2D0')],24:[('R_MIPS_LO16','D_8008FD8C')],
    32:[('R_MIPS_LO16','D_800CC2D0')],36:[('R_MIPS_LO16','D_800D18A0')]}
NORMALIZED_SHA='70dcb8f7279b1aeef68c4e544f63b2eb2955269bd87b271dada292fb9d46e2eb'


def fields(word):
    if word>>26==0 and word&63==42:return (21,16,11)
    return shared_fields(word)


def origins():
    order=list(range(47));order[6:10]=[7,8,9,6];return order


def normalize(raw,bindings):
    if len(raw)!=188 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown round-robin body or bindings')
    words=struct.unpack('>47I',raw);order=origins();result=[];moved={}
    if sorted(order)!=list(range(47)):raise ValueError('Lost round-robin source origin')
    for new,old in enumerate(order):
        word=original=words[old]
        for shift in fields(original):
            value=original>>shift&31;word=word&~(31<<shift)|(GP.get(value,value)<<shift)
        result.append(word)
        if old*4 in bindings:moved[new*4]=bindings[old*4]
    normalized=struct.pack('>47I',*result)
    if hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA:raise ValueError('Changed round-robin layout recipe')
    return normalized,moved


def relocate(raw,bindings,anchors):
    words=list(struct.unpack('>47I',raw))
    for at,entries in bindings.items():
        if len(entries)!=1:raise ValueError('Unknown round-robin relocation group')
        kind,name=entries[0];value=anchors[name]
        if kind=='R_MIPS_HI16':words[at//4]=words[at//4]&0xFFFF0000|((value+0x8000)>>16)&65535
        elif kind=='R_MIPS_LO16':words[at//4]=words[at//4]&0xFFFF0000|value&65535
        else:raise ValueError('Unknown round-robin relocation kind')
    return words


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings);old=struct.unpack('>47I',raw);new=struct.unpack('>47I',normalized)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):raise ValueError('Existing round-robin guards')
    if not before.endswith(b'\n'):raise ValueError('Unterminated round-robin predecessor')
    spec=lambda entries:';'.join(kind+':'+name for kind,name in entries) or '-'
    rows=[]
    for i,(a,b) in enumerate(zip(old,new)):
        if a==b and bindings.get(i*4,[])==moved.get(i*4,[]):continue
        rows.append(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
            replacement='0x%08X'%b,expected_relocations=spec(bindings.get(i*4,[])),replacement_relocations=spec(moved.get(i*4,[])),
            note='Normalize round-robin slot GPR cycle and independent opening schedule',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=14:raise ValueError('Changed round-robin guard coverage')
    output=io.StringIO(newline='');csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+output.getvalue().encode()
