"""Closed row-address schedule and shared low-ID allocation recipe."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_packed_row_dispatch_candidates as source
from tools.experiments.game_packed_peer_lookup_layout import fields

RAW_SHA='44b0c2eb531f5b3b30da2f7ca213838cdc20f6af6c5540f247963572be422916'
NORMALIZED_SHA='55b4439f2255412264316483b94b36c9b6cae113683edc9ee5277d887385e08e'
GP={22:{24:14},23:{24:14},26:{14:15},27:{14:15},28:{15:24},29:{24:14},30:{24:14},31:{15:24},
    46:{3:2},47:{3:2,5:3},48:{5:3},50:{5:3}}
BINDINGS={48:[('R_MIPS_HI16','D_80087380')],52:[('R_MIPS_LO16','D_80087380')],
    60:[('R_MIPS_HI16','D_800D23C0')],72:[('R_MIPS_LO16','D_800D23C0')],
    216:[('R_MIPS_26','func_15114B94')],244:[('R_MIPS_26','func_1503DDD0')],284:[('R_MIPS_26','func_1508EDBC')],
    224:[('R_MIPS_HI16','D_800D23C0')],228:[('R_MIPS_LO16','D_800D23C0')],
    252:[('R_MIPS_HI16','D_800D23C0')],256:[('R_MIPS_LO16','D_800D23C0')]}


def origins():
    order=list(range(91));order[22:32]=[26,27,24,25,22,23,29,28,31,30];return order


def normalize(raw,bindings):
    if len(raw)!=364 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown packed-row dispatcher body or bindings')
    words=struct.unpack('>91I',raw);order=origins()
    if sorted(order)!=list(range(91)):raise ValueError('Lost dispatcher source origin')
    if (words[49],words[55],words[62])!=(0,0x30640FFF,0x30640FFF):
        raise ValueError('Unknown duplicated low-ID call operands')
    result=[]
    for new,old in enumerate(order):
        word=words[old];mapping=GP.get(new,{})
        shifts=fields(word);present={word>>shift&31 for shift in shifts}
        if not set(mapping)<=present or 0 in mapping or any(not 0<v<32 for v in mapping.values()):
            raise ValueError('Unknown dispatcher register recipe')
        original=word
        for shift in shifts:
            value=original>>shift&31;word=word&~(31<<shift)|(mapping.get(value,value)<<shift)
        if new==48:
            if word!=0x12830005:raise ValueError('Unknown type-2 comparison operands')
            word=0x10740005
        elif new==49:word=0x30450FFF
        elif new in (55,62):word=0x00A02025
        result.append(word)
    normalized=struct.pack('>91I',*result)
    if hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA:raise ValueError('Changed dispatcher layout recipe')
    return normalized,dict(bindings)


def relocate(raw,bindings,anchors):
    words=list(struct.unpack('>91I',raw))
    for at,entries in bindings.items():
        if len(entries)!=1:raise ValueError('Unknown dispatcher relocation group')
        kind,name=entries[0];value=anchors[name]
        if kind=='R_MIPS_HI16':words[at//4]=words[at//4]&0xFFFF0000|((value+0x8000)>>16)&65535
        elif kind=='R_MIPS_LO16':words[at//4]=words[at//4]&0xFFFF0000|value&65535
        elif kind=='R_MIPS_26':
            if value&3 or value>>28!=source.ENTRY>>28:raise ValueError('Invalid dispatcher call rebase')
            words[at//4]=words[at//4]&0xFC000000|(value>>2)&0x3FFFFFF
        else:raise ValueError('Unknown dispatcher relocation kind')
    return words


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings);old=struct.unpack('>91I',raw);new=struct.unpack('>91I',normalized)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):
        raise ValueError('Existing dispatcher guards')
    if not before.endswith(b'\n'):raise ValueError('Unterminated dispatcher guard predecessor')
    spec=lambda entries:';'.join(kind+':'+name for kind,name in entries) or '-'
    rows=[]
    for i,(a,b) in enumerate(zip(old,new)):
        if a==b:continue
        rows.append(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
            replacement='0x%08X'%b,expected_relocations=spec(bindings.get(i*4,[])),replacement_relocations=spec(moved.get(i*4,[])),
            note='Normalize packed-row dispatcher schedule and shared low-ID allocation',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=15:raise ValueError('Changed dispatcher guard coverage')
    output=io.StringIO(newline='');csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+output.getvalue().encode()
