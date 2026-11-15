"""Constant-operand proof, fired memory prefixes and the original dispatch."""
from dataclasses import replace
import json,struct
from tools.experiments import game_impact_phase_150c3994_match as s
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests import game_impact_phase_150c3994_oracle as g
from tools.tests import game_impact_phase_150c3994_native as native
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

CALLER,END,TABLE,CALLER_ROM=0x1504AB00,0x1504AB38,0x80086014,0x77FB0

def run(words,initial,c,cut=None,rule='left'):
    m=g.Oracle(words,dict(initial),c);m.cut=cut;m.nan_rule=rule;hit=False
    try:m.run()
    except AccessBoundary:hit=True
    return m,hit

def state(m):return m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.trace,m.all_accesses,m.current_pc,m.delay_of

def caller(words,c,blocked=False,null=False,window=None):
    initial=g.fixture(c);g.put(initial,g.OWNER+0x25C,0x200 if blocked else 0)
    g.put(initial,TABLE+c.state*4,0 if null else s.ENTRY)
    expected,calls,allocated=g.reference(initial,c) if not blocked and not null else (g.public(initial),[],[])
    if window is None:
        rom=(s.OUT/'production-baseline/conker/conker.us.bin').read_bytes();window=list(struct.unpack_from('>14I',rom,CALLER_ROM))
    code=dict(zip(range(s.ENTRY,s.ENTRY+4*len(words),4),words));code[END]=0
    m=g.Oracle(window,initial,c,entry=CALLER,connected=code);m.r[16]=g.OWNER;m.before[16]=g.OWNER
    m.code=WindowCode(m.code,m);m.code.ends=(END,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller window did not end')
    assert g.public(m.memory)==expected and m.calls==calls and m.allocated==allocated
    assert m.entries==([] if blocked or null else [g.OWNER])
    assert m.r[16]==g.OWNER and m.r[29]==m.before[29] and m.f[20:]==m.before_f[20:]
    return m

def main():
    raw,refs=payload(s.OUT/'recovered.o',s.NAME);fixed,fr=s.normalize(raw,refs)
    a=list(struct.unpack('>237I',raw));b=list(struct.unpack('>237I',fixed))
    assert {i for i,(x,y) in enumerate(zip(a,b)) if x!=y}=={77}
    assert a[77]==0x46100482 and b[77]==0x46008482 and not refs.get(308)
    # The dominating instruction sets F16 to the finite, nonzero -20 constant.
    assert a[71]==0x3C01C1A0 and a[74]==0x44818000
    assert a[75:77]==[0x24040092,0x02002825]
    assert a[59]==0x4608003C and a[61]==0x4502001C
    assert a[0]==b[0]==0x27BDFFB0 and a[-2:]==[0x03E00008,0]
    values=(0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC00001,0x7FC30002,0x7F800001)
    for value in values+tuple((i*1664525+1013904223)&0xFFFFFFFF for i in range(1024)):
        for rule in ('left','right'):assert fp(value,0xC1A00000,'mul',rule)==fp(0xC1A00000,value,'mul',rule)
    programs=s.programs();assert programs[0]==programs[2]
    g.main()
    finite=list(g.cases());prefixes=0
    prefix_cases=[replace(v,state=19+i%2,counter=(0,9,10,20,21,255)[i%6],marker=i%2,mutation=i%3,outcome=i%3) for i,v in enumerate(finite[::170])]
    prefix_cases += [g.Case(seed=outcome,phase=phase,outcome=outcome) for outcome in (0,1,2) for phase in (0,8)]
    for c in prefix_cases:
        initial=g.fixture(c);complete,_=run(programs[0],initial,c)
        for cut in range(complete.all_accesses+1):
            machines=[run(words,initial,c,cut=cut) for words in programs]
            assert len({hit for m,hit in machines})==1
            assert state(machines[0][0])==state(machines[1][0])==state(machines[2][0])
            prefixes+=int(machines[0][1])
    exceptional=0
    for i,value in enumerate(values):
        for off in (0x14,0x18,0x1C,0x20,0x28,0xB8,0x148):
            c=g.Case(seed=i,counter=0 if off<0x20 else 21,mutation=0)
            initial=g.fixture(c);g.put(initial,g.OWNER+off,value)
            for rule in ('left','right'):
                machines=[run(words,initial,c,rule=rule)[0] for words in programs]
                assert state(machines[0])==state(machines[1])==state(machines[2]);exceptional+=1
    rejected=0
    for i in range(237):
        bad=bytearray(raw);bad[4*i+3]^=1
        try:s.normalize(bytes(bad),refs)
        except AssertionError:rejected+=1
        else:raise AssertionError('Corrupt body accepted')
    for at in refs:
        bad=dict(refs);bad[at]=[('R_MIPS_26',s.NAME)]
        try:s.normalize(raw,bad)
        except AssertionError:rejected+=1
        else:raise AssertionError('Corrupt binding accepted')
    broken=programs[1][:];broken[77]=(broken[77]&~63)|1
    c=g.Case(velocity=g.bits(-2.),timer=g.bits(21.));initial=g.fixture(c);right,_=run(programs[0],initial,c);wrong,_=run(broken,initial,c)
    assert state(right)!=state(wrong)
    rom=(s.OUT/'production-baseline/conker/conker.us.bin').read_bytes()
    assert struct.unpack_from('>2I',rom,0x22AB20)==(s.ENTRY,s.ENTRY)
    window=list(struct.unpack_from('>14I',rom,CALLER_ROM));assert window[11:13]==[0x0040F809,0x02002025]
    count=0
    for c in finite[::8]:
        # Cover both table slots independently of the sampled seed parity.
        for state_value in (19,20):
            c=replace(c,state=state_value)
            for blocked,null in ((False,False),(True,False),(False,True)):
                for words in programs:caller(words,c,blocked,null,window)
                count+=1
    broken=window[:];broken[12]=0x00002025
    try:caller(programs[2],g.Case(),window=broken)
    except (AssertionError,KeyError):pass
    else:raise AssertionError('Wrong caller argument was accepted')
    native.main()
    report=dict(finite_cases=2048,streams=3,frame=80,guards=1,original_constructor_words=48,
        fired_prefixes=prefixes,exceptional_cases=exceptional,nan_rules=['left','right'],
        invalid_conversion='explicit modeled 0x80000000; hardware FCSR not claimed',corrupt_pins_rejected=rejected,
        multiply_control_effective=True,caller_cases=count,caller_argument_control_effective=True,whole_parent_qualified=False,
        installed=(s.ROOT/s.SOURCE).read_text()==s.proposed((s.OUT/'production-baseline'/s.SOURCE).read_text()))
    (s.OUT/'qualification-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
