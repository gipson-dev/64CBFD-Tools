"""Closed experimental layout of the complete 305-word spline payload C body."""
import hashlib
import csv
import io
import struct

from tools.experiments import game_route_spline_payload_fitting as source
from tools.experiments import game_route_projection_layout_normalizer as projection

NORMALIZED_SHA='d8eb98efcc1916cc0d79acc7c086951fbdc3ff195a67f56d026d74dba1abdd20'
SCAN={3:4,4:5,5:6,6:7,7:8,8:9,9:10,10:11,11:12,12:13,13:14,16:3,22:23}
LOOP={17:18,18:19,19:20,20:21,21:22,22:23,23:17}
EXTRAPOLATION=(205,206,211,210,207,216,221,212,226,208,215,231,213,220,209,
    217,214,222,218,225,223,230,219,227,224,232,228,233,229,234)
COMMUTED=(208,213,218,223,228,233)
SPECIAL={17:{16:2},18:{16:2},21:{16:2,23:17},34:{16:17},98:{23:17},101:{14:15},102:{14:15},
    103:{15:24},104:{15:24},107:{15:24},120:{30:2},123:{30:2},124:{30:2},128:{2:9},129:{3:25},
    130:{30:2},133:{2:9},134:{2:9},136:{3:25},142:{21:22},143:{23:17},144:{17:18},145:{18:19},
    146:{19:20},147:{20:21},172:{24:10},173:{24:10},236:{8:11},242:{8:11},285:{9:12},289:{9:12}}


def origins():
    order=list(range(305));order[1],order[5]=order[5],order[1]
    order[22:29]=[27,22,23,24,25,26,28]
    order[142:150]=[149,142,143,144,145,146,147,148]
    order[155],order[157]=order[157],order[155]
    order[205:235]=EXTRAPOLATION
    if len(order)!=305 or set(order)!=set(range(305)):raise ValueError('Invalid closed spline word ordering')
    return order


def fields(word):
    op,fmt,fn=word>>26,word>>21&31,word&63
    if op in (53,61):return (21,),(16,)
    if op==17:
        if fmt==0:return (16,), (11,)
        if fmt==16 and fn==62:return (), (16,11)
        if fmt==16 and fn==33 or fmt==17 and fn==32:return (), (11,6)
        if fmt==17 and fn==2:return (), (16,11,6)
    return projection.fields(word)


def gp_map(old):
    result={22:23} if old==2 or 17<=old<290 else {}
    if 39<=old<=69:result.update(SCAN)
    if 150<=old<=243:result.update(LOOP)
    result.update(SPECIAL.get(old,{}))
    return result


def normalize(raw,bindings):
    if len(raw)!=1220 or hashlib.sha256(raw).hexdigest()!=source.JOINT_SHA or bindings!=source.JOINT_BINDINGS:
        raise ValueError('Unknown complete spline body or bindings')
    words=struct.unpack('>305I',raw);order=origins();destination={old:new for new,old in enumerate(order)}
    result=[]
    for new,old in enumerate(order):
        word=words[old];op,rs=word>>26,word>>21&31
        if op in (4,5,6,7,20,21) or op==17 and rs==8:
            target=old+1+(((word&65535)^32768)-32768)
            if target not in destination:raise ValueError('Missing spline branch target')
            word=word&0xFFFF0000|((destination[target]-new-1)&65535)
        if old in (23,28):
            if op!=(43 if old==23 else 57) or rs!=22 or word&65535!=(92 if old==23 else 88):
                raise ValueError('Unknown stop payload store')
            word=(word&~(31<<21)&0xFFFF0000)|(6<<21)|((word&65535)-76)
        gp,fp=fields(word);before=word;rename=gp_map(old)
        for shift in gp:
            register=before>>shift&31
            word=word&~(31<<shift)|rename.get(register,register)<<shift
        if old in COMMUTED:
            if word>>26!=17 or word>>21&31!=16 or word&63!=0:raise ValueError('Unknown extrapolation add')
            ft,fs=word>>16&31,word>>11&31
            word=word&~((31<<16)|(31<<11))|(ft<<11)|(fs<<16)
        result.append(word)
    moved={destination[at//4]*4:[(kind,'D_8009DA18' if name=='.rodata' else name) for kind,name in entries]
        for at,entries in bindings.items()}
    if len(moved)!=33:raise ValueError('Lost spline binding')
    normalized=struct.pack('>305I',*result)
    if hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA:
        raise ValueError('Changed spline layout recipe')
    return normalized,moved


def relocate(raw,bindings,anchors):return projection.relocate(raw,bindings,anchors)


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings);old=struct.unpack('>305I',raw);new=struct.unpack('>305I',normalized)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==source.source.OWNER and r['function']==source.source.FUNCTION for r in reader):
        raise ValueError('Spline payload guards already exist')
    if not before.endswith(b'\n'):raise ValueError('Unterminated guard prefix')
    spec=lambda entries:';'.join(kind+':'+name for kind,name in entries) or '-'
    rows=[dict(filename=source.source.OWNER,function=source.source.FUNCTION,offset='0x%X'%(i*4),
        expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=spec(bindings.get(i*4,[])),
        replacement_relocations=spec(moved.get(i*4,[])),
        note='Recover spline payload register layout and schedule from C source word %d'%origins()[i],
        insert_after='',insert_after_relocations='',omit='false') for i,(a,b) in enumerate(zip(old,new))]
    output=io.StringIO(newline='');writer=csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n');writer.writerows(rows)
    return before+output.getvalue().encode()
