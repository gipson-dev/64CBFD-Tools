"""Alias-aware comparison of the dispatcher's nine closed temporary lifetimes."""
REGIONS=((0x58,0xAC),(0xD0,0x114),(0x11C,0x164),(0x174,0x1F8),
         (0x274,0x2C0),(0x348,0x3D0),(0x3F8,0x484),(0x494,0x520),(0x530,0x5B4))
def ex(op,a,b):
    if op=='add':
        if a==0:return b
        if b==0:return a
        a,b=sorted((a,b),key=repr)
    if isinstance(a,int) and isinstance(b,int):
        return {'add':lambda:a+b,'sub':lambda:a-b,'shl':lambda:a<<b,'or':lambda:a|b,'and':lambda:a&b}[op]()&0xffffffff
    return op,a,b

def block(words,start,end):
    r=[('GPR',i) for i in range(32)];f=[('FPR',i) for i in range(32)];r[0]=0
    mem=('initial-memory',);events=[]
    for pc in range(start,end,4):
        w=words[pc//4];op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        imm=((w&65535)^32768)-32768
        if not w:continue
        if op==0:
            if fn==0:r[rd]=ex('shl',r[rt],sa)
            elif fn in (33,35,37):r[rd]=ex({33:'add',35:'sub',37:'or'}[fn],r[rs],r[rt])
            else:raise AssertionError(hex(w))
        elif op in (9,12,13):r[rt]=ex({9:'add',12:'and',13:'or'}[op],r[rs],imm if op==9 else w&65535)
        elif op==15:r[rt]=(w&65535)<<16
        elif op in (35,36,49,43,57):
            addr=ex('add',r[rs],imm);size=1 if op==36 else 4
            if op in (43,57):
                value=f[rt] if op==57 else r[rt];events.append(('W',addr,size,value));mem=('store',mem,addr,size,value)
            else:
                value=('load',mem,addr,size);events.append(('R',addr,size,value))
                if op==49:f[rt]=value
                else:r[rt]=value
        elif op==17 and rs==4:f[rd]=r[rt]
        elif op==3:r[31]=('return-address',pc+8)
        else:raise AssertionError(hex(w))
        r[0]=0
    # T3..T5 are private to these straight-line address/argument sequences.
    # Every other GPR, all FPRs, and every ordered memory effect must agree.
    live=tuple(r[i] for i in range(32) if i not in (11,12,13)),tuple(f)
    return events,mem,live

def qualify(a,b):
    assert len(a)==len(b)==392
    covered={pc//4 for start,end in REGIONS for pc in range(start,end,4)}
    assert all(x==y for i,(x,y) in enumerate(zip(a,b)) if i not in covered)
    for start,end in REGIONS:assert block(a,start,end)==block(b,start,end),(start,end)
    # Check the ignored temporary values are dead on every successor, including
    # all twelve jump-table edges. A call kills these caller-clobbered registers.
    for words in (a,b):
        for _,end in REGIONS:
            for reg in (11,12,13):assert dead(words,end//4,reg),(end,reg)
    # A changed outgoing parameter is detected, rather than merely accepting shape.
    bad=b[:];assert bad[0x100//4]==0xafa00018;bad[0x100//4]^=4
    assert block(a,0xD0,0x114)!=block(bad,0xD0,0x114)
    return {'regions':len(REGIONS),'instructions':len(covered),'ordered_memory_events':sum(len(block(a,s,e)[0]) for s,e in REGIONS),'effective_control':True}

def dead(words,start,reg):
    pending=[(start,None)];seen=set()
    entries=tuple(v//4 for v in (0xD0,0x11C,0x16C,0x200,0x268,0x3D8,0x48C,0x528,0x260,0x5BC,0x2C8,0x328))
    while pending:
        pc,after=pending.pop()
        if (pc,after) in seen:continue
        seen.add((pc,after));w=words[pc];op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
        if op==3:
            pending.append((pc+1,()))
            continue
        if op==0:
            uses=(rt,) if fn in (0,2,3) else (rs,) if fn in (8,9) else (rs,rt)
            defs=() if fn in (8,9) else (rd,)
        elif op in (4,5,20,21):uses,defs=(rs,rt),()
        elif op in (40,41,43):uses,defs=(rs,rt),()
        elif op in (49,57):uses,defs=(rs,),()
        elif op==17:uses,defs=((rt,),()) if rs==4 else ((),(rt,)) if rs==0 else ((),())
        elif op==15:uses,defs=(),(rt,)
        else:uses,defs=(rs,),(rt,)
        if reg in uses:return False
        if reg in defs:continue
        if after is not None:pending.extend((n,None) for n in after);continue
        if op in (4,5,20,21):
            imm=((w&65535)^32768)-32768;pending.append((pc+1,(pc+2,pc+1+imm)))
        elif op==0 and fn==8:
            if rs==31:
                pending.append((pc+1,()))
                continue
            assert pc==0xC8//4;pending.append((pc+1,entries))
        else:pending.append((pc+1,None))
    return True
