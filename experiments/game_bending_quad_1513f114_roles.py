"""Closed FP-role/spill schedules, with ordered public-expression equivalence."""
import struct,hashlib
def fp(fn,d,s,t=0):return 0x46000000|(t<<16)|(s<<11)|(d<<6)|fn
def mem(op,t,s,i):return(op<<26)|(s<<21)|(t<<16)|(i&65535)
def mfc(t,s):return 0x44000000|(t<<16)|(s<<11)
def upper_schedule():
    # The third and fourth corners share an upper*sine value. Keep it in
    # F12, spill the third offset, and retire cosine F0 after upper*cosine.
    return [
        fp(2,12,10,4),fp(0,6,14,12),fp(7,8,6),fp(2,4,8,20),mem(57,8,29,0x34),
        mem(49,10,16,0x34),fp(0,6,10,4),fp(13,8,6),mfc(10,8),0,mem(41,10,11,0x20),
        mem(49,10,29,0x78),mem(35,14,29,0x8C),fp(2,4,10,0),fp(1,0,14,12),mem(57,4,29,0x40),
        mem(49,6,16,0x38),fp(0,8,6,4),fp(1,10,8,16),fp(13,6,10),mfc(13,6),0,mem(41,13,14,0x22),
        mem(49,8,29,0x34),mem(49,4,16,0x3C),mem(35,25,29,0x8C),fp(2,10,8,18),fp(1,6,4,10),
        fp(2,10,0,20),fp(13,8,6),mfc(24,8),0,mem(41,24,25,0x24),mem(35,8,29,0x8C),mem(41,0,8,0x26),
        mem(49,4,16,0x34),mem(35,11,29,0x8C),fp(0,6,4,10),fp(13,8,6),mfc(10,8),0,mem(41,10,11,0x30),
        mem(49,10,29,0x40),mem(49,4,16,0x38),mem(35,14,29,0x8C),fp(0,6,4,10),fp(0,8,6,16),fp(2,6,0,18),
    ]
def expression_trace(words):
    # This proof's domain is valid output/actor RAM disjoint from compiler
    # private slots. Guest stack aliases are checked separately against
    # the complete normalized retail machine, including physical writes.
    f=[('fp',i)for i in range(32)];r=[('gpr',i)for i in range(32)];r[0]=0;r[11]=('cursor',)
    for i,name in((0,'cosine'),(4,'sine'),(10,'upper'),(14,'widthCos'),(16,'widthSin'),(18,'forward'),(20,'side')):f[i]=('input',name)
    initial_f=f[:];initial_r=r[:];private={0x78:('input','upper'),0x74:('input','sine'),0x8C:('cursor',),0x88:('first',)};events=[]
    def value(op,a,b=None):
        if op in('add','mul')and repr(a)>repr(b):a,b=b,a
        return(op,a)if b is None else(op,a,b)
    for w in words:
        if w==0:continue
        op,s,t,d,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;i=((w&65535)^32768)-32768
        if op==17 and s==16:
            if fn in(0,1,2):f[fd]=value({0:'add',1:'sub',2:'mul'}[fn],f[d],f[t])
            elif fn in(7,13):f[fd]=value('neg'if fn==7 else'trunc',f[d])
            else:raise ValueError('Foreign FP operation in upper-corner schedule')
        elif op==17 and s==0:r[t]=f[d]
        elif op==49:
            if s==29:
                if i not in private:raise ValueError('Uninitialized private FP spill read')
                f[t]=private[i]
            elif s==16:f[t]=('actor',i,len(events))
            else:raise ValueError('Foreign FP load base')
        elif op==57:
            if s!=29 or i not in(0x30,0x34,0x38,0x3C,0x40,0x44):raise ValueError('Foreign private spill destination')
            private[i]=f[t]
        elif op==35:
            if s!=29 or i!=0x8C:raise ValueError('Foreign integer load in upper-corner schedule')
            r[t]=private[i]
        elif op==41:
            if r[s]!=('cursor',):raise ValueError('Changed upper-corner output base')
            events.append((i,0 if r[t]==0 else('low16',r[t])))
        else:raise ValueError('Foreign instruction in upper-corner schedule')
    if tuple(i for i,v in events)!=(0x20,0x22,0x24,0x26,0x30):raise ValueError('Changed upper-corner store order')
    if f[20:]!=initial_f[20:]or r[16:24]!=initial_r[16:24]:raise ValueError('Changed preserved-register lifetime')
    # Common following code truncates/stores Y3 from F8, then subtracts
    # F6 from the freshly reloaded center Z. T6 is its pending Y pointer.
    return(events,f[6],f[8],r[14],private[0x88],private[0x8C])
def prove_upper(before,after):
    if len(before)!=48 or len(after)!=48 or expression_trace(before)!=expression_trace(after):raise ValueError('Upper-corner public expression graph changed')
    return dict(words=48,ordered_stores=5,live_FP_outputs=[6,8],live_output_pointer=14,preserved_FP_registers=list(range(20,32)),preserved_GPRs=list(range(16,24)),private_spills_only=True,FP_add_mul_commutation_only=True,no_reassociation=True,guest_private_aliases_separate=True)
def rename_fp(w,mapping):
    op,rs=w>>26,w>>21&31
    if op in(49,57):return(w&~(31<<16))|(mapping.get(w>>16&31,w>>16&31)<<16)
    if op==17 and rs in(0,4):return(w&~(31<<11))|(mapping.get(w>>11&31,w>>11&31)<<11)
    if op==17 and rs==16:
        for shift in(6,11,16):w=(w&~(31<<shift))|(mapping.get(w>>shift&31,w>>shift&31)<<shift)
    return w
def commute_mul(w):
    if w>>26!=17 or w>>21&31!=16 or w&63!=2:raise ValueError('Changed expected floating multiply')
    return(w&~(31<<11|31<<16))|((w>>11&31)<<16)|((w>>16&31)<<11)
def normalize_words(raw):
    w=list(struct.unpack('>231I',raw))
    for i in(23,24,27,28):
        if w[i]>>21&31!=29 or w[i]&65535 not in(0x38,0x3C):raise ValueError('Changed copy spill role')
        w[i]=(w[i]&0xFFFF0000)|((w[i]&65535)+8)
    for i in range(43,87):w[i]=rename_fp(w[i],{14:18,18:16,16:14})
    for i in(59,78):w[i]=commute_mul(w[i])
    w[85],w[86]=w[86],w[85]
    if w[161:164]!=[mem(49,10,29,0x78),mem(49,4,29,0x74),mem(35,11,29,0x8C)]:raise ValueError('Changed upper-corner input boundary')
    new=upper_schedule();prove_upper(w[164:212],new);w[164:212]=new
    return struct.pack('>231I',*w)
