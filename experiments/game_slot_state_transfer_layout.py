"""Experimental explicit slot-transfer allocation and scheduling recipe."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_slot_state_transfer_candidates as source

RAW_SHA='6614844cb6c0714ad69f73adab4fa0214a709c66aeefac7aea114d0fcdc127fe'
NORMALIZED_SHA='70b4fa7e70377c696f09b510e462abaae7a665dd7615a95db41bb585ab9f9c05'
GP={
    19:{25:11},23:{25:11},26:{12:25},29:{12:25},
    68:{12:14},69:{12:14,14:13},70:{24:25},71:{24:25,25:11},72:{25:11,11:12},73:{14:13,11:12},
    79:{13:24},80:{13:24,15:25},81:{24:11},82:{24:11,15:25},
    86:{25:12},87:{25:12,12:13},88:{11:15},89:{11:15,12:13},
    93:{14:25},94:{14:25,13:11},95:{15:14},96:{15:14,13:11},98:{24:12},99:{24:12},
    101:{25:13},102:{25:13,12:15},103:{12:15},107:{11:24},108:{11:24,14:25},
    111:{13:11},112:{13:11,14:25},113:{15:14},114:{15:14},115:{24:12},117:{24:12,25:13},
    119:{25:13},120:{12:15},121:{12:15},124:{11:24},125:{11:24},128:{11:24},
    129:{14:25},134:{14:25},135:{14:25},144:{13:11},145:{12:15},146:{13:11},147:{15:14},
    148:{15:14,24:12},149:{24:12},150:{12:15},152:{25:13},153:{25:13},155:{11:24},156:{11:24},
    163:{12:15},167:{14:25},168:{13:11},169:{25:13},170:{14:25},171:{13:11},172:{15:14},
    173:{24:12},174:{24:12,15:14},175:{12:15},176:{12:15,25:13},181:{11:24},182:{11:24,14:25},183:{14:25},
}
BINDINGS={
    16:[('R_MIPS_HI16','D_800D18A4')],24:[('R_MIPS_LO16','D_800D18A4')],
    28:[('R_MIPS_HI16','D_800D18A2')],32:[('R_MIPS_LO16','D_800D18A2')],
    68:[('R_MIPS_HI16','D_800D18A0')],72:[('R_MIPS_LO16','D_800D18A0')],
    140:[('R_MIPS_26','func_150859AC')],168:[('R_MIPS_26','func_15085710')],184:[('R_MIPS_26','func_15085710')],
    192:[('R_MIPS_HI16','D_800D23B0')],196:[('R_MIPS_LO16','D_800D23B0')],
    416:[('R_MIPS_HI16','D_800D23B0')],420:[('R_MIPS_LO16','D_800D23B0')],
    436:[('R_MIPS_HI16','D_800CC2D0')],440:[('R_MIPS_LO16','D_800CC2D0')],
    488:[('R_MIPS_26','func_15062800')],496:[('R_MIPS_HI16','D_800BE9F0')],500:[('R_MIPS_LO16','D_800BE9F0')],
    524:[('R_MIPS_HI16','D_800D2E48')],544:[('R_MIPS_LO16','D_800D2E48')],548:[('R_MIPS_26','func_1509B570')],
    572:[('R_MIPS_HI16','D_800CC2D0')],580:[('R_MIPS_LO16','D_800CC2D0')],708:[('R_MIPS_26','func_15128774')],
    716:[('R_MIPS_HI16','D_8008FD94')],720:[('R_MIPS_LO16','D_8008FD94')],
}
HOMES={31:(0x1C,0x20),32:(0x20,0x24),36:(0x18,0x1C),44:(0x1A,0x1E),
    51:(0x20,0x24),60:(0x1C,0x20),118:(0x1C,0x2C),127:(0x1C,0x2C),
    138:(0x1C,0x2C),140:(0x1C,0x2C)}
# Each pair materializes the computed address, then tests that address for zero.
CHECKS={54:(0x9C,24),76:(0x39C,15),84:(0x3DC,14),91:(0xEB0,24)}
CHECK_BRANCHES={65:54,77:76,85:84,92:91}


def fields(word):
    op,fn=word>>26,word&63
    if op==0:
        if fn in (0,3):return (16,11)
        if fn in (4,33,35,36,37,39):return (21,16,11)
        if fn in (25,26):return (21,16)
        if fn==18:return (11,)
        if fn==8:return (21,)
        if fn==13:return ()
    if op==1:return (21,)
    if op in (4,5,9,10,13,20,21,32,33,35,36,37,40,41,43):return (21,16)
    if op==15:return (16,)
    if op==3:return ()
    raise ValueError('Unsupported transfer instruction: %08X'%word)


def origins():
    order=list(range(source.WORDS))
    order[26],order[27]=order[27],order[26]
    order[54:65]=list(range(55,65))+[54]
    order[141:147]=[143,145,142,141,146,144]
    order[171],order[173]=order[173],order[171]
    if len(set(order))!=source.WORDS:raise ValueError('Non-permutation transfer schedule')
    return order


def structure(raw,bindings):
    if len(raw)!=756 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown slot-transfer source body or bindings')
    words=list(struct.unpack('>189I',raw));order=origins();destination={old:new for new,old in enumerate(order)}
    result=[]
    for new,old in enumerate(order):
        word=words[old];op=word>>26
        if old in HOMES:
            before,after=HOMES[old]
            if op not in (33,35,43) or word>>21&31!=29 or word&65535!=before:
                raise ValueError('Unknown slot-transfer home at %d'%old)
            word=word&0xFFFF0000|after
        if old in CHECKS:
            offset,register=CHECKS[old]
            if word!=0x24010000|(-offset&65535):raise ValueError('Unknown computed-address constant')
            word=(9<<26)|(2<<21)|(register<<16)|offset
        elif old in CHECK_BRANCHES:
            _,register=CHECKS[CHECK_BRANCHES[old]]
            if op!=4 or word>>21&31!=2 or word>>16&31!=1:
                raise ValueError('Unknown computed-address comparison')
            word=(word&65535)|(4<<26)|(register<<21)
        if op in (1,4,5,20,21):
            target=old+1+(((word&65535)^32768)-32768)
            # The first constant was hoisted before the flags branch in raw C.
            target=destination[54] if old==56 else destination[target]
            word=word&0xFFFF0000|((target-new-1)&65535)
        result.append(word)
    moved={destination[at//4]*4:entries for at,entries in bindings.items()}
    return result,moved


def normalize(raw,bindings):
    words,moved=structure(raw,bindings);result=[]
    for index,word in enumerate(words):
        mapping=GP.get(index,{})
        shifts=fields(word);present={word>>shift&31 for shift in shifts}
        if not set(mapping)<=present or any(not 0<v<32 for v in mapping.values()) or 0 in mapping:
            raise ValueError('Unknown transfer register recipe at %d'%index)
        old=word
        for shift in shifts:
            value=old>>shift&31;word=word&~(31<<shift)|(mapping.get(value,value)<<shift)
        result.append(word)
    normalized=struct.pack('>189I',*result)
    if hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA:
        raise ValueError('Changed slot-transfer layout recipe')
    return normalized,moved


def relocate(raw,bindings,anchors):
    words=list(struct.unpack('>189I',raw))
    for at,entries in bindings.items():
        if len(entries)!=1:raise ValueError('Unknown transfer relocation group')
        kind,name=entries[0];value=anchors[name]
        if kind=='R_MIPS_HI16':words[at//4]=words[at//4]&0xFFFF0000|((value+0x8000)>>16)&65535
        elif kind=='R_MIPS_LO16':words[at//4]=words[at//4]&0xFFFF0000|value&65535
        elif kind=='R_MIPS_26':
            if value&3 or value>>28!=source.ENTRY>>28:raise ValueError('Invalid transfer call rebase')
            words[at//4]=words[at//4]&0xFC000000|(value>>2)&0x3FFFFFF
        else:raise ValueError('Unknown transfer relocation kind')
    return words


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings);old=struct.unpack('>189I',raw);new=struct.unpack('>189I',normalized)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):
        raise ValueError('Existing slot-transfer guards')
    if not before.endswith(b'\n'):raise ValueError('Unterminated original guard prefix')
    spec=lambda entries:';'.join(kind+':'+name for kind,name in entries) or '-'
    rows=[]
    for i,(a,b) in enumerate(zip(old,new)):
        previous,following=bindings.get(i*4,[]),moved.get(i*4,[])
        if a==b and previous==following:continue
        rows.append(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%(i*4),
            expected='0x%08X'%a,replacement='0x%08X'%b,
            expected_relocations=spec(previous),replacement_relocations=spec(following),
            note='Normalize closed slot-transfer allocation and schedule; output word %d'%i,
            insert_after='',insert_after_relocations='',omit='false'))
    output=io.StringIO(newline='')
    csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+output.getvalue().encode()
