"""Instruction-driven complete normal execution, including the two loop trips.

The raw binding occupies SP3C..43 rather than SP34..3B. Their eight-byte
ranges are exchanged by an explicit private-entry/address relation. The
152-byte payload and saved result have literal homes. Opaque services may
mutate public memory and retained binding bytes, but cannot inspect unpassed
locals or implementation PCs. COPY performs the specified nonoverlapping
152-byte copy and returns its destination. Raw fault-state identity is unclaimed.
"""
from pathlib import Path
from copy import deepcopy
import json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
e=g.e
ENTRY=0x151B09BC
CLASSIFY,BIND,FACTORY,COPY=0x15134070,0x151494E0,0x151491F4,0x10022EC0

class State(g.State):
    def __init__(self,side,remap):
        super().__init__('common');self.side=side;self.remap=remap
        self.r[4:8]=[('OWNER',),('SOURCE',),('DURATION',),('CHANNEL',)]
        self.r[29],self.r[31]=('STACK',0),('RETURN',)
        self.mem={off:('PRIVATE_ENTRY',off)for off in range(-224,20)}
        self.binding=False

    def canonical(self,off):
        if self.remap:
            if -164<=off<-156:return off-8
            if -172<=off<-164:return off+8
        return off

    def address(self,value):
        return('STACK',self.canonical(value[1]))if e.tagged(value,'STACK')else value

    def load(self,address,size,pool=b''):
        if e.tagged(address,'STACK'):
            off=address[1];assert size in(1,2,4)and off%size==0 and -224<=off and off+size<=20
            return g.join([self.mem[self.canonical(off+i)]for i in range(size)])
        return super().load(address,size,pool)

    def store(self,address,size,value):
        if e.tagged(address,'STACK'):
            off=address[1];assert size in(1,2,4)and off%size==0 and -224<=off and off+size<=20
            for i in range(size):self.mem[self.canonical(off+i)]=g.byte(value,8*(size-i-1))
        else:super().store(address,size,value)

    def frame(self):return tuple(self.mem[i]for i in range(-224,20))

class Program(g.Program):
    def __init__(self,words,terms):
        e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()

    def predicate(self,op,a,b):
        if e.tagged(a,'STACK')or e.tagged(b,'STACK'):
            assert op=='EQ'and e.tagged(a,'STACK')and e.tagged(b,'STACK')
            return a==b
        return g.predicate(op,a,b)

    def paths(self,initial):
        states=[(0,initial)];answers={};work=0
        while states:
            pc,s=states.pop();work+=1;s.steps+=1;assert work<100000 and s.steps<800
            if pc==-4:
                key=tuple(sorted(s.facts.items(),key=repr));assert key not in answers;answers[key]=s;continue
            w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31
            if op in(4,5,20,21):
                predicate=self.predicate('EQ',s.r[rs],s.r[rt])
                if op in(5,21):predicate=e.negate(predicate)
                for take in e.choices(s,predicate):
                    n=deepcopy(s);e.assume(n,predicate,take)
                    if take or op<20:self.step(n,self.instruction(pc+4))
                    dest=pc+4+4*(((w&65535)^32768)-32768)if take else pc+8
                    states.append((dest,n))
            elif op==3:
                s.r[31]=self.entry+pc+8;self.step(s,self.instruction(pc+4))
                self.call(s,((self.entry+pc+4)&0xf0000000)|((w&0x3ffffff)<<2));states.append((pc+8,s))
            elif op==0 and w&63==8:
                assert s.r[rs]==('RETURN',);self.step(s,self.instruction(pc+4));states.append((-4,s))
            else:self.step(s,w);states.append((pc+4,s))
        return answers

    def call(self,s,target):
        count={CLASSIFY:1,BIND:2,FACTORY:8,COPY:3}[target]
        args=tuple(s.r[4:4+min(count,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,count-4)))
        canonical=tuple(s.address(a)for a in args)
        assert s.r[29]==('STACK',-224)
        observed=()
        if target==BIND:
            assert canonical==(('STACK',-172),19),('binding ABI',canonical)
            observed=tuple(s.mem[i]for i in range(-172,-164));s.binding=True
        elif target==FACTORY:
            assert canonical[1:3]==(0xffffffff,19)and canonical[4:6]==(15,152),('factory ABI',canonical)
        elif target==COPY:
            assert canonical[1:]==(('STACK',-156),152),('copy ABI',canonical)
            e.plain(canonical[0]);observed=tuple(s.mem[i]for i in range(-156,-4))
        else:e.plain(canonical[0])
        s.trace.append(('CALL',target,canonical,observed,s.fcsr))
        s.trace.append(('PRIVATE_FRAME',s.frame()))
        ordinal=sum(s.calls.values());s.calls[target]+=1;s.epoch+=1
        if target==COPY:
            for i,v in enumerate(observed):s.trace.append(('COPY_WRITE',e.add(args[0],i),v))
        elif s.binding:
            for off in range(-172,-164):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
        for i in range(max(4,count)):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
        for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
        for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
        s.r[2]=args[0]if target==COPY else('CREATED',ordinal)if target==FACTORY else('RESULT',target,ordinal)
        s.r[31]=('CALL_RETURN',ordinal);s.hi,s.lo,s.fcsr=('CALL_HI',ordinal),('CALL_LO',ordinal),('CALL_FCSR',ordinal)
        s.condition=('CALL_CONDITION',ordinal)

def prove(raw,retail,remap=True):
    assert raw[38]==retail[38]==0x24010001,'Preserve the original unreachable duplicate constant'
    terms=Terms();values=[];coverage={}
    for side,words in(('raw',raw),('retail',retail)):
        p=Program(words,terms);paths=p.paths(State(side,remap and side=='raw'));results={}
        for key,s in paths.items():
            assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
            assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
            results[key]=(s.trace,s.read_set,s.frame(),s.r[2],s.fcsr)
        values.append(results);coverage[side]=p.seen
    a,b=values;assert a.keys()==b.keys(),('path predicates',len(a),len(b))
    for key in a:
        if a[key]!=b[key]:
            part=next(i for i,(x,y)in enumerate(zip(a[key],b[key]))if x!=y)
            if part==0:
                x,y=a[key][0],b[key][0];at=next((i for i,(u,v)in enumerate(zip(x,y))if u!=v),min(len(x),len(y)))
                raise AssertionError(('trace',key,at,repr(x[at]if at<len(x)else'<end>')[:1600],repr(y[at]if at<len(y)else'<end>')[:1600]))
            raise AssertionError(('state',key,part,repr(a[key][part])[:1400],repr(b[key][part])[:1400]))
    reachable=set(range(0,460,4))-{38*4}
    for side,seen in coverage.items():assert seen==reachable,('coverage',side,len(seen),sorted(reachable-seen),sorted(seen-reachable))
    return dict(paths=len(a),reachable_words={k:len(v)for k,v in coverage.items()},unreachable_word_preserved=38,
                private_and_incoming_bytes=244,full_binding_and_payload_and_return=True,all_saved_registers_restored=True)

def main(raw,truth):
    from tools.tests import game_owner_record_151b09bc_derive as derive
    from tools.experiments import game_owner_record_151b09bc_match as recovery
    p=recovery.OUT
    derived=derive.derive(raw);assert derived==truth
    report=dict(raw_relation=prove(raw,truth),derived_relation=prove(derived,truth,False))
    controls=[]
    for label,old,new in(
        ('disabled-category',0x24010002,0x24010003),
        ('duration-sentinel',0x2401FFFF,0x24010000),
        ('default-duration',0x2404012C,0x2404012D),
        ('binding-home',0x27A40034,0x27A40038),
        ('copy-size',0x24060098,0x24060094),
        ('retained-created-result',0x8FA300DC,0x8FA300D8),
        ('group-third-word',0xAC40FFF0,0xAC41FFF0),
        ('loop-end',0x27A300C8,0x27A30098),
        ('unreachable-duplicate',None,None)):
        bad=truth[:]
        if old is None:bad[38]=0x24010002
        else:assert bad.count(old)==1,(label,hex(old));bad[bad.index(old)]=new
        try:prove(bad,truth,False)
        except(AssertionError,KeyError,ValueError):controls.append(label)
        else:raise AssertionError(('ineffective proof control',label))
    renamed=[]
    for w in truth:
        op=w>>26;fields=(21,16,11)if op==0 else(16,)if op==17 and w>>21&31==4 else(21,)if op in(49,57)else()if op in(3,17)else(21,16)
        for shift in fields:
            reg=w>>shift&31
            if reg in(24,25):w=(w&~(31<<shift))|((49-reg)<<shift)
        renamed.append(w)
    report.update(effective_negatives=controls,independent_GPR_positive=prove(renamed,truth,False))
    (p/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
