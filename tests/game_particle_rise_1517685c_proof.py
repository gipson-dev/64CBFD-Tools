"""Closed operation inventory, constant reuse and the two return lowerings."""
from collections import Counter

def key(w):
    op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=w&65535
    reg=lambda r:r if r in (0,16,17,18,19,20,21,22,23,29,30,31)else'T'
    if not w:return('nop',)
    if op==0:
        if fn in(0,2,3):return op,fn,reg(rt),reg(rd),sa
        if fn in(16,18):return op,fn,reg(rd)
        if fn==27:return op,fn,reg(rs),reg(rt)
        return op,fn,reg(rs),reg(rt),reg(rd)
    if op==17:
        if rs in(0,4):return op,rs,reg(rt),'F'
        if rs==8:return op,rs,rt&1
        return op,rs,fn
    if op in(4,5,20,21):return op%16,reg(rs),reg(rt)
    if op==3:return op,w&0x3ffffff
    if op==15:return op,reg(rt),imm
    if op in(49,57):return op,reg(rs),'F',imm
    return op,reg(rs),reg(rt),imm

def epilogue(words,start,le):
    r=[0]*32;r[16]=0x50000;r[29]=0x20000;r[31]=0x12340000
    m={0x20018:0x76543210,0x2001c:0xdead0000};f=[0x3fa00000]*32
    def step(w):
        op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63;imm=((w&65535)^32768)-32768
        if not w:return
        if op==35:r[rt]=m[r[rs]+imm]
        elif op==9:r[rt]=(r[rs]+imm)&0xffffffff
        elif op==57:m[r[rs]+imm]=f[rt]
        else:raise AssertionError(hex(w))
    pc=start
    for _ in range(20):
        if pc==0xdead0000:return m,(r[16],r[29],r[31])
        w=words[pc//4];op=w>>26
        if op==17 and w>>21&31==8:
            rt=w>>16&31;assert rt in(0,2);taken=not le
            if taken or rt==0:step(words[pc//4+1])
            pc=pc+4+4*(((w&65535)^32768)-32768)if taken else pc+8
        elif op==4:
            assert w>>21&31==w>>16&31==0;step(words[pc//4+1]);pc=pc+4+4*(((w&65535)^32768)-32768)
        elif op==0 and w&63==8:
            target=r[w>>21&31];step(words[pc//4+1]);pc=target
        else:step(w);pc+=4
    raise AssertionError('Return proof exceeded bounded window')

def prove(raw,normal,order,refs,nrefs):
    assert len(raw)==len(normal)==len(order)==202 and sorted(order)==list(range(0,808,4))
    assert raw[:4]==normal[:4] and raw[-5:]==normal[-5:]
    # The active marker's literal one also supplies the first switch compare.
    # No instruction between that definition and comparison writes V1.
    assert raw[0x40//4]==0x24010001 and normal[0x30//4]==0x24030001
    assert normal[0x48//4]>>16&31==3
    for pc in range(0x34,0x48,4):
        w=normal[pc//4];op=w>>26
        if op==0:assert w>>11&31!=3
        elif op in(9,15,33,35,36):assert w>>16&31!=3
        else:assert op in(4,40)
    rewritten=raw[:];rewritten[0x40//4]=0x8fbf001c;assert raw[0x1c4//4]==0;rewritten[0x1c4//4]=0x8fbf001c
    assert Counter(map(key,rewritten))==Counter(map(key,normal)), 'Non-return operation inventory changed'
    calls=lambda mapping:[name for pc,rows in sorted(mapping.items())for kind,name in rows if kind=='R_MIPS_26']
    assert calls(refs)==calls(nrefs) and Counter(v for rows in refs.values()for v in rows)==Counter(v for rows in nrefs.values()for v in rows)
    for le in(False,True):
        a=epilogue(raw,0x1c0,le);b=epilogue(normal,0x1bc,le);assert a==b,(le,a,b)
        assert a[1]==(0x76543210,0x20020,0xdead0000)
    assert epilogue(raw,0x228,True)==epilogue(normal,0x224,True)
    return dict(permuted_source_words=202,constant_reuse=True,extra_return_loads=2,return_paths=3,non_return_inventory_closed=True,named_call_order_preserved=True)
