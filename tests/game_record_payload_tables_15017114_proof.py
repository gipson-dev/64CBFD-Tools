"""Closed captured-count schedule proof; exact suffix and checked dead inputs.

Normal execution uses valid mapped storage and the o32 argument interface.
Providers may change mutable public data and caller-saved state, but cannot
inspect implementation code/PC, implicit register inputs or unpassed locals.
The exposed metadata output is outside this prefix; its complete instruction
suffix and original home remain identical, including explicit output aliases.
"""
import json
from tools.tests.game_record_initializer_150169a0_proof import State,Program

class PrefixProgram(Program):
    def call(self,s,target):
        # These four-register helpers only own SP+0..0xF. S0 is saved at +0x14.
        keys=[s.r[29][1]+i for i in range(16,32,4)];saved={i:s.mem[i]for i in keys if i in s.mem}
        super().call(s,target)
        for i in keys:
            if i in saved:s.mem[i]=saved[i]
            else:s.mem.pop(i,None)

def initial(side):
    s=State(side,'payload-prefix');s.mem={};s.r[29]=('STACK',0);s.r[31]=('RETURN',);s.r[4]=('CATEGORY',)
    for i in range(16,24):s.r[i]=('ENTRY',i)
    for i in(26,27):s.r[i]=('ENTRY',i)
    return s

def uses(w):
    op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
    if not w:return set(),set()
    if op==0:
        if fn in(0,2,3):return{rt},{rd}
        if fn in(33,35,36,37,42,43):return{rs,rt},{rd}
        if fn==8:return{rs},set()
    if op==15:return set(),{rt}
    if op in(9,10,11,12,13,32,33,35,36,37):return{rs},{rt}
    if op in(40,41,43):return{rs,rt},set()
    if op==3:return{4,5,6,7},{31}
    if op in(4,5,6,7,20,21,22,23):return{rs,rt},set()
    raise AssertionError(('unsupported dead-input instruction',hex(w)))

def dead_inputs(words):
    states=[(0x90,frozenset((19,20,31)))];seen=set();cuts=0
    def transfer(w,dead):
        reads,writes=uses(w);assert not reads&dead,('suffix consumes differing incoming role',hex(w),reads&dead)
        return dead-writes
    while states:
        pc,dead=states.pop()
        if not dead:cuts+=1;continue
        assert(pc,dead)not in seen,('unclosed dead-role path',hex(pc));seen.add((pc,dead));assert len(seen)<150
        w=words[pc//4];op=w>>26
        if op in(4,5,6,7,20,21,22,23):
            after=transfer(w,dead);delay=transfer(words[pc//4+1],after)
            target=pc+4+4*(((w&65535)^32768)-32768)
            states.append((target,delay));states.append((pc+8,after if op>=20 else delay))
        else:states.append((pc+4,transfer(w,dead)))
    return cuts

def prove(raw,normal,raw_entry=0x14000000,normal_entry=0x15017114):
    assert len(raw)==len(normal)==121
    assert raw[0x90//4:]==normal[0x90//4:],'Payload suffix changed'
    a=PrefixProgram(raw,b'',raw_entry).paths(0,{0x90:'suffix'},initial('raw'))
    b=PrefixProgram(normal,b'',normal_entry).paths(0,{0x90:'suffix'},initial('normal'))
    assert a.keys()==b.keys()and len(a)==1
    for key in a:
        x,y=a[key],b[key]
        assert x.trace==y.trace,('ordered prefix effects',x.trace,y.trace)
        assert x.mem==y.mem and x.f==y.f and x.fcsr==y.fcsr
        assert all(x.r[i]==y.r[i]for i in range(32)if i not in(19,20,31)),('live prefix roles',[(i,x.r[i],y.r[i])for i in range(32)if i not in(19,20,31)and x.r[i]!=y.r[i]])
        assert x.r[29]==('STACK',-72)
        assert x.mem[-8]==0 and x.mem[0]==('CATEGORY',)
        for reg,offset in((16,20),(17,24),(18,28),(19,32),(20,36),(21,40)):
            assert x.mem[-72+offset]==('ENTRY',reg)
        assert x.mem[-72+44]==('RETURN',)
    cuts=dead_inputs(raw);assert cuts==dead_inputs(normal)==2
    return dict(symbolic_prefix_paths=1,dead_input_paths=cuts,ordered_public_access_and_call_traces=True,all_private_homes_equal=True,saved_entry_s0_s5_equal=True,exact_suffix_words=len(raw)-0x90//4,exposed_output_suffix_unchanged=True,full_raw_fault_state_claimed=False)

def main():
    from tools.experiments import game_record_payload_tables_15017114_match as s
    from tools.experiments.game_paired_ground_constructor_match import payload
    from tools.experiments.game_path_heading_turn_roles import bound_blob
    raw,refs=payload(s.OUT/'selected.o',s.NAME);normal,nrefs=s.normalize(raw,refs);symbols=s.draft.symbols()
    a,b=bound_blob(raw,refs,symbols),bound_blob(normal,nrefs,symbols);report=prove(a,b);controls=[]
    for name,pc,change in(('count-read',0x28,lambda w:(w&0xffff0000)|0x2101),('captured-copy',0x54,lambda w:(w&~(31<<21))|(17<<21)),('clear-length',0x8c,lambda w:w&~(31<<21))):
        bad=b[:];assert change(bad[pc//4])!=bad[pc//4];bad[pc//4]=change(bad[pc//4])
        try:prove(a,bad)
        except AssertionError:controls.append(name)
        else:raise AssertionError(('Ineffective proof control',name))
    alternate=b[:];alternate[0x54//4]=(alternate[0x54//4]&~(31<<11))|(20<<11);alternate[0x8c//4]=(alternate[0x8c//4]&~(31<<21))|(20<<21)
    assert prove(a,alternate)==report;report.update(effective_controls=controls,independent_saved_role_positive_control=True)
    (s.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
