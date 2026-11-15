"""Private-buffer bijection, six-byte descriptor snapshots and caller gates.

The descriptor padding byte is qualified only in the guest frame mapping.
Portable native C leaves that byte unspecified. Modeled providers do not
establish PI hardware behavior, instruction-cache coherence or full gameplay.
"""
from dataclasses import replace
import json,shutil,struct
from tools.experiments import game_actor_exit_150c3d5c_match as s
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests import game_actor_exit_150c3d5c_oracle as g
from tools.tests import game_actor_exit_150c3d5c_native as native
from tools.tests import game_actor_exit_150c3d5c_callers as callers
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary


def address(p,c):
    base=g.STACK+c.phase-256
    if base+0xE8<=p<base+0xFA:return p-8
    if base+0xE0<=p<base+0xE8:return p+18
    return p


def raw_initial(initial,c):return {p:initial[address(p,c)] for p in initial}


class Oracle(g.Oracle):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.descriptor_bytes=[]
    def record_call(self,t):
        if t==g.EMIT:
            p=self.r[4];self.descriptor_bytes.append(bytes(self.memory[p+i] for i in range(6)))
        super().record_call(t)


def run(words,initial,c,raw=False,cut=None,rule='left'):
    m=Oracle(words,raw_initial(initial,c) if raw else dict(initial),c)
    m.cut=cut;m.nan_rule=rule;hit=False
    try:m.run()
    except AccessBoundary:hit=True
    return m,hit


def state(m,c,raw=False):
    memory={address(p,c):v for p,v in m.memory.items()} if raw else m.memory
    regs=m.r[:]
    # These are address-valued only from the final two LEAs through the
    # emitter's delay slot. Do not reinterpret arbitrary coordinate integers.
    if raw and s.ENTRY+229*4<=m.current_pc<=s.ENTRY+234*4:
        regs[4]=address(regs[4],c);regs[5]=address(regs[5],c)
    trace=[(kind,address(p,c) if raw else p,n,v) for kind,p,n,v in m.trace]
    return memory,regs,m.f,m.hi,m.lo,m.calls,trace,m.all_accesses,m.current_pc,m.delay_of,m.observed,m.descriptor_bytes


def main():
    blob,refs=payload(s.OUT/'recovered.o',s.NAME);fixed,fr=s.normalize(blob,refs)
    a=list(struct.unpack('>240I',blob));b=list(struct.unpack('>240I',fixed))
    assert {i for i,(x,y) in enumerate(zip(a,b)) if x!=y}==set(s.PATCHES) and len(s.PATCHES)==9
    assert a[0]==b[0]==0x27BDFF00 and a[-2:]==b[-2:]==[0x03E00008,0]
    for i in s.PATCHES:
        x,y=a[i],b[i]
        assert x>>26 in (9,40,41,43) and x>>21&31==29
        assert x&0xFFFF0000==y&0xFFFF0000 and (x&65535)-8==y&65535 and not refs.get(i*4)
    assert {i for i in s.PATCHES if a[i]>>26==9}=={229,230}
    assert a[229:231]==[0x27A400F4,0x27A500E8]
    assert b[229:231]==[0x27A400EC,0x27A500E0]
    # All 26 bytes are a bijection; outgoing homes, S0/RA and cartridge word
    # lie outside it. The 18 moved bytes cover both complete aggregate objects.
    for phase in (0,8):
        c=g.Case(phase=phase);base=g.STACK+phase-256
        domain=set(range(base+0xE0,base+0xFA))
        assert {address(p,c) for p in domain}==domain
        for p in (*range(base,base+0xD8),*range(base+0xFC,base+0x100)):assert address(p,c)==p
    truth,raw,normalized=s.programs();assert truth==normalized
    values=list(g.cases());visited=set();coverage=set()
    for c in values:
        for words in (truth,raw,normalized):
            m=g.check(words,c);coverage.update(t for t,args in m.calls)
            if words is truth:visited.update(m.visits)
    prefixes=0;complete_cases=0
    for mode in range(3):
        for phase in (0,8):
            for outcome in (0,1):
                c=g.Case(seed=mode*4+phase+outcome,phase=phase,read_mode=mode,mutation=1,outcome=outcome)
                initial=g.fixture(c);ret,_=run(truth,initial,c)
                for cut in range(ret.all_accesses+1):
                    machines=[run(words,initial,c,raw=k==1,cut=cut) for k,words in enumerate((truth,raw,normalized))]
                    assert len({hit for m,hit in machines})==1
                    states=[state(m,c,k==1) for k,(m,hit) in enumerate(machines)]
                    assert states[0]==states[1]==states[2],('prefix',c,cut,[i for i in range(len(states[0])) if not states[0][i]==states[1][i]])
                    prefixes+=int(machines[0][1]);complete_cases+=int(not machines[0][1])
    exceptional=0
    for i,value in enumerate((0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC00001,0x7FC30002,0x7F800001)):
        for off in (0x14,0x18,0x1C):
            c=g.Case(seed=i,read_mode=i%3);initial=g.fixture(c);g.put(initial,g.OWNER+off,value)
            for rule in ('left','right'):
                machines=[run(words,initial,c,raw=k==1,rule=rule)[0] for k,words in enumerate((truth,raw,normalized))]
                assert state(machines[0],c)==state(machines[1],c,True)==state(machines[2],c)
                exceptional+=1
    rejected=0
    for i in range(240):
        bad=bytearray(blob);bad[4*i+3]^=1
        try:s.normalize(bytes(bad),refs)
        except AssertionError:rejected+=1
        else:raise AssertionError('Corrupt body accepted')
    for at in refs:
        bad=dict(refs);bad[at]=[('R_MIPS_26',s.NAME)]
        try:s.normalize(blob,bad)
        except AssertionError:rejected+=1
        else:raise AssertionError('Corrupt binding accepted')
    broken=raw[:];broken[191]^=1;c=g.Case();initial=g.fixture(c)
    ret,_=run(truth,initial,c);wrong,_=run(broken,initial,c,raw=True)
    assert state(ret,c)!=state(wrong,c,True)
    count=0
    for c in values[::4]:
        for phase in (0,8):
            c=replace(c,phase=phase)
            for wrapper,enabled in ((False,True),(True,True),(True,False)):
                for words in (truth,raw,normalized):callers.check(words,c,wrapper,enabled)
                count+=1
    try:callers.check(normalized,g.Case(),wrong_argument=True)
    except (AssertionError,KeyError):pass
    else:raise AssertionError('Wrong caller argument accepted')
    assert s.BODY==s.old.BODY and (s.OUT/'recovered.c').read_bytes()==(s.old.OUT/'recovered.c').read_bytes()
    native.main();shutil.copyfile(s.old.OUT/'native-report.json',s.OUT/'native-report.json')
    report=dict(finite_cases=len(values),streams=3,visited_retail_words=sum(s.ENTRY<=v<s.ENTRY+s.SIZE for v in visited),
        helper_targets=len(coverage),frame=256,home_guards=9,moved_buffer_bytes=18,permuted_frame_bytes=26,
        guest_descriptor_bytes=6,native_descriptor_defined_bytes=5,native_descriptor_padding_bytes_uncredited=1,
        fired_prefixes=prefixes,complete_prefix_routes=complete_cases,exceptional_cases=exceptional,nan_rules=['left','right'],
        invalid_conversion='explicit modeled 0x80000000; hardware FCSR not claimed',corrupt_body_and_binding_pins_rejected=rejected,
        home_control_effective=True,caller_cases=count,caller_argument_control_effective=True,exit_window_words=12,complete_wrapper_words=15,
        whole_state_parent_qualified=False,native_source_identity_verified=True,
        installed=(s.ROOT/s.SOURCE).read_text()==s.proposed((s.OUT/'production-baseline'/s.SOURCE).read_text()))
    (s.OUT/'qualification-report.json').write_text(json.dumps(report,indent=2)+'\n')
    (s.OUT/'oracle-report.json').write_text(json.dumps(dict(finite_cases=len(values),streams=3,visited_retail_words=report['visited_retail_words']),indent=2)+'\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__':main()
