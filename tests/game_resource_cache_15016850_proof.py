"""Relational transfer proof for the split integer bound and loop induction."""

def add(a,b):
    if isinstance(a,int)and isinstance(b,int):return(a+b)&0xffffffff
    if a==0:return b
    if b==0:return a
    return('ADD',*sorted((a,b),key=repr))

def paths(words,start,stop,bound_register):
    r=[('R',i)for i in range(32)];r[0]=0;r[29]=('SP',0);r[20]=add(r[29],80)
    r[18],r[19],r[21],r[22]=0x800be590,0x800d20fc,0x800be5a8,0x800be598
    states=[(start,r,[],{})];answers={};steps=0
    def execute(w,r,trace):
        if not w:return
        op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=((w&65535)^32768)-32768
        if op==0:
            if fn==0:r[rd]=('SHL',r[rt],sa)
            elif fn==33:r[rd]=add(r[rs],r[rt])
            elif fn==35:r[rd]=('SUB',r[rs],r[rt])
            elif fn==37:assert rs==0 or rt==0;r[rd]=r[rt]if rs==0 else r[rs]
            else:raise AssertionError(hex(w))
        elif op==9:r[rt]=add(r[rs],imm)
        elif op==10:r[rt]=('SLT',r[rs],imm)
        elif op==15:r[rt]=(w&65535)<<16
        elif op in(35,36,40,41,43):
            size={35:4,36:1,40:1,41:2,43:4}[op];address=add(r[rs],imm)
            if op in(35,36):
                value=('READ',len(trace),address,size);trace.append(('READ',address,size));r[rt]=value
            else:trace.append(('WRITE',address,size,r[rt]))
        else:raise AssertionError(hex(w))
        r[0]=0
    while states:
        pc,r,trace,facts=states.pop();steps+=1;assert steps<200
        if pc==stop:
            key=tuple(sorted(facts.items(),key=repr));assert key not in answers
            answers[key]=(trace,r[16:24],r[29],r[6],r[bound_register]);continue
        w=words[pc//4];op,rs,rt=w>>26,w>>21&31,w>>16&31
        if op in(4,5,20):
            predicate=('EQ',*sorted((r[rs],r[rt]),key=repr));fixed=r[rs]==r[rt]if r[rs]==r[rt]or isinstance(r[rs],int)and isinstance(r[rt],int)else None
            choices=(facts[predicate],)if predicate in facts else(fixed,)if fixed is not None else(False,True)
            for eq in choices:
                nr,nt,nf=r[:],trace[:],facts.copy()
                if fixed is None:nf[predicate]=eq
                taken=eq if op in(4,20)else not eq
                if taken or op!=20:execute(words[pc//4+1],nr,nt)
                dest=pc+4+4*(((w&65535)^32768)-32768)if taken else pc+8
                states.append((dest,nr,nt,nf))
        elif op==3:
            execute(words[pc//4+1],r,trace);target=0x10000000|((w&0x3ffffff)<<2)
            assert target==0x1502b7f0
            trace.append(('CALL',target,*r[4:8]));epoch=len(trace)
            for reg in(1,2,3,*range(4,16),24,25):r[reg]=('CALLER',epoch,reg)
            r[31]=pc+8;states.append((pc+8,r,trace,facts))
        else:execute(w,r,trace);states.append((pc+4,r,trace,facts))
    return answers

def prove(raw,normal):
    assert len(raw)==81 and len(normal)==84
    # Prefix, deduplication, scalar addresses and private homes are identical.
    assert raw[:0x40//4]==normal[:0x40//4]
    assert raw[0x40//4]&0xffff0000==normal[0x40//4]&0xffff0000==0x18c00000
    target=lambda w,pc:pc+4+4*(((w&65535)^32768)-32768)
    assert target(raw[0x40//4],0x40)==0x11c and target(normal[0x40//4],0x40)==0x128
    assert raw[0x44//4:0xa8//4]==normal[0x44//4:0xa8//4]
    a=paths(raw,0xa8,0x10c,13);b=paths(normal,0xa8,0x118,3)
    assert a==b and len(a)==5
    # The equal bound/offset makes the original signed loop predicate equal.
    assert raw[0x10c//4]==normal[0x118//4]==0x26310030
    assert raw[0x110//4]==0x022d082a and normal[0x11c//4]==0x0223082a
    assert raw[0x114//4]&0xffff0000==normal[0x120//4]&0xffff0000==0x54200000
    assert target(raw[0x114//4],0x114)==target(normal[0x120//4],0x120)==0x64
    assert raw[0x118//4]==normal[0x124//4]==0x8e6e0000
    assert raw[0x11c//4:]==normal[0x128//4:]
    return dict(transfer_paths=5,ordered_access_and_call_traces=True,live_loop_state=True,original_saved_homes=True,epilogue_exact=True,full_fault_state_claimed=False)

def main():
    import json
    from tools.experiments import game_resource_cache_15016850_match as source
    from tools.experiments.game_paired_ground_constructor_match import payload
    raw,refs=payload(source.OUT/'selected.o',source.NAME);normal,nrefs=source.normalize(raw,refs)
    a,b=source.bound(raw,refs),source.bound(normal,nrefs);report=prove(a,b)
    for pc,word in((0xe8,b[0xe8//4]&~(31<<21)),(0xf0,b[0xf0//4]^(1<<6)),(0x100,b[0x100//4]^(1<<6))):
        changed=b[:];assert changed[pc//4]!=word;changed[pc//4]=word
        try:prove(a,changed)
        except AssertionError:pass
        else:raise AssertionError('Altered proof control accepted')
    report['proof_controls']=3
    (source.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
