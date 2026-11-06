"""Private symbolic contract comparison; not an installation or fault proof."""
from collections import Counter
import json,struct
from pathlib import Path
from tools.pad_generated_object import parse_object
C=lambda n:('C',n&0xFFFFFFFF)

def ex(op,*a):
    if op in('add','and','or','eq'):a=tuple(sorted(a,key=repr))
    if op in('add','or') and C(0) in a:return a[1] if a[0]==C(0) else a[0]
    if op=='and':
        x,k=a if a[0][0]!='C' else (a[1],a[0])
        if k==C(255) and (x[0]=='load8' or x[0]=='and' and C(255) in x[1:]):return x
    if all(isinstance(x,tuple) and x[0]=='C' for x in a):
        v=[x[1] for x in a]
        if op=='add':return C(v[0]+v[1])
        if op=='or':return C(v[0]|v[1])
        if op=='and':return C(v[0]&v[1])
        if op=='shl':return C(v[0]<<v[1])
    return (op,*a)

def bound_blob(raw,bindings,symbols=None):
    original=list(struct.unpack('>%dI'%(len(raw)//4),raw));ws=original[:];pending={}
    for at,rows in sorted(bindings.items()):
        assert len(rows)==1
        i=at//4;kind,name=rows[0];v=int(name.split('_')[1],16) if symbols is None else symbols[name]
        if kind=='R_MIPS_HI16':pending.setdefault(name,[]).append(i)
        elif kind=='R_MIPS_LO16':
            low=((original[i]&65535)^32768)-32768
            for hi in pending.pop(name,[]):
                addend=((original[hi]&65535)<<16)+low
                ws[hi]=(original[hi]&0xFFFF0000)|(((v+addend+32768)>>16)&65535)
            ws[i]=(original[i]&0xFFFF0000)|((v+low)&65535)
        else:
            assert kind=='R_MIPS_26';ws[i]=(original[i]&0xFC000000)|((v>>2)&0x3FFFFFF)
    assert not pending
    return ws

def step(w,r,f,mem,events):
    op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
    imm=((w&65535)^32768)-32768
    if op==0:
        if not w:pass
        elif fn in(0,3):r[rd]=ex('shl' if fn==0 else 'sra',r[rt],C(sa))
        elif fn in(33,35,36,37,42):r[rd]=ex({33:'add',35:'sub',36:'and',37:'or',42:'slt'}[fn],r[rs],r[rt])
        else:raise AssertionError(('R',hex(w)))
    elif op==15:r[rt]=C((w&65535)<<16)
    elif op in(9,12):r[rt]=ex('add' if op==9 else 'and',r[rs],C(imm if op==9 else w&65535))
    elif op in(32,33,35,36,37,49,40,41,43):
        addr=ex('add',r[rs],C(imm));sizes={32:1,33:2,35:4,36:1,37:2,49:4,40:1,41:2,43:4};size=sizes[op]
        if op in(40,41,43):
            value=ex('and',r[rt],C((1<<(8*size))-1)) if size<4 else r[rt]
            events.append(('W',addr,size,value));mem=('store',mem,addr,size,value)
        else:
            value=('load%d'%(size*8),mem,addr)
            if op in(32,33):value=ex('sext%d'%(size*8),value)
            if op==49:f[rt]=value
            else:r[rt]=value
            events.append(('R',addr,size))
    elif op==17:
        fmt=rs;ft=rt;fs=rd;fd=sa
        if fmt==4:f[fs]=r[rt]
        elif fmt==20 and fn==32:f[fd]=ex('float_s32',f[fs])
        else:
            assert fmt==16 and fn==1,hex(w)
            f[fd]=ex('float_sub',f[fs],f[ft])
    else:raise AssertionError(('opcode',hex(w)))
    r[0]=C(0);return mem

def paths(words):
    r=[('arg',i) for i in range(32)];r[0]=C(0);f=[('fp',i) for i in range(32)]
    pending=[(0,r,f,('memory',),[],[],[],[])];results=[];states=0
    while pending:
        pc,r,f,mem,events,calls,branches,pre_reads=pending.pop()
        w=words[pc//4];op=w>>26;states+=1
        if op in(4,20):
            cond=ex('eq',r[w>>21&31],r[w>>16&31]);dest=pc+4+4*(((w&65535)^32768)-32768)
            assert dest>pc
            for take in(True,False):
                rr,ff,ev=r[:],f[:],events[:];mm=mem
                if take or op!=20:mm=step(words[pc//4+1],rr,ff,mm,ev)
                pending.append((dest if take else pc+8,rr,ff,mm,ev,calls[:],branches+[(cond,take)],pre_reads[:]))
            continue
        if op==3:
            target=(0x10000000)|((w&0x3FFFFFF)<<2)
            mem=step(words[pc//4+1],r,f,mem,events)
            if target==0x1505A630:
                args=(f[12],f[14],r[6]);idx=0
                # All ordinary data reads precede the saved-byte write. They
                # commute before that write; compare their complete multiset.
                writes=[e for e in events if e[0]=='W'];assert len(writes)==2
                assert events[0][0]=='W' and events[-1][0]=='W' and all(e[0]=='R' for e in events[1:-1])
                pre_reads=[e for e in events if e[0]=='R'];events=writes
            else:
                assert target==0x15056A00
                args=(r[4],ex('and',r[5],C(255)),ex('and',r[6],C(255)));idx=1
            calls.append((target,args));events.append(('CALL',target,args))
            mem=('provider-effects',idx,mem,args)
            for reg in(1,2,3,*range(4,16),24,25):r[reg]=('clobber',idx,reg)
            f[:20]=[('fp-clobber',idx,i) for i in range(20)];r[2]=('answer',idx)
            pc+=8
            pending.append((pc,r,f,mem,events,calls,branches,pre_reads));continue
        if op==0 and w&63==8:
            assert w>>21&31==31
            mem=step(words[pc//4+1],r,f,mem,events)
            results.append(dict(memory=mem,events=events,calls=calls,branches=branches,pre_reads=sorted(pre_reads,key=repr),stack=r[29],return_address=r[31]));continue
        mem=step(w,r,f,mem,events)
        pending.append((pc+4,r,f,mem,events,calls,branches,pre_reads))
    return results,states

def key(w):
    op=w>>26
    if op==0:mask=(31<<21)|(31<<16)|(31<<11)
    elif op==17:
        fmt=w>>21&31
        mask=(31<<16)|(31<<11) if fmt==4 else (31<<11)|(31<<6) if fmt==20 else (31<<16)|(31<<11)|(31<<6)
    elif op==3:mask=0
    else:mask=(31<<16) if op==15 else (31<<21)|(31<<16)
    return w&~mask


def prove(original,raw):
    a,sa=paths(original);b,sb=paths(raw)
    if a!=b:raise ValueError('Heading turn symbolic values, calls, branches or memory differ')
    ka,kb=Counter(map(key,original)),Counter(map(key,raw))
    if ka-kb!=Counter({0x25:1}) or kb-ka:raise ValueError('Heading turn opcode/immediate inventory differs beyond one copy')
    if not all(w>>21&31==0 or w>>16&31==0 for ws in(original,raw) for w in ws if w>>26==0 and w&63==37):raise ValueError('Heading turn OR is not a copy')
    if (len(original),len(raw),sa,sb,len(a))!=(68,67,78,77,4):raise ValueError('Heading turn symbolic path geometry changed')
    return dict(original_states=sa,raw_states=sb,paths=len(a),one_OR_copy=True,ordinary_first_reads_commute_before_saved_byte_store=True)
