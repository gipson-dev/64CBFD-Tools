"""Explicit pointer lifetimes, duplicate-slot CSE and timer edge-load splitting."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_actor_target_timer_candidates as source
from tools.experiments.game_record_release_layout import fields as shared_fields

RAW_SHA='7a173d55e1f6d80293c18209802ce9ab0bb18cba06317baa1329024ca4adc601'
NORMALIZED_SHA='ab81695a5e81d361f6b34284a44efdfb16e96b19189fd380922d29e237d967cb'
BINDINGS={4:[('R_MIPS_HI16','D_800CC2D0')],16:[('R_MIPS_LO16','D_800CC2D0')],
    8:[('R_MIPS_HI16','D_800D23B0')],12:[('R_MIPS_LO16','D_800D23B0')],
    112:[('R_MIPS_HI16','D_8009DA8C')],136:[('R_MIPS_LO16','D_8009DA8C')],
    72:[('R_MIPS_HI16','D_800E0BD0')],224:[('R_MIPS_LO16','D_800E0BD0')],
    252:[('R_MIPS_HI16','D_80087320')],260:[('R_MIPS_LO16','D_80087320')],
    328:[('R_MIPS_26','func_1508EB90')],364:[('R_MIPS_26','func_150ADA68')],
    380:[('R_MIPS_HI16','D_800E0BD0')],384:[('R_MIPS_LO16','D_800E0BD0')],
    392:[('R_MIPS_HI16','D_800872E8')],400:[('R_MIPS_LO16','D_800872E8')]}
OPEN={10:7,9:10,7:9,8:6,6:8}
SELECTOR={14:13,15:14,24:15,25:24,13:25}
TAIL={13:24,24:15,15:25,7:9}


def fields(word):
    if word>>26==1:return (21,)
    if word>>26==0 and word&63 in (4,36):return (21,16,11)
    return shared_fields(word)


def origins():
    # Omit only the second identical slot shift. Split the later timer load
    # across mutually exclusive notification-bypass and notification-call edges.
    return [*range(10),18,11,12,13,63,14,15,16,17,*range(19,57),58,57,
            59,60,61,62,64,65,66,67,68,69,70,71,72,73,74,76,75,77,80,78,79,
            86,*range(81,115)]


def mapping(old):
    if old<=24:return {14:13} if old==18 else OPEN
    if old<=55:return {7:9,10:7}
    if old==56 or 59<=old<=62:return SELECTOR
    if old==57:return {13:6,9:10,3:7}
    if old==58:return {25:24}
    if 63<=old<=65:return {14:3,13:25}
    if old==66:return {3:7,15:13}
    if old==67:return {14:3,15:13}
    if old in (69,86):return {3:7,15:25}
    if old==70:return {3:7}
    if old==71:return {24:25}
    if old==72:return {6:8}
    if old==74:return {24:25,8:6,25:13}
    if old==75:return {25:13,13:15}
    if old==78:return {13:15,25:14}
    if old==79:return {25:14}
    if old in (81,84):return {3:7}
    if old in (83,85,92):return {7:9}
    if old==87:return {15:25}
    if old==89:return {7:9,14:13}
    if old==90:return {14:13}
    if 95<=old<=108:return TAIL
    if old==109:return {14:13}
    if old==110:return {13:24,14:13}
    return {}


def normalize(raw,bindings):
    if len(raw)!=460 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown actor-target timer body or bindings')
    words=struct.unpack('>115I',raw);order=origins()
    if len(order)!=115 or sorted(set(order))!=[i for i in range(115) if i!=10] or order.count(86)!=2:
        raise ValueError('Changed actor-target timer origin recipe')
    if words[9]>>6&31!=2 or words[10]>>6&31!=2 or words[9]>>16&31!=4 or words[10]>>16&31!=4:
        raise ValueError('Slot shifts no longer identical computations')
    if words[68]!=0x50200012 or words[79]!=0x13200006 or words[86]!=0x8C6F0000:
        raise ValueError('Changed timer edge-load split preconditions')
    result=[];moved={}
    for new,old in enumerate(order):
        original=word=words[old];gp=mapping(old)
        for shift in fields(original):
            value=original>>shift&31;word=word&~(31<<shift)|(gp.get(value,value)<<shift)
        if old in (57,78):
            expected=33 if old==57 else 36
            if word>>26 or word&63!=expected:raise ValueError('Noncommutative timer operand exchange')
            rs,rt=word>>21&31,word>>16&31
            word=word&~((31<<21)|(31<<16))|(rt<<21)|(rs<<16)
        if old==68:word=word&0xFFFF0000|0x13
        if old==79:word=word&0x03FF0000|(20<<26)|7
        result.append(word)
        if old*4 in bindings:moved[new*4]=bindings[old*4]
    normalized=struct.pack('>115I',*result)
    if hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA:raise ValueError('Changed timer lifetime/edge recipe')
    return normalized,moved


def relocate(raw,bindings,anchors):
    words=list(struct.unpack('>115I',raw))
    for at,entries in bindings.items():
        if len(entries)!=1:raise ValueError('Unknown timer relocation group')
        kind,name=entries[0];value=anchors[name]
        if kind=='R_MIPS_HI16':words[at//4]=words[at//4]&0xFFFF0000|((value+0x8000)>>16)&65535
        elif kind=='R_MIPS_LO16':words[at//4]=words[at//4]&0xFFFF0000|value&65535
        elif kind=='R_MIPS_26':words[at//4]=words[at//4]&0xFC000000|(value>>2)&0x3FFFFFF
        else:raise ValueError('Unknown timer relocation kind')
    return words


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings);old=struct.unpack('>115I',raw);new=struct.unpack('>115I',normalized)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):raise ValueError('Existing timer guards')
    if not before.endswith(b'\n'):raise ValueError('Unterminated timer guard predecessor')
    spec=lambda entries:';'.join(k+':'+n for k,n in entries) or '-';rows=[]
    for i,(a,b) in enumerate(zip(old,new)):
        if a==b and bindings.get(i*4,[])==moved.get(i*4,[]):continue
        rows.append(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
            replacement='0x%08X'%b,expected_relocations=spec(bindings.get(i*4,[])),replacement_relocations=spec(moved.get(i*4,[])),
            note='Normalize proven timer pointer lifetimes and mutually exclusive timer-load edges',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=60:raise ValueError('Changed timer guard coverage')
    output=io.StringIO(newline='');csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+output.getvalue().encode()
