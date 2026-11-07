"""Independent float32 vertex model and bounded MIPS words; not a FCSR emulator."""
from dataclasses import dataclass
from functools import lru_cache
import itertools,math,struct
from tools.experiments import game_resource_texture_callback_1513bbfc_candidates as c
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
ENTRY,MATRIX,SINE,VIEW=0x1513BBFC,0x1513B968,0x15047D60,0x15144B34
MATRIX_SERVICE=0x150A7B80
RESOURCE,BUFFER0,BUFFER1,VIEWER=0x50000,0x60000,0x70000,0x90000
CENTERS,RANGES,COEFF,PAGE=0x800A49C0,0x800A4A2C,0x800A4A74,0x800BE9C0
STATE_PTR,STATE_BASE=0x800DBFF0,0xA0000
u32=lambda v:v&0xFFFFFFFF
signed16=lambda v:((v&65535)^32768)-32768
f32=lambda v:floating(bits(v))
def add(a,b):return f32(a+b)
def sub(a,b):return f32(a-b)
def mul(a,b):return f32(a*b)
def div(a,b):return f32(a/b if b else math.nan if not a else math.copysign(math.inf,a*math.copysign(1.0,b)))
def trunc(v):return u32(math.trunc(v))if math.isfinite(v)and -2147483648.0<=v<2147483648.0 else 0x80000000
def rd(m,p,n=4,order='big'):return int.from_bytes(bytes(m[u32(p+i)]for i in range(n)),order)
def wr(m,p,v,n=4,order='big'):
    for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,order)):m[u32(p+i)]=b
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
@lru_cache(None)
def retained_data():return (c.ROOT/'conker/conker.us.bin').read_bytes()[0x249480:0x249544]
@dataclass(frozen=True)
class Case:
    view:int=0
    page:int=0
    layout:int=0
    geometry:int=0
    positions:int=0
    mutation:int=0
    alias:int=0
    connected:int=0
    phase:int=0
    seed:int=0
    scrollS:int=0
    scrollT:int=0
    sin0:int=0x3E800000
    sin1:int=0x3F000000
    base:int=RESOURCE
def symbols():return dict(func_1513B968=MATRIX,sinf=SINE,func_15144B34=VIEW,D_800A49C0=CENTERS,D_800A4A2C=RANGES,D_800A4A74=COEFF,D_800A4A78=COEFF+4,D_800A4A7C=COEFF+8,D_800A4A80=COEFF+12,D_800BE9C0=PAGE)
def viewer(c):return u32(STATE_BASE+signed16(c.view)*0x9A0+0x2F8)if c.connected&2 else VIEWER
def payload(m,c,order='big'):return u32(c.base+rd(m,c.base+0x50,4,order)+0xF8)
def slot(c,page):return u32(c.base+0x58+(page&255)*16+signed16(c.view)*4)
def fixture(c=Case(),order='big'):
    rr=((c.base,16384),(BUFFER0,4096),(BUFFER1,4096),(CENTERS-32,260),(PAGE-32,128),(STACK+c.phase-1024,1536),(VIEWER,32))
    seen=set();m={}
    for base,n in rr:
        addresses={u32(base+i)for i in range(n)};assert not seen&addresses,'Disjoint fixture arenas required';seen|=addresses
        for i in range(n):m[u32(base+i)]=(i*29+c.seed*11+90)&255
    for i,(word,)in enumerate(struct.iter_unpack('>I',retained_data())):wr(m,CENTERS+4*i,word,4,order)
    if c.geometry:
        for i in range(27):wr(m,CENTERS+4*i,bits(0.0 if c.geometry==1 else float(i%3-1)),4,order)
    for i in range(9):
        if c.layout==1:first,count=(0,2)if i==0 else(i*2,0)
        elif c.layout==2:first,count=i*4,0
        elif c.layout==3:first,count=i*4,-1
        elif c.layout==4:first,count=i,1
        elif c.layout==5:first,count=0,2
        else:first,count=rd(m,RANGES+8*i,4,order),rd(m,RANGES+8*i+4,4,order)
        wr(m,RANGES+8*i,first,4,order);wr(m,RANGES+8*i+4,count,4,order)
    for bank in(BUFFER0,BUFFER1):
        for i in range(160):
            values=(i*17%1000-500,i*7%500-250,i*31%1000-500)if c.positions==0 else(-32768,32767,0)if c.positions==1 else(0,0,0)
            for j,v in enumerate(values):wr(m,bank+i*16+j*2,v,2,order)
    wr(m,c.base+0x50,0x200,4,order);m[PAGE]=c.page&255;wr(m,STATE_PTR,STATE_BASE,4,order)
    for i,v in enumerate((0.0,0.0,0.0)):wr(m,viewer(c)+4*i,bits(v),4,order)
    if c.alias:
        assert c.layout==1 and c.geometry==1
        bank=(0,c.base+0x50,RANGES-4,PAGE-8,CENTERS-8)[c.alias]
        xyz=(2,0,0)if c.alias==1 else(90,0,0)if c.alias==3 else(16384,0,0)if c.alias==4 else(0,0,0)
        for j,v in enumerate(xyz):wr(m,bank+2*j,v,2,order)
        if c.alias==2:wr(m,RANGES+4,1,4,order)
        if c.alias==4:wr(m,COEFF,0,4,order);wr(m,COEFF+4,bits(1.0),4,order)
    else:bank=BUFFER0
    for page,pointer in((c.page,bank),(0,bank),(1,BUFFER1)):
        wr(m,slot(c,page),pointer,4,order)
    for off in(0x200,0x400,0x600):
        p=u32(c.base+off+0xF8)
        for j,v in enumerate((c.scrollS,c.scrollT,0,bits(0.125),bits(-0.5))):wr(m,p+j*4,v,4,order)
    # A deliberate resource/vertex alias can change word50 before entry.
    p=payload(m,c,order)
    for j,v in enumerate((c.scrollS,c.scrollT,0,bits(0.125),bits(-0.5))):wr(m,p+j*4,v,4,order)
    return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-1024<=p<STACK+c.phase+512}
def effect(m,c,t,number,order='big',home=None):
    if c.mutation==1 and t in(MATRIX,MATRIX_SERVICE):wr(m,c.base+0x50,0x400,4,order);wr(m,payload(m,c,order)+12,bits(0.75),4,order)
    if c.mutation==2 and t==SINE and number==1:
        wr(m,payload(m,c,order)+16,bits(1.25),4,order)
        for i,v in enumerate((2.0,1.0,3.0,2.0)):wr(m,COEFF+4*i,bits(v),4,order)
    if c.mutation==3 and t==VIEW:
        p=payload(m,c,order);wr(m,p,bits(-2049.75),4,order);wr(m,p+4,bits(2050.25),4,order);wr(m,c.base+0x50,0x600,4,order)
    if c.mutation==4 and t in(MATRIX,MATRIX_SERVICE):
        assert home is not None;wr(m,home+4,0xABCDFFFF,4,order)
def reference(initial,c=Case(),order='big',home=None):
    m=dict(initial);calls=[];home=STACK+c.phase if home is None else home
    def call(t,a,number=0):
        calls.append((t,tuple(map(u32,a))))
        if not((t==MATRIX and c.connected&1)or(t==VIEW and c.connected&2)):effect(m,c,t,number,order,home)
    call(MATRIX,(c.base,u32(signed16(c.view))))
    if c.connected&1:call(MATRIX_SERVICE,(c.base+0x78+m[PAGE]*64,))
    p=payload(m,c,order)
    angleS=rd(m,p+12,4,order);call(SINE,(angleS,),1)
    scaleS=add(mul(floating(c.sin0),floating(rd(m,COEFF,4,order))),floating(rd(m,COEFF+4,4,order)))
    angleT=rd(m,p+16,4,order);call(SINE,(angleT,),2)
    scaleT=add(mul(floating(c.sin1),floating(rd(m,COEFF+8,4,order))),floating(rd(m,COEFF+12,4,order)))
    call(VIEW,(u32(signed16(c.view)),))
    s,t=(floating(rd(m,p+4*j,4,order))for j in(0,1))
    wrappedS=sub(s,mul(f32(signed(trunc(mul(s,1.0/1024.0)))),1024.0))
    wrappedT=sub(t,mul(f32(signed(trunc(mul(t,1.0/1024.0)))),1024.0))
    for group in range(9):
        center=CENTERS+group*12;range_=RANGES+group*8;v=viewer(c)
        horizontal=sub(floating(rd(m,center,4,order)),floating(rd(m,v,4,order)))
        vertical=sub(floating(rd(m,center+8,4,order)),floating(rd(m,v+8,4,order)))
        if horizontal!=0.0 or vertical!=0.0:
            length=math.sqrt(add(mul(horizontal,horizontal),mul(vertical,vertical)))
            inverse=div(1.0,f32(length));directionX=mul(vertical,inverse);directionZ=mul(-horizontal,inverse)
        else:directionX,directionZ=1.0,0.0
        index=rd(m,range_,4,order);iterations=0
        while signed(index)<signed(u32(rd(m,range_+4,4,order)+rd(m,range_,4,order))):
            assert iterations<256,'Fixture range exceeds bounded capacity';iterations+=1
            vertex=u32(rd(m,slot(c,m[PAGE]),4,order)+index*16)
            x,y,z=(float(signed16(rd(m,vertex+j*2,2,order)))for j in range(3))
            dx=sub(x,floating(rd(m,center,4,order)));dy=sub(y,floating(rd(m,center+4,4,order)));dz=sub(z,floating(rd(m,center+8,4,order)))
            stS=sub(mul(add(mul(dx,directionX),mul(dz,directionZ)),scaleS),wrappedS)
            stT=sub(mul(dy,scaleT),wrappedT)
            wr(m,vertex+8,trunc(stS),2,order);wr(m,vertex+10,trunc(stT),2,order)
            index=u32(index+1)
    return dict(memory=m,observed=public(m,c),calls=calls,value=1)
def helpers(rom,c):
    code={}
    for bit,entry,offset,n in((1,MATRIX,0x168E18,16),(2,VIEW,0x171FE4,13)):
        if c.connected&bit:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return code
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,arguments=None):
        self.sin_calls=0;self.home=STACK+c.phase
        super().__init__(words,memory,c,entry=entry,s=symbols(),connected=connected,arguments=arguments or(c.base,u32(c.view)))
    def execute(self,w):
        op,rs,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        if op!=17 or rs==8:return super().execute(w)
        if rs==0:self.r[rt]=self.f[fs]
        elif rs==4:self.f[fs]=self.r[rt]
        elif rs==20 and fn==32:self.f[fd]=bits(float(signed(self.f[fs])))
        elif rs==16:
            a,b=floating(self.f[fs]),floating(self.f[rt])
            if fn==0:self.f[fd]=bits(add(a,b))
            elif fn==1:self.f[fd]=bits(sub(a,b))
            elif fn==2:self.f[fd]=bits(mul(a,b))
            elif fn==3:self.f[fd]=bits(div(a,b))
            elif fn==4:self.f[fd]=bits(math.sqrt(a)if a>=0.0 else math.nan)
            elif fn==6:self.f[fd]=self.f[fs]
            elif fn==7:self.f[fd]=self.f[fs]^0x80000000
            elif fn==13:self.f[fd]=trunc(a)
            elif fn==50:self.condition=a==b
            else:raise AssertionError(('foreign FP op',hex(w)))
        else:raise AssertionError(('foreign COP1',hex(w)))
        self.r[0]=0
    def record_call(self,t):
        assert t in(ENTRY,MATRIX,SINE,VIEW,MATRIX_SERVICE),hex(t)
        a=(self.f[12],)if t==SINE else tuple(map(u32,self.arguments(2 if t in(ENTRY,MATRIX)else 1)))
        if t==SINE:self.sin_calls+=1
        if t==ENTRY:self.home=self.r[29]
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        c=self.case;effect(self.memory,c,t,self.sin_calls,home=self.home)
        value=viewer(c)if t==VIEW else 1 if t==MATRIX else 0xA5000002
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
        if t==SINE:self.f[0]=c.sin0 if self.sin_calls==1 else c.sin1
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def cases():
    for layout,geometry,page,seed in itertools.product((0,1,2,3,4,5),(0,1),(0,1),(0,1)):
        yield Case(layout=layout,geometry=geometry,page=page,seed=seed)
    for value in(0.0,-0.0,1023.75,1024.0,1025.5,-1025.5,1048576.25,-1048576.25):
        yield Case(layout=4,scrollS=bits(value),scrollT=bits(-value))
    for view in(1,3,0x12340001,0xFFFF8000,0xFFFF):yield Case(layout=4,view=view)
    for mutation,phase in itertools.product(range(1,5),(0,8)):yield Case(layout=4,mutation=mutation,phase=phase)
    for alias in(1,2,3,4):yield Case(layout=1,geometry=1,alias=alias,sin0=0)
    for s0,s1 in((0,0),(0x3F800000,0xBF800000),(0x80000000,0x3F000000),(0x7FC12345,0x3F000000),(0x7F800000,0x3F000000)):
        yield Case(layout=4,sin0=s0,sin1=s1)
