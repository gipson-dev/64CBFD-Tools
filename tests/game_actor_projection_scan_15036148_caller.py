from pathlib import Path
import sys
from tools.experiments import game_actor_projection_scan_15036148_recovery as source
ROOT=source.ROOT
from dataclasses import replace
import json,struct
from tools.tests import game_actor_projection_scan_15036148_oracle as g
from tools.tests.game_frame_timing_oracle import TimingOracle,STACK,put
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
OUT=source.OUT;CALLER=0x150193A4;POST=0x1515D6C8;CANARY=0xA5000
class Connected(TimingOracle):
    def __init__(self,window,callee,memory,c):
        self.c=c;self.trace=[];self.boundaries=[];self.inner=replace(c,phase=c.phase-24)
        self.outputs=tuple(STACK+self.inner.phase+x for x in(-6,-8,-10));self.entered=self.post=0
        prefix=(0x27BDFFE8,0xAFBF0014,0xAFB00010)
        suffix=(0x8FB00010,0x8FBF0014,0x03E00008,0x27BD0018)
        super().__init__(prefix+window+suffix,memory,phase=c.phase,entry=CALLER-12,
            arguments=(),connected={g.ENTRY+4*i:w for i,w in enumerate(callee)})
    def record_call(self,target):
        if target==g.ENTRY:self.entered+=1;return
        if target==POST:self.post+=1;self.calls.append((POST,()));return
        assert target in(g.EXTENT,g.SUBMIT);args=list(self.arguments(4 if target==g.EXTENT else 10))
        if target==g.EXTENT:
            assert tuple(args[1:])==self.outputs;args[1:]=[g.TOKEN,g.TOKEN+2,g.TOKEN+4]
        self.trace.append((target,tuple(args)));self.calls.append((target,tuple(args)))
        self.boundaries.append(bytes(self.memory[STACK+self.inner.phase+i]for i in range(-152,16)))
    def hook(self,target):
        if target!=POST:return g.Oracle.hook(self,target)
        assert self.entered==1;put(self.memory,CANARY,0xC0FEBABE)
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)]
def run():
    rom=(ROOT/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>4I',rom,0x46854)
    assert window==(0x0D40D852,0,0x0D4575B2,0)
    raw,refs=payload(OUT/'qualified-screen/candidate.o','func_15036148')
    anchors={n:0x80097D74 if n=='.rodata'else int(n.split('_')[1],16)for rs in refs.values()for _,n in rs}
    code=tuple(bound_blob(raw,refs,anchors));retail=struct.unpack_from('>112I',rom,0x635F8);count=calls=0
    for c in list(g.cases())[:96]:
        initial=g.fixture(c);put(initial,CANARY,0x12345678);expected,trace=g.reference(initial,replace(c,phase=c.phase-24));put(expected,CANARY,0xC0FEBABE);models=[]
        for words in(code,retail):
            model=Connected(window,words,initial,c).run();assert model.trace==trace and model.entered==model.post==1,(c,'connected trace')
            assert g.public(model.memory)==g.public(expected),(c,'post-call continuation');models.append(model)
        assert models[0].boundaries==models[1].boundaries and models[0].memory==models[1].memory,(c,'complete RAM')
        count+=1;calls+=len(trace)
    r=dict(cases=count,logical_helper_calls=calls,actual_original_words=4,synthetic_prefix_words=3,synthetic_suffix_words=4,
        JAL_and_delay_preserved=True,following_original_call_executed=True,return_value_ignored=True,complete_RAM_equal=True,
        full_outer_caller_claim=False,matching_credit=0)
    (OUT/'caller.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
