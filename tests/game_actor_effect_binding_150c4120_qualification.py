"""Literal guest padding/RAM and live-read prefixes, plus native sender gates."""
import json,struct
from tools.experiments import game_actor_effect_binding_150c4120_match as s
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests import game_actor_effect_binding_150c4120_oracle as g
from tools.tests import game_actor_effect_binding_150c4120_native as native
from tools.tests import game_actor_effect_binding_150c4120_roles as roles
from tools.tests import test_game_actor_burst_consumer_match as faults

def address(p,c):
    base=g.STACK+c.phase-240
    for old,new in ((0x38,0x30),(0x30,0x38)):
        if base+old<=p<base+old+4:return base+new+p-(base+old)
    return p

def reads(w,m,raw):
    op,fn=w>>26,w&63;rs,rt,fs,ft=w>>21&31,w>>16&31,w>>11&31,w>>16&31
    signature=w&~roles.mask(w);values=[];commute=False
    i=(m.current_pc-s.ENTRY)//4
    if raw and i in (55,214) and s.ENTRY<=m.current_pc<s.ENTRY+s.SIZE:signature=(signature&~65535)|0x30
    if op==0:
        if fn in (0,2,3):values=[m.r[rt]]
        elif fn in (8,9):values=[m.r[rs]]
        elif fn in (16,18):values=[m.hi if fn==16 else m.lo]
        elif fn in (26,27,33,35,36,37,38,42,43):values=[m.r[rs],m.r[rt]];commute=fn in (33,36,37,38)
        else:raise AssertionError(('read opcode',hex(w),hex(m.current_pc)))
    elif op in (4,5,20,21):values=[m.r[rs],m.r[rt]];commute=True
    elif op in (1,6,7,9,10,11,12,13,14,22,23):values=[m.r[rs]]
    elif op in (2,3,15):pass
    elif op in (32,33,35,36,37,40,41,43,49,57):
        p=(m.r[rs]+roles.sign(w))&0xFFFFFFFF;values=[address(p,m.case) if raw else p]
        if op in (40,41,43):values.append(m.r[rt])
        if op==57:values.append(m.f[rt])
    elif op==17:
        fmt=w>>21&31
        if fmt==4:values=[m.r[rt]]
        elif fmt==0:values=[m.f[fs]]
        else:
            assert fmt==16 and fn in (0,1,2)
            values=[m.f[fs],m.f[ft]]
    else:raise AssertionError(('read opcode',hex(w),hex(m.current_pc)))
    return signature,tuple(sorted(values) if commute else values)

class ReadCode(faults.TrackedCode):
    def __getitem__(self,pc):
        w=super().__getitem__(pc);self.owner.operand_reads.append((pc,reads(w,self.owner,self.owner.raw_stream)));return w

class Oracle(g.Oracle):
    def __init__(self,*args,raw=False,**kwargs):
        super().__init__(*args,**kwargs);self.raw_stream=raw;self.operand_reads=[];self.full_packets=[]
        self.code=ReadCode(self.code,self)
    def record_call(self,t):
        if t==g.COPY:
            p,q,n=self.arguments(3);self.full_packets.append((n,bytes(self.memory[q+i] for i in range(n))))
        elif t==g.EFFECT:self.full_packets.append((112,bytes(self.memory[self.r[4]+i] for i in range(112))))
        super().record_call(t)
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63 in (0,1,2):
            self.f[w>>6&31]=g.fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul')[w&63],getattr(self,'nan_rule','left'));return
        return super().execute(w)
    def hook(self,t):
        ordinal=self.counts[t];super().hook(t)
        if t==g.RF and getattr(self,'float_override',None) is not None:self.f[0]=self.float_override[ordinal]

def run(words,initial,c,raw=False,cut=None,rule='left',floats=None):
    memory={p:initial[address(p,c)] for p in initial} if raw else dict(initial)
    m=Oracle(words,memory,c,raw=raw);m.cut=cut;m.nan_rule=rule;m.float_override=floats;hit=False
    try:m.run()
    except faults.AccessBoundary:hit=True
    return m,hit

def state(m,c,raw=False):
    memory={address(p,c):v for p,v in m.memory.items()} if raw else m.memory
    trace=[(kind,address(p,c) if raw else p,n,v) for kind,p,n,v in m.trace]
    # Caller-saved dead GPR contents may differ after register allocation.
    # All actual operand reads, ABI state, FP/HI/LO and RAM remain coupled.
    return (memory,m.r[0],m.r[4:8],m.r[16:24],m.r[26:32],m.f,m.hi,m.lo,m.calls,m.packets,m.full_packets,
        trace,m.operand_reads,m.all_accesses,m.current_pc,m.delay_of)

def main():
    roles.main();programs=s.programs();assert programs[0]==programs[2]
    visits=set()
    for c in g.cases():
        for words in programs:g.check(words,c)
        initial=g.fixture(c);machines=[run(words,initial,c,raw=i==1)[0] for i,words in enumerate(programs)]
        assert state(machines[0],c)==state(machines[1],c,True)==state(machines[2],c)
        assert machines[0].r[2]==machines[1].r[2]==machines[2].r[2]
        visits.update(machines[0].visits)
    prefixes=0;routes=0
    for outcome in (0,1,3):
        for phase in (0,8):
            for mutation in (0,1):
                c=g.Case(seed=outcome+phase+mutation,outcome=outcome,phase=phase,mutation=mutation);initial=g.fixture(c)
                ret,_=run(programs[0],initial,c)
                for cut in range(ret.all_accesses+1):
                    machines=[run(words,initial,c,raw=i==1,cut=cut) for i,words in enumerate(programs)]
                    assert len({hit for m,hit in machines})==1
                    states=[state(m,c,i==1) for i,(m,hit) in enumerate(machines)]
                    assert states[0]==states[1]==states[2],('prefix',c,cut,[i for i in range(len(states[0])) if states[0][i]!=states[1][i]])
                    prefixes+=int(machines[0][1]);routes+=int(not machines[0][1])
    exceptional=0
    for value in (0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC00001,0x7FC30002,0x7F800001):
        for slot in (0,1):
            c=g.Case();initial=g.fixture(c);floats=[g.real(c,0),g.real(c,1)];floats[slot]=value
            for rule in ('left','right'):
                machines=[run(words,initial,c,raw=i==1,rule=rule,floats=floats)[0] for i,words in enumerate(programs)]
                assert state(machines[0],c)==state(machines[1],c,True)==state(machines[2],c);exceptional+=1
    blob,refs=payload(s.OUT/'recovered.o',s.NAME);rejected=0
    for i in range(225):
        bad=bytearray(blob);bad[4*i+3]^=1
        try:s.normalize(bytes(bad),refs)
        except AssertionError:rejected+=1
        else:raise AssertionError('Corrupt body accepted')
    for at in refs:
        bad=dict(refs);bad[at]=[('R_MIPS_26',s.NAME)]
        try:s.normalize(blob,bad)
        except AssertionError:rejected+=1
        else:raise AssertionError('Corrupt binding accepted')
    native.main(s)
    report=dict(finite_cases=512,streams=3,visited_retail_words=sum(s.ENTRY<=v<s.ENTRY+s.SIZE for v in visits),
        fired_prefixes=prefixes,complete_prefix_routes=routes,guest_padding_bytes_compared=7,native_padding_bytes_uncredited=7,
        exceptional_fp_cases=exceptional,nan_rules=['left','right'],hardware_FCSR_uncredited=True,
        body_binding_corruptions_rejected=rejected,all_actual_operand_reads_coupled=True,dead_caller_saved_gpr_identity_uncredited=True,
        installed=(s.ROOT/s.SOURCE).read_text()==s.proposed((s.OUT/'production-baseline'/s.SOURCE).read_text()))
    (s.OUT/'qualification-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
