"""Independent opacity/state model, late random inputs and registry dispatch."""
from dataclasses import dataclass
import itertools,json,math,struct
from tools.experiments import game_particle_state_15176b84_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
RECORD,MARK,TRACK=0x50000,0x70000,0x71000
MODELS,LOW,HIGH,CONTROL,LIVE,ACTIVE,STEP,ACTOR=0x800dde80,0x800dde84,0x800dde88,0x800ddf78,0x800ddf5c,0x800ddf68,0x800be9e4,0x800cc2d0
FREE,DIST,RANDOM,UPDATE=0x1516972c,0x150ad960,0x150ada20,0x15175958
u32=lambda x:x&0xffffffff
half=lambda x:((x&65535)^32768)-32768
class DivisionBoundary(Exception):pass

@dataclass(frozen=True)
class Case:
    variant:int=7
    slot:int=1
    present:int=1
    enabled:int=1
    live:int=1
    opacity:int=255
    fading:int=0
    state:int=0
    step:int=1
    distance:int=199
    random:int=0x80000081
    divisor:int=-1
    late_divisor:int=-1
    low:int=0
    height:int=0x40000000
    ground:int=0x3f800000
    mode:int=0
    phase:int=0
    seed:int=0
    alias:int=0

def address(c):return (RECORD,ACTIVE+c.variant-0x91,MODELS-0x94)[c.alias]
def snapshot(m,p):return tuple(m[p+i]for i in range(248))

def cases():
    for i,row in enumerate(itertools.product((0,1),(0,1),(0,1),(0,1),(0,1,127,252,255),(0,1,2,3,4,255))):
        present,enabled,live,fading,opacity,state=row
        yield Case(present=present,enabled=enabled,live=live,fading=fading,opacity=opacity,state=state,step=(-1,0,1,65,0x40000000,0x80000000)[i%6],variant=(0,7,10,255)[i%4],slot=(0,7,11,255)[i//4%4],distance=(199,200,-1,0x7fffffff)[i//5%4],seed=i,ground=bits((1.,3.)[i%2]))
    for i in range(256):yield Case(state=i,mode=i%16,opacity=255,step=0,seed=i)
    for divisor,random,mode in itertools.product((0,1,-1,32767,-32768),(0,1,0x7fffffff,0x8000007f,0x80000080,0x80000081,0x8000017f,0xffffffff),(0,2)):
        yield Case(divisor=divisor,late_divisor=divisor,random=random,mode=mode,low=(0,-32768,32767)[random%3])
    for alias,mode,state in itertools.product((1,2),(0,3,15),(0,4,255)):yield Case(alias=alias,mode=mode,state=state)
    for height,ground in ((bits(1.),bits(3.)),(bits(3.),bits(1.)),(bits(2.),bits(2.)),(0x7fc12345,bits(1.)),(bits(1.),0x7fc12345),(0xff800000,0x7f800000),(0x80000000,0)):
        yield Case(state=4,height=height,ground=ground)

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,512)}
    for base,n in ((MODELS-32,5248),(address(c)-16,280),(ACTOR,64),(MARK,4),(TRACK,4)):
        for i in range(n):m.setdefault(base+i,(i*29+c.seed*11+0x59)&255)
    for i in range(256):
        put(m,MODELS+i*20,0x81230000+i*256);put(m,LOW+i*20,0x82340000+i*256);put(m,HIGH+i*20,0x83450000+i*256)
    p=address(c);m[p+0x90]=c.slot;m[p+0x91]=c.state;m[p+0xed]=c.variant;m[p+0xf0]=c.opacity;m[p+0xf1]=c.fading
    for off,value in ((0x94,0x84560000),(0x98,bits(17.75)),(0x9c,c.height),(0xa0,bits(-19.25)),(0xc8,c.ground),(0xe4,bits(13.))):put(m,p+off,value)
    put(m,p+0xd2,c.low&65535,2);put(m,p+0xda,c.divisor&65535,2)
    put(m,MODELS+c.variant*20,0x81230000+c.variant*256 if c.present else 0);put(m,CONTROL+c.variant*4,c.enabled)
    m[LIVE+c.slot]=c.live;put(m,STEP,u32(c.step));put(m,MARK,0)
    put(m,ACTOR+0x14,bits(-123.75));put(m,ACTOR+0x1c,bits(234.5))
    return m

def effects(m,c,t,n):
    p=address(c);put(m,MARK,u32(t^n*0x1020304))
    if t==DIST and c.mode&1 or t==RANDOM and c.mode&2:
        m[p+0xed]=(c.seed+n)%4;m[p+0x90]=(c.seed+n)%12;m[p+0x91]=(c.seed+n)%6
        put(m,p+0xd2,(-7+n)&65535,2);put(m,p+0xda,c.late_divisor&65535,2)
        put(m,p+0x98,bits(10.+n));put(m,p+0xa0,bits(-20.-n));put(m,p+0x9c,bits(3.+n));put(m,p+0xc8,bits(1.+n))
    if t in (FREE,UPDATE)and c.mode&4:m[p+0x91]=0x75;put(m,p+0xb4,0x86780000+n)
    if c.mode&8:
        for i in range(256):put(m,LOW+i*20,0x85670000+n*256+i);put(m,HIGH+i*20,0x86780000+n*256+i)
        put(m,STEP,n+1)

def unsigned_float(value):
    # Preserve the retail signed-conversion rounding before the 2^32 add.
    first=bits(float(signed(value)))
    return bits(floating(first)+4294967296.)if value&0x80000000 else first

def trunc(v):
    f=floating(v);assert math.isfinite(f)and-2147483648<=math.trunc(f)<=2147483647,hex(v)
    return math.trunc(f)

def reference(initial,c):
    m=dict(initial);p=address(c);calls=[];obs=[]
    def call(t,*a):
        calls.append((t,tuple(map(u32,a))));obs.append(snapshot(m,p));effects(m,c,t,len(calls))
        return u32(c.random)if t==RANDOM else u32(c.distance)if t==DIST else 0x87654321
    variant=m[p+0xed]
    if not read(m,MODELS+variant*20)or not read(m,CONTROL+variant*4):call(FREE,p);return m,calls,obs,False
    opacity=m[p+0xf0]
    if not m[p+0xf1]:
        if not m[LIVE+m[p+0x90]]:m[p+0xf1]=1
        elif opacity!=255:
            opacity=signed(u32(opacity+u32(read(m,STEP)<<2)));opacity=255 if opacity>=256 else opacity;m[p+0xf0]=opacity&255
    else:
        if not opacity:call(FREE,p);return m,calls,obs,False
        opacity=signed(u32(opacity-u32(read(m,STEP)<<2)));m[p+0xf0]=max(0,opacity)&255
    m[ACTIVE+m[p+0xed]]=1;state=m[p+0x91]
    if state==0:
        result=call(DIST,trunc(read(m,ACTOR+0x14)),trunc(read(m,ACTOR+0x1c)),trunc(read(m,p+0x98)),trunc(read(m,p+0xa0)))
        if signed(result)<200:
            m[p+0x91]=2;value=call(RANDOM);divisor=u32(half(read(m,p+0xda,2)))
            if not divisor:return m,calls,obs,True
            height=unsigned_float(value%divisor);put(m,p+0xe4,bits(floating(height)+float(half(read(m,p+0xd2,2)))))
            put(m,p+0x94,read(m,HIGH+m[p+0xed]*20))
        else:put(m,p+0x94,read(m,LOW+m[p+0xed]*20))
    elif state==4 and floating(read(m,p+0x9c))<floating(read(m,p+0xc8)):call(FREE,p)
    else:call(UPDATE,p)
    return m,calls,obs,False

class Oracle(FactoryOracle):
    def __init__(self,w,initial,c,entry=source.ENTRY,connected=None):
        super().__init__(w,initial,c,entry=entry,connected=connected,arguments=(address(c),));self.observed=[];self.before_r=self.r[:];self.before_f=self.f[:]
    def execute(self,w):
        if w>>26==0 and w&63==27 and self.r[w>>16&31]==0:raise DivisionBoundary
        return super().execute(w)
    def record_call(self,t):
        if t==source.ENTRY:assert self.r[4]==address(self.case);return
        assert t in (FREE,DIST,RANDOM,UPDATE)
        a=tuple(self.arguments(0 if t==RANDOM else 4 if t==DIST else 1));self.calls.append((t,a));self.observed.append(snapshot(self.memory,address(self.case)));self.events.append(('CALL',t,a))
    def hook(self,t):
        effects(self.memory,self.case,t,len(self.calls));value=self.case.random if t==RANDOM else self.case.distance if t==DIST else 0x87654321
        for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)

def public(m):return {a:v for a,v in m.items()if not STACK-512<=a<STACK+512}
def state(m):return m.memory,m.r,m.f,m.calls,m.observed,m.events,m.trace,m.hi,m.lo,m.current_pc,m.delay_of
def verify(m,initial,c):
    want,calls,obs,zero=reference(initial,c);assert(public(m.memory),m.calls,m.observed)==(public(want),calls,obs),c
    if not zero:assert m.r[16:24]==m.before_r[16:24]and m.r[29:31]==m.before_r[29:31]and m.f[20:]==m.before_f[20:]

def main():
    programs=[source.bound(*payload(source.OUT/n,source.NAME))for n in('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2];seen=set();count=zeroes=0
    for c in cases():
        initial=fixture(c);zero=reference(initial,c)[3];models=[]
        for w in programs:
            m=Oracle(w,initial,c)
            try:m.run();assert not zero
            except DivisionBoundary:assert zero
            verify(m,initial,c);models.append(m)
        assert state(models[0])==state(models[2]);seen.update(models[0].visits);count+=1;zeroes+=zero
    registry=0;rom=(source.ROOT/'conker/conker.us.bin').read_bytes();start,end=0x15167164,0x15167178;window=struct.unpack_from('>5I',rom,0x194614)
    for descriptor,mode,kind,phase in itertools.product((21,22,23,24),(0,1,2,15),(0,1,4,255),(0,8)):
        c=Case(state=kind,mode=mode,phase=phase);initial=fixture(c);table=0x8008b4a8+descriptor*0x34
        assert struct.unpack_from('>I',rom,0x22ff68+descriptor*0x34)[0]==source.ENTRY
        put(initial,table,source.ENTRY);put(initial,TRACK,read(initial,address(c)+8))
        for w in programs:
            code=dict(zip(range(source.ENTRY,source.ENTRY+len(w)*4,4),w));code[end]=0;m=Oracle(window,initial,c,entry=start,connected=code);m.r[16],m.r[17],m.r[18]=address(c),TRACK,table;m.before_r=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing update dispatcher boundary')
            verify(m,initial,c)
        registry+=1
    prefixes=0
    for c in (Case(),Case(mode=15),Case(state=4,ground=bits(3.)),Case(alias=1),Case(present=0)):
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
    for label,pc,word,c in (('distance-boundary',0x180,0x284100c9,Case(distance=200)),('fade-direction',0xec,0x004f1021,Case(fading=1,opacity=127,state=1)),('active-marker',0x10c,programs[0][0x10c//4]&~(31<<16),Case(state=1)),('low-model',0x21c,programs[0][0x21c//4]&0xffff0000|0xde88,Case(distance=200)),('unsigned-correction',0x198,0x3c014f00,Case(random=0x80000081))):
        w=programs[0][:];assert w[pc//4]!=word;w[pc//4]=word;initial=fixture(c)
        try:m=Oracle(w,initial,c);m.run();verify(m,initial,c)
        except AssertionError as e:assert e.args==(c,),(label,e.args)
        else:raise AssertionError('Ineffective emitted control: '+label)
        controls.append(label)
    report=dict(cases=count,predivision_zero_prefixes=zeroes,streams=3,visited_words=155-len(missing),unvisited_offsets=list(map(hex,missing)),dispatcher_cases=registry,registry_slots=4,full_state_prefixes=prefixes,unsigned_rounding_edges=True,emitted_controls=controls,raw_fault_order_claimed=False)
    (source.OUT/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
