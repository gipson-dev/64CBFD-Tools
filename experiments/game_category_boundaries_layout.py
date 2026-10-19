"""Restore proven register lifetimes and two independent nontrapping address adds."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_category_boundaries_candidates as source
from tools.experiments.game_record_release_layout import fields

RAW_SHA='6b07847f295342b95623749ed173b20a3c0969dd8dda5f9831ef329c18148a77'
NORMALIZED_SHA='9111eb1829ded7f968afba03b8f8449dd03b722f1017dd9d2231b4633c486e4d'
BINDINGS={4:[('R_MIPS_HI16','D_8009D9C0')],8:[('R_MIPS_LO16','D_8009D9C0')],
    12:[('R_MIPS_HI16','D_8009D9C4')],20:[('R_MIPS_LO16','D_8009D9C4')],
    60:[('R_MIPS_HI16','D_80087290')],64:[('R_MIPS_LO16','D_80087290')],
    72:[('R_MIPS_HI16','D_800D2350')],88:[('R_MIPS_LO16','D_800D2350')],
    196:[('R_MIPS_HI16','D_800D2358')],200:[('R_MIPS_LO16','D_800D2358')],
    204:[('R_MIPS_HI16','D_800D237C')],220:[('R_MIPS_LO16','D_800D237C')],
    300:[('R_MIPS_HI16','D_800D237C')],304:[('R_MIPS_LO16','D_800D237C')],
    324:[('R_MIPS_HI16','D_800D2360')],332:[('R_MIPS_LO16','D_800D2360')],
    412:[('R_MIPS_HI16','D_8009D9C8')],416:[('R_MIPS_LO16','D_8009D9C8')],
    420:[('R_MIPS_HI16','D_800D2360')],436:[('R_MIPS_LO16','D_800D2360')]}
ROW_GP={6:2,7:6,8:7,9:8,10:9,11:10}
BASE_GP={10:9,11:10}
FINAL_GP={5:6,6:8,25:5,14:7,15:25,24:11,10:9,11:10}
FP={0:2,2:0}


def origins():
    result=list(range(112));result[89:91]=[90,89];return result


def fp_fields(word):
    op=word>>26
    if op in (49,57):return (16,)
    if op!=17:return ()
    if word>>21&31==8:return ()
    if word>>21&31!=16:raise ValueError('Unexpected category-boundary FP format')
    if word&63 in (0,2):return (6,11,16)
    if word&63==60:return (11,16)
    raise ValueError('Unexpected category-boundary FP operation')


def normalize(raw,bindings):
    if len(raw)!=448 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown category-boundary body or bindings')
    words=struct.unpack('>112I',raw);order=origins()
    if sorted(order)!=list(range(112)):raise ValueError('Lost category-boundary source origin')
    # Both swapped ADDU definitions are independent of each other and cannot trap.
    a,b=words[89:91]
    if any(w>>26 or w&63!=33 for w in (a,b)) or {a>>11&31,b>>11&31}&{a>>21&31,a>>16&31,b>>21&31,b>>16&31}:
        raise ValueError('Dependent category-boundary address adds')
    result=[]
    for new,old in enumerate(order):
        original=word=words[old]
        mapping=ROW_GP if 20<=old<=47 else BASE_GP if old in (52,53) else FINAL_GP if 75<=old<=103 else {25:14} if old in (106,107) else {}
        for shift in fields(original):
            value=original>>shift&31;word=word&~(31<<shift)|(mapping.get(value,value)<<shift)
        if old<15 or 84<=old<=103:
            for shift in fp_fields(original):
                value=original>>shift&31;word=word&~(31<<shift)|(FP.get(value,value)<<shift)
        result.append(word)
    normalized=struct.pack('>112I',*result)
    if hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA:raise ValueError('Changed category-boundary lifetime recipe')
    return normalized,dict(bindings)


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings);old=struct.unpack('>112I',raw);new=struct.unpack('>112I',normalized)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):raise ValueError('Existing category-boundary guards')
    if not before.endswith(b'\n'):raise ValueError('Unterminated category-boundary predecessor')
    spec=lambda entries:';'.join(k+':'+n for k,n in entries) or '-';rows=[]
    for i,(a,b) in enumerate(zip(old,new)):
        if a==b:continue
        rows.append(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
            replacement='0x%08X'%b,expected_relocations=spec(bindings.get(i*4,[])),replacement_relocations=spec(moved.get(i*4,[])),
            note='Normalize proven category-boundary register lifetimes and independent address adds',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=35:raise ValueError('Changed category-boundary guard coverage')
    output=io.StringIO(newline='');csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+output.getvalue().encode()


def relocate(raw,bindings,anchors):
    words=list(struct.unpack('>112I',raw))
    for at,entries in bindings.items():
        if len(entries)!=1:raise ValueError('Unknown category-boundary relocation group')
        kind,name=entries[0];value=anchors[name]
        if kind=='R_MIPS_HI16':words[at//4]=words[at//4]&0xFFFF0000|((value+0x8000)>>16)&65535
        elif kind=='R_MIPS_LO16':words[at//4]=words[at//4]&0xFFFF0000|value&65535
        else:raise ValueError('Unknown category-boundary relocation kind')
    return words
