"""Qualify the selected source stream without weakening private-byte checks."""
from pathlib import Path
import sys
from tools.experiments import game_projection_submit_15035808_recovery as recovery
ROOT=recovery.ROOT
import hashlib,json,struct
from tools.tests import game_projection_submit_15035808_oracle as g
from tools.tests.game_projection_submit_15035808_observed import Observed
from tools.experiments.game_paired_ground_constructor_match import payload
OUT=recovery.OUT

def run(normalized=False,source=None,label=None):
    path=source or recovery.WHERE/'candidate.o'
    raw,refs=payload(path,'func_15035808');words=g.bind(raw,refs)
    if normalized:
        from tools.tests.game_projection_submit_15035808_normal_form import derive
        words,_=derive(words)
    original=struct.unpack_from('>345I',(ROOT/'conker/conker.us.bin').read_bytes(),0x62cb8)
    report=dict(source_object=str(path),raw_words=len(words),frame=(-words[0])&65535,raw_sha256=hashlib.sha256(raw).hexdigest(),
        cases=0,calls=0,allocations=0,equal_call_frames=0,equal_final_frames=0,private_call_offsets={},private_return_offsets={},matching_credit=0)
    from collections import Counter
    call_diff,return_diff=Counter(),Counter();seen={'raw':set(),'retail':set()}
    for c in g.cases():
        memory=g.fixture(c);reference=g.Reference(memory,c).run()
        a,b=Observed(words,memory,c).run(),Observed(original,memory,c).run()
        assert a.trace==b.trace==reference.trace,(c,'provider packets')
        assert a.actual_calls==b.actual_calls,(c,'actual private pointer arguments')
        assert g.public(a.memory)==g.public(b.memory)==g.public(reference.memory),(c,'public memory')
        for x,y in zip(a.frames,b.frames):
            if x==y:report['equal_call_frames']+=1
            else:call_diff.update(i-216 for i,(v,w)in enumerate(zip(x,y))if v!=w)
        if a.frame()==b.frame():report['equal_final_frames']+=1
        else:return_diff.update(i-216 for i,(v,w)in enumerate(zip(a.frame(),b.frame()))if v!=w)
        seen['raw'].update(pc for pc in a.visits if g.ENTRY<=pc<g.ENTRY+len(words)*4)
        seen['retail'].update(pc for pc in b.visits if g.ENTRY<=pc<g.ENTRY+345*4)
        report['cases']+=1;report['calls']+=len(a.trace);report['allocations']+=a.allocations
    report['private_call_offsets']=dict(call_diff);report['private_return_offsets']=dict(return_diff)
    report['coverage']={name:dict(visited_words=len(rows),unvisited_offsets=[hex(i*4)for i in range(len(words)if name=='raw'else 345)if g.ENTRY+i*4 not in rows])for name,rows in seen.items()}
    report['actual_private_addresses_and_full_public_behavior']=True
    report['private_stack_normal_form']=normalized
    if normalized:
        report['derived_bound_sha256']=hashlib.sha256(struct.pack('>%dI'%len(words),*words)).hexdigest()
        assert not call_diff and not return_diff,report
    label=label or ('normalized-guest'if normalized else'selected-guest')
    assert '/'not in label and '\\'not in label
    (OUT/(label+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return report
