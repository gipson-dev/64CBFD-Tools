"""Explicit peer-lookup parameter homes, entry edge and allocation recipe."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_packed_peer_lookup_candidates as source
from tools.experiments.game_slot_state_transfer_layout import fields as shared_fields

RAW_SHA='24b2c822fdd4365a8bf9df44f1614b83ca16b08e2c19babd04e0059a9b3d02ca'
NORMALIZED_SHA='750aa7902c6654ecbdb453d806b36ffa26da8ad81feb3ba8bfdaeaa17c9bf444'
GP={19:{13:24},20:{13:24},23:{24:25},24:{24:25,10:12},25:{13:24},26:{13:24,11:10},
    27:{10:12,25:13},28:{25:13,10:12},29:{11:10,12:11},30:{12:11},31:{10:12},36:{11:10},54:{12:11}}
BINDINGS={16:[('R_MIPS_HI16','D_80087380')],20:[('R_MIPS_LO16','D_80087380')],
    48:[('R_MIPS_HI16','D_800D23C0')],52:[('R_MIPS_LO16','D_800D23C0')]}
INSERTS={2:0xAFA40008,3:0xAFA5000C,15:0x2402FFFF}


def fields(word):
    if word>>26==12:return (21,16)
    if word>>26==0 and word&63==43:return (21,16,11)
    return shared_fields(word)


def origins():
    return [0,1,None,None,6,7,9,8,2,3,4,5,11,12,10,None,13,14,15,20,21,18,19,16,17,22,23,24,25,26,*range(27,60)]


def structure(raw,bindings):
    if len(raw)!=240 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown packed-peer source body or bindings')
    order=origins();destination={old:new for new,old in enumerate(order) if old is not None}
    if len(order)!=63 or sorted(destination)!=list(range(60)) or [i for i,v in enumerate(order) if v is None]!=list(INSERTS):
        raise ValueError('Lost or duplicated peer source origin')
    words=struct.unpack('>60I',raw);result=[]
    for new,old in enumerate(order):
        if old is None:result.append(INSERTS[new]);continue
        word=words[old];op=word>>26
        if op in (4,5,20,21):
            target=old+1+(((word&65535)^32768)-32768)
            if old==10:
                if word!=0x1060002D:raise ValueError('Unknown shared peer early-return edge')
                word=word&0x03FFFFFF|(20<<26);target=57
            word=word&0xFFFF0000|((destination[target]-new-1)&65535)
        result.append(word)
    return result,{destination[at//4]*4:entries for at,entries in bindings.items()}


def normalize(raw,bindings):
    words,moved=structure(raw,bindings);result=[]
    for index,word in enumerate(words):
        mapping=GP.get(index,{});shifts=fields(word);present={word>>shift&31 for shift in shifts}
        if not set(mapping)<=present or 0 in mapping or any(not 0<v<32 for v in mapping.values()):
            raise ValueError('Unknown packed-peer register recipe')
        old=word
        for shift in shifts:
            value=old>>shift&31;word=word&~(31<<shift)|(mapping.get(value,value)<<shift)
        result.append(word)
    normalized=struct.pack('>63I',*result)
    if hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA:raise ValueError('Changed peer layout recipe')
    return normalized,moved


def relocate(raw,bindings,anchors):
    words=list(struct.unpack('>63I',raw))
    for at,entries in bindings.items():
        if len(entries)!=1:raise ValueError('Unknown peer relocation group')
        kind,name=entries[0];value=anchors[name]
        if kind=='R_MIPS_HI16':part=((value+0x8000)>>16)&65535
        elif kind=='R_MIPS_LO16':part=value&65535
        else:raise ValueError('Unknown peer relocation kind')
        words[at//4]=words[at//4]&0xFFFF0000|part
    return words


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings);old=struct.unpack('>60I',raw);new=struct.unpack('>63I',normalized)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):
        raise ValueError('Existing packed-peer guards')
    if not before.endswith(b'\n'):raise ValueError('Unterminated peer guard predecessor')
    spec=lambda entries:';'.join(kind+':'+name for kind,name in entries) or '-'
    rows=[];destination=0
    # Associate the derived 63-word output stream with all 60 checked source words.
    inserted={1,3,15}
    for i,word in enumerate(old):
        row=dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%word,
            replacement='0x%08X'%new[destination],expected_relocations=spec(bindings.get(i*4,[])),
            replacement_relocations=spec(moved.get(destination*4,[])),
            note='Normalize complete packed-peer output word %d; checked parameter homes and allocation'%destination,
            insert_after='',insert_after_relocations='',omit='false')
        destination+=1
        if destination in inserted:
            row['insert_after']='0x%08X'%new[destination];row['insert_after_relocations']=spec(moved.get(destination*4,[]))
            destination+=1
        rows.append(row)
    if destination!=63 or sum(bool(r['insert_after']) for r in rows)!=3:raise ValueError('Unknown peer stream expansion')
    output=io.StringIO(newline='');csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+output.getvalue().encode()
