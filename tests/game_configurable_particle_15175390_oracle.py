"""Private source behavior and retail-only unwritten-local boundaries; no match credit."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,math,os,struct
from tools.experiments import game_configurable_particle_15175390_recovery as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
source.ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();source.OUT=source.ROOT/source.BUILD
ENTRY=source.ENTRY;HEADING,ALLOC,RNG,GROUND,SOUND=0x15048fc8,0x15167a68,0x150ada20,0x1510f8d8,0x10010e78
SCENE,RATE,MODELS,BASE,MATS,KINDS=0x800dbff0,0x800a7178,0x800dde88,0x800dbe3c,0x800dbe5c,0x800a7170
VIEWS,PARTICLES,SURFACES,TABLE,MARK=0x30000,0x50000,0x70000,0x80000,0x90000
u32=lambda n:n&0xffffffff
fadd=lambda a,b:bits(floating(a)+floating(b))
fmul=lambda a,b:bits(floating(a)*floating(b))
class GuestBoundary(Exception):pass
@dataclass(frozen=True)
class Case:
    count:int=2
    slot:int=0xabcd0080
    x:int=-32768
    y:int=32767
    z:int=0x7fffffff
    outer:int=63
    view:int=1
    vertical:int=30
    inner:int=0
    flags:int=0x30003
    base_type:int=10
    type_range:int=0
    base_model:int=2
    model_mask:int=-1
    state:int=0
    base:int=0x3f4ccccd
    spread:int=0x3f000000
    ground_flags:int=1
    fail:int=3
    mutation:int=0
    alias:bool=False
    phase:int=0
    seed:int=1
    heading:int=0x43b3e000
    ground_height:int=-7
    write_surface:bool=True
    untouched_surface:int=0
    trap:str=''
def args(c):return tuple(map(u32,(c.count,c.slot,c.x,c.y,c.z,c.outer,c.view,c.vertical,c.inner,c.flags,c.base_type,c.type_range,c.base_model,c.model_mask,c.state,c.base,c.spread,c.ground_flags)))
def home(c):return STACK+c.phase
def particle(c,n):return PARTICLES if c.alias else PARTICLES+(n-1)*256
def random(c,n):
    if c.trap=='overflow-first' and n==1 or c.trap=='overflow-second' and n==2:return 0x80000000
    if c.trap=='overflow-second' and n==1:return 1
    return u32((c.seed*0x9e3779b9+n*0x41c64e6d)^0xa55aff00) if c.seed%3 else (0,0xffffffff,127,31,255,65535,15,1)[(n-1)%8]
def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-768,768)}
    for i,v in enumerate(args(c)):put(m,home(c)+4*i,v)
    if not c.write_surface:put(m,home(c)-0x38,c.untouched_surface)
    for n in range(4):m.update({PARTICLES+n*256+i:(i*29+c.seed*11+n+0x59)&255 for i in range(248)})
    p=u32(VIEWS+u32(c.view)*0x9a0)
    for i,v in enumerate((bits(2.5),bits(-3.25),bits(7.75))):put(m,p+0x2f8+4*i,v)
    put(m,SCENE,VIEWS);put(m,RATE,bits(.01));put(m,MARK,0)
    for i in range(16):put(m,MODELS+i*20,0x98765000+i*0x1234)
    put(m,BASE,SURFACES);put(m,MATS,TABLE)
    for i in range(-4,8):put(m,TABLE+4*i,u32(((i*0x23456789)^0xabcdef00)|((c.seed&3)<<5)))
    for i in range(4):m[KINDS+i]=(0,42,84,127)[i]
    return m
def effects(m,c,target,ordinal,rng):
    put(m,MARK,u32(target^ordinal*0x1020304))
    if c.mutation&1:
        put(m,RATE,bits(.125+ordinal*.01));put(m,SCENE,VIEWS+0x1000)
        for i in range(16):put(m,MODELS+i*20,0x76540000+ordinal*256+i)
        for n in range(4):put(m,PARTICLES+n*256+0x92,0x8010+ordinal,2)
        for i in range(4):m[KINDS+i]=(ordinal*17+i)&255
    if c.mutation&2:
        for i,v in ((0,1+ordinal%3),(1,0x87650000+ordinal),(2,-1234+ordinal),(3,333+ordinal),(4,2345+ordinal),(5,100+ordinal%7),(6,2),(7,1+ordinal%31),(8,17+ordinal%3),(9,(0x10000 if ordinal&1 else 0x20000)|(ordinal*3&255)),(10,10 if ordinal%3 else 77),(11,3),(12,2),(13,(0,1,3)[ordinal%3]),(14,ordinal&1),(15,bits(.25+ordinal*.125)),(16,bits(.5+ordinal*.125)),(17,ordinal&1)):put(m,home(c)+4*i,u32(v))
    if target==RNG and c.trap=='type-zero' and rng==1:put(m,home(c)+44,0)
    if target==RNG and c.trap=='vertical-zero' and rng==3:put(m,home(c)+28,0)
def remainder(a,b):
    if not b:raise GuestBoundary('break7')
    if a==-2147483648 and b==-1:raise GuestBoundary('break6')
    q=(abs(a)//abs(b))*(-1 if (a<0)!=(b<0) else 1);return a-q*b
def trunc(value):
    f=floating(value)
    if not math.isfinite(f) or not -2147483648<=f<2147483648:raise GuestBoundary('conversion')
    return math.trunc(f)
def reference(initial,c):
    m=dict(initial);calls=[];rng=allocated=0;arg=lambda i:read(m,home(c)+4*i)
    def call(t,a):calls.append((t,tuple(map(u32,a))));effects(m,c,t,len(calls),rng)
    def rand():
        nonlocal rng
        rng+=1;call(RNG,());return random(c,rng)
    try:
        if c.flags&0x40 and c.vertical<=0:return m,calls,None
        toward=c.flags&0x10000;heading=0
        if toward:
            p=u32(read(m,SCENE)+u32(c.view)*0x9a0)
            vec=tuple(bits(floating(bits(float(signed(v))))-floating(read(m,p+0x2f8+4*i))) for i,v in enumerate((u32(c.x),u32(c.y),u32(c.z))))
            call(HEADING,vec);heading=trunc(c.heading)
        i=0
        if signed(arg(0))<=0:return m,calls,None
        inner=arg(8)
        while True:
            variant=rand() if arg(11) else None
            if variant is None:variant=0
            else:
                d=arg(11)
                if not d:raise GuestBoundary('break7')
                variant%=d
            call(ALLOC,(u32(arg(10)+variant),0,248,1,255,1));allocated+=1
            if allocated>c.fail:return m,calls,None
            q=particle(c,allocated);grounded=arg(17)&1;tilted=arg(9)&0x20000;yy=arg(3);difference=signed(u32(arg(5)-inner))
            r=remainder(signed(rand()),difference);xx=u32(r+inner if r>=0 else r-inner);xx=u32(xx+arg(2))
            r=remainder(signed(rand()),difference);zz=u32(r+inner if r>=0 else r-inner);zz=u32(zz+arg(4))
            if arg(14)==0 or grounded:
                call(GROUND,(xx,arg(3),zz));put(m,q+0xc8,bits(float(signed(u32(c.ground_height-allocated+1)))))
                if c.write_surface:surface=SURFACES+12*(allocated-2)
                else:surface=read(m,home(c)-0x38)
            if arg(14)==0:yy=u32(trunc(read(m,q+0xc8)))
            elif arg(7):
                r=rand();d=arg(7)
                if not d:raise GuestBoundary('break7')
                yy=u32(arg(3)+r%d)
            m[q+0x90]=arg(1)&255;put(m,q+0x92,arg(9),2);m[q+0x91]=arg(14)&255
            for off,v in ((0x98,xx),(0x9c,yy),(0xa0,zz)):put(m,q+off,bits(float(signed(v))))
            put(m,q+0xa4,rand()%15+10,2);put(m,q+0xa6,0,2)
            r=rand()
            if toward:
                angle=signed(u32((r&31)+u32(heading)-15));angle=angle+360 if angle<0 else angle-360 if angle>=360 else angle
            else:angle=r%360
            if tilted:
                r=rand();put(m,q+0xb4,bits(-1.));put(m,q+0xa8,bits(float((r&31)-15)))
            else:put(m,q+0xa8,0);put(m,q+0xb4,0)
            put(m,q+0xb0,0);put(m,q+0xac,bits(float(angle)))
            r=rand();put(m,q+0xbc,0);put(m,q+0xb8,fmul(bits(float((r&255)-128)),read(m,RATE)))
            r=rand();put(m,q+0xc0,fadd(fmul(fmul(bits(float(r&65535)),0x38000000),arg(16)),arg(15)))
            if arg(13)!=0xffffffff:variant=0 if not arg(13) else rand()&arg(13)
            variant=u32(variant+arg(12));model=read(m,u32(MODELS+variant*20));m[q+0xed]=variant&255;put(m,q+0x94,model)
            for off,v in ((0xd0,arg(2)),(0xd2,arg(3)),(0xd4,arg(4)),(0xd8,inner),(0xd6,arg(5)),(0xda,arg(7)),(0xdc,0),(0xde,0)):put(m,q+off,v,2)
            put(m,q+0xe8,0);put(m,q+0xe0,0)
            if i==0:
                if arg(10)==10:call(SOUND,(0,162,32000,0,0,0,xx,yy,zz,1000,4000));put(m,q+0xee,0x8001,2)
            else:put(m,q+0xee,0,2)
            if grounded:
                put(m,q+0x92,read(m,q+0x92,2)|128,2);material=0
                if surface:
                    distance=signed(u32(surface-read(m,BASE)))
                    index=(abs(distance)//12)*(-1 if distance<0 else 1)
                    material=read(m,read(m,MATS)+index*4)
                put(m,q+0xe8,material);m[q+0xec]=m[KINDS+(material>>5&3)]
            else:m[q+0xec]=0
            m[q+0xf0]=m[q+0xf1]=0;i+=1
            if i==arg(0):return m,calls,None
    except GuestBoundary as e:return m,calls,e.args[0]
class Oracle(FactoryOracle):
    def __init__(self,ws,initial,c):super().__init__(ws,initial,c,entry=ENTRY,arguments=args(c));self.rng=self.allocs=0
    def execute(self,w):
        if w in (0x0007000d,0x0006000d):raise GuestBoundary('break7' if w==0x0007000d else 'break6')
        if w>>26==17 and w>>21&31==16 and w&63==13:self.f[w>>6&31]=u32(trunc(self.f[w>>11&31]));return
        if w>>26==0 and w&63 in (26,27) and not self.r[w>>16&31]:self.hi=self.r[w>>21&31];self.lo=0xffffffff;return
        super().execute(w)
    def record_call(self,t):
        if t==HEADING:a=tuple(read(self.memory,self.r[4]+4*i) for i in range(3))
        else:a=tuple(self.arguments({ALLOC:6,RNG:0,GROUND:3,SOUND:11}[t]))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        if t==RNG:self.rng+=1
        effects(self.memory,self.case,t,len(self.calls),self.rng);v=0
        if t==RNG:v=random(self.case,self.rng)
        elif t==ALLOC:self.allocs+=1;v=particle(self.case,self.allocs) if self.allocs<=self.case.fail else 0
        elif t==GROUND:
            v=u32(self.case.ground_height-self.allocs+1)
            if self.case.write_surface:self.put(self.r[7],SURFACES+12*(self.allocs-2),4)
        elif t==SOUND:v=0x87658001
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=v;self.hi,self.lo=0xa5000010,0xa5000011
        if t==HEADING:self.f[0]=self.case.heading
def public(m):return {a:v for a,v in m.items() if not STACK-768<=a<STACK+768}
def run_case(c,programs):
    initial=fixture(c);want,calls,boundary=reference(initial,c);coverage=set()
    for program_index,w in enumerate(programs):
        m=Oracle(w,initial,c);observed=None
        try:m.run()
        except GuestBoundary as e:observed=e.args[0]
        assert observed==boundary,(c,observed,boundary)
        assert (public(m.memory),m.calls)==(public(want),calls),(c,m.calls,calls)
        if program_index==0:coverage.update(m.visits)
    return coverage,calls,boundary
def main():
    rom=(source.ROOT/'conker/conker.us.bin').read_bytes();retail=list(struct.unpack_from('>370I',rom,source.ROM));raw=bound_blob(*payload(source.OUT/'selected.o',source.NAME));assert len(raw)==370 and raw!=retail
    count=0;coverage=set();sound=ground=0
    for n,flags,state,ground_flags,mutation,alias in itertools.product((-1,0,1,3),(0,0x10000,0x20000,0x30000,0x40,0x30040),(0,1,2),(0,1),(0,1,2,3),(False,True)):
        c=Case(count=n,flags=flags,state=state,ground_flags=ground_flags,mutation=mutation,alias=alias,fail=(0,1,3)[count//2%3],type_range=(0,3)[count//3%2],model_mask=(-1,0,3)[count//5%3],base_type=(10,77,125)[count//7%3],vertical=(-1,0,1,30)[count//11%4],seed=count%7,phase=8*(count&1))
        used,calls,b=run_case(c,(retail,raw));assert b is None;coverage.update(used);sound+=sum(t==SOUND for t,a in calls);ground+=sum(t==GROUND for t,a in calls);count+=1
    assert sound and ground
    directed=0
    for heading,base,spread in itertools.product((-400.,-15.,0.,360.,720.,2147483520.,-2147483648.),(-3.25,-0.,.8),(0.,-.5,2.)):
        c=Case(count=1,flags=0x30003,heading=bits(heading),base=bits(base),spread=bits(spread),seed=directed%7,phase=8*(directed&1))
        used,calls,b=run_case(c,(retail,raw));assert b is None;coverage.update(used);directed+=1
    boundaries=[]
    for c in (Case(trap='type-zero',type_range=3),Case(trap='vertical-zero',state=1,ground_flags=0,vertical=1,type_range=0,flags=0),Case(outer=5,inner=5,type_range=0,flags=0),Case(outer=1,inner=2,trap='overflow-first',type_range=0,flags=0),Case(outer=1,inner=2,trap='overflow-second',type_range=0,flags=0),Case(flags=0x10000,heading=0x7fc01234),Case(flags=0x10000,heading=0x4f000000),Case(state=0,ground_height=2147483647)):
        used,calls,b=run_case(c,(retail,raw));assert b;coverage.update(used);boundaries.append(b)
    unwritten=0
    for old,state,alias,phase in itertools.product((0,SURFACES-12,SURFACES+12),(0,1),(False,True),(0,8)):
        c=Case(write_surface=False,untouched_surface=old,state=state,ground_flags=1,alias=alias,phase=phase,count=2,flags=0);used,calls,b=run_case(c,(retail,));assert b is None;coverage.update(used);unwritten+=1
    missing=sorted(set(range(ENTRY,ENTRY+1480,4))-coverage)
    report=dict(semantic_cases=count,directed_source_cases=directed,source_streams=2,source_guest_boundaries=boundaries,retail_only_unwritten_cases=unwritten,sound_calls=sound,ground_calls=ground,retail_words_visited=370-len(missing),retail_unvisited_offsets=[hex(a-ENTRY) for a in missing],raw_words=370,frame=184,word_differences=201,c_match_credit=0,installed=False,native_or_caller_execution_claimed=False)
    (source.OUT/'semantic-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
