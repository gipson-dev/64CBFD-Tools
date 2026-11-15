"""Literal-pool domain, semantic streams, exceptional states and original caller."""
from dataclasses import dataclass,replace
import json
from tools.experiments import game_motion_effect_150c2c00_match as s
from tools.experiments import game_motion_effect_150c2c00_recovery as old
from tools.tests import game_motion_effect_150c2c00_oracle as g
from tools.tests import game_motion_effect_150c2c00_native as native
from tools.tests import game_motion_effect_150c2c00_callers as caller
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp as ieee
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

old_cases,old_result=g.cases,g.result
@dataclass(frozen=True)
class ExtendedCase(g.Case):
    alias:int=0
    float_draws:tuple=()

def cases():
    for c in old_cases():
        yield c
        if c.outcome:yield replace(c,outcome=2)

def readonly(memory):
    assert g.data(memory,g.CONST,80)==g.rom()[0x244d80:0x244dd0],'Readonly coefficient domain violated'

def effect(m,c,t,n):
    readonly(m);g.put(m,g.MARK,(0x13579bdf+t+n*0x10203)&0xffffffff)
    if not c.mutation:return
    if t==g.RANDF:g.put(m,g.SELECT,g.read(m,g.SELECT)^0x55)
    if t==g.ANGLE:
        g.put(m,g.MOTION,g.bits(2000.+n*100.));g.put(m,g.MOTION+8,g.bits(-1000.-n*50.))
    if t==g.DIFF and n==0:g.put(m,g.OWNER+0x28,g.bits(3.25))
    if t==g.EMIT:
        g.put(m,g.OWNER+0x28,g.sub(g.read(m,g.OWNER+0x28),g.bits(.25)))
        m[g.OWNER+12]^=0x55;m[g.OWNER+1]^=0xa3
    readonly(m)

def result(c,t,n):
    if t==g.RANDF:
        for index,value in getattr(c,'float_draws',()):
            if n==index:return value
    if t==g.EMIT:
        if not c.outcome or c.outcome==2 and n%2:return 0
        dest={1:g.OWNER+12,2:g.OWNER+40,3:g.MOTION,4:g.MOTION+8}.get(getattr(c,'alias',0),g.OUTPUT+0x160)
        return dest-0x160
    return old_result(c,t,n)

def state(m):return m.r,m.f,m.hi,m.lo,m.memory,m.trace,m.calls,m.observed,m.copies,m.current_pc,m.delay_of

def main():
    g.s=native.s=caller.s=s;g.effect=effect;g.result=result;g.cases=cases
    programs=s.programs();assert programs[0]==programs[2]
    seen=[set(),set(),set()];count=emissions=copies=0;shapes=set()
    for c in cases():
        initial=g.fixture(c);readonly(initial)
        for i,words in enumerate(programs):
            m=g.Oracle(words,initial,c);m.run();g.verify(m,initial,c);readonly(m.memory);seen[i].update(m.visits)
        emissions+=len(m.observed);copies+=len(m.copies);shapes.add((len(m.observed),len(m.copies)));count+=1
    assert all(len(v&set(range(s.ENTRY,s.ENTRY+s.SIZE,4)))==241 for v in seen)
    assert all(set(g.helper_code())<=v for v in seen)
    aliases=0
    for alias in (1,2,3,4):
        for mutation in (0,1):
            c=ExtendedCase(accumulator=g.bits(4.25),outcome=2,mutation=mutation,alias=alias,float_draws=((1,0),) if alias==2 else ())
            initial=g.fixture(c)
            for words in programs:m=g.Oracle(words,initial,c);m.run();g.verify(m,initial,c);readonly(m.memory)
            aliases+=1
    exceptional=0;nan_boundaries=[]
    for rule in ('left','right'):
        g.fp=lambda a,b,op:ieee(a,b,op,rule)
        for value in (0,0x80000000,1,0x807fffff,0xff7fffff,0xff800000,0x7f800001,0x7fc30002):
            for slot in ('accumulator','motionX','motionZ','draw0','draw1','draw2','draw3','draw4','draw5'):
                c=ExtendedCase(dt=0 if slot=='draw0' else g.bits(.5),float_draws=((int(slot[4:]),value),) if slot.startswith('draw') else ())
                initial=g.fixture(c)
                if slot=='accumulator':g.put(initial,g.OWNER+40,value)
                elif slot=='motionX':g.put(initial,g.MOTION,value)
                elif slot=='motionZ':g.put(initial,g.MOTION+8,value)
                states=[]
                for words in (programs[0],programs[2]):
                    m=g.Oracle(words,initial,c);m.run();g.verify(m,initial,c);states.append(state(m))
                assert states[0]==states[1],(rule,slot,hex(value));exceptional+=1
        c=ExtendedCase();initial=g.fixture(c);g.put(initial,g.MOTION,0x7fc00001);g.put(initial,g.MOTION+8,0x7fc30002);states=[]
        for words in (programs[0],programs[2]):
            m=g.Oracle(words,initial,c);m.run();g.verify(m,initial,c);states.append(state(m))
        assert states[0]==states[1] and m.f[12]==(0x7fc00001 if rule=='left' else 0x7fc30002)
        nan_boundaries.append(dict(rule=rule,norm_register='F12',result='%08x'%m.f[12]));exceptional+=1
    g.fp=lambda a,b,op:ieee(a,b,op,'left')
    prefixes=0
    for c in (g.Case(accumulator=0),g.Case(policy=1),g.Case(outcome=0),g.Case(outcome=2,mutation=1)):
        initial=g.fixture(c);m=g.Oracle(programs[0],initial,c);m.run()
        for cut in range(m.all_accesses):
            states=[]
            for words in (programs[0],programs[2]):
                m=g.Oracle(words,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError('Access cut did not fire')
                states.append(state(m))
            assert states[0]==states[1];prefixes+=1
    invalid=g.fixture(g.Case());invalid[g.CONST]^=1
    try:readonly(invalid)
    except AssertionError:pass
    else:raise AssertionError('Mutated readonly pool accepted')
    native.main(controls_override={'motion':('secondScale * secondScale + firstScale * firstScale','secondScale * secondScale - firstScale * firstScale'),'cached':(' * headingScale + headingBase',' * headingScale - headingBase')},declarations_override=old.PREAMBLE,readonly_coefficients=True,mixed_outcomes=True)
    n=json.loads((s.OUT/'native-report.json').read_text());n.pop('private_uninstalled');n.update(readonly_coefficients=True,mixed_allocation_outcomes=True,source_installed=(s.ROOT/s.SOURCE).read_text()==s.proposed((s.OUT/'production-baseline'/s.SOURCE).read_text()));(s.OUT/'native-report.json').write_text(json.dumps(n,indent=2)+'\n')
    caller.main();c=json.loads((s.OUT/'caller-report.json').read_text());c.pop('private_uninstalled');c['streams']=3;c['retail_normalized_literal_equality']=True;(s.OUT/'caller-report.json').write_text(json.dumps(c,indent=2)+'\n')
    report=dict(finite_cases=count,streams=3,emissions=emissions,copies=copies,allocation_shapes=sorted(shapes),alias_cases=aliases,exceptional_cases=exceptional,exceptional_streams=2,ordered_nan_boundaries=nan_boundaries,literal_access_prefixes=prefixes,readonly_pool_bytes=80,readonly_corruption_rejected=True,polar_words=22,copy_words=11,hardware_FCSR_not_claimed=True,native_alias_and_exceptional_not_claimed=True)
    (s.OUT/'qualification-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
