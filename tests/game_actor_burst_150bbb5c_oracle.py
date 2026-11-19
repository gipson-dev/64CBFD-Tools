"""Independent bounded burst reference; no private-frame or matching credit."""
from dataclasses import dataclass
import itertools
import json
import struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_actor_attached_emitter_150bb760_oracle import unspecified
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.test_game_point_transform_match import put, read

from tools.experiments import game_actor_burst_150bbb5c_recovery as source
P = source.OUT
ENTRY = 0x150BBB5C
RNG, REAL, SINE = 0x150ADA20, 0x150ADA68, 0x151423D8
COLOR, SPRITE, FACTORY, TRAIL, SOUND = 0x1516865C, 0x15168800, 0x15132A4C, 0x151DA6F8, 0x10010F88
COUNTS = {RNG:0, REAL:0, SINE:1, COLOR:5, SPRITE:3, FACTORY:6, TRAIL:18, SOUND:10}
ACTOR = 0x10000
GLOBALS = tuple(range(0x8009FEA8, 0x8009FEBC, 4))
u32 = lambda x: x & 0xFFFFFFFF
short = lambda x: ((x & 65535) ^ 32768) - 32768
mul = lambda a,b: fp(a,b,'mul','left')
add = lambda a,b: fp(a,b,'add','left')
sub = lambda a,b: fp(a,b,'sub','left')
public = lambda m: {a:b for a,b in m.items() if not STACK-4096 <= a < STACK+4096}

@dataclass(frozen=True)
class Case:
    seed:int = 0
    pattern:int = 0
    mutation:int = 0
    phase:int = 0
    gate:int = 2
    actor:int = ACTOR

def fixture(c):
    m = {STACK+i:(17*i+13*c.seed+165)&255 for i in range(-4096,4096)}
    m.update({c.actor+i:(29*i+7*c.seed+83)&255 for i in range(0x400)})
    put(m,c.actor,0 if c.gate==1 else 1)
    m[c.actor+4] = 31 if c.gate==0 else 32
    put(m,c.actor+0x1D4,0 if c.pattern&1 else 0x30000)
    put(m,c.actor+0x184,(0,31,32,0xFFFFFFFF)[c.pattern])
    put(m,c.actor+0x76,((0,127,128,255)[c.pattern]<<8)|c.seed,2)
    for offset,value in ((0x14,1.25),(0x18,-2.5),(0x1C,3.75),(0x3C,(0.,-0.,1.5,-2.25)[c.pattern]),
            (0x180,-19.75),(0xB8,45.),(0x40,-90.),(0xC4,180.),(0x14C,1.5),(0x150,.75)):
        put(m,c.actor+offset,bits(value))
    for offset,value in ((0xE4,(-32768,0,17,32767)[c.pattern]),(0xE6,(32767,-91,0,-32768)[c.pattern])):
        put(m,c.actor+offset,value,2)
    for address,value in zip(GLOBALS,(.25,1.25,.125,-.5,-1.5)):
        put(m,address,bits(value))
    return m

def random(c,index):
    if index==0:return ((c.seed&3)|((0,0x80000000,0x7FFFFFFC,0xFFFFFFFC)[c.pattern]))&0xFFFFFFFF
    if index==1:return (((c.seed>>2)&3)|((0,0x80000000,0x7FFFFFFC,0xFFFFFFFC)[c.pattern]))&0xFFFFFFFF
    values=(0,0xFFFFFFFF,0x80000000,0x7FFFFFFF,31,32,63,64,127,128,255,0x12345678)
    return values[(c.seed+index*5)%len(values)]

def real(c,index):
    return bits((0.,-0.,.125,.5,1.,-.5,1.25)[(c.seed+index*3)%7])

def sine(c,angle):
    angle &= 255
    return bits(-0. if angle==0 and c.seed&1 else ((angle^128)-128)/128.)

def effects(m,c,target,index):
    if not c.mutation:return
    a=c.actor
    if target==RNG and index==0:
        put(m,a+0xE4,77,2);put(m,a+0xE6,-88,2)
    if target==SINE and index==0:
        put(m,a+0x76,0xA531,2)
    if target==SINE and index==1:
        put(m,a+0x3C,bits(4.25));put(m,a+0x180,bits(29.5))
    if target==REAL and index==2:
        put(m,GLOBALS[1],bits(-1.75))
    if target==RNG:
        put(m,GLOBALS[2],bits((index%7-3)*.25))
    if target==FACTORY and index==0:
        for offset,value in ((0x14,123.5),(0x18,456.25),(0x1C,-789.75),(0x14C,-2.25),(0x150,1.75)):
            put(m,a+offset,bits(value))
    if target==SPRITE:
        put(m,GLOBALS[0],bits(-.125))

def packet_bytes(d):
    return tuple(d[i] for i in range(124) if not unspecified(i))

def sprite_bytes(d):
    # Vertices are initialized by the opaque color service; capture its input
    # header fields. Reserved bytes have no portable initialization contract.
    return tuple(d[i] for i in (*range(0x80,0x84),*range(0x88,0x9A),*range(0xA0,0xA3)))

def reference(initial,c):
    m=dict(initial);calls=[];observations=[];counts={t:0 for t in COUNTS}
    a=c.actor
    if m[a+4]!=32 or a==0 or read(m,a)==0:return public(m),calls,observations
    def invoke(t,args=()):
        index=counts[t];counts[t]+=1
        calls.append((t,args))
        answer=random(c,index) if t==RNG else real(c,index) if t==REAL else sine(c,args[0]) if t==SINE else 0xDEADBEEF
        effects(m,c,t,index)
        return answer
    def load(offset):return read(m,a+offset)
    def f32(value):return bits(float(value))
    width=f32(short(read(m,a+0xE4,2)));height=f32(short(read(m,a+0xE6,2)))
    n=(invoke(RNG)&3)+6;k=(invoke(RNG)&3)+10
    hs=invoke(SINE,(read(m,a+0x76,2)>>8,))
    hc=invoke(SINE,(((read(m,a+0x76,2)>>8)+64)&255,))
    motion=load(0x3C);dx=mul(mul(motion,hs),bits(.5));dz=mul(mul(motion,hc),bits(.5))
    alpha=255 if not load(0x1D4) else (255-((load(0x184)>>5)<<6))&255
    sprite=bytearray(168)
    for offset,value,size in ((0x80,alpha,4),(0x88,0,2),(0x8A,128,2),
            (0x8C,int(floating(load(0x14))),2),(0x8E,int(floating(add(load(0x180),bits(60.)))) ,2),
            (0x90,int(floating(load(0x1C))),2),(0x92,int(floating(width)),2),(0x94,int(floating(height)),2),
            (0x96,int(floating(load(0x180))),2),(0x98,52,2),(0xA0,46,1),(0xA1,0,1),(0xA2,255,1)):
        sprite[offset:offset+size]=(value&((1<<(size*8))-1)).to_bytes(size,'big')
    observations.append((COLOR,sprite_bytes(sprite)))
    invoke(COLOR,('sprite',255,255,255,255));invoke(SPRITE,('sprite',255,0))
    d=bytearray(124)
    def field(offset,value,size=4):d[offset:offset+size]=(value&((1<<(size*8))-1)).to_bytes(size,'big')
    def emit():
        observations.append((FACTORY,packet_bytes(d)))
        invoke(FACTORY,('descriptor',3,255,0,255,0))
    for offset,value,size in ((0x56,1,2),(0x54,120,2),(0x50,0x29E9,4),(0x58,0,1),(0x5C,0,4),
            (0x60,255,1),(0x61,1,1),(0x62,0,1),(0x63,2,1),(0x64,0,1),(0x65,0,1),(0x66,0,1),
            (0x67,0,1),(0x68,0,1),(0x6A,0,1),(0x6C,0,4),(0x70,0,1),(0x72,32,2),(0x74,7,2),
            (4,read(m,GLOBALS[0]),4),(0x48,0,4),(0x4C,bits(-1.5),4)):
        field(offset,value,size)
    for offset in (0x1C,0x20,0x24):field(offset,bits(1.))
    size_base=read(m,GLOBALS[1])
    for unused in range(n):
        angle=invoke(RNG)&255;rs=invoke(SINE,(angle,));rc=invoke(SINE,((angle-64)&255,))
        radius=mul(invoke(REAL),width);ox=mul(rs,radius);oz=mul(rc^0x80000000,radius)
        angle=invoke(RNG)&255;ss=invoke(SINE,(angle,));sc=invoke(SINE,((angle-64)&255,))
        speed=add(mul(invoke(REAL),bits(4.)),bits(2.));vx=mul(sc,speed);vz=mul(ss,speed)
        first=add(mul(invoke(REAL),size_base),size_base);second=add(mul(invoke(REAL),size_base),size_base)
        field(8,first);field(12,second);field(0,mul(add(first,second),bits(.5)))
        for offset in (0x10,0x14,0x18):field(offset,mul(invoke(REAL),bits(360.)))
        field(0x28,add(load(0x14),ox));sample=invoke(REAL)
        field(0x2C,add(add(mul(sample,height),load(0x18)),bits(5.)))
        field(0x34,add(dx,vx));field(0x30,add(load(0x1C),oz))
        field(0x38,add(mul(invoke(REAL),bits(7.)),bits(13.)));field(0x3C,add(dz,vz))
        field(0x40,sub(bits(25.),mul(invoke(REAL),bits(50.))));field(0x44,sub(bits(25.),mul(invoke(REAL),bits(50.))))
        emit()
    for unused in range(k):
        radius=mul(invoke(REAL),width);speed=add(mul(invoke(REAL),bits(7.)),bits(7.))
        angle=invoke(RNG)&255;ss=invoke(SINE,(angle,));sc=invoke(SINE,((angle-64)&255,))
        x=add(load(0x14),mul(ss,radius));sample=invoke(REAL)
        y=add(add(mul(sample,height),load(0x18)),bits(5.));vx=add(mul(sc,speed),dx)
        z=sub(load(0x1C),mul(sc,radius));vy=add(mul(invoke(REAL),bits(9.)),bits(15.));vz=add(mul(ss,speed),dz)
        first=invoke(RNG);second=invoke(RNG);sample=invoke(REAL);selector=invoke(RNG)
        duration=(first&7)+25;color=(second&127)+128
        time=add(mul(mul(sample,read(m,GLOBALS[2])),width),bits(13.))
        observations.append((TRAIL,(x,y,z),(vx,vy,vz)))
        invoke(TRAIL,('position','velocity',bits(1.6),duration,color,time,(selector&3)+2,0,
            bits(1.),bits(1.),1,1,0,16,15,0,255,0))
    field(0x56,0,2);field(0x54,(invoke(RNG)&15)+16,2);field(4,read(m,GLOBALS[3]))
    for offset,actor_offset in ((0x10,0xB8),(0x14,0x40),(0x18,0xC4)):field(offset,load(actor_offset))
    field(0x50,0x39E8)
    for offset in (0x1C,0x20,0x24):field(offset,bits(1.))
    field(0x48,0);field(0x4C,read(m,GLOBALS[4]))
    for offset,actor_offset in ((0x28,0x14),(0x2C,0x18),(0x30,0x1C)):field(offset,load(actor_offset))
    field(0,mul(load(0x14C),bits(20.)));sample=load(0x14C);field(8,add(sample,sample));field(12,add(sample,sample))
    for offset,value,size in ((0x58,0,1),(0x5C,0,4),(0x60,255,1),(0x61,1,1),(0x62,0,1),(0x63,0,1),
            (0x64,0,1),(0x65,0,1),(0x66,0,1),(0x67,0,1),(0x68,0,1),(0x6A,0,1),(0x6C,0,4),
            (0x70,0,1),(0x72,16,2),(0x74,15,2)):
        field(offset,value,size)
    for unused in range(2):
        sample=invoke(REAL);speed=add(mul(mul(sample,bits(30.)),load(0x150)),bits(10.))
        angle=invoke(RNG)&127;pitch=-32-(invoke(RNG)&31)
        ss=invoke(SINE,(angle,));sc=invoke(SINE,((angle-64)&255,));ps=invoke(SINE,(pitch&255,));pc=invoke(SINE,((pitch-64)&255,))
        horizontal=mul(speed,ps)
        field(0x38,mul(speed^0x80000000,pc));field(0x34,add(mul(horizontal,sc),dx));field(0x3C,add(mul(horizontal,ss),dz))
        field(0x40,sub(bits(30.),mul(invoke(REAL),bits(60.))));field(0x44,sub(bits(30.),mul(invoke(REAL),bits(60.))))
        emit()
    invoke(SOUND,(170,26000,0,0,0,u32(int(floating(load(0x14)))),u32(int(floating(load(0x18)))),u32(int(floating(load(0x1C)))),200,2000))
    return public(m),calls,observations

class Oracle(FactoryOracle):
    def __init__(self,words,initial,c):
        super().__init__(words,initial,c,entry=ENTRY,s={},arguments=(c.actor,))
        self.cc=c;self.calls=[];self.obs=[];self.indices={t:0 for t in COUNTS}
        self.saved={i:self.r[i] for i in (*range(16,24),28,29,30)}
        self.saved_fp=tuple(self.f[20:])
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63 in (0,1,2,3):
            self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul','div')[w&63],'left');return
        if w>>26==17 and w>>21&31==16 and w&63==7:
            self.f[w>>6&31]=self.f[w>>11&31]^0x80000000;return
        return super().execute(w)
    def record_call(self,t):
        assert t in COUNTS,hex(t)
        raw=tuple(self.arguments(COUNTS[t]));a=list(raw)
        if t in (COLOR,SPRITE):a[0]='sprite'
        if t==FACTORY:a[0]='descriptor'
        if t==TRAIL:a[:2]=['position','velocity']
        self.calls.append((t,tuple(a)));self.actual_args=raw
        if t==COLOR:self.obs.append((t,sprite_bytes(bytes(self.memory[raw[0]+i] for i in range(168)))))
        if t==FACTORY:self.obs.append((t,packet_bytes(bytes(self.memory[raw[0]+i] for i in range(124)))))
        if t==TRAIL:self.obs.append((t,tuple(read(self.memory,raw[0]+i*4) for i in range(3)),tuple(read(self.memory,raw[1]+i*4) for i in range(3))))
    def hook(self,t):
        c=self.cc;i=self.indices[t];self.indices[t]+=1
        answer=random(c,i) if t==RNG else real(c,i) if t==REAL else sine(c,self.actual_args[0]) if t==SINE else 0xDEADBEEF
        effects(self.memory,c,t,i)
        # Only the ABI argument-home area may be clobbered by opaque helpers.
        for j in range(max(4,COUNTS[t])):self.put(self.r[29]+4*j,0xB5000000+j,4)
        for j in (1,2,3,*range(4,16),24,25):self.r[j]=0xA5000000+j
        self.f[:20]=[0xA5000000+j for j in range(20)]
        self.r[2]=u32(answer);self.hi=self.lo=0xDEADBEEF
        if t in (REAL,SINE):self.f[0]=answer

def run():
    code=source.state();seen=set();cases=[]
    cases.extend(Case(seed,pattern,mutation,phase) for seed,pattern,mutation,phase in itertools.product(range(16),range(4),(0,1),(0,8)))
    cases.extend(Case(seed,pattern,1,0,gate) for seed,pattern,gate in itertools.product((0,15),range(4),(0,1)))
    cases.extend((Case(actor=0,gate=0),Case(actor=0,gate=2)))
    for index,c in enumerate(cases):
        initial=fixture(c);expected=reference(initial,c)
        for label,words in code.items():
            machine=Oracle(words,initial,c).run()
            actual=(public(machine.memory),machine.calls,machine.obs)
            if actual!=expected:
                detail=dict(label=label,case=c.__dict__,public_equal=actual[0]==expected[0],calls_equal=actual[1]==expected[1],observations_equal=actual[2]==expected[2])
                for key,observed,wanted in (('calls',actual[1],expected[1]),('observations',actual[2],expected[2])):
                    if observed!=wanted:
                        detail[key]=next(((i,x,y) for i,(x,y) in enumerate(itertools.zip_longest(observed,wanted)) if x!=y),None)
                (P/'guest-failure.json').write_text(json.dumps(detail,indent=2)+'\n')
                raise AssertionError(detail)
            assert all(machine.r[i]==v for i,v in machine.saved.items())
            assert tuple(machine.f[20:])==machine.saved_fp
            if label=='retail':seen|=machine.visits
        if index%128==0:print(json.dumps(dict(completed=index+1,total=len(cases))),flush=True)
    report=dict(passes=True,cases=len(cases),programs=2,executions=len(cases)*2,retail_words_visited=len(seen),
        source_installed=False,c_match_credit=0,private_frame_equality_claimed=False,uninitialized_bytes_compared=False,
        complete_caller_qualified=False,opaque_helpers_qualified=False,private_pointer_locations_compared=False)
    (P/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    return report

def faults():
    reports=[]
    for label,words in source.state().items():
        c=Case(actor=0);initial=fixture(c);del initial[4]
        machine=Oracle(words,initial,c)
        try:machine.run()
        except AssertionError as error:assert error.args[0]==('unmapped read',4,1),error
        else:raise AssertionError(('missing byte4 fault',label))
        assert not machine.calls
        indices=[i for i,word in enumerate(words) if word==0x926E0004]
        assert len(indices)==1
        bad=list(words);bad[indices[0]]=0x240E0020
        control=Oracle(bad,initial,c).run();assert not control.calls
        reports.append(dict(label=label,byte4_fault=True,missing_read_control_effective=True))
    report=dict(passes=True,programs=len(reports),controls=reports,
        native_null_semantics_claimed=False,raw_private_fault_equivalence_claimed=False)
    (P/'fault-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
