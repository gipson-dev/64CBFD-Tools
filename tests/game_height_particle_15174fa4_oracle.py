"""Independent particle-field model and authentic ten-word caller packets."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,os,struct
from tools.experiments import game_height_particle_15174fa4_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
source.ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();source.OUT=source.ROOT/source.BUILD
ENTRY=source.ENTRY;RESET,ALLOC,RNG,LOOKUP,RELEASE=0x1510f800,0x15167a68,0x150ada20,0x150a3a70,0x1516979c
HEIGHTS,MODEL,PARTICLES,MARK=0x800d3300,0x800ddf14,0x50000,0x90000
u32=lambda n:n&0xffffffff
fmul=lambda a,b:bits(floating(a)*floating(b))
fadd=lambda a,b:bits(floating(a)+floating(b))
class GuestBreak(Exception):pass
@dataclass(frozen=True)
class Case:
    count:int=3
    slot:int=0xabcd0080
    x:int=-32768
    y:int=32767
    z:int=0x7fffffff
    width:int=128
    view:int=0xdeadbeef
    elevated:int=0
    base:int=0x3f4ccccd
    spread:int=0x3f000000
    fail:int=3
    hits:int=5
    mutation:int=0
    alias:bool=False
    phase:int=0
    seed:int=0
def args(c):return tuple(map(u32,(c.count,c.slot,c.x,c.y,c.z,c.width,c.view,c.elevated,c.base,c.spread)))
def home(c):return STACK+c.phase
def particle(c,n):return PARTICLES if c.alias else PARTICLES+(n-1)*256
def random(c,n):return u32((c.seed*0x9e3779b9+n*0x41c64e6d)^0xa55aff00) if c.seed%3 else (0,0xffffffff,127,31,255,65535,15,1)[(n-1)%8]
def height(c,n):return u32((0x7fffffff,-1,-257,0,-2147483648,0x12345678,-256,256,257)[(n+c.seed)%9])
def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,512)}
    for i,v in enumerate(args(c)):put(m,home(c)+4*i,v)
    for n in range(4):m.update({PARTICLES+n*256+i:(i*29+c.seed*11+n+0x59)&255 for i in range(248)})
    for n in range(12):
        for j in range(4):put(m,HEIGHTS+n*16+j*4,height(c,n) if j==0 else 0xabcdef00+n*4+j)
    put(m,MODEL,0x98765430);put(m,MARK,0);return m
def effects(m,c,target,ordinal):
    put(m,MARK,u32(target^ordinal*0x1020304))
    if c.mutation&1:
        put(m,MODEL,0x76540000+ordinal*256)
        for n in range(4):put(m,PARTICLES+n*256+0x92,0x8010+ordinal,2)
        for n in range(12):put(m,HEIGHTS+n*16,u32(height(c,n)+ordinal*0x101))
    if c.mutation&2:
        for i,v in ((0,1+ordinal%3),(1,0x87650000+ordinal),(2,0x87650001),(3,0x87650002),(4,0x87650003+ordinal),(5,3+ordinal%7),(6,0x12345678),(7,ordinal&1),(8,bits(.25+ordinal*.125)),(9,bits(.5+ordinal*.125))):put(m,home(c)+4*i,u32(v))
def reference(initial,c):
    m=dict(initial);calls=[];rng=allocated=0;arg=lambda i:read(m,home(c)+4*i)
    def call(t,a):calls.append((t,tuple(map(u32,a))));effects(m,c,t,len(calls))
    if c.elevated==0:call(RESET,(0,))
    z=arg(4);width=arg(5);i=0
    if signed(arg(0))<=0:return m,calls,False
    def rand():
        nonlocal rng
        call(RNG,());rng+=1;return random(c,rng)
    while True:
        call(ALLOC,(19,0,248,1,255,1));allocated+=1
        if allocated>c.fail:return m,calls,False
        q=particle(c,allocated);half=signed(width)>>1
        r=rand()
        if not width:return m,calls,True
        x=u32(u32(c.x)+r%width-half);zj=u32(z+rand()%width-half)
        m[q+0x90]=arg(1)&255;put(m,q+0x98,bits(float(signed(x))));put(m,q+0x9c,bits(float(c.y)));put(m,q+0xa0,bits(float(signed(zj))))
        put(m,q+0xa4,rand()%3+4,2);put(m,q+0xa6,0,2)
        put(m,q+0xa8,bits(float((rand()&31)-15)));put(m,q+0xac,bits(float(rand()%360)))
        r=rand();put(m,q+0xb4,0);put(m,q+0xbc,0);put(m,q+0xb8,bits(3.));put(m,q+0xb0,bits(float((r&31)-15)))
        r=rand();put(m,q+0xc0,fadd(fmul(fmul(bits(float(r&65535)),0x38000000),arg(9)),arg(8)))
        model=read(m,MODEL);m[q+0xed]=7;put(m,q+0x94,model)
        call(LOOKUP,(x,zj))
        if c.hits==0:call(RELEASE,(q,))
        else:
            lowest=min(signed(read(m,HEIGHTS+16*n)) for n in range(max(1,c.hits)))>>8
            put(m,q+0xc8,bits(float(lowest)))
            if arg(7)==0:
                m[q+0x91]=0;put(m,q+0x9c,bits(float(lowest+10)));put(m,q+0x92,1,2)
            else:
                m[q+0x91]=2;put(m,q+0x92,4,2)
                put(m,q+0xe4,bits(float((rand()&127)+lowest+300)));put(m,q+0x9c,bits(float((rand()&127)+lowest+300)))
            put(m,q+0xcc,0);put(m,q+0xd0,c.x,2);put(m,q+0xd4,z,2);put(m,q+0xd6,half,2);put(m,q+0xe0,0);put(m,q+0xdc,0,2);put(m,q+0xe8,0)
            m[q+0xec]=m[q+0xf0]=m[q+0xf1]=0
        i+=1
        if i==arg(0):return m,calls,False
class Oracle(FactoryOracle):
    def __init__(self,ws,initial,c,entry=ENTRY,connected=None):
        super().__init__(ws,initial,c,entry=entry,arguments=args(c),connected=connected);self.rng=self.allocs=0;self.constructor_calls=[]
    def execute(self,w):
        if w==0x0007000d:raise GuestBreak
        if w>>26==0 and w&63==27 and not self.r[w>>16&31]:self.hi=self.r[w>>21&31];self.lo=0xffffffff
        else:super().execute(w)
    def record_call(self,t):
        if t==ENTRY:self.constructor_calls.append(tuple(self.arguments(10)));return
        a=tuple(self.arguments({RESET:1,ALLOC:6,RNG:0,LOOKUP:2,RELEASE:1}[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        effects(self.memory,self.case,t,len(self.calls));v=0
        if t==RNG:self.rng+=1;v=random(self.case,self.rng)
        elif t==ALLOC:self.allocs+=1;v=particle(self.case,self.allocs) if self.allocs<=self.case.fail else 0
        elif t==LOOKUP:v=u32(self.case.hits)
        for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=v;self.hi,self.lo=0xa5000010,0xa5000011
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
def state(m):return m.memory,m.r,m.f,m.calls,m.trace,m.events,m.hi,m.lo,m.current_pc,m.delay_of
def main():
    rom=(source.ROOT/'conker/conker.us.bin').read_bytes();raw=bound_blob(*payload(source.OUT/'selected.o',source.NAME));retail=list(struct.unpack_from('>251I',rom,source.ROM));assert raw==retail;programs=(retail,raw)
    count=0;coverage=set()
    for n,fail,elevated,hits,mutation,alias in itertools.product((-1,0,1,3),(0,1,3),(0,0x80000001),(0,-1,1,2,3,4,5,9),(0,1,3),(False,True)):
        c=Case(count=n,fail=fail,elevated=elevated,hits=hits,mutation=mutation,alias=alias,seed=count%7,phase=8*(count&1),width=(1,2,128,1024,-1,-2147483648)[count%6]);initial=fixture(c);want,calls,trap=reference(initial,c);assert not trap
        for w in programs:
            m=Oracle(w,initial,c).run();assert (public(m.memory),m.calls)==(public(want),calls),(c,m.calls,calls)
            coverage.update(m.visits)
        count+=1
    caller_count=0
    for elevated,start,end,offset,words,constant in ((0,0x15183504,0x15183550,0x1b09b4,19,0x800a7328),(1,0x15183560,0x151835b0,0x1b0a10,20,0x800a732c)):
        window=list(struct.unpack_from('>%dI'%words,rom,offset));assert window[-2]==0x0c000000|((ENTRY>>2)&0x3ffffff)
        for n,hits,alias in itertools.product((0,1,3),(0,1,5,9),(False,True)):
            c=Case(count=n,hits=hits,elevated=elevated,alias=alias,seed=1,fail=2,width=128,spread=bits(.5));initial=fixture(c)
            for off,v in ((0x68,c.x),(0x6c,c.y),(0x70,c.z),(0x74,c.count),(0x80,c.view),(0x84,c.width>>2)):put(initial,home(c)+off,u32(v))
            put(initial,constant,c.base);want,calls,trap=reference(initial,c)
            for w in programs:
                connected=dict(zip(range(ENTRY,ENTRY+1004,4),w));connected[end]=0;m=Oracle(window,initial,c,entry=start,connected=connected);m.r[16]=u32(c.slot);m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
                try:m.run()
                except WindowBoundary:pass
                else:raise AssertionError('Missing caller boundary')
                assert m.constructor_calls==[args(c)],m.constructor_calls
                assert (public(m.memory),m.calls)==(public(want),calls),(c,m.calls,calls)
            caller_count+=1
    traps=prefixes=0
    for elevated,phase in itertools.product((0,1),(0,8)):
        c=Case(width=0,elevated=elevated,phase=phase);initial=fixture(c);want,calls,trap=reference(initial,c);assert trap;models=[]
        for w in programs:
            m=Oracle(w,initial,c)
            try:m.run()
            except GuestBreak:pass
            else:raise AssertionError('Missing dispatched break 7')
            assert (public(m.memory),m.calls)==(public(want),calls);models.append(m)
        assert state(models[0])==state(models[1]);traps+=1;coverage.update(models[0].visits)
    for c in (Case(count=1),Case(count=3,elevated=1,hits=9,mutation=3,alias=True,phase=8),Case(count=2,hits=0)):
        initial=fixture(c);full=Oracle(retail,initial,c).run()
        for cut in range(full.all_accesses):
            models=[]
            for w in programs:
                m=Oracle(w,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError('Missing memory boundary')
                models.append(m)
            assert state(models[0])==state(models[1]);prefixes+=1
    unvisited=sorted(set(range(ENTRY,ENTRY+1004,4))-coverage)
    assert [a-ENTRY for a in unvisited]==[0x104,0x178,0x17c,0x180,0x330]
    report=dict(semantic_cases=count,caller_cases=caller_count,zero_width_traps=traps,memory_prefixes=prefixes,visited_words=251-len(unvisited),unvisited_word_offsets=[hex(a-ENTRY) for a in unvisited],total_words=251,installed_source='void '+source.NAME+'(' in (source.ROOT/source.SOURCE).read_text())
    (source.OUT/'semantic-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
