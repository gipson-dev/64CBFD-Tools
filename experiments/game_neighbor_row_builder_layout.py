"""Checked source origins for neighbor-row allocation, spills and induction."""
import hashlib
import struct
import csv
import io

from tools.experiments import game_neighbor_row_builder_home_candidates as homes
from tools.experiments import game_actor_pair_scheduler_layout as prior

source,SELECTED = homes.source,homes.SELECTED
BUILD = homes.BUILD+'/match'
RAW_SHA='a4e4ea9044579105869bf6ea4f1426c15074b4ae8f9e22601e7f425ded1e6082'
NORMALIZED_SHA='bb487d0c6e0aae625247d46836747348c1f059d31fb1f4436a0c57298736d3b6'
BINDINGS={
    0x4:[('R_MIPS_HI16','D_800D23B0')],0x8:[('R_MIPS_LO16','D_800D23B0')],
    0x114:[('R_MIPS_HI16','D_8008FD90')],0x120:[('R_MIPS_LO16','D_8008FD90')],
    0x118:[('R_MIPS_HI16','D_800CC2D0')],0x11C:[('R_MIPS_LO16','D_800CC2D0')],
    0x164:[('R_MIPS_HI16','D_800D23B0')],0x168:[('R_MIPS_LO16','D_800D23B0')],
    0x2B8:[('R_MIPS_26','func_150859AC')],
    0x328:[('R_MIPS_HI16','D_800D23B0')],0x32C:[('R_MIPS_LO16','D_800D23B0')],
    0x508:[('R_MIPS_HI16','D_800D23B0')],0x50C:[('R_MIPS_LO16','D_800D23B0')],
}
MASKS={0x8C,0x9C,0x1E8}
PRIVATE_SPILLS={0x10,0x558,0xA0,0x34C,0x468,0x524,0x2A4,0x2DC,0x2BC,0x2D4}
POINTER_STEPS={0xC8,0x3D0,0x3DC,0x404,0x410,0x504}
ADDRESS_COPIES={0x8,0x50C,0x120,0x218,0x278}
# Coalesce the null-distance definition and the common zero-return copy.
REMOVED=MASKS|PRIVATE_SPILLS|POINTER_STEPS|ADDRESS_COPIES|{0x51C,0x190}


def origins():
    # Public accesses retain unique source words. Private register promotion
    # and caller-save spills account for the additional/removed private words.
    order=[0,0xC,0x14,0x18,0x1C,0x20,0x24,0x28,0x2C,0x30,
        0x4,0x34,0x3C,0x84,0x54,0x12C,0x40,0x44,0x48,0x4C,
        0x130,0x50,0x58,0x60,0x5C,0x64,0x68,0x6C,
        ('context-hi-a',0x4),0x70,0x78,0x38,0x7C,0x80,0x74,0x88,
        ('slot-shift',0xA4),0x90,('context-hi-b',0x4),0x94,0x98,0xA4,
        0xA8,0xAC,('slot-copy',0xB4),0xB0,0xB4,0xB8,0xBC,0xC0,
        ('disabled-address',0xBC),0xC4,0xCC,0xD0,0xD4,0xD8,0xDC,0xE0,0xE4,
        ('group-load',0x140),0xE8,0xEC,0xF0,0xF4,0xF8,0xFC,0x100,
        ('count-load',0x47C),0x104,0x128,0x10C,0x110,0x118,0x11C,0x108,0x124,
        0x134,0x138,0x13C,0x140,0x144,0x148,0x14C,0x150,0x154,0x158,
        0x15C,0x160,0x164,0x168,0x16C,0x174,0x114,0x170,0x178,0x1F8,
        0x184,0x188,0x18C,0x180,0x17C,0x198,0x19C,0x194,
        *range(0x1A0,0x1E4,4),0x1FC,0x1E4,0x1EC,0x200,0x1F4,0x204,0x208,
        0x1F0,0x210,0x214,0x224,0x21C,0x220,('mode-copy',0x224),0x228,0x22C,
        *range(0x230,0x278,4),0x288,0x27C,0x280,0x284,0x290,0x28C,0x298,
        0x294,0x2A8,0x29C,0x2A0,0x2AC,0x2B4,('row-save',0x2B0),
        ('neighbor-save',0x2B4),0x2B0,0x2B8,('index-save',0x2B0),0x2C0,0x2C4,
        ('primary-hi',0x114),0x2CC,0x308,0x2D0,('row-load',0x2C8),
        ('neighbor-load',0x2D0),0x2C8,('index-load',0x2C8),0x2D8,
        *range(0x2E0,0x308,4),0x20C,0x30C,*range(0x310,0x34C,4),
        ('minimum-test',0x46C),*range(0x350,0x3B0,4),('remainder-negu',0x3B4),
        0x3B0,0x3B4,0x3B8,0x3BC,0x3C0,0x3C8,0x3C4,0x3CC,0x3D4,0x3D8,
        0x3E0,0x3E4,0x3E8,0x3EC,0x3F0,0x3F4,0x3FC,0x3F8,0x400,0x408,
        0x40C,0x414,*range(0x418,0x44C,4),0x44C,0x450,0x454,0x458,0x45C,
        0x460,0x464,0x46C,0x470,0x474,0x478,0x47C,0x480,0x484,0x488,0x48C,
        0x490,0x494,0x498,0x49C,0x4A0,0x4A4,0x4A8,0x4AC,0x4B0,0x4B4,
        0x4B8,0x4BC,0x4C0,0x4C4,0x4C8,0x4CC,0x4D0,0x4D4,0x4DC,0x4E0,
        0x4D8,0x4E8,0x4E4,0x4EC,0x4F0,0x4F4,0x4F8,0x500,0x4FC,
        0x508,0x510,0x520,0x514,0x518,0x528,0x52C,0x530,
        *range(0x534,0x558,4),0x55C,0x560]
    kept=[o for o in order if isinstance(o,int)]
    if len(order)!=336 or len(set(kept))!=319 or set(kept)!=set(range(0,1380,4))-REMOVED:
        raise ValueError(('Neighbor row origins are not closed',len(order),len(set(kept)),
            sorted(set(range(0,1380,4))-set(kept)-REMOVED), sorted(set(kept)&REMOVED)))
    return order


def fields(word):
    if word>>26==0 and word&63==13:return (),()
    if word>>26==0 and word&63==26:return (21,16),()
    if word>>26==0 and word&63==3:return (16,11),()
    if word>>26==1:return (21,),()
    if word>>26==17:
        fmt=word>>21&31
        if fmt in (0,4):return (16,),(11,)
        if fmt in (16,20):
            if word&63 in (0,1,2,3):return (),(16,11,6)
            if word&63 in (4,6,7,13,32):return (),(11,6)
    return prior.fields(word)


def allocation(old):
    if old<=0x34 or old>=0x534:return {},{}
    gp={10:12,11:9,12:17,13:31,17:13,18:10,21:11,22:6,23:21,30:22}
    if old<0x1E4:gp[7]=15
    elif old<=0x464:gp[7]=8
    if old<0x138:gp[8]=2
    elif old<=0x280:gp[8]=15
    elif 0x3B8<=old<=0x400:gp[8]=4
    if 0x180<=old<=0x314:gp[9]=7
    if 0x3A8<=old<=0x3B4:gp[9]=2
    if 0x350<=old<=0x460:gp.update({4:5,5:6,6:7})
    gp[31]=8 if old<=0x1DC else 18
    fp={8:6,10:8,6:10} if 0x324<=old<=0x344 else {}
    return gp,fp


# Split/coalesced result copies and temporaries around the long-lived cycle.
REGISTERS = {
    0x4:{16:2},0x34:{21:2},0x3C:{11:13},
    0x48:{16:24},0x4C:{16:24},0x50:{16:25},
    0x54:{16:14},0x5C:{16:14,21:25},0x6C:{16:14},
    0x74:{16:23},0x80:{16:15},0x88:{16:3,21:15},
    0xA4:{21:3},0xB8:{11:15},0xBC:{11:3,16:15},
    0xC0:{16:4},0xC4:{16:13,21:13},0xD8:{16:4,21:13},
    0xE8:{11:14,16:6},0xEC:{16:14},0xF0:{11:15,16:14,21:25},
    0xF4:{21:15},0xF8:{11:25,16:14,21:2},0x104:{16:15,21:25},
    0x10C:{21:24},0x110:{16:15},0x128:{16:6},
    0x12C:{16:14},0x13C:{16:14},0x144:{21:14},
    0x148:{11:24},0x150:{16:14,21:24},0x154:{16:14},
    0x158:{16:25},0x160:{16:24},0x164:{16:14},
    0x168:{16:14,21:14},0x16C:{16:24},0x17C:{16:15},
    0x180:{21:14},0x194:{21:15},0x1A0:{11:24},
    0x1A4:{16:24},0x1E0:{16:14},0x1E4:{11:18,21:8},
    0x1EC:{16:14},0x1F4:{21:8},0x200:{11:24,21:16},
    0x204:{11:14,21:24},0x208:{21:14},0x21C:{16:15,21:3},
    0x220:{21:15},0x234:{11:24},0x238:{21:24},
    0x244:{16:25},0x248:{11:14,21:25},0x24C:{21:14},
    0x280:{16:15,21:3},0x28C:{21:15},0x290:{11:25},
    0x298:{21:25},0x29C:{11:24},0x2A0:{21:24},
    0x2C4:{16:14},0x2CC:{16:14},0x2E0:{21:14},
    0x2F0:{21:14},0x328:{16:15},0x32C:{16:15,21:15},
    0x334:{21:15},0x358:{11:25},0x35C:{11:14,16:25},
    0x360:{16:15,21:14},0x364:{21:15},0x37C:{11:24},
    0x380:{11:25,16:24},0x384:{11:14},0x388:{11:15,16:14,21:25},
    0x38C:{16:24,21:15},0x390:{21:24},0x3AC:{16:25},
    0x3B0:{21:2},0x3BC:{11:14},0x3C0:{16:14},
    0x3C4:{16:14},0x3C8:{16:15},0x3D4:{16:15},
    0x3D8:{16:24},0x3E0:{16:5,21:7},0x3E4:{16:24},
    0x3E8:{16:5,21:6},0x3F0:{11:25},0x3F4:{16:25},
    0x3F8:{16:25},0x3FC:{16:14},0x408:{16:14},
    0x40C:{16:15},0x414:{16:15},0x418:{16:24},
    0x41C:{16:24},0x420:{16:25},0x424:{16:25},
    0x428:{16:14},0x42C:{16:14},0x430:{16:15},
    0x434:{16:15},0x438:{16:24},0x43C:{16:24},
    0x440:{16:25},0x444:{16:5,21:6},0x448:{16:25},
    0x450:{11:14},0x454:{11:15,16:14},0x458:{21:15},
    0x45C:{11:24,16:14},0x464:{21:24},0x46C:{16:23},
    0x474:{16:25},0x47C:{16:25},0x488:{16:25},
    0x4B0:{11:2},0x4B4:{11:15},0x4B8:{11:3,16:15},
    0x4BC:{11:13},0x4C0:{11:24,16:13,21:3},0x4C8:{21:24},
    0x4CC:{16:16,21:2},0x4D0:{16:13,21:13},0x4D8:{11:13},
    0x4DC:{11:25},0x4E0:{11:3,16:25},0x4E4:{16:13,21:3},
    0x4E8:{16:4},0x4EC:{16:13,21:13},0x500:{16:4,21:13},
    0x508:{16:2},0x510:{21:2},0x520:{16:15},
    0x528:{11:24,16:15},0x52C:{16:23,21:24},
}
HOMES={0x4C:0x64,0x12C:0x78,0x130:0x70,0xEC:0x40,0x100:0x8C,
    0x128:0x88,0x110:0x84,0x140:0x78,0x14C:0x8C,0x158:0x70,0x160:0x40,
    0x1F8:0x84,0x17C:0x88,0x244:0x64,0x2AC:0x90,0x2B4:0x5C,
    0x2B0:0x94,0x2C0:0x90,0x2D0:0x5C,0x2C8:0x94,0x474:0x70,
    0x47C:0x70,0x520:0x40,0xC:0x34,0x534:0x34}
for _at in (*range(0x14,0x34,4),*range(0x538,0x558,4)):
    HOMES[_at]=None


def rename(word,gp=None,fp=None,overrides=None):
    result=word
    for shifts,mapping in zip(fields(word),(gp or {},fp or {})):
        for shift in shifts:
            reg=word>>shift&31
            result=result&~(31<<shift)|mapping.get(reg,reg)<<shift
    for shift,reg in (overrides or {}).items():
        if shift not in fields(word)[0]+fields(word)[1]:raise ValueError('Not a neighbor-row operand')
        result=result&~(31<<shift)|reg<<shift
    return result


def form(words,item):
    old=item[1] if isinstance(item,tuple) else item
    word=words[old//4];overrides={};reloc=None
    if isinstance(item,tuple):
        role=item[0]
        if role.startswith('context-hi'):
            overrides={16:2};reloc=BINDINGS[0x4]
        elif role=='slot-shift':overrides={21:3,16:24,11:25}
        elif role=='slot-copy':overrides={21:3,16:0,11:6}
        elif role=='disabled-address':overrides={21:3,16:13,11:2}
        elif role=='group-load':word=word&0xFFFF0000|0x78;overrides={16:25}
        elif role=='count-load':word=word&0xFFFF0000|0x70;overrides={16:24}
        elif role=='mode-copy':pass
        elif role=='primary-hi':overrides={16:6};reloc=BINDINGS[0x114]
        elif role in ('row-save','row-load','neighbor-save','neighbor-load','index-save','index-load'):
            reg,home={'row':(10,0x3C),'neighbor':(11,0x60),'index':(13,0x44)}[role.split('-')[0]]
            word=word&0xFFFF0000|home;overrides={21:29,16:reg}
        elif role=='remainder-negu':overrides={21:0,16:25,11:2}
        elif role=='minimum-test':overrides={21:18,16:23,11:1}
        else:raise ValueError('Unknown neighbor-row derived form')
    else:
        if old in HOMES:
            home=HOMES[old]
            word=word&0xFFFF0000|((word&65535)-4 if home is None else home)
        # Replace advanced pointers with base + cursor; preserve each access.
        if old in (0xCC,0xD0,0xD4,0xDC):word=word&0xFFFF0000|((word+16)&65535)
        if old in (0x3D4,0x3E4):word=word&0xFFFF0000|((word-4)&65535)
        if old in (0x408,0x414,*range(0x418,0x444,4),0x448):word=word&0xFFFF0000|((word-16)&65535)
        if old in (0x18C,0x518):word=word&0x03FFFFFF|4<<26
        if old==0x214:word=word&0x03FFFFFF|21<<26
        if old==0x3B4:
            word=word&~63|33;overrides={21:2,16:12,11:7}
        if old==0x478:
            # nearest's private spill becomes its saved-register assignment.
            word=(word>>16&31)<<21|23<<11|37;overrides={11:23}
        if old==0x514:
            word=word&0xFFFF0000|((-((word&65535)^32768)+32768)&65535)
            overrides={21:2,16:14}
        if old==0x518:overrides={21:14,16:0}
        if old in (0x34,0x70,0x94,0x510):
            # Fold cached symbol addresses into HI/LO loads, not new loads.
            word&=0xFFFF0000;reloc=BINDINGS[0x8]
        elif old in (0x170,0x308):
            word&=0xFFFF0000;reloc=BINDINGS[0x120];overrides={21:6,16:6}
        elif old in BINDINGS:reloc=BINDINGS[old]
        overrides.update(REGISTERS.get(old,{}))
    gp,fp=allocation(old)
    word=rename(word,gp,fp,overrides)
    if not isinstance(item,tuple) and old==0x338:
        a,b=word>>16&31,word>>11&31
        word=word&~((31<<16)|(31<<11))|a<<11|b<<16
    return word,reloc


BRANCH_TARGETS={0x88:('after',0xA4),0xB0:('group-load',0x140),0xD8:('disabled-address',0xBC),0x18C:0x1DC,
    0x1EC:0x204,0x214:0x26C,0x294:0x2AC,0x348:0x470,0x3B0:0x3EC,
    0x3E0:0x3B8,0x444:0x3EC,0x4AC:0x4DC,0x4CC:0x4C0,0x500:0x4E4,0x518:0x530}


def normalize(raw,bindings):
    if len(raw)!=1380 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown neighbor-row source instructions/bindings')
    words=struct.unpack('>345I',raw);order=origins()
    if any(words[at//4]>>26!=12 or words[at//4]&65535!=31 for at in MASKS):
        raise ValueError('Unknown neighbor-row shift masks')
    if words[0x190//4]!=words[0x1DC//4]:raise ValueError('Null-distance copies diverged')
    at={item:i*4 for i,item in enumerate(order)}
    output,moved=[],{}
    for i,item in enumerate(order):
        old=item[1] if isinstance(item,tuple) else item
        word,reloc=form(words,item)
        if not isinstance(item,tuple) and word>>26 in (1,4,5,6,7,20,21,22,23):
            original=words[old//4]
            target=BRANCH_TARGETS.get(old,old+4+(((original&65535)^32768)-32768)*4)
            dest=at[target[1]]+4 if isinstance(target,tuple) and target[0]=='after' else at[target]
            word=word&0xFFFF0000|((dest-i*4-4)//4)&65535
        output.append(word)
        if reloc:moved[i*4]=reloc
    result=struct.pack('>336I',*output)
    if hashlib.sha256(result).hexdigest()!=NORMALIZED_SHA or len(moved)!=19:
        raise ValueError('Changed neighbor-row source-origin recipe')
    return result,moved


def private_guards(before,raw,bindings):
    normalized,moved=normalize(raw,bindings)
    old,new=struct.unpack('>345I',raw),struct.unpack('>336I',normalized)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if not before.endswith(b'\n') or any(r['filename']==source.OWNER and
            r['function']==source.FUNCTION for r in reader):
        raise ValueError('Unknown neighbor-row guard predecessor')
    order,inserted,last=origins(),set(),-2
    for i,item in enumerate(order):
        if isinstance(item,tuple):
            at=max(i,last+2);inserted.add(at);last=at
    if len(inserted)!=17 or 0 in inserted or max(inserted)>=336:
        raise ValueError('Neighbor-row insertion grouping differs')
    spec=lambda entries:';'.join(kind+':'+name for kind,name in entries) or '-'
    rows,cursor=[],0
    for i,word in enumerate(old):
        at,omitted=i*4,i*4 in REMOVED
        added=not omitted and cursor+1 in inserted
        if not omitted and cursor in inserted:raise ValueError('Unpaired neighbor-row insertion')
        rows.append(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%at,
            expected='0x%08X'%word,replacement='0x%08X'%(0 if omitted else new[cursor]),
            expected_relocations=spec(bindings.get(at,[])),
            replacement_relocations='-' if omitted else spec(moved.get(cursor*4,[])),
            note='Omit checked neighbor-row spill or redundant address/mask/copy' if omitted else
                'Normalize checked neighbor-row origin %s'%(order[cursor],),
            insert_after='0x%08X'%new[cursor+1] if added else '',
            insert_after_relocations=spec(moved.get((cursor+1)*4,[])) if added else '',
            omit='true' if omitted else 'false'))
        if not omitted:cursor+=2 if added else 1
    if cursor!=336:raise ValueError('Neighbor-row guard extent differs')
    stream=io.StringIO(newline='')
    csv.DictWriter(stream,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+stream.getvalue().encode()
