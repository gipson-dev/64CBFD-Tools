"""Restore closed pointer roles and the retail independent copy schedule."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_parallel_array_reset_candidates as source
from tools.experiments.game_round_robin_slot_layout import fields as shared_fields

RAW_SHA='e1044cf33288b566d09ddaefd2a95eabca0ba295540ad44f5640058d22036bf4'
NORMALIZED_SHA='7f154a2e849808aa06216d80c7e1518184b1fe74ff644dfc4c0976b5cfa7363d'
BINDINGS={4:[('R_MIPS_HI16','D_800D23B0')],8:[('R_MIPS_LO16','D_800D23B0')]}
EARLY={4:2,5:4,6:5,7:6,8:7,10:8,11:10}
SETUP={27:{6:5},29:{8:7,4:10},30:{5:4},31:{5:4},32:{7:6},33:{10:8}}
LATE={4:10,5:4}


def fields(word):
    if word>>26 in (6,7):return (21,)
    return shared_fields(word)


def origins():
    order=list(range(52));order[29:34]=[30,29,33,31,32];return order


def normalize(raw,bindings):
    if len(raw)!=208 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown parallel-reset body or bindings')
    words=struct.unpack('>52I',raw);order=origins();result=[]
    if sorted(order)!=list(range(52)):raise ValueError('Lost parallel-reset source origin')
    for new,old in enumerate(order):
        mapping=EARLY if new<27 else SETUP.get(new,LATE if new>=34 else {})
        word=original=words[old]
        for shift in fields(original):
            value=original>>shift&31;word=word&~(31<<shift)|(mapping.get(value,value)<<shift)
        result.append(word)
    normalized=struct.pack('>52I',*result)
    if hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA:raise ValueError('Changed parallel-reset layout recipe')
    return normalized,dict(bindings)


def relocate(raw,bindings,anchors):
    words=list(struct.unpack('>52I',raw))
    for at,entries in bindings.items():
        if len(entries)!=1:raise ValueError('Unknown parallel-reset relocation group')
        kind,name=entries[0];value=anchors[name]
        if kind=='R_MIPS_HI16':words[at//4]=words[at//4]&0xFFFF0000|((value+0x8000)>>16)&65535
        elif kind=='R_MIPS_LO16':words[at//4]=words[at//4]&0xFFFF0000|value&65535
        else:raise ValueError('Unknown parallel-reset relocation kind')
    return words


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings);old=struct.unpack('>52I',raw);new=struct.unpack('>52I',normalized)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):raise ValueError('Existing parallel-reset guards')
    if not before.endswith(b'\n'):raise ValueError('Unterminated parallel-reset predecessor')
    spec=lambda entries:';'.join(kind+':'+name for kind,name in entries) or '-';rows=[]
    for i,(a,b) in enumerate(zip(old,new)):
        if a==b:continue
        rows.append(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
            replacement='0x%08X'%b,expected_relocations=spec(bindings.get(i*4,[])),replacement_relocations=spec(moved.get(i*4,[])),
            note='Normalize parallel-reset pointer allocation and independent copy schedule',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=19:raise ValueError('Changed parallel-reset guard coverage')
    output=io.StringIO(newline='');csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+output.getvalue().encode()
