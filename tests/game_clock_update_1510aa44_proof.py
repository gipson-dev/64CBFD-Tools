"""Whole-stream equality outside a commutative branch and closed FPR cycle."""
import json,struct

def fp(w):
    op,fmt,fn=w>>26,w>>21&31,w&63
    if op==49:return (),((16,w>>16&31),)
    if op==57:return ((16,w>>16&31),),()
    if op==17:
        if fmt==4:return (),((11,w>>11&31),)
        if fmt==0:return ((11,w>>11&31),),()
        assert fmt in(16,20)
        reads=((11,w>>11&31),)
        if fn not in(7,32):reads+=((16,w>>16&31),)
        return reads,((6,w>>6&31),)
    return (),()

def prove(raw,normal,refs):
    assert len(raw)==len(normal)==229
    edge=0x2b8//4;a,b=raw[edge],normal[edge]
    assert a>>26==b>>26==20 and a&65535==b&65535
    assert (a>>21&31,a>>16&31)==(b>>16&31,b>>21&31)
    assert raw[:edge]==normal[:edge]and raw[edge+1:0x300//4]==normal[edge+1:0x300//4]
    mapping={};edits=0
    for i in range(0x300//4,229):
        a,b=raw[i],normal[i];reads,writes=fp(a);mask=0
        for shift,old in reads+writes:
            new=b>>shift&31;assert mapping.setdefault(old,new)==new;mask|=31<<shift
        assert a&~mask==b&~mask
        edits+=a!=b
    changed={a:b for a,b in mapping.items()if a!=b}
    assert changed=={8:6,10:8,16:10,6:4,18:16,4:18}
    assert set(changed)==set(changed.values())and all(r<20 for r in changed)
    assert mapping[0]==0 and mapping[2]==2 and edits==9
    assert not any(pc>=0x300 and any(kind!='R_MIPS_26'for kind,_ in rows)for pc,rows in refs.items())
    # Every renamed value is defined before use along all three tail paths.
    # Opaque callees may clobber all caller FPRs; subsequent uses must be redefined.
    def step(w,defined):
        reads,writes=fp(w)
        assert all(r not in changed or r in defined for _,r in reads)
        return defined|{r for _,r in writes}
    paths=0;states=[(0x300,frozenset())]
    while states:
        pc,defined=states.pop();w=raw[pc//4];op,fn=w>>26,w&63
        if op==0 and fn==8:step(raw[pc//4+1],defined);paths+=1;continue
        if op in(4,20):
            target=pc+4+4*(((w&65535)^32768)-32768)
            states.append((target,step(raw[pc//4+1],defined)))
            states.append((pc+8,defined if op==20 else step(raw[pc//4+1],defined)))
        elif op==3:
            step(raw[pc//4+1],defined);states.append((pc+8,frozenset()))
        else:states.append((pc+4,step(w,defined)))
    assert paths==3
    return dict(body_words=229,tail_paths=paths,caller_fprs=6,register_edit_words=9,commutative_branches=1,all_other_bits_and_bindings_fixed=True,no_renamed_incoming_values_read=True)

def main():
    from tools.experiments import game_clock_update_1510aa44_match as source
    from tools.experiments.game_paired_ground_constructor_match import payload
    raw,refs=payload(source.OUT/'selected.o',source.NAME);normal,nrefs=source.normalize(raw,refs)
    a=list(struct.unpack('>229I',raw));b=list(struct.unpack('>229I',normal));assert refs==nrefs;report=prove(a,b,refs)
    for pc,word in((0x384,b[0x384//4]^4),(0x2b8,b[0x2b8//4]^(16<<26))):
        changed=b[:];changed[pc//4]=word
        try:prove(a,changed,refs)
        except AssertionError:pass
        else:raise AssertionError('Invalid proof control accepted')
    report['proof_controls']=2
    (source.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
