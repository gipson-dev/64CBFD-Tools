"""Complete word/binding pins and a bijection of three private frame cells."""
from dataclasses import replace
import hashlib,json,math,struct
from tools.experiments import game_actor_motion_150c3574_match as s
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests import game_actor_motion_150c3574_oracle as g
from tools.tests import game_actor_motion_150c3574_native as native
from tools.tests import game_actor_motion_150c3574_callers as callers
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp,is_nan
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

SLOTS={0x30:0x28,0x2C:0x30,0x28:0x2C}

def address(p,c):
    base=g.STACK+c.phase-56
    for old,new in SLOTS.items():
        if base+old<=p<base+old+4:return base+new+p-(base+old)
    return p

def renamed_memory(m,c):return {address(p,c):v for p,v in m.items()}
def raw_initial(m,c):return {p:m[address(p,c)] for p in m}

class Oracle(g.Oracle):
    def execute(self,w):
        op,fmt,fn=w>>26,w>>21&31,w&63
        if op==17 and fmt==16 and fn in (0,1,2):
            self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul')[fn],getattr(self,'nan_rule','left'));return
        if op==17 and fmt==16 and fn in (4,13):
            value=self.f[w>>11&31];number=g.floating(value)
            if fn==4:
                result=value|0x400000 if is_nan(value) else 0x7FC00000 if number<0 else g.bits(math.sqrt(number))
            else:
                result=0x80000000 if not math.isfinite(number) or not -2147483648<=number<2147483648 else math.trunc(number)&0xFFFFFFFF
            self.f[w>>6&31]=result;return
        return super().execute(w)

def run(words,initial,c,raw=False,cut=None,rule='left'):
    m=Oracle(words,raw_initial(initial,c) if raw else dict(initial),c);m.cut=cut;m.nan_rule=rule
    boundary=False
    try:m.run()
    except AccessBoundary:boundary=True
    return m,boundary

def state(m,c,raw=False):
    memory=renamed_memory(m.memory,c) if raw else m.memory
    trace=[(kind,address(p,c) if raw else p,n,v) for kind,p,n,v in m.trace]
    return memory,m.r,m.f,m.hi,m.lo,m.calls,trace,m.all_accesses,m.current_pc,m.delay_of

def main():
    blob,refs=payload(s.OUT/'recovered.o',s.NAME);fixed,fr=s.normalize(blob,refs)
    a=list(struct.unpack('>264I',blob));b=list(struct.unpack('>264I',fixed))
    changed={i for i,(x,y) in enumerate(zip(a,b)) if x!=y};assert changed==set(s.PATCHES) and len(changed)==11
    for i in changed:
        x,y=a[i],b[i]
        assert x>>26 in (49,57) and x>>21&31==29 and x&0xFFFF0000==y&0xFFFF0000
        assert SLOTS[x&65535]==y&65535 and not refs.get(i*4)
    assert a[0]==b[0]==0x27BDFFC8 and a[-2:]==b[-2:]==[0x03E00008,0]
    assert not any(w>>26==9 and w>>21&31==29 and w>>16&31!=29 for w in a)
    slots=lambda ws:{w&65535 for w in ws if w>>26 in (32,33,35,36,37,40,41,43,49,53,57,61) and w>>21&31==29}
    assert slots(a)=={16,32,36,44,48} and slots(b)=={16,32,36,40,48}
    assert all(40<=p<52 for p in SLOTS) and set(SLOTS)==set(SLOTS.values())
    truth,raw,normalized=s.programs();assert truth==normalized
    coverage=set()
    values=list(g.cases())
    for c in values:
        for words in (truth,raw,normalized):
            m=g.check(words,c);coverage.update(t for t,args in m.calls)
    # Complete guest state and memory traces agree under the local-cell
    # bijection at every fired memory boundary on the selected routes.
    prefixes=0
    for c in [replace(v,kind=(0x10,0x25,0xAC)[i%3],flags=(0,1,4,255)[i%4],playing=i%2,mutation=i%3,phase=(i%2)*8) for i,v in enumerate(values[::128])]:
        initial=g.fixture(c);ret,_=run(truth,initial,c)
        for cut in range(ret.all_accesses+1):
            machines=[run(words,initial,c,raw=i==1,cut=cut) for i,words in enumerate((truth,raw,normalized))]
            assert len({hit for m,hit in machines})==1
            assert state(machines[0][0],c)==state(machines[1][0],c,True)==state(machines[2][0],c)
            prefixes+=int(machines[0][1])
    exceptional=0
    for i,value in enumerate((0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC00001,0x7FC30002,0x7F800001)):
        for off in (0x14,0x1C,0x28,0x44,0x14C):
            c=g.Case(seed=i,kind=0x25,flags=1,playing=0,mutation=0)
            initial=g.fixture(c);g.put(initial,g.OWNER+off,value)
            for rule in ('left','right'):
                machines=[run(words,initial,c,raw=k==1,rule=rule)[0] for k,words in enumerate((truth,raw,normalized))]
                assert state(machines[0],c)==state(machines[1],c,True)==state(machines[2],c)
                exceptional+=1
    rejected=0
    for i in range(264):
        bad=bytearray(blob);bad[4*i+3]^=1
        try:s.normalize(bytes(bad),refs)
        except AssertionError:rejected+=1
        else:raise AssertionError('Corrupted body pin accepted')
    for offset in refs:
        bad=dict(refs);bad[offset]=[('R_MIPS_26',s.NAME)]
        try:s.normalize(blob,bad)
        except AssertionError:rejected+=1
        else:raise AssertionError('Corrupted relocation pin accepted')
    # This wrong local address must fail the mapped-state equality.
    broken=raw[:];broken[188]^=4;c=g.Case();initial=g.fixture(c)
    ret,_=run(truth,initial,c);wrong,_=run(broken,initial,c,raw=True)
    assert state(ret,c)!=state(wrong,c,True)
    # Both published C interfaces retain the same actor argument. Re-execute
    # all three streams through the retained parent window, without claiming
    # its surrounding parent body.
    rom=(s.OUT/'production-baseline/conker/conker.us.bin').read_bytes()
    window=list(struct.unpack_from('>14I',rom,callers.ROM));caller_cases=0
    for c in values[::8]:
        for blocked,null in ((False,False),(True,False),(False,True)):
            for words in (truth,raw,normalized):callers.check(words,c,blocked,null,window)
            caller_cases+=1
    native.main(s)
    report=dict(finite_cases=len(values),streams=3,helper_targets=len(coverage),frame=56,home_guards=11,
        local_cell_bijection={hex(k):hex(v) for k,v in SLOTS.items()},fired_prefixes=prefixes,
        exceptional_cases=exceptional,nan_rules=['left','right'],invalid_conversion='explicit modeled 0x80000000; hardware FCSR not claimed',
        corrupt_body_and_binding_pins_rejected=rejected,home_control_effective=True,caller_cases=caller_cases,whole_parent_qualified=False,
        installed=(s.ROOT/s.SOURCE).read_text()==s.proposed((s.OUT/'production-baseline'/s.SOURCE).read_text()))
    (s.OUT/'qualification-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
