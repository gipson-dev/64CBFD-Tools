"""Independent actor trail reference with mutable retained helper outputs."""
from pathlib import Path
from dataclasses import dataclass,asdict
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_actor_trail_151b01b8_derive as normalizer
from tools.experiments import game_actor_trail_151b01b8_match as recovery

p=recovery.OUT
ENTRY=0x151B01B8
A,S,M1,M2,MARK,TABLE,POINT,COEF=0x30000,0x90000,0x50000,0x60000,0x70000,0x800A3FD8,0x800AA120,0x800AA2A0
PREP,CLASSIFY,TRANSFORM,TRAIL=0x1504715C,0x15134070,0x15143134,0x15153F18
COUNTS={PREP:2,CLASSIFY:1,TRANSFORM:3,TRAIL:5}
u32=lambda n:n&0xffffffff
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
public=lambda m:{a:b for a,b in m.items()if not STACK-4096<=a<STACK+1024}

@dataclass(frozen=True)
class Case:
    seed:int=0;route:int=0;identity:int=0;kind:int=0;category:int=1;mutation:int=0
    phase:int=0;source_null:int=0;alias:int=0;heading:int=0xF4A5

def source(c): return A if c.alias else S

def cases():
    for seed in range(256):
        yield Case(seed=seed,identity=seed,kind=99 if seed%11==0 else seed%20,
                   category=seed%4,mutation=seed%32,phase=8*(seed&1),
                   source_null=int(seed%7==0),heading=(seed<<8)|((seed*13)&255))
    for identity,kind,category,high,mutation in itertools.product((0,0x53,0xA5),(0,4,19,99),(0,1,2,255),(0,63,64,191,192,255),(0,31)):
        yield Case(seed=197,identity=identity,kind=kind,category=category,heading=(high<<8)|0xA5,mutation=mutation,phase=8)
    for route,seed,mutation in itertools.product((1,2,3),range(8),(0,31)):
        yield Case(seed=seed,route=route,identity=0x87,kind=seed%20,mutation=mutation)
    for seed,mutation in itertools.product(range(16),(0,31)):
        yield Case(seed=seed,identity=(0,0x53,0xA5,0x87)[seed%4],kind=seed%20,
                   category=seed%4,mutation=mutation,alias=1,heading=(seed*17<<8)|0xA5)

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-4096,1024)}
    for at,n in ((A,512),(S,32),(M1,512),(M2,512),(MARK,4),(TABLE,320),(POINT,12),(COEF,20)):
        assert at+n<=STACK-4096 or at>=STACK+1024,('public/private fixture overlap',hex(at),n,hex(STACK))
        m.update({at+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
    put(m,A+0x1D4,0 if c.route==2 else M1)
    m[A+0x74]=0xAF if c.route==3 else 0x20
    put(m,A+0x7A,c.heading,2)
    m[source(c)+4]=c.identity
    for i in range(20):m[TABLE+16*i+14]=c.category
    for i in range(3):put(m,POINT+4*i,bits((c.seed-128+i)*.125))
    for i in range(5):put(m,COEF+4*i,bits((c.seed-100+i)*.25))
    return m

def trail_bytes(m,address): return bytes(0 if 53<=i<56 else m[address+i]for i in range(68))

def fill_surface(m,address,c,ordinal):
    for i in range(36):m[address+i]=(i*11+c.seed+ordinal*7)&255
    put(m,address,bits((c.seed-128)*.25+ordinal*2.))

class Service:
    def __init__(self,m,c,home):
        self.m,self.c,self.home=m,c,home
        self.calls=[]
        self.surface=self.position=None

    def invoke(self,t,args):
        m,c=self.m,self.c
        ordinal=len(self.calls)
        normal=list(args);observed=b''
        if t==PREP:
            self.surface=args[0]
            assert args[1]==A
            normal[:2]=['surface','actor']
        elif t==CLASSIFY:
            assert args[0]==source(c)
            normal[0]='source'
        elif t==TRANSFORM:
            assert args[0]==POINT and args[2]in(M1+0x180,M2+0x180)
            self.position=args[1]
            normal[:3]=['point','position','matrix1'if args[2]==M1+0x180 else'matrix2']
            observed=data(m,POINT,12)
        elif t==TRAIL:
            assert args[1]==self.position and args[2]==self.surface and args[3:]==(255,1)
            normal[:3]=['angles','trail','surface']
            observed=data(m,args[0],8)+trail_bytes(m,args[1])+data(m,args[2],36)
        else: raise AssertionError(hex(t))
        self.calls.append((t,tuple(normal),observed))
        if t==PREP:fill_surface(m,self.surface,c,ordinal)
        if t==TRANSFORM:
            for i in range(3):put(m,self.position+4*i,bits((c.seed+i-70)*.375))
        put(m,MARK,u32(0x13579BDF+ordinal*0x10203+t))
        if c.mutation&1 and t==PREP:
            put(m,A+0x1D4,M2);put(m,A+0x7A,0xC8A5,2);m[A+0x74]=0xAF
            m[source(c)+4]=0x53 if c.seed&1 else 0x87
        if c.mutation&2 and t==CLASSIFY:
            put(m,A+0x1D4,M2);put(m,A+0x7A,0xF4A5,2)
        if c.mutation&4 and t==TRANSFORM:
            for i in range(20):m[TABLE+16*i+14]=c.seed%4
        if c.mutation&8 and self.surface is not None:fill_surface(m,self.surface,c,ordinal+11)
        if c.mutation&16 and t==TRANSFORM:
            for i in range(5):put(m,COEF+4*i,bits((ordinal+i-5)*.125))
        return c.kind if t==CLASSIFY else 0xE5000000+ordinal

def reference(initial,c):
    m=dict(initial);home=STACK+c.phase
    surface,angles,trail=home-116,home-76,home-68
    service=Service(m,c,home)
    if c.route==1 or not read(m,A+0x1D4) or m[A+0x74]&15==15:return m,service.calls
    service.invoke(PREP,(surface,A))
    kind=4
    if not c.source_null:
        identity=m[source(c)+4]
        if identity not in(0x53,0xA5):kind=service.invoke(CLASSIFY,(source(c),))
    if kind==99:return m,service.calls
    record=TABLE+16*kind
    if m[record+14]==2:return m,service.calls
    heading=((read(m,A+0x7A,2)>>8)+64)&255
    service.invoke(TRANSFORM,(POINT,trail,read(m,A+0x1D4)+0x180))
    for i,v in enumerate((heading-104,208,-27,54)):put(m,angles+2*i,v,2)
    for off,v in ((12,read(m,COEF)),(16,read(m,COEF+4)),(20,read(m,COEF+8)),
                  (24,read(m,COEF+12)),(28,bits(6.)),(32,read(m,COEF+16)),(56,bits(.5)),(64,0)):
        put(m,trail+off,v)
    for off,v in ((36,10),(38,20),(40,3),(42,2),(44,30),(46,40),(48,155),(50,100),(60,16),(62,15)):
        put(m,trail+off,v,2)
    m[trail+52]=int(m[record+14]==1)
    service.invoke(TRAIL,(angles,trail,surface,255,1))
    return m,service.calls

def exchange(memory,home):
    m=dict(memory)
    for i in range(4):m[home-128+i],m[home-120+i]=memory[home-120+i],memory[home-128+i]
    return m

class Oracle(FactoryOracle):
    def __init__(self,words,initial,c):
        super().__init__(words,initial,c,entry=ENTRY,s={},arguments=(0 if c.route==1 else A,0 if c.source_null else source(c)))
        self.service=Service(self.memory,c,self.target_home)
        self.saved=tuple(self.r[16:24]);self.saved_fp=tuple(self.f[20:])
    def record_call(self,t):
        assert t in COUNTS,hex(t)
        self.pending=t,tuple(self.arguments(COUNTS[t]))
    def hook(self,t):
        target,args=self.pending;assert target==t
        result=self.service.invoke(t,args)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi=self.lo=0xDEADBEEF;self.r[2]=result

def verify(words,c,remap=False):
    initial=fixture(c);expected,calls=reference(initial,c)
    if remap:initial=exchange(initial,STACK+c.phase)
    m=Oracle(words,initial,c).run()
    assert public(m.memory)==public(expected),('public',asdict(c))
    assert m.service.calls==calls,('calls',asdict(c),next(((i,a,b)for i,(a,b)in enumerate(zip(m.service.calls,calls))if a!=b),None))
    assert tuple(m.r[16:24])==m.saved and tuple(m.f[20:])==m.saved_fp
    return m

def main(retail,raw,derived):
    streams=(retail,raw,derived);seen=[set(),set(),set()];count=0
    for c in cases():
        a,b,d=verify(streams[0],c),verify(streams[1],c,True),verify(streams[2],c)
        assert a.memory==exchange(b.memory,STACK+c.phase)==d.memory,('canonical RAM',c)
        for cover,m in zip(seen,(a,b,d)):cover.update(m.visits)
        count+=1
    assert all(len(s)==128 for s in seen)
    report=dict(cases_per_stream=count,coverage=[len(s)for s in seen],full_canonical_RAM=True,
                all_call_arguments_and_112_exposed_bytes=True,angle_wrap_and_retained_mutations=True,c_match_credit=0)
    (p/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return report
