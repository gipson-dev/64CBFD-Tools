"""Ordered f32/ordinary-RAM model; bounded FP helpers, no FCSR/payload claim."""
from dataclasses import dataclass,replace
import itertools,math,struct
from functools import lru_cache
from tools.tests import game_record_vertex_callback_1513e83c_oracle as base
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
ENTRY,SIN,COS=0x1513F114,0x15047D60,0x15047C00
CALLER,BACKEND,COPY,ALLOC=base.CALLER,base.BACKEND,base.COPY,base.ALLOC
ACTOR,BUFFER,ALT,GFX,PAGE,TABLE,STACK=base.ACTOR,base.BUFFER,base.ALT,base.GFX,base.PAGE,base.TABLE,base.STACK
AXIS_Z,AXIS_X,BEND,CLAMP,LIMIT=0x800DD1D8,0x800DD1E8,0x800BE9A8,0x800A51BC,0x800A51C0
u32,rd,wr,state,half=base.u32,base.rd,base.wr,base.state,base.half
floating,trunc=base.floating,base.trunc
def bits(v):return 0x7FC00000 if math.isnan(v)else base.bits(v)
def add(a,b):return floating(bits(a+b))
def sub(a,b):return floating(bits(a-b))
def mul(a,b):return floating(bits(a*b))
def neg(a):return floating(base.bits(a)^0x80000000)
def sqrt(a):return floating(bits(math.sqrt(a)if a>=0 else math.nan))
AXES=((0.,1.),(1.,0.),(-.5,.75),(.70710677,-.70710677))

@dataclass(frozen=True)
class Case(base.Case):
    pivot:int=0x3F000000
    gain:int=0x3E000000
    bend:int=0x3D800000
    targetX:int=0x41A40000
    targetZ:int=0x3F800000
    axis:int=0
    sin_value:int=0x3F000000
    cos_value:int=0x3F400000

def symbols():return dict(func_151D5D60=BACKEND,memcpy=COPY,sinf=SIN,cosf=COS,D_800DD1D8=AXIS_Z,D_800DD1E8=AXIS_X,D_800BE9A8=BEND,D_800A51BC=CLAMP,D_800A51C0=LIMIT)
def slot(case,view=None):return u32(ACTOR+0x100+half(case.view if view is None else view)*4)
def output(case,home=None):
    home=STACK+case.phase if home is None else home
    if case.alias==2:return ACTOR+0x30
    if case.alias in(3,4):return home-144+(0x30 if case.alias==3 else 0x50)
    return base.output(case)
def fixture(case=Case(),order='big'):
    m=base.fixture(case,order)
    for off,v in((0x50,case.pivot),(0x4C,case.gain),(0x40,case.targetX),(0x48,case.targetZ)):wr(m,ACTOR+off,v,4,order)
    views=range(4)if 0<=half(case.view)<4 else(half(case.view),)
    if case.private==1:views=set((*views,1));wr(m,slot(case,1),ALT,4,order)
    for view in views:
        for p,v in zip((u32(AXIS_Z+view*4),u32(AXIS_X+view*4)),AXES[case.axis]):
            for i in range(4):m.setdefault(p+i,0)
            wr(m,p,bits(v),4,order)
    for p,v in((BEND,case.bend),(CLAMP,0x3FC90FDB),(LIMIT,0x3FC90FDB)):
        for i in range(4):m.setdefault(p+i,0)
        wr(m,p,v,4,order)
    return m
def public(m,case):
    result=base.public(m,case)
    if case.alias in(3,4):result.update({p:m[p]for p in range(output(case),output(case)+64)})
    return result
def effect(m,case,stage,index,home,order='big'):
    frame=home-144
    if stage==BACKEND and case.private==1:wr(m,home+4,0xABCD0001,4,order)
    if stage==COPY and index==1:
        if case.mutation&1:wr(m,slot(case,half(rd(m,home+4,4,order))),ALT,4,order);wr(m,ACTOR+0x2C,bits(-4.75),4,order)
        if case.private==5:wr(m,home+4,0xABCD0001,4,order)
    if stage==SIN:
        if case.mutation&1:
            for off,v in((0x2C,19),(0x30,6.5),(0x50,-2),(0x34,-7.5),(0x38,2.25),(0x3C,-9.5)):wr(m,ACTOR+off,bits(v),4,order)
        if case.mutation&2:
            wr(m,frame+0x84,bits(-.75),4,order)
            view=half(rd(m,home+4,4,order));wr(m,u32(AXIS_Z+view*4),bits(.25),4,order);wr(m,u32(AXIS_X+view*4),bits(-.5),4,order)
        if case.private==2:wr(m,frame+0x4C,bits(1.125),4,order)
        if case.private==4:wr(m,home,0xA0000,4,order)
    if stage==COS:
        if case.redirect:wr(m,frame+0x8C,ALT+64,4,order)
        if case.mutation&4:wr(m,frame+0x88,ALT+128,4,order)
        if case.private==3:wr(m,frame+0x7C,bits(-1.25),4,order);wr(m,frame+0x78,bits(2.75),4,order)

def reference(initial,case=Case(),order='big',home=None):
    m=dict(initial);home=STACK+case.phase if home is None else home;frame=home-144;cur,first,fresh=frame+0x8C,frame+0x88,frame+0x4B;wr(m,home+4,case.view,4,order)
    calls=[(BACKEND,(ACTOR+0x100,u32(half(case.view)),64,cur,fresh))];casts=[]
    if case.connected&4:
        assert not case.private
        p=rd(m,slot(case),4,order);m[fresh]=0
        if not p:
            calls.append((ALLOC,(128,1,2,1)));p=BUFFER if case.success else 0;wr(m,slot(case),p,4,order)
            if p:m[fresh]=1
        answer=u32(p+(0 if case.page else 64))if p else 0
    else:m[fresh]=case.fresh;answer=output(case,home)if case.success else 0
    wr(m,cur,answer,4,order);effect(m,case,BACKEND,0,home,order);wr(m,first,answer,4,order)
    def result():return dict(memory=m,observed=public(m,case),calls=calls,value=rd(m,first,4,order),casts=casts)
    if not answer:return result()
    if m[fresh]:
        address=slot(case,half(rd(m,home+4,4,order)))
        wr(m,frame+0x40,ACTOR+0xC0,4,order);wr(m,frame+0x44,address-0x100,4,order)
        for i in range(2):
            dest=u32(rd(m,address,4,order)+i*64);calls.append((COPY,(dest,ACTOR+0xC0,64)));base.copy_bytes(m,dest,ACTOR+0xC0,64);effect(m,case,COPY,i+1,home,order)
    load=lambda p:floating(rd(m,u32(p),4,order))
    store=lambda p,v:wr(m,p,bits(v),4,order)
    view=half(rd(m,home+4,4,order));height=load(ACTOR+0x30);lower=neg(mul(load(ACTOR+0x50),height));upper=add(height,lower);store(frame+0x78,upper)
    forward,side=load(AXIS_Z+view*4),load(AXIS_X+view*4)
    turn=mul(sub(mul(sub(load(ACTOR+0x40),load(ACTOR+0x34)),side),mul(forward,sub(load(ACTOR+0x48),load(ACTOR+0x3C)))),load(BEND))
    sign=-1.
    if turn<0:sign=1.;turn=neg(turn)
    angle=mul(sqrt(turn),load(ACTOR+0x4C))
    if load(CLAMP)<angle:angle=load(LIMIT)
    angle=mul(angle,sign);store(frame+0x7C,lower);store(frame+0x84,forward);store(frame+0x4C,angle)
    calls.append((SIN,(bits(angle),)));effect(m,case,SIN,0,home,order)
    sine=floating(case.sin_value);wr(m,frame+0x74,case.sin_value,4,order);calls.append((COS,(rd(m,frame+0x4C,4,order),)));effect(m,case,COS,0,home,order);cosine=floating(case.cos_value)
    width=load(ACTOR+0x2C);sine=load(frame+0x74);widthCos=mul(width,cosine);widthSin=mul(width,sine);lowerSin=mul(load(frame+0x7C),sine);forward=load(frame+0x84);store(frame+0x3C,lowerSin)
    def emit(i,j,v):casts.append(bits(v));wr(m,rd(m,cur,4,order)+i*16+j*2,trunc(v),2,order)
    def flag(i):wr(m,rd(m,cur,4,order)+i*16+6,0,2,order)
    offset=sub(widthCos,lowerSin);emit(0,0,add(load(ACTOR+0x34),mul(offset,side)));lowerCos=mul(load(frame+0x7C),cosine);store(frame+0x38,lowerCos);emit(0,1,add(add(load(ACTOR+0x38),lowerCos),widthSin));emit(0,2,sub(load(ACTOR+0x3C),mul(offset,forward)));flag(0)
    offset=neg(add(widthCos,load(frame+0x3C)));emit(1,0,add(load(ACTOR+0x34),mul(offset,side)));emit(1,1,sub(add(load(ACTOR+0x38),load(frame+0x38)),widthSin));emit(1,2,sub(load(ACTOR+0x3C),mul(offset,forward)));flag(1)
    upperSin=mul(load(frame+0x78),load(frame+0x74));offset=neg(add(widthCos,upperSin));store(frame+0x34,offset);emit(2,0,add(load(ACTOR+0x34),mul(offset,side)));upperCos=mul(load(frame+0x78),cosine);last=sub(widthCos,upperSin);store(frame+0x40,upperCos);emit(2,1,sub(add(load(ACTOR+0x38),upperCos),widthSin));emit(2,2,sub(load(ACTOR+0x3C),mul(load(frame+0x34),forward)));flag(2)
    emit(3,0,add(load(ACTOR+0x34),mul(last,side)));emit(3,1,add(add(load(ACTOR+0x38),load(frame+0x40)),widthSin));emit(3,2,sub(load(ACTOR+0x3C),mul(last,forward)));flag(3)
    return result()

class Oracle(base.Oracle):
    def __init__(self,words,memory,case=Case(),entry=ENTRY,connected=None,arguments=None,reference_leaf=False):
        self.home=STACK+case.phase;self.copies=self.transforms=0;self.reference_bending=reference_leaf;self.reference_leaf=False
        code={}
        for bit,address,at,n in((1,COPY,0x22EC0,11),(4,BACKEND,0x203210,52)):
            if case.connected&bit:code.update(zip(range(address,address+n*4,4),struct.unpack_from('>%dI'%n,base.rom(),at)))
        code.update(connected or{});FactoryOracle.__init__(self,words,memory,case,entry=entry,s=symbols(),connected=code,arguments=arguments or(ACTOR,u32(case.view)))
    def execute(self,w):
        op,rs,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        if op==17 and rs==16:
            a,b=floating(self.f[fs]),floating(self.f[ft])
            if fn==60:self.condition=a<b
            elif fn==0:self.f[fd]=bits(add(a,b))
            elif fn==1:self.f[fd]=bits(sub(a,b))
            elif fn==2:self.f[fd]=bits(mul(a,b))
            elif fn==4:self.f[fd]=bits(sqrt(a))
            elif fn==6:self.f[fd]=self.f[fs]
            elif fn==7:self.f[fd]=self.f[fs]^0x80000000
            elif fn==13:self.f[fd]=trunc(a)
            else:raise AssertionError(('foreign bending FP op',hex(w)))
            self.r[0]=0;return
        return super().execute(w)
    def record_call(self,t):
        if t in(SIN,COS):a=(self.f[12],)
        elif t==ENTRY:a=tuple(map(u32,self.arguments(2)));self.home=self.r[29]
        else:return super().record_call(t)
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        case=self.case;a=self.calls[-1][1];value=0;fp=None
        if t==ENTRY:
            assert self.reference_bending;e=reference(self.memory,replace(case,view=a[1]),home=self.home);self.memory=e['memory'];self.calls.extend(e['calls']);value=e['value']
        elif t==BACKEND:self.put(a[3],output(case,self.home)if case.success else 0,4);self.put(a[4],case.fresh,1);effect(self.memory,case,t,0,self.home)
        elif t==COPY:base.copy_bytes(self.memory,*a);self.copies+=1;effect(self.memory,case,t,self.copies,self.home);value=a[0]
        elif t in(SIN,COS):effect(self.memory,case,t,0,self.home);fp=case.sin_value if t==SIN else case.cos_value
        elif t==ALLOC:value=BUFFER if case.success else 0
        else:return super().hook(t)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
        if fp is not None:self.f[0]=fp

def caller_fixture(case,flags=0,enabled=1,visible=255,attached=0,animation=255):
    m=base.caller_fixture(case,flags,enabled,visible,attached,animation);extra=fixture(case)
    for p,v in extra.items():
        if p not in m:m[p]=v
    for off in(0x50,0x4C,0x40,0x48):wr(m,ACTOR+off,rd(extra,ACTOR+off,4),4)
    m[ACTOR+0x73]=3;return m
def cases():
    for view,axis,gain,x,fresh,success in itertools.product((0,1,3,0x12340002),range(4),(bits(.125),bits(-.5),bits(4)),(bits(-9.5),bits(10.5),bits(30.5)),(0,1),(0,1)):
        yield Case(view=view,axis=axis,gain=gain,targetX=x,fresh=fresh,success=success)
    for alias,mutation,redirect,fresh in itertools.product(range(5),(0,1,2,4,7),(0,1),(0,1)):yield Case(alias=alias,mutation=mutation,redirect=redirect,fresh=fresh)
    for private in range(1,6):yield Case(private=private,mutation=1,redirect=1)
    for connected,fresh,success,page in itertools.product((1,4,5),(0,1),(0,1),(0,1)):yield Case(connected=connected,fresh=fresh,success=success,page=page)
    for gain,x in itertools.product((0x3FC90FDA,0x3FC90FDB,0x3FC90FDC,0,0x80000000),(bits(9.5),bits(10.5),bits(11.5))):yield Case(gain=gain,targetX=x,targetZ=bits(3.75),bend=bits(1))
    for view in(0xFFFF,0x8000,0x7FFF):yield Case(view=view)
    for bend,gain in itertools.product((0x80000000,0x7FC12345,0x7F800000,0xFF800000,1),(bits(1),bits(-1))):yield Case(bend=bend,gain=gain)
    for s,v in((0,0x3F800000),(0x80000000,0x3F800000),(0x7FC12345,0x3F800000),(0x7F800000,0x3F800000)):yield Case(sin_value=s,cos_value=v)
    for width in(0,0x80000000,bits(-2.75),bits(32767.75),bits(65536.5)):yield Case(width=width)
    for fresh in(2,128,255):yield Case(fresh=fresh)
@lru_cache(None)
def native_cases():
    result=[]
    for case in cases():
        if case.private or case.alias or case.connected or case.phase or not 0<=half(case.view)<4:continue
        e=reference(fixture(case),case)
        if not all(math.isfinite(floating(v))and-2147483648<=floating(v)<2147483648 for v in e['casts']):continue
        if not all(math.isfinite(floating(a[0]))for t,a in e['calls']if t in(SIN,COS)):continue
        if case.success and not all(math.isfinite(floating(v))for v in(case.sin_value,case.cos_value)):continue
        result.append(case)
    return tuple(result)
