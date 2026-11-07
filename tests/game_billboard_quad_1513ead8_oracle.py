"""Ordered float32 billboard model, original copies/query and typed wrappers."""
from dataclasses import dataclass,replace
import itertools,math,struct
from tools.experiments import game_billboard_quad_1513ead8_candidates as c
from tools.tests import game_record_vertex_callback_1513e83c_oracle as base
from tools.tests.game_owner_float_payload_oracle import FactoryOracle

ENTRY,WRAP0,WRAP1=0x1513EAD8,0x1513EDB4,0x1513EDE4
BACKEND,COPY,ALLOC,CALLER=base.BACKEND,base.COPY,base.ALLOC,base.CALLER
ACTOR,BUFFER,ALT,GFX,STACK=base.ACTOR,base.BUFFER,base.ALT,base.GFX,base.STACK
AXIS_Z,AXIS_X=0x800DD1D8,0x800DD1E8
u32,rd,wr,state,half=base.u32,base.rd,base.wr,base.state,base.half
bits,floating,trunc=base.bits,base.floating,base.trunc
add,mul,sub=base.add,base.mul,base.ram.sub

@dataclass(frozen=True)
class Case(base.Case):
    rotated:int=0
    pivot:int=0x3F000000
    axis:int=0

AXES=((0.0,1.0),(1.0,0.0),(-0.5,0.75),(0.70710677,-0.70710677),(0.0,-0.0),(math.nan,1.0))

def symbols():return dict(func_151D5D60=BACKEND,memcpy=COPY,D_800DD1D8=AXIS_Z,D_800DD1E8=AXIS_X)
def slot(case,view=None):return u32(ACTOR+0x100+half(case.view if view is None else view)*4)
def output(case,home=None):return ACTOR+0x2E if case.alias==3 else(STACK+case.phase if home is None else home)-32 if case.alias==4 else base.output(case)
def arguments(case):return ACTOR,u32(case.rotated),u32(case.view)

def fixture(case=Case(),order='big'):
    m=base.fixture(case,order);wr(m,ACTOR+0x50,case.pivot,4,order)
    for view in set((half(case.view),0,1,2,3)):
        for p,v in zip((AXIS_Z+view*4,AXIS_X+view*4),AXES[case.axis]):
            for i in range(4):m.setdefault(u32(p+i),0)
            wr(m,p,bits(v),4,order)
    if case.private==1:wr(m,slot(case,1),ALT,4,order)
    return m

def public(m,case):return base.public(m,case)

def effect(m,case,stage,number,home,order='big'):
    frame=home-104;cur=frame+0x64
    if stage==BACKEND and case.private==1:wr(m,home+8,0xABCD0001,4,order)
    if stage==COPY and number==1:
        if case.mutation:
            view=half(rd(m,home+8,4,order));wr(m,slot(case,view),ALT,4,order);wr(m,ACTOR+0x2C,bits(-4.75),4,order);wr(m,ACTOR+0x50,bits(0.25),4,order)
        if case.redirect:wr(m,cur,ALT+64,4,order)
        if case.private==2:wr(m,home+8,0xABCD0001,4,order)
        if case.private==3:wr(m,home,0xA0000,4,order)
        if case.private==4:wr(m,frame+0x60,ALT+128,4,order)

def reference(initial,case=Case(),order='big',home=None):
    m=dict(initial);home=STACK+case.phase if home is None else home;frame=home-104;cur,first,fresh,points=(frame+x for x in(0x64,0x60,0x37,0x48))
    wr(m,home+4,case.rotated,4,order);wr(m,home+8,case.view,4,order);calls=[(BACKEND,(ACTOR+0x100,u32(half(case.view)),64,cur,fresh))]
    if case.connected&4:
        assert case.private==0 and case.alias!=4
        p=rd(m,slot(case),4,order);m[fresh]=0
        if not p:
            calls.append((ALLOC,(128,1,2,1)));p=BUFFER if case.success else 0;wr(m,slot(case),p,4,order)
            if p:m[fresh]=1
        answer=u32(p+(0 if case.page else 64))if p else 0
    else:m[fresh]=case.fresh;answer=output(case,home)if case.success else 0
    wr(m,cur,answer,4,order);effect(m,case,BACKEND,0,home,order);wr(m,first,rd(m,cur,4,order),4,order)
    if not rd(m,cur,4,order):return dict(memory=m,observed=public(m,case),calls=calls,value=0)
    if m[fresh]:
        address=slot(case,half(rd(m,home+8,4,order)));template=ACTOR+0xC0
        for i in range(2):
            dest=u32(rd(m,address,4,order)+i*64);calls.append((COPY,(dest,template,64)));base.copy_bytes(m,dest,template,64,order);effect(m,case,COPY,i+1,home,order)
    view=half(rd(m,home+8,4,order));width=floating(rd(m,ACTOR+0x2C,4,order));height=floating(rd(m,ACTOR+0x30,4,order))
    forward=mul(floating(rd(m,AXIS_Z+view*4,4,order)),width);side=mul(floating(rd(m,AXIS_X+view*4,4,order)),width);lower=mul(floating(rd(m,ACTOR+0x50,4,order)),height);upper=sub(height,lower)
    for i in range(4):wr(m,rd(m,cur,4,order)+i*16+6,0,2,order)
    for off,value in((0,add(floating(rd(m,ACTOR+0x34,4,order)),side)),):
        v=trunc(value);wr(m,points,v,2,order);wr(m,points+18,v,2,order)
    v=trunc(sub(floating(rd(m,ACTOR+0x38,4,order)),lower));wr(m,points+2,v,2,order);wr(m,points+8,v,2,order)
    v=trunc(sub(floating(rd(m,ACTOR+0x3C,4,order)),forward));wr(m,points+4,v,2,order);wr(m,points+22,v,2,order)
    v=trunc(sub(floating(rd(m,ACTOR+0x34,4,order)),side));wr(m,points+6,v,2,order);wr(m,points+12,v,2,order)
    v=trunc(add(floating(rd(m,ACTOR+0x38,4,order)),upper));wr(m,points+14,v,2,order);wr(m,points+20,v,2,order)
    v=trunc(add(floating(rd(m,ACTOR+0x3C,4,order)),forward));wr(m,points+10,v,2,order);wr(m,points+16,v,2,order)
    rotated=m[home+(7 if order=='big' else 4)]!=0
    for i,p in enumerate((1,2,3,0)if rotated else(0,1,2,3)):
        for j in range(3):wr(m,rd(m,cur,4,order)+i*16+j*2,rd(m,points+p*6+j*2,2,order),2,order)
    return dict(memory=m,observed=public(m,case),calls=calls,value=rd(m,first,4,order))

def helper_code(case):return base.helpers(case)
def wrapper_code(rom):
    return {**dict(zip(range(WRAP0,WRAP0+48,4),struct.unpack_from('>12I',rom,0x16C264))),**dict(zip(range(WRAP1,WRAP1+48,4),struct.unpack_from('>12I',rom,0x16C294)))}

class Oracle(base.Oracle):
    def __init__(self,words,memory,case=Case(),entry=ENTRY,connected=None,args=None,reference_leaf=False):
        self.home=STACK+case.phase;self.copies=self.transforms=0;self.reference_billboard=reference_leaf;self.reference_leaf=False
        code=helper_code(case);code.update(connected or{})
        FactoryOracle.__init__(self,words,memory,case,entry=entry,s=symbols(),connected=code,arguments=arguments(case)if args is None else args)
    def record_call(self,t):
        if t in(ENTRY,WRAP0,WRAP1):
            a=tuple(map(u32,self.arguments(3 if t==ENTRY else 2)));self.calls.append((t,a));self.events.append(('CALL',t,a))
            if t==ENTRY:self.home=self.r[29]
        else:super().record_call(t)
    def hook(self,t):
        case=self.case;a=self.calls[-1][1];value=0
        if t==ENTRY:
            assert self.reference_billboard;actual=replace(case,rotated=a[1],view=a[2]);e=reference(self.memory,actual,home=self.home);self.memory=e['memory'];self.calls.extend(e['calls']);self.events.extend(('CALL',t,args)for t,args in e['calls']);value=e['value']
        elif t==BACKEND:
            self.put(a[3],output(case,self.home)if case.success else 0,4);self.put(a[4],case.fresh,1);effect(self.memory,case,t,0,self.home)
        elif t==COPY:
            base.copy_bytes(self.memory,*a);self.copies+=1;effect(self.memory,case,t,self.copies,self.home);value=a[0]
        elif t==ALLOC:value=BUFFER if case.success else 0
        else:return super().hook(t)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def caller_fixture(case,flags=0,enabled=1,visible=255,attached=0,animation=255):
    m=base.caller_fixture(case,flags,enabled,visible,attached,animation)
    extra=fixture(case)
    for p in(AXIS_Z,AXIS_X):
        for view in set((half(case.view),0,1,2,3)):
            for i in range(4):m[u32(p+view*4+i)]=extra[u32(p+view*4+i)]
    wr(m,ACTOR+0x50,case.pivot,4);m[ACTOR+0x73]=35 if case.rotated&255 else 34
    return m

def cases():
    for view,rotated,fresh,success,axis,pivot in itertools.product((0,1,3,0x12340002),(0,1,255),(0,1,255),(0,1),range(4),(0,0x3F000000,0xBF800000)):
        yield Case(view=view,rotated=rotated,fresh=fresh,success=success,axis=axis,pivot=pivot,seed=axis)
    for width,height in itertools.product((bits(-0.0),bits(-2.75),bits(32767.75),bits(65536.5),0x7FC12345,0x7F800000),(bits(2.5),bits(-1.5))):yield Case(width=width,height=height)
    for alias,rotated,fresh in itertools.product((1,2,3,4),(0,1),(0,1)):yield Case(alias=alias,rotated=rotated,fresh=fresh)
    for private in(1,2,3,4):yield Case(private=private,rotated=1,view=0)
    for mutation,redirect in itertools.product((0,1),(0,1)):yield Case(mutation=mutation,redirect=redirect)
    for view in(0xFFFF,0x8000,0x1234FFFF):yield Case(view=view,fresh=0)
    for connected,fresh,success,page in itertools.product((1,4,5),(0,1),(0,1),(0,1)):yield Case(connected=connected,fresh=fresh,success=success,page=page,rotated=1)
    yield Case(axis=5)
    for rotated in(0x100,0x12340001):yield Case(rotated=rotated)

def native_cases():
    result=[]
    for case in cases():
        if case.private or case.alias or case.connected or case.phase or not 0<=case.view<4:continue
        if not all(math.isfinite(floating(v))for v in(case.width,case.height,case.pivot)):continue
        # Native fixtures require representable float-to-s32 inputs. The
        # independent point snapshot records the exact finite cast operands.
        w=floating(case.width);h=floating(case.height);z,x=AXES[case.axis];lo=mul(floating(case.pivot),h);up=sub(h,lo)
        values=(add(10.5,mul(x,w)),sub(10.5,mul(x,w)),sub(-12.25,lo),add(-12.25,up),sub(3.75,mul(z,w)),add(3.75,mul(z,w)))
        if all(math.isfinite(v)and-2147483648<=v<2147483648 for v in values):result.append(case)
    return tuple(result)
