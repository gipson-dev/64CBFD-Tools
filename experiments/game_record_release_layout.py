"""Restore only the post-lookup state/actor GPR cycle; FP fields stay untouched."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_record_release_candidates as source
from tools.experiments.game_parallel_array_reset_layout import fields as shared_fields

RAW_SHA='fd31bb42488446f081ba82001aa1f0d2ed933fd9567783ee3a5cc6b7b1085a98'
NORMALIZED_SHA='f6d3adaf757e663f6e8e93d6782baed348c072c7a9bbd0755b4523fbc807886c'
GP={3:5,5:3}
BINDINGS={0:[('R_MIPS_HI16','D_800D23B0')],4:[('R_MIPS_LO16','D_800D23B0')],
    164:[('R_MIPS_HI16','D_800CC2D0')],172:[('R_MIPS_LO16','D_800CC2D0')]}


def fields(word):
    op=word>>26
    if op in (49,57):return (21,)
    if op==17:return (16,) if word>>21&31 in (0,4) else ()
    return shared_fields(word)


def normalize(raw,bindings):
    if len(raw)!=312 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown record-release body or bindings')
    words=struct.unpack('>78I',raw);result=[]
    for i,original in enumerate(words):
        word=original
        if i>=33:
            for shift in fields(original):
                value=original>>shift&31;word=word&~(31<<shift)|(GP.get(value,value)<<shift)
        result.append(word)
    normalized=struct.pack('>78I',*result)
    if hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA:raise ValueError('Changed record-release GPR recipe')
    return normalized,dict(bindings)


def relocate(raw,bindings,anchors):
    words=list(struct.unpack('>78I',raw))
    for at,entries in bindings.items():
        if len(entries)!=1:raise ValueError('Unknown record-release relocation group')
        kind,name=entries[0];value=anchors[name]
        if kind=='R_MIPS_HI16':words[at//4]=words[at//4]&0xFFFF0000|((value+0x8000)>>16)&65535
        elif kind=='R_MIPS_LO16':words[at//4]=words[at//4]&0xFFFF0000|value&65535
        else:raise ValueError('Unknown record-release relocation kind')
    return words


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings);old=struct.unpack('>78I',raw);new=struct.unpack('>78I',normalized)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):raise ValueError('Existing record-release guards')
    if not before.endswith(b'\n'):raise ValueError('Unterminated record-release predecessor')
    spec=lambda entries:';'.join(kind+':'+name for kind,name in entries) or '-';rows=[]
    for i,(a,b) in enumerate(zip(old,new)):
        if a==b:continue
        rows.append(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
            replacement='0x%08X'%b,expected_relocations=spec(bindings.get(i*4,[])),replacement_relocations=spec(moved.get(i*4,[])),
            note='Normalize record-release state and actor GPR allocation',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=7:raise ValueError('Changed record-release guard coverage')
    output=io.StringIO(newline='');csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+output.getvalue().encode()
