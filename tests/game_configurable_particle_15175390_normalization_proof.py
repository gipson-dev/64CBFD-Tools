"""Check the closed operation inventory and the three local control lowerings.

The surface proof compares symbolic memory and saved state. The query proof
executes both actual branch/delay streams, with arbitrary provider state-home
changes. Neither claims raw instruction-fault or portable uninitialized-C parity.
"""
from collections import Counter
from tools.tests.game_particle_constructor_15174bf0_proof import ex,dead

def key(w):
    def reg(r):return r if r in (0,16,17,18,19,20,21,22,23,29,30,31) else 'T'
    op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=w&65535
    if not w:return ('nop',)
    if op==0:
        if fn==13:return op,fn,w>>6
        if fn in (0,2,3):return op,fn,reg(rt),reg(rd),sa
        if fn in (16,18):return op,fn,reg(rd)
        if fn in (26,27):return op,fn,reg(rs),reg(rt)
        return op,fn,reg(rs),reg(rt),reg(rd)
    if op==3:return op,w&0x3ffffff
    if op in (4,5,20,21):return (4 if op in (4,20) else 5),reg(rs),reg(rt)
    if op==1:return op,reg(rs),rt
    if op in (6,7,22,23):return op%16,reg(rs)
    if op==15:return op,reg(rt),imm
    if op in (9,10,11,12,13):return op,reg(rs),reg(rt),imm
    if op in (33,35,36,37,40,41,43,49,53,55,57,61,63):return op,reg(rs),rt if op in (49,57,53,61) else reg(rt),imm
    if op==17:
        if rs in (0,4):return op,rs,reg(rt),rd
        if rs in (16,20):return op,rs,rt,rd,sa,fn
    raise AssertionError(hex(w))

def surface(words,null):
    r=[('GPR',i) for i in range(32)];r[0]=0;r[16]=('particle',);r[29]=0x20000
    memory=('initial-memory',);events=[];lo=None
    def step(w):
        nonlocal memory,lo
        op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        imm=((w&65535)^32768)-32768
        if not w:return
        if op==0:
            if fn in (0,2):r[rd]=ex('shl' if fn==0 else 'shr',r[rt],sa)
            elif fn in (33,35,37):r[rd]=ex({33:'add',35:'sub',37:'or'}[fn],r[rs],r[rt])
            elif fn==26:lo=ex('signed-div',r[rs],r[rt])
            elif fn==18:r[rd]=lo
            else:raise AssertionError(hex(w))
        elif op in (9,12,13):r[rt]=ex({9:'add',12:'and',13:'or'}[op],r[rs],imm if op==9 else w&65535)
        elif op==15:r[rt]=(w&65535)<<16
        elif op in (33,35,36,40,41,43):
            address=ex('add',r[rs],imm);size=1 if op in (36,40) else 2 if op in (33,41) else 4
            if op in (40,41,43):
                value=ex('and',r[rt],(1<<(8*size))-1) if size<4 else r[rt]
                events.append(('W',address,size,value));memory=('write',memory,address,size,value)
            else:
                value=(0 if null else ('surface-reference',)) if address==0x20080 else ('load',memory,address,size)
                event=('R',address,size,value)
                # Only coalesce the repeated ordinary surface-local read; no
                # intervening write/provider exists between these two loads.
                if not(address==0x20080 and events and events[-1]==event):events.append(event)
                r[rt]=value
        else:raise AssertionError(hex(w))
        r[0]=0
    pc=0x50c
    for _ in range(100):
        if pc==0x57c:break
        w=words[pc//4];op,rs,rt=w>>26,w>>21&31,w>>16&31
        if op in (4,20):
            taken=r[rs]==r[rt];imm=((w&65535)^32768)-32768
            if taken or op==4:step(words[pc//4+1])
            pc=pc+4+4*imm if taken else pc+8
        else:step(w);pc+=4
    else:raise AssertionError('Surface proof budget')
    return events,memory,tuple(r[i] for i in (16,17,18,19,20,21,22,23,29,30))

def query(words,normal,before,after,grounded,remainder):
    r=[0x87650000+i for i in range(32)];f=[('FPR',i) for i in range(32)]
    r[0]=0;r[3]=r[4]=remainder&0xffffffff;r[8]=before;r[16]=0x50000;r[19]=0xfffffffd;r[20]=44;r[21]=5;r[29]=0x20000;r[30]=grounded
    mem={0x200f0:before,0x200c8:17,0x200c4:0x80000001};calls=[];stores=[]
    def step(w):
        op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
        imm=((w&65535)^32768)-32768
        if not w:return
        if op==0 and fn in (33,35,37):r[rd]=({33:lambda:r[rs]+r[rt],35:lambda:r[rs]-r[rt],37:lambda:r[rs]|r[rt]}[fn]())&0xffffffff
        elif op==9:r[rt]=(r[rs]+imm)&0xffffffff
        elif op==35:r[rt]=mem[(r[rs]+imm)&0xffffffff]
        elif op==57:
            address=(r[rs]+imm)&0xffffffff;mem[address]=f[rt];stores.append((address,f[rt]))
        elif op==17:
            if rs==4:f[rd]=r[rt]
            elif rs==20 and fn==32:f[w>>6&31]=('float32-signed',f[rd])
            else:raise AssertionError(hex(w))
        else:raise AssertionError(hex(w))
        r[0]=0
    pc,stop=(0x21c,0x264) if normal else (0x218,0x268)
    for _ in range(100):
        if pc==stop:break
        w=words[pc//4];op,rs,rt=w>>26,w>>21&31,w>>16&31
        if op==3:
            step(words[pc//4+1]);calls.append((w&0x3ffffff,tuple(r[i] for i in (4,5,6,7))))
            # A real provider can mutate homes: keep the independent reload
            # following it, including when it changes zero to nonzero or back.
            mem[0x200f0]=after;mem[0x200c4]=123;mem[0x200c8]=456
            for i in (1,2,3,*range(4,16),24,25):r[i]=0xa5000000+i
            r[2]=0x12345;pc+=8
        elif op in (1,4,20):
            if op==1:
                assert rt==1;taken=r[rs]<0x80000000
            else:taken=r[rs]==r[rt]
            imm=((w&65535)^32768)-32768
            if taken or op!=20:step(words[pc//4+1])
            pc=pc+4+4*imm if taken else pc+8
        else:step(w);pc+=4
    else:raise AssertionError('Query proof budget')
    assert bool(calls)==(before==0 or grounded!=0)
    assert r[10 if normal else 9]==(after if calls else before)
    return calls,stores,mem,tuple(r[i] for i in (16,17,18,19,20,21,22,23,29,30))

def qualify(raw,normal):
    from tools.experiments.game_configurable_particle_15175390_normalization import SPECIALS,FIELDS,OPCODES,ORDER,TEMP_REGS
    assert len(raw)==len(normal)==370 and sorted(ORDER)==list(range(0,1480,4))
    for changes in FIELDS.values():
        for old,new in changes.values():assert old in TEMP_REGS and new in TEMP_REGS
    assert OPCODES=={0x23c:(20,4),0x52c:(20,4)}
    a=Counter(map(key,raw));b=Counter(map(key,normal))
    assert Counter(k for k in a if (a-b)[k]) # Explicit nonidentity control inventory.
    expected=Counter(key(raw[pc//4]) for pc in SPECIALS)
    assert a-b==expected and b-a==Counter({('nop',):1,(4,0,0):3})
    assert raw[0x1f0//4]==0x00602025 and raw[0x218//4]==0x00958821
    # Retail schedules the first state load before the remaining division
    # checks. No provider or memory write separates it from this query gate.
    assert raw[0x220//4]==normal[0x1f4//4]==0x8fa800f0
    # The sole consumed copy is v1 -> a0 -> add. v1 is not redefined;
    # a0 is dead after the add until the unrelated query argument write.
    assert all(w>>11&31!=3 for w in raw[0x1f4//4:0x218//4] if w>>26==0 and w&63 not in (13,26))
    assert dead(raw,0x21c//4,4)
    assert normal[0x21c//4]==0x00758821
    for null in (False,True):assert surface(raw,null)==surface(normal,null),null
    bad=normal[:];bad[0x56c//4]^=1
    assert surface(raw,False)!=surface(bad,False),'Ineffective surface kind-offset control'
    cases=0
    for before in (0,1,0x80000000):
        for after in (0,1,0xffffffff):
            for ground in (0,1):
                for rem in (-7,0,9):
                    assert query(raw,False,before,after,ground,rem)==query(normal,True,before,after,ground,rem),(before,after,ground,rem)
                    cases+=1
    bad=normal[:];bad[0x240//4]^=1<<21
    try:query(bad,True,1,0,0,0)
    except (AssertionError,KeyError):pass
    else:raise AssertionError('Ineffective query register control')
    return dict(operation_inventory=True,saved_and_float_registers_preserved=True,surface_symbolic_paths=2,query_branch_cases=cases,second_remainder_copy_dead=True,effective_controls=2,raw_fault_order_claimed=False,portable_unwritten_surface_claimed=False)
