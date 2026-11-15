"""Independent rise, idle tilt and steering model with late provider mutations."""
from dataclasses import dataclass
import itertools,json,struct
from tools.experiments import game_particle_rise_1517685c_match as source
from tools.tests import game_particle_state_15176b84_oracle as base
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
bits,floating,read,put,u32,signed=base.bits,base.floating,base.read,base.put,base.u32,base.signed
RECORD,MARK,TRACK,MODELS,LOW,HIGH,CONTROL,LIVE,ACTIVE,STEP,ACTOR=base.RECORD,base.MARK,base.TRACK,base.MODELS,base.LOW,base.HIGH,base.CONTROL,base.LIVE,base.ACTIVE,base.STEP,base.ACTOR
FREE,DIST,RANDOM,UPDATE=base.FREE,base.DIST,base.RANDOM,base.UPDATE
address,snapshot,public=base.address,base.snapshot,base.public
def state(m):return (*base.state(m),m.condition)

@dataclass(frozen=True)
class Case(base.Case):
    distance:int=400
    tilt:int=0x41f00000
    tilt_step:int=0xc0a00000
    heading:int=0x41a00000
    angular:int=0x40000000
    speed:int=0xbf800000
    target:int=0x43c80000
    flags:int=0x1235
    samples:tuple=(50,0xffffffff)

def sample(c,draw):assert draw<2;return c.samples[draw]

def cases():
    for i in range(256):yield Case(state=i,mode=i%32,phase=8*(i&1),seed=i)
    for rate,tilt,random,mode,phase in itertools.product((-5.,0.,5.,-0.,float('nan'),float('inf')),(9.,10.,25.,26.,40.,45.,46.,float('nan')),(0,12,24,255),(0,16,31),(0,8)):
        yield Case(tilt=bits(tilt),tilt_step=bits(rate),samples=(random,0xffffffff),mode=mode,phase=phase)
    for distance,live,mode,phase in itertools.product((399,400,401,-1,0x7fffffff,-0x80000000),(0,1),(0,1,2,16,31),(0,8)):
        yield Case(distance=distance,live=live,mode=mode,phase=phase)
    for rate,first,second,mode in itertools.product((0.,-5.),(0,12,13,24,25,50,51,255),(0,1,5,6,0x80000001,0xffffffff),(0,16)):
        yield Case(tilt_step=bits(rate),samples=(first,second),mode=mode)
    for flags,random,mode,height in itertools.product((0,1,0x1235,0x8001,0xffff),(0,127,0xffffffff),(0,2,16,31),(300.,301.)):
        yield Case(state=1,ground=bits(0.),height=bits(height),flags=flags,samples=(random,0),mode=mode)
    for kind,height,target,tilt in itertools.product((2,3,255),(0.,400.,401.,float('nan')),(400.,float('nan')),(-1.,0.,float('nan'))):
        yield Case(state=kind,height=bits(height),target=bits(target),tilt=bits(tilt))
    for alias,kind,mode in itertools.product((1,2),(0,1,2,255),(0,16,31)):yield Case(alias=alias,state=kind,mode=mode)

def fixture(c):
    m=base.fixture(c);p=address(c)
    for off,value in((0xa8,c.tilt),(0xac,c.heading),(0xb4,c.speed),(0xb8,c.angular),(0xcc,c.tilt_step),(0xe4,c.target)):put(m,p+off,value)
    put(m,p+0x92,c.flags&65535,2);return m

def effects(m,c,t,n):
    base.effects(m,c,t,n)
    if c.mode&16:
        p=address(c)
        for off,value in((0xa8,bits((7.,28.,50.)[n%3])),(0xac,bits(20.+n)),(0xb8,bits(-3.+n)),(0xcc,bits((-5.,0.,5.)[n%3])),(0xc8,bits(3.+n)),(0xe4,bits(300.+n))):put(m,p+off,value)
        put(m,p+0x92,(0x4321+n)&65535,2)

def reference(initial,c):
    m=dict(initial);p=address(c);calls=[];obs=[];draws=0
    def call(t,*args):
        nonlocal draws
        calls.append((t,tuple(map(u32,args))));obs.append(snapshot(m,p));value=sample(c,draws)if t==RANDOM else c.distance if t==DIST else 0x87654321
        if t==RANDOM:draws+=1
        effects(m,c,t,len(calls));return u32(value)
    def f(off):return floating(read(m,p+off))
    if not m[LIVE+m[p+0x90]]:call(FREE,p);return m,calls,obs,False
    m[ACTIVE+m[p+0xed]]=1;kind=m[p+0x91]
    if kind==0:
        result=call(DIST,base.trunc(read(m,ACTOR+0x14)),base.trunc(read(m,ACTOR+0x1c)),base.trunc(read(m,p+0x98)),base.trunc(read(m,p+0xa0)))
        if signed(result)<400:
            m[p+0x91]=1;value=call(RANDOM);put(m,p+0xa8,bits(-8.));put(m,p+0xb4,bits(float(-1-(value&3))))
        elif f(0xcc)!=0.:
            step=f(0xcc);put(m,p+0xa8,bits(f(0xa8)+step))
            if step<0.:put(m,p+0xac,bits(f(0xac)+f(0xb8)))
            if f(0xa8)>45.:put(m,p+0xcc,bits(-5.))
            elif f(0xcc)<0. and f(0xa8)>25.:
                value=call(RANDOM)
                if value&255<51:put(m,p+0xcc,bits(5.))
            if f(0xa8)<=10.:put(m,p+0xcc,0)
        else:
            value=call(RANDOM)&255
            if value<25:
                put(m,p+0xcc,bits(5.))
                if value<13:put(m,p+0xb8,bits(float(call(RANDOM)%6-3)))
                else:put(m,p+0xb8,0)
    elif kind==1:
        if f(0x9c)>=floating(bits(300.+f(0xc8))):
            m[p+0x91]=2;put(m,p+0x92,read(m,p+0x92,2)&65534,2);put(m,p+0x92,read(m,p+0x92,2)|4,2)
            value=call(RANDOM)&127;put(m,p+0xe4,bits(float(value)+floating(bits(300.+f(0xc8)))))
        call(UPDATE,p)
    else:
        if f(0x9c)<f(0xe4):put(m,p+0xb4,bits(-1.5))
        elif f(0xa8)<0.:put(m,p+0xb4,bits(1.5))
        call(UPDATE,p)
    return m,calls,obs,False

class Oracle(FactoryOracle):
    def __init__(self,w,initial,c,entry=source.ENTRY,connected=None):
        super().__init__(w,initial,c,entry=entry,connected=connected,arguments=(address(c),));self.draws=0;self.observed=[];self.before_r=self.r[:];self.before_f=self.f[:]
    def record_call(self,t):
        if t==source.ENTRY:assert self.r[4]==address(self.case);return
        assert t in(FREE,DIST,RANDOM,UPDATE);a=tuple(self.arguments(0 if t==RANDOM else 4 if t==DIST else 1));self.calls.append((t,a));self.events.append(('CALL',t,a));self.observed.append(snapshot(self.memory,address(self.case)))
    def hook(self,t):
        value=sample(self.case,self.draws)if t==RANDOM else self.case.distance if t==DIST else 0x87654321
        if t==RANDOM:self.draws+=1
        effects(self.memory,self.case,t,len(self.calls))
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value);self.condition=bool((len(self.calls)+self.case.seed)&1)

def verify(m,initial,c):
    want,calls,obs,_=reference(initial,c);assert(public(m.memory),m.calls,m.observed)==(public(want),calls,obs),c
    assert m.r[16:24]==m.before_r[16:24]and m.r[29:31]==m.before_r[29:31]and m.f[20:]==m.before_f[20:]

def main():
    programs=[source.bound(*payload(source.OUT/n,source.NAME))for n in('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2];seen=set();count=0
    for c in cases():
        initial=fixture(c);models=[]
        for w in programs:m=Oracle(w,initial,c);m.run();verify(m,initial,c);models.append(m)
        assert state(models[0])==state(models[2]);seen.update(models[0].visits);count+=1
    dispatcher=0;rom=(source.ROOT/'conker/conker.us.bin').read_bytes();start,end=0x15167164,0x15167178;window=struct.unpack_from('>5I',rom,0x194614);table=0x8008b4a8+19*0x34
    assert struct.unpack_from('>I',rom,0x22ff68+19*0x34)[0]==source.ENTRY
    for kind,mode,live,phase in itertools.product((0,1,2,255),(0,3,16,31),(0,1),(0,8)):
        c=Case(state=kind,mode=mode,live=live,phase=phase);initial=fixture(c);put(initial,table,source.ENTRY);put(initial,TRACK,0x12345678)
        expected=dict(initial);put(expected,TRACK,read(initial,address(c)+8));assert expected!=initial
        for w in programs:
            code=dict(zip(range(source.ENTRY,source.ENTRY+len(w)*4,4),w));code[end]=0;m=Oracle(window,initial,c,entry=start,connected=code);m.r[16],m.r[17],m.r[18]=address(c),TRACK,table;m.before_r=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing update dispatcher boundary')
            verify(m,expected,c)
        dispatcher+=1
    c=Case();initial=fixture(c);put(initial,table,source.ENTRY);put(initial,TRACK,0x12345678);expected=dict(initial);put(expected,TRACK,read(initial,address(c)+8))
    changed=list(window);stores=[i for i,w in enumerate(changed)if w>>26==43];assert len(stores)==1;changed[stores[0]]=0
    code=dict(zip(range(source.ENTRY,source.ENTRY+source.SIZE,4),programs[2]));code[end]=0;m=Oracle(changed,initial,c,entry=start,connected=code);m.r[16],m.r[17],m.r[18]=address(c),TRACK,table;m.before_r=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing altered caller boundary')
    try:verify(m,expected,c)
    except AssertionError as e:assert e.args==(c,)
    else:raise AssertionError('Ineffective missing bookkeeping control')
    prefixes=0
    for c in(Case(),Case(tilt_step=0,samples=(12,0xffffffff),mode=31),Case(state=1,height=bits(400.),ground=bits(0.),mode=16),Case(state=2),Case(live=0),Case(alias=1)):
        initial=fixture(c);full=Oracle(programs[0],initial,c);full.run()
        for cut in range(full.all_accesses):
            models=[]
            for w in(programs[0],programs[2]):
                m=Oracle(w,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError('Missing target-memory boundary')
                models.append(m)
            assert state(models[0])==state(models[1]);prefixes+=1
    missing=sorted(pc-source.ENTRY for pc in set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-seen)
    controls=[]
    for label,pc,word,c in(('distance-boundary',0xa8,0x28410191,Case()),('idle-threshold',0x1dc,0x28610018,Case(tilt_step=0,samples=(24,0))),('flag-transition',0x270,0x356d0002,Case(state=1,height=bits(400.),ground=0)),('steering-sign',0x2b4,0x3c013fc0,Case(state=2)),('tilt-clamp',0x130,0x4600803e,Case(tilt=bits(40.),tilt_step=bits(5.)))):
        w=programs[0][:];assert w[pc//4]!=word;w[pc//4]=word;initial=fixture(c)
        try:m=Oracle(w,initial,c);m.run();verify(m,initial,c)
        except AssertionError as e:assert e.args==(c,),(label,e.args)
        else:raise AssertionError('Ineffective emitted control: '+label)
        controls.append(label)
    report=dict(cases=count,streams=3,visited_words=202-len(missing),unvisited_offsets=list(map(hex,missing)),dispatcher_cases=dispatcher,registry_slots=1,full_state_prefixes=prefixes,emitted_controls=controls,bookkeeping_control_killed=True,raw_fault_order_claimed=False)
    (source.OUT/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
