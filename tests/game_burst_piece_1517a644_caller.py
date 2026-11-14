"""Connect the real matched burst loop to the recovered piece factory."""
from dataclasses import replace
import itertools,json,struct
from tools.tests import game_burst_piece_1517a644_oracle as b
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
BURST,EMIT=0x1517aa20,b.source.ENTRY
def reference(initial,c,count):
    m=dict(initial);calls=[];obs=[];draw=0
    if b.floating(c.size)<12.:return m,calls,obs
    modulus=int(b.floating(b.bits(b.floating(c.size)*8.)));reduced=b.floating(b.bits(b.floating(c.size)*.5))
    for i in range(max(0,count)):
        values=[]
        for j in range(4):
            values.append(b.sample(c,draw));draw+=1;obs.append((b.RANDOM,b.observe(m)));calls.append((b.RANDOM,()));b.effect(m,c,len(calls)-1,b.RANDOM,b.STACK+c.phase)
        size=b.bits(b.floating(b.bits(float((values[2]%modulus)>>4)))+reduced)
        args=(size,values[3]&1,b.u32(b.half(c.x+(values[0]&63)-32)),b.u32(b.half(c.y)),b.u32(c.z+(values[1]&63)-32))
        obs.append((EMIT,b.observe(m)));calls.append((EMIT,args))
        child=replace(c,size=size,kind=args[1],x=args[2],y=args[3],z=args[4],phase=c.phase-80)
        m,more,observations=b.reference(m,child,draw,len(calls));draw+=sum(t==b.RANDOM for t,_ in more);calls.extend(more);obs.extend(observations)
    return m,calls,obs
class Coupled(b.Oracle):
    def __init__(self,words,initial,c,count,callee):
        self.draws=0;self.observed=[]
        code=dict(zip(range(EMIT,EMIT+b.source.SIZE,4),callee))
        FactoryOracle.__init__(self,words,initial,c,entry=BURST,connected=code,arguments=(0,b.u32(c.x),b.u32(c.y),b.u32(c.z),b.u32(count)))
        self.f[12]=c.size;self.before_r=self.r[:];self.before_f=self.f[:]
    def record_call(self,t):
        if t!=EMIT:return super().record_call(t)
        args=(self.f[12],*map(b.u32,self.arguments(5)[1:]));self.calls.append((t,args));self.events.append(('CALL',t,args));self.observed.append((t,b.observe(self.memory)))
def main():
    root,out,values,programs=b.load();raw=bound_blob(*payload(out/'selected.o','func_1517AA20'));truth=list(struct.unpack_from('>87I',(root/'conker/conker.us.bin').read_bytes(),0x1a7ed0));assert raw==truth
    count=0
    for size,n,outcome,pattern,phase in itertools.product((11.,12.,31.875),(-1,1,2),(0,1),(0,1,2),(0,8)):
        c=b.Case(size=b.bits(size),outcome=outcome,pattern=pattern,phase=phase,seed=19,mutation=0);initial=b.fixture(c,values);expected,calls,obs=reference(initial,c,n);states=[]
        for callee in programs:
            m=Coupled(raw,initial,c,n,callee);m.run();assert (b.public(m.memory),m.calls,m.observed)==(b.public(expected),calls,obs),(c,n)
            assert m.r[16:24]==m.before_r[16:24] and m.f[20:]==m.before_f[20:] and m.r[29]==m.before_r[29];states.append(b.state(m))
        assert states[0]==states[2];count+=1
    report=dict(cases=count,burst_words=87,callee_words=130,real_caller_connected=True,allocator_ground_rng_modeled=True,callee_saves_preserved=True,mutable_homes_excluded=True)
    (out/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
