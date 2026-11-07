"""Live record tables, seven initialized float fields and original query provider."""
from dataclasses import dataclass,replace
import itertools,math,struct
from tools.experiments import game_record_position_query_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
ENTRY,QUERY=source.ENTRY,0x150A1DA0
COUNT,BASE=0x800D3094,0x800D3098
A,B,MARK,POSITION,POSITION_TABLE=0x100000,0x110000,0x150000,0x130000,0x120000
FIELDS=(0x14,0x18,0x1C,0x2C,0x30,0x34,0x180)
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
s16=lambda v:((v&65535)^32768)-32768
def symbols():return dict(D_800D3094=COUNT,D_800D3098=BASE,func_150A1DA0=QUERY)
@dataclass(frozen=True)
class Case:
    kind:int=3
    subtype:int=11
    coords:tuple=(1,10,-2)
    count:int=6
    layout:int=0
    outcomes:tuple=(0,)
    mutation:int=0
    phase:int=0
    alias:int=0
    seed:int=0
    connected:int=0
    geometry:int=2
    height_gate:int=0
    inactive:int=1
def args(c):return tuple(map(u32,(c.kind,c.subtype,*c.coords)))
def query_address(home):return home-816
def table(c,s,home):return(A,query_address(home),s['D_800D3098']-20,s['D_800D3094']-20)[c.alias]
def initial_words(c):
    x,y,z=(bits(float(signed(v)))for v in c.coords);return(x,y,z,x,y,z,y)
def modified_words(n):return tuple(bits(v)for v in(n*.5,-n-.25,n*2.,n+1.,n+2.,-n*3.,n+.5))
def row(c,i,bank=0):
    status,kind,subtype=0,c.kind&63,c.subtype&255;layout=c.layout if not bank else(5 if c.layout==0 else c.layout)
    if layout==0:
        if i==0:status=1
        if i==1:kind=(kind+1)&63
        if i==2:subtype=(subtype+1)&255
    elif layout==2:status=c.inactive&255
    elif layout==3:kind=(kind+1)&63
    elif layout==4:subtype=(subtype+1)&255
    elif layout==5 and i&1:subtype=(subtype+1)&255
    return status,kind*4+c.geometry,subtype
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;home=STACK+c.phase;m={home+i:(i*17+c.seed*13+165)&255 for i in range(-4096,2048)};a=table(c,s,home)
    for bank,p in enumerate((a,B)):
        for i in range(8):
            r=u32(p+i*52)
            for k in range(52):m[u32(r+k)]=(k*13+c.seed)&255
            for at,v in((0,0),(2,0),(4,0),(6,10),(8,20),(10,10)):put(m,r+at,v,2)
            for at,v in((0xC,0.),(0x10,0.),(0x24,0.),(0x28,1.),(0x2C,0.),(0x30,1.)):put(m,r+at,bits(v))
            status,flags,subtype=row(c,i,bank);m[r+20]=status;m[r+21]=flags;m[r+22]=c.height_gate;m[r+23]=subtype
    put(m,s['D_800D3094'],c.count);put(m,s['D_800D3098'],a);put(m,MARK,0);return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-4096<=p<STACK+c.phase+2048}
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def effect(m,c,s,home,n):
    put(m,MARK,n)
    if c.mutation&1:put(m,s['D_800D3098'],B if n&1 else table(c,s,home))
    if c.mutation&2:put(m,s['D_800D3094'],max(0,min(8,c.count+(1 if n&1 else-2))))
    if c.mutation&4:
        for at,v in zip(FIELDS,modified_words(n)):put(m,query_address(home)+at,v)
    if c.mutation&8:
        for i in range(5):put(m,home+4*i,0xABCDEF00+i)
    if c.mutation&16:
        r=u32(read(m,s['D_800D3098'])+((n+3)%8)*52);m[r+20]=0;m[r+21]=(c.kind&63)*4+c.geometry;m[r+23]=c.subtype&255
def provider(m,q,r):
    if m[r+20]==1 or not q or not r:return 1
    vals=[floating(read(m,q+at))for at in FIELDS];x,y,z,ox,oy,oz,previous_y=vals
    delta=[]
    for value,at in zip((x,y,z),(0,2,4)):
        difference=floating(bits(value-float(s16(read(m,r+at,2)))));assert math.isfinite(difference)and-2147483648<=difference<2147483648;delta.append(s16(math.trunc(difference)))
    if m[r+22]&1 and floating(bits(float(math.trunc(y))-previous_y))>5:return 1
    geometry=m[r+21]&3
    if geometry==3:
        assert(x,y,z)==(ox,oy,oz),'Connected plane fixture must retain equal old/current positions';return 1
    assert geometry==2,geometry
    dx,dy,dz=delta;return int(not(-s16(read(m,r+6,2))<dx<s16(read(m,r+6,2))and-s16(read(m,r+10,2))<dz<s16(read(m,r+10,2))and 0<dy<s16(read(m,r+8,2))))
def reference(initial,c=Case(),s=None,home=None):
    s=symbols()if s is None else s;home=STACK+c.phase if home is None else home;m=dict(initial);q=query_address(home);calls=[];observations=[];n=0
    for at,v in zip(FIELDS,initial_words(c)):put(m,q+at,v)
    for i in range(16):
        if i>=read(m,s['D_800D3094']):return m,calls,0,observations
        r=u32(read(m,s['D_800D3098'])+i*52)
        if m[r+20]or m[r+21]>>2!=u32(c.kind)or m[r+23]!=u32(c.subtype):continue
        calls.append((s['func_150A1DA0'],(q,r,0)));observations.append((r,data(m,q,812)));n+=1;effect(m,c,s,home,n)
        result=provider(m,q,r)if c.connected else c.outcomes[(n-1)%len(c.outcomes)]
        if not result:return m,calls,u32(read(m,s['D_800D3098'])+i*52),observations
    raise AssertionError('Unbounded record fixture')
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s;self.home=STACK+c.phase;self.n=0;self.observations=[];self.root_args=[]
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=args(c)if arguments is None else arguments)
    def record_call(self,t):
        assert t in(ENTRY,self.s['func_150A1DA0']),hex(t);a=tuple(map(u32,self.arguments(5 if t==ENTRY else 3)));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.home=self.r[29];self.root_args.append(a)
        else:
            assert a[0]==query_address(self.home)and a[2]==0;self.observations.append((a[1],data(self.memory,a[0],812)));self.n+=1;effect(self.memory,self.case,self.s,self.home,self.n)
    def hook(self,t):
        assert t==self.s['func_150A1DA0'];value=self.case.outcomes[(self.n-1)%len(self.case.outcomes)]
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def helper_code(rom,c):
    if not c.connected:return{}
    return dict(zip(range(QUERY,0x150A23E4,4),struct.unpack_from('>401I',rom,0xCF250)))
def cases():
    for kind,subtype in itertools.product(range(64),(0,11,128,255)):yield Case(kind=kind,subtype=subtype,mutation=(kind+subtype)%8)
    for byte in range(256):yield Case(kind=byte,subtype=byte,count=8,layout=1)
    for byte in range(256):
        yield Case(kind=byte>>2,subtype=byte,geometry=byte&3,layout=1)
        yield Case(layout=2,inactive=byte)
    for count,layout,outcomes,mutation in itertools.product(range(9),range(6),((0,),(1,),(1,0),(0x80000000,0xFFFFFFFF,0)),(0,7,19)):
        yield Case(count=count,layout=layout,outcomes=outcomes,mutation=mutation)
    for v in(0,1,-1,0x7FFFFFFF,0x80000000,16777215,16777216,16777217,-16777217):
        yield Case(coords=(v,v^0x55,u32(-signed(v))),layout=1,outcomes=(1,0),mutation=4)
    for count in(0x7FFFFFFF,0x80000000,0xFFFFFFFF):yield Case(count=count,layout=1)
    for value in(0x100,0x80000000,0xFFFFFFFF):yield Case(kind=value);yield Case(subtype=value)
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.all_accesses,m.visits,m.current_pc,m.delay_of,m.observations,m.root_args)

def caller_machine(rom,words,c=Case(),which=0,floats=(17.75,-91.25,255.875)):
    from tools.tests.test_game_character_effect_pair import WindowCode
    coords=tuple(s16(v)for v in c.coords)if which==2 else tuple(math.trunc(floating(bits(v)))for v in floats)
    c=replace(c,kind=4 if which<2 else 3,subtype=5 if which==0 else 11,coords=coords,alias=0,connected=0)
    initial=fixture(c);parent_home=STACK+c.phase;home=parent_home-32 if which==2 else parent_home
    starts=(0x15080010,0x1508004C,0x15086C70,0x1509A850);lengths=(15,13,19,23);ends=((0x15080080,0x1508004C),(0x15080080,),(),(0x1509A8AC,0x1509B484))
    for i,value in enumerate(floats):put(initial,POSITION+0x14+4*i,bits(value))
    put(initial,0x800D2350,POSITION_TABLE)
    for i,value in enumerate(coords):put(initial,POSITION_TABLE+3*16+2*i,value,2)
    code=dict(zip(range(ENTRY,ENTRY+288,4),words))
    for end in ends[which]:code[end]=0
    body=struct.unpack_from('>%dI'%lengths[which],rom,starts[which]-0x15000000+0x2D4B0);m=Oracle(body,initial,c,entry=starts[which],connected=code,arguments=(3,)if which==2 else())
    if which<2:m.r[17]=POSITION
    if which==3:m.r[16]=POSITION
    m.saved=tuple(m.r[i]for i in(*range(16,24),28,29,30));m.code=WindowCode(m.code,m);m.code.ends=ends[which];expected,calls,result,obs=reference(initial,c,home=home)
    answer=result
    if which==3:answer=u32((result-read(expected,BASE))//52)if result else 0xFFFFFFFF
    return m,(expected,[(ENTRY,args(c))]+calls,answer,obs,result),c
