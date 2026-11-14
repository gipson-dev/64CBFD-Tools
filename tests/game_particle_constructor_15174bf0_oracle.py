from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,math,struct,sys
from tools.experiments import game_particle_constructor_15174bf0_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
source.ROOT=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();source.OUT=source.ROOT/source.BUILD
ENTRY=source.ENTRY;HEADING,ALLOC,RNG,SOUND,GROUND=0x15048fc8,0x15167a68,0x150ada20,0x10010e78,0x1510f8d8
SCENE,RATE,MODELS,BASE,MATS,KINDS=0x800dbff0,0x800a7174,0x800dde88,0x800dbe3c,0x800dbe5c,0x800a7170
VIEWS,PARTICLES,SURFACES,TABLE,MARK=0x30000,0x50000,0x70000,0x80000,0x90000
u32=lambda n:n&0xffffffff
fadd=lambda a,b:bits(floating(a)+floating(b))
fmul=lambda a,b:bits(floating(a)*floating(b))
class ConversionBoundary(Exception):pass
@dataclass(frozen=True)
class Case:
    count:int=2
    slot:int=0xabcd0080
    x:int=-32768
    y:int=32767
    z:int=0x7fffffff
    view:int=1
    base:int=0x3f4ccccd
    spread:int=0x3f000000
    flags:int=1
    heading:int=0x43b3e000
    fail:int=4
    null_surface:bool=False
    alias:bool=False
    mutation:int=0
    seed:int=0
    phase:int=0
    write_surface:bool=True
    untouched_surface:int=0
def args(c):return tuple(map(u32,(c.count,c.slot,c.x,c.y,c.z,c.view,c.base,c.spread,c.flags)))
def home(c):return STACK+c.phase
def particle(c,n):return PARTICLES if c.alias else PARTICLES+(n-1)*256
def random(c,n):return u32((c.seed*0x9e3779b9+n*0x41c64e6d)^0xa55aff00) if c.seed%3 else (0,0xffffffff,127,31,255,65535,15,1)[(n-1)%8]
def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-768,512)}
    for i,v in enumerate(args(c)):put(m,home(c)+4*i,v)
    if not c.write_surface:put(m,home(c)-0x3c,c.untouched_surface)
    for n in range(4):m.update({PARTICLES+n*256+i:(i*29+c.seed*11+n+0x59)&255 for i in range(248)})
    p=u32(VIEWS+u32(c.view)*0x9a0)
    for i,v in enumerate((bits(2.5),bits(-3.25),bits(7.75))):put(m,p+0x2f8+4*i,v)
    put(m,SCENE,VIEWS);put(m,RATE,bits(.01));put(m,MARK,0)
    for i in range(2):put(m,MODELS+i*20,0x98765430+i*0x1234)
    put(m,BASE,SURFACES);put(m,MATS,TABLE)
    for i in range(-4,8):put(m,TABLE+4*i,u32(((i*0x23456789)^0xabcdef00)|((c.seed&3)<<5)))
    for i in range(4):m[KINDS+i]=(0,42,84,127)[i]
    return m
def effects(m,c,target,ordinal):
    put(m,MARK,u32(target^ordinal*0x1020304))
    if c.mutation&1:
        put(m,RATE,bits(.125+ordinal*.01));put(m,SCENE,VIEWS+0x1000)
        for i in range(2):put(m,MODELS+i*20,0x76540000+ordinal*256+i)
        for n in range(4):put(m,PARTICLES+n*256+0x92,0x8010+ordinal,2)
        for i in range(4):m[KINDS+i]=(ordinal*17+i)&255
    if c.mutation&2:
        for i,v in ((1,0x87650000+ordinal),(2,0x87650001),(3,0x87650002),(4,0x87650003+ordinal),(8,ordinal&1)):
            put(m,home(c)+4*i,v)
        put(m,home(c)+24,bits(.25+ordinal*.125));put(m,home(c)+28,bits(.5+ordinal*.125))
        if target==SOUND:put(m,home(c),1 if c.seed&1 else 3)

def reference(initial,c):
    m=dict(initial);calls=[];rng=0;allocated=0;arg=lambda i:read(m,home(c)+i*4)
    p=u32(read(m,SCENE)+u32(c.view)*0x9a0)
    vec=tuple(bits(floating(bits(float(signed(v))))-floating(read(m,p+0x2f8+4*i))) for i,v in enumerate((u32(c.x),u32(c.y),u32(c.z))))
    def call(t,a):
        calls.append((t,tuple(map(u32,a))));effects(m,c,t,len(calls))
    call(HEADING,vec)
    h=floating(c.heading)
    if not math.isfinite(h) or not -2147483648<=h<2147483648:return m,calls,False
    heading=math.trunc(h);i=0;base=arg(6)
    if signed(arg(0))<=0:return m,calls,True
    factor=read(m,RATE);spread=arg(7);yf=bits(float(c.y))
    def rand():
        nonlocal rng
        call(RNG,());rng+=1;return random(c,rng)
    while True:
        call(ALLOC,(10,0,248,1,255,1));allocated+=1
        if allocated>c.fail:return m,calls,True
        q=particle(c,allocated);grounded=arg(8)&1
        x=u32(rand()+0) # All masks are applied before wrapping coordinate arithmetic.
        x=u32((x&127)+u32(c.x)-63)
        r=rand();z=u32((r&127)+arg(4)-63)
        put(m,q+0x92,3,2);put(m,q+0x9c,yf);put(m,q+0x98,bits(float(signed(x))));m[q+0x90]=arg(1)&255;put(m,q+0xa0,bits(float(signed(z))))
        put(m,q+0xa4,rand()%15+10,2);put(m,q+0xa6,1,2)
        turn=signed(u32((rand()&31)+u32(heading)-15));angle=turn+360 if turn<0 else turn-360 if turn>=360 else turn
        tilt=(rand()&31)-15;put(m,q+0xb0,0);put(m,q+0xb4,bits(-1.));put(m,q+0xa8,bits(float(tilt)));put(m,q+0xac,bits(float(angle)))
        rate=(rand()&255)-128;put(m,q+0xbc,0);put(m,q+0xb8,fmul(bits(float(rate)),factor))
        scale=rand()&65535;put(m,q+0xc0,fadd(fmul(fmul(bits(float(scale)),0x38000000),spread),base))
        variant=rand()&1;m[q+0xed]=variant;put(m,q+0x94,read(m,MODELS+variant*20))
        if i==0:
            call(SOUND,(0,162,32000,0,0,0,x,u32(c.y),z,1000,4000));put(m,q+0xee,0x87658001,2)
        else:put(m,q+0xee,0,2)
        put(m,q+0xe8,0)
        if grounded:
            put(m,q+0x92,read(m,q+0x92,2)|128,2)
            call(GROUND,(x,u32(c.y),z))
            returned=u32(-7-allocated if c.write_surface else -10000);put(m,q+0xc8,bits(float(signed(returned))))
            surface=(0 if c.null_surface else SURFACES+12*(allocated-2)) if c.write_surface else read(m,home(c)-0x3c)
            material=0
            if surface:
                difference=signed(u32(surface-read(m,BASE)));index=(abs(difference)//12)*(-1 if difference<0 else 1)
                material=read(m,u32(read(m,MATS)+index*4))
            put(m,q+0xe8,material);m[q+0xec]=m[KINDS+(material>>5&3)]
        else:m[q+0xec]=0
        m[q+0xf0]=m[q+0xf1]=0;i+=1
        if i==arg(0):return m,calls,True

class Oracle(FactoryOracle):
    def __init__(self,ws,initial,c,entry=ENTRY,connected=None):
        super().__init__(ws,initial,c,entry=entry,arguments=args(c),connected=connected);self.rng=0;self.allocs=0;self.initial_r=self.r[:];self.initial_f=self.f[:];self.constructor_calls=[];self.ground_internal=[]
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63==13:
            v=floating(self.f[w>>11&31])
            if not math.isfinite(v) or not -2147483648<=v<2147483648:raise ConversionBoundary
            self.f[w>>6&31]=u32(math.trunc(v))
        else:super().execute(w)
    def record_call(self,t):
        if t==ENTRY:self.constructor_calls.append(tuple(self.arguments(9)));return
        if t in (0x1510f800,0x150a3a70):self.ground_internal.append((t,tuple(self.arguments(1 if t==0x1510f800 else 2))));return
        if t==HEADING:a=tuple(read(self.memory,self.r[4]+i*4) for i in range(3))
        elif t==GROUND:a=tuple(self.arguments(4)[:3])
        else:a=tuple(self.arguments({ALLOC:6,RNG:0,SOUND:11}[t]))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        a=tuple(self.arguments(4));v=0
        if t not in (0x1510f800,0x150a3a70):effects(self.memory,self.case,t,len(self.calls))
        elif t==0x150a3a70:effects(self.memory,self.case,GROUND,len(self.calls))
        else:assert a[0]==0
        if t==RNG:self.rng+=1;v=random(self.case,self.rng)
        elif t==ALLOC:self.allocs+=1;v=particle(self.case,self.allocs) if self.allocs<=self.case.fail else 0
        elif t==SOUND:v=0x87658001
        elif t==GROUND:
            v=u32(-7-self.allocs if self.case.write_surface else -10000)
            if self.case.write_surface:self.put(a[3],0 if self.case.null_surface else SURFACES+12*(self.allocs-2),4)
        for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=v;self.hi,self.lo=0xa5000010,0xa5000011
        if t==HEADING:self.f[0]=self.case.heading
def public(m):return {a:v for a,v in m.items() if not STACK-768<=a<STACK+512}
def state(m):return m.memory,m.r,m.f,m.calls,m.trace,m.events,m.hi,m.lo,m.current_pc,m.delay_of,m.ground_internal
def main():
    rom=(source.ROOT/'conker/conker.us.bin').read_bytes();ws=bound_blob(*payload(source.OUT/'selected.o',source.NAME));programs=[list(struct.unpack_from('>237I',rom,source.ROM)),ws,bound_blob(*payload(source.OUT/'guarded.o',source.NAME))];assert programs[0]==programs[2]
    count=0
    for n,fail,flags,mutation,null,alias,phase in itertools.product((-1,0,1,3),(0,1,3),(0,1,0x80000001),(0,1,2,3),(False,True),(False,True),(0,8)):
        c=Case(count=n,fail=fail,flags=flags,mutation=mutation,null_surface=null,alias=alias,phase=phase,seed=count%7)
        initial=fixture(c);want,calls,valid=reference(initial,c)
        for w in programs:
            m=Oracle(w,initial,c).run();assert (public(m.memory),m.calls)==(public(want),calls),(c,m.calls,calls)
        count+=1
    caller_count=0;window=struct.unpack_from('>17I',rom,0x1b094c);start,end=0x1518349c,0x151834e0
    assert window[-2]==0x0c000000|((ENTRY>>2)&0x3ffffff)
    for n,slot,flags,mode in itertools.product((0,1,3),(0,3),(0,1,0x80000001),(0,1,2,3)):
        c=Case(count=n,slot=slot,flags=flags,mutation=mode,fail=2,seed=1);initial=fixture(c)
        for offset,value in ((0x68,c.x),(0x6c,c.y),(0x70,c.z),(0x74,c.count),(0x80,c.view),(0x90,c.flags)):
            put(initial,home(c)+offset,u32(value))
        put(initial,0x800a7324,c.base);want,calls,valid=reference(initial,c)
        for w in programs:
            connected=dict(zip(range(ENTRY,ENTRY+4*len(w),4),w));connected[end]=0
            m=Oracle(window,initial,c,entry=start,connected=connected);m.r[16]=slot;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing caller boundary')
            assert m.constructor_calls==[args(c)],m.constructor_calls
            assert (public(m.memory),m.calls)==(public(want),calls),(c,m.calls,calls)
        caller_count+=1
    invalid=0
    for value in (0x7fc01234,0x7f800000,0xff800000,0x4f000000):
        c=Case(heading=value);initial=fixture(c);want,calls,valid=reference(initial,c);assert not valid
        for w in programs:
            m=Oracle(w,initial,c)
            try:m.run()
            except ConversionBoundary:pass
            else:raise AssertionError('Missing conversion boundary')
            assert (public(m.memory),m.calls)==(public(want),calls)
        invalid+=1
    unwritten=connected_fail=0;failure_visits=set()
    real_ground=dict(zip(range(GROUND,GROUND+215*4,4),struct.unpack_from('>215I',rom,0x13cd88)))
    for untouched,alias,mode,phase,connected in itertools.product((0,SURFACES-12,SURFACES+12),(False,True),(0,1,3),(0,8),(False,True)):
        c=Case(write_surface=False,untouched_surface=untouched,alias=alias,mutation=mode,phase=phase,seed=1);initial=fixture(c);want,calls,valid=reference(initial,c)
        for w in (programs[0],programs[2]):
            m=Oracle(w,initial,c,connected=real_ground if connected else None).run()
            assert (public(m.memory),m.calls)==(public(want),calls),(c,m.calls,calls)
            assert read(m.memory,home(c)-0x3c)==untouched
            if connected:
                expected_internal=[]
                for t,a in calls:
                    if t==GROUND:expected_internal.extend(((0x1510f800,(0,)),(0x150a3a70,(a[0],a[2]))))
                assert m.ground_internal==expected_internal
                failure_visits.update(set(real_ground)&m.visits)
        if connected:connected_fail+=1
        else:unwritten+=1
    assert len(failure_visits)==19,len(failure_visits)
    prefixes=0
    cut_cases=((Case(count=1,flags=0),None),(Case(count=3,mutation=1,alias=True,phase=8,seed=1),None),
               (Case(write_surface=False,untouched_surface=SURFACES-12),real_ground))
    for c,connected in cut_cases:
        initial=fixture(c);full=Oracle(programs[0],initial,c,connected=connected).run()
        for cut in range(full.all_accesses):
            models=[]
            for w in (programs[0],programs[2]):
                m=Oracle(w,initial,c,connected=connected);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError('Missing memory boundary')
                models.append(m)
            assert state(models[0])==state(models[1]);prefixes+=1
    unmapped=0
    for connected in (None,real_ground):
        c=Case(write_surface=False,untouched_surface=0x12345678);initial=fixture(c);models=[];errors=[]
        for w in (programs[0],programs[2]):
            m=Oracle(w,initial,c,connected=connected)
            try:m.run()
            except AssertionError as e:
                assert isinstance(e.args[0],tuple) and e.args[0][0]=='unmapped read';errors.append(e.args)
            else:raise AssertionError('Missing unmapped surface boundary')
            models.append(m)
        assert state(models[0])==state(models[1]) and errors[0]==errors[1];unmapped+=1
    report={'semantic_cases':count,'programs':3,'candidate_words':237,'frame':216,'caller_cases':caller_count,'conversion_prefixes':invalid,'unwritten_output_cases':unwritten,'real_ground_failure_cases':connected_fail,'ground_failure_words':len(failure_visits),'memory_prefixes':prefixes,'unmapped_surface_prefixes':unmapped,'installed_source':'void '+source.NAME+'(' in (source.ROOT/source.SOURCE).read_text()}
    (source.OUT/'semantic-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
