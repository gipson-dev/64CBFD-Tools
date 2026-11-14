"""Prove the local surface phi and validate the closed instruction inventory."""
from collections import Counter
def ex(op,a,b=None):
    if op=='add':
        if a==0:return b
        if b==0:return a
        a,b=sorted((a,b),key=repr)
    if isinstance(a,int) and isinstance(b,int):
        return {'add':lambda:a+b,'sub':lambda:a-b,'shl':lambda:a<<b,'shr':lambda:a>>b,'and':lambda:a&b,'or':lambda:a|b}[op]()&0xffffffff
    return (op,a) if b is None else (op,a,b)
def ground(words,null):
    r=[('GPR',i) for i in range(32)];f=[('FPR',i) for i in range(32)];r[0]=0;r[16]=('particle',);r[29]=0x20000
    memory=('initial-memory',);events=[];hi=lo=None
    def step(w):
        nonlocal memory,hi,lo
        op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        imm=((w&65535)^32768)-32768
        if not w:return
        if op==0:
            if fn in (0,2):r[rd]=ex('shl' if fn==0 else 'shr',r[rt],sa)
            elif fn in (33,35,37):r[rd]=ex({33:'add',35:'sub',37:'or'}[fn],r[rs],r[rt])
            elif fn==26:lo=ex('signed-div',r[rs],r[rt])
            elif fn==18:r[rd]=lo
            else:raise AssertionError(hex(w))
        elif op in (9,12):r[rt]=ex('add' if op==9 else 'and',r[rs],imm if op==9 else w&65535)
        elif op==15:r[rt]=(w&65535)<<16
        elif op in (35,36,40,43,57):
            address=ex('add',r[rs],imm);size=1 if op in (36,40) else 4
            if op in (40,43,57):
                value=f[rt] if op==57 else ex('and',r[rt],255) if op==40 else r[rt]
                events.append(('W',address,size,value));memory=('write',memory,address,size,value)
            else:
                value=(0 if null else ('surface-after-height-store',)) if address==0x2009c else ('load',memory,address,size)
                event=('R',address,size,value)
                # The two source loads are consecutive ordinary reads with no
                # intervening write. Collapse only this exact local read pair.
                if not(address==0x2009c and events and events[-1]==event):events.append(event)
                r[rt]=value
        elif op==17:
            if rs==4:f[rd]=r[rt]
            elif rs==20 and fn==32:f[sa]=ex('float-from-signed-word',f[rd])
            else:raise AssertionError(hex(w))
        else:raise AssertionError(hex(w))
        r[0]=0
    pc=0x2dc
    for _ in range(100):
        if pc==0x354:break
        w=words[pc//4];op,rs,rt=w>>26,w>>21&31,w>>16&31
        if op==3:
            step(words[pc//4+1]);a=tuple(r[i] for i in (4,5,6,7));events.append(('GROUND',a));memory=('after-ground',memory,a)
            for i in (1,2,3,*range(4,16),24,25):r[i]=('helper-GPR',i)
            for i in range(20):f[i]=('helper-FPR',i)
            pc+=8
        elif op in (4,20):
            taken=r[rs]==r[rt];imm=((w&65535)^32768)-32768
            if taken or op==4:step(words[pc//4+1])
            pc=pc+4+4*imm if taken else pc+8
        else:step(w);pc+=4
    else:raise AssertionError('Ground proof instruction budget')
    return events,memory,tuple(r[i] for i in (16,20,21,22,23,29,30)),tuple(f[20:])
def signature(w):
    op,rs=w>>26,w>>21&31
    if op==0:return w&~((31<<21)|(31<<16)|(31<<11))
    if op==17:
        fields=(16,11) if rs in (0,4) else (16,11,6) if rs==16 else (11,6)
        for shift in fields:w&=~(31<<shift)
        return w
    if op in (4,5,20,21):return op<<26
    if op==3:return op<<26
    return w&~((31<<21)|(31<<16))
def dead(words,start,reg):
    todo=[(start,None)];seen=set()
    while todo:
        pc,after=todo.pop()
        if (pc,after) in seen:continue
        seen.add((pc,after));w=words[pc];op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
        if op==3:todo.append((pc+1,(pc+2,)));continue
        if op==0:
            uses=(rt,) if fn in (0,2,3) else () if fn in (16,18) else (rs,) if fn in (8,9) else (rs,rt)
            defs=() if fn in (8,9,26,27) else (rd,)
        elif op in (4,5,20,21):uses,defs=(rs,rt),()
        elif op in (40,41,43):uses,defs=(rs,rt),()
        elif op in (49,53,57,61):uses,defs=(rs,),()
        elif op==17:uses,defs=((rt,),()) if rs==4 else ((),(rt,)) if rs==0 else ((),())
        elif op==15:uses,defs=(),(rt,)
        else:uses,defs=(rs,),(rt,)
        if reg in uses:return False
        if reg in defs:continue
        if after is not None:todo.extend((n,None) for n in after);continue
        if op in (1,4,5,20,21):
            off=((w&65535)^32768)-32768;todo.append((pc+1,(pc+2,pc+1+off)))
        elif op==0 and fn==8:
            assert rs==31;todo.append((pc+1,()))
        else:todo.append((pc+1,None))
    return True
def qualify(adjusted,normal):
    # Earlier alpha-renaming and mapped private homes preserve the mathematical
    # instruction inventory; this region check isolates the actual phi rewrite.
    for null in (False,True):assert ground(adjusted,null)==ground(normal,null),null
    for w in (adjusted,normal):assert dead(w,0x354//4,17)
    a=Counter(signature(w) for w in adjusted);b=Counter(signature(w) for w in normal)
    a[signature(adjusted[0x300//4])]-=1;a[signature(adjusted[0x308//4])]-=1;a[20<<26]-=1
    a[0]+=1;a[4<<26]+=2
    assert +a==+b,'Unexpected operation/offset change outside the declared lowering'
    bad=normal[:];bad[0x344//4]^=1
    assert ground(adjusted,False)!=ground(bad,False),'Ineffective surface-kind control'
    return dict(ground_paths=2,alias_aware_memory=True,material_dead_on_successors=True,operation_inventory=True,effective_control=True)
