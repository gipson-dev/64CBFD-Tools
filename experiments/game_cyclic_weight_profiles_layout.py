"""Closed cyclic-weight entry schedule, named private homes and early RA-load copy."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_cyclic_weight_profiles_candidates as source

RAW_SHA='df73a3db75bc1d3e8d61487629cf1ea7dc9bcb7f3d80d9bc5c7c1bf56406cf06'
NORMALIZED_SHA='d679333ccc0f40f736ec6bb2092f3346336763b6263f96f35f0d88053a754666'
BINDINGS={0x2C:[('R_MIPS_HI16','D_8008FD8C')],0x30:[('R_MIPS_LO16','D_8008FD8C')],
    0x34:[('R_MIPS_HI16','D_800D23B0')],0x38:[('R_MIPS_LO16','D_800D23B0')],
    0xD0:[('R_MIPS_26','func_150ADA68')],0xE8:[('R_MIPS_26','func_150ADA68')]}
HOMES={0x40:0x48,0x48:0x6C,0x64:0x84,0x68:0x50,0x78:0x60}


def origins():
    result=[*range(0,0x54,4),0x5C,0x60,0x68,0x6C,*range(0x74,0x98,4),
        0x58,0x54,'early-RA-copy',0x64,0x9C,0xA0,0x70,0xA4,0x98,
        0xB4,0xA8,0xAC,0xB0,0xB8,0xCC,0xBC,0xC0,0xC8,0xC4,*range(0xD0,0x2F0,4)]
    if len(result)!=189 or len(set(result))!=189 or set(result)-{'early-RA-copy'}!=set(range(0,752,4)):
        raise ValueError('Changed cyclic-weight source-origin accounting')
    return result


def normalize(raw,bindings):
    if len(raw)!=752 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown cyclic-weight source or bindings')
    words=list(struct.unpack('>188I',raw));order=origins();destination={x:i for i,x in enumerate(order)}
    if words[0x2C0//4]!=0x8FBF003C:raise ValueError('Changed cyclic-weight RA home')
    result=[];moved={}
    for new,old in enumerate(order):
        if old=='early-RA-copy':result.append(words[0x2C0//4]);continue
        word=words[old//4];op,rs=word>>26,word>>21&31
        if op in (1,4,5,6,7,20,21,22,23) or op==17 and rs==8:
            target=old+4+(((word&65535)^32768)-32768)*4
            if old==0x48:target=0x5C
            elif old in (0x84,0x8C):target=0x58
            elif old==0x54:target=0x2C4
            elif old==0x2B8:target=0xB4
            if target not in destination:raise ValueError('Removed cyclic-weight branch destination')
            offset=destination[target]-new-1
            if not -32768<=offset<32768:raise ValueError('Cyclic-weight branch out of range')
            word=word&0xFFFF0000|offset&65535
        if old==0x54:word=word&0x03FFFFFF|22<<26
        if op in (9,32,35,43,49,57) and rs==29 and word&65535 in HOMES:
            word=word&0xFFFF0000|HOMES[word&65535]
        if old in bindings:moved[new*4]=bindings[old]
        result.append(word)
    normalized=struct.pack('>189I',*result)
    if len(moved)!=6 or hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA:
        raise ValueError('Changed cyclic-weight schedule or bindings')
    return normalized,moved


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings);old=struct.unpack('>188I',raw);new=struct.unpack('>189I',normalized)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if not before.endswith(b'\n') or any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):
        raise ValueError('Unknown cyclic-weight guard predecessor')
    spec=lambda entries:';'.join(k+':'+n for k,n in entries) or '-'
    rows=[];cursor=0;order=origins()
    for i,word in enumerate(old):
        at=i*4;insert=cursor+1<len(order) and order[cursor+1]=='early-RA-copy'
        replacement=new[cursor];expected_reloc=spec(bindings.get(at,[]));replacement_reloc=spec(moved.get(cursor*4,[]))
        rows.append(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%at,
            expected='0x%08X'%word,replacement='0x%08X'%replacement,
            expected_relocations=expected_reloc,replacement_relocations=replacement_reloc,
            note='Recover cyclic-weight entry/private schedule; source word 0x%X'%order[cursor],
            insert_after='0x%08X'%new[cursor+1] if insert else '',insert_after_relocations='-' if insert else '',omit='false'))
        cursor+=2 if insert else 1
    if cursor!=189 or sum(bool(r['insert_after']) for r in rows)!=1:
        raise ValueError('Changed cyclic-weight guard accounting')
    output=io.StringIO(newline='');csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+output.getvalue().encode()
