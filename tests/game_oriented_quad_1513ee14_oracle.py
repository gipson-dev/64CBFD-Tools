"""Independent ordered matrix/corner model and original float helper connections."""
import itertools,math,struct
from dataclasses import replace
from tools.tests import game_record_vertex_callback_1513e83c_oracle as base
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
ENTRY=0x1513EE14
CALLER,BACKEND,COPY,ORIENT,MATRIX,ALLOC=base.CALLER,base.BACKEND,base.COPY,base.ORIENT,base.MATRIX,base.ALLOC
ACTOR,BUFFER,ALT,GFX,PAGE,TABLE,STACK=base.ACTOR,base.BUFFER,base.ALT,base.GFX,base.PAGE,base.TABLE,base.STACK
Case,u32,rd,wr,state,half=base.Case,base.u32,base.rd,base.wr,base.state,base.half
bits,floating,trunc,mul=base.bits,base.floating,base.trunc,base.mul
symbols,slot,matrix_values=base.symbols,base.slot,base.matrix_values
ram=base.ram
def output(case,home=None):return (STACK+case.phase if home is None else home)-152 if case.alias==3 else base.output(case)
def fixture(case=Case(),order='big'):
    m=base.fixture(case,order)
    if case.private==1:wr(m,ACTOR+0x104,ALT,4,order)
    return m
def public(m,case):
    result=base.public(m,case)
    if case.alias==3:
        # This deliberately aliased output is part of the observable guest
        # buffer, even though it resides in the routine's private frame.
        start=output(case)
        result.update({a:m[a]for a in range(start,start+64)})
    return result
def effect(m,case,stage,index,home,order='big'):
    cur=home-4
    if stage==BACKEND and case.private==1:wr(m,home+4,0xABCD0001,4,order)
    if stage==COPY and index==1:
        if case.mutation:wr(m,ACTOR+0x100+half(rd(m,home+4,4,order))*4,ALT,4,order);wr(m,ACTOR+0x2C,bits(-4.75),4,order)
        if case.private==3:wr(m,home+4,0xABCD0001,4,order)
    if stage==ORIENT:
        if case.mutation:
            for off,v in((0x34,-7.5),(0x50,-2),(0x2C,19),(0x30,-5.25)):wr(m,ACTOR+off,bits(v),4,order)
        if case.private==2:wr(m,cur,ALT+64,4,order)
    if stage==MATRIX:
        if case.redirect:wr(m,cur,ALT+index*16,4,order)
        if case.private==4:wr(m,home-8,ALT+128,4,order)

def reference(initial,case=Case(),order='big',home=None):
    m=dict(initial);home=STACK+case.phase if home is None else home;frame=home-216;cur,first,fresh,points,corners,matrix=(frame+x for x in(0xD4,0xD0,0x3F,0x40,0x70,0x90));wr(m,home+4,case.view,4,order)
    calls=[(BACKEND,(ACTOR+0x100,u32(half(case.view)),64,cur,fresh))]
    if case.connected&4:
        assert not case.private
        p=rd(m,slot(case),4,order);m[fresh]=0
        if not p:
            calls.append((ALLOC,(128,1,2,1)));p=BUFFER if case.success else 0;wr(m,slot(case),p,4,order)
            if p:m[fresh]=1
        answer=u32(p+(0 if case.page else 64))if p else 0
    else:m[fresh]=case.fresh;answer=output(case,home)if case.success else 0
    wr(m,cur,answer,4,order);effect(m,case,BACKEND,0,home,order);wr(m,first,answer,4,order)
    if not answer:return dict(memory=m,observed=public(m,case),calls=calls,value=0)
    if m[fresh]:
        address=ACTOR+0x100+half(rd(m,home+4,4,order))*4
        for i in range(2):
            dest=u32(rd(m,address,4,order)+i*64);calls.append((COPY,(dest,ACTOR+0xC0,64)));base.copy_bytes(m,dest,ACTOR+0xC0,64);effect(m,case,COPY,i+1,home,order)
    calls.append((ORIENT,(matrix,*[rd(m,ACTOR+o,4,order)for o in(0x40,0x44,0x48)])))
    for i,v in enumerate(matrix_values(case.pattern)):wr(m,matrix+i*4,bits(v),4,order)
    effect(m,case,ORIENT,0,home,order)
    for i,off in enumerate((0x34,0x38,0x3C),12):wr(m,matrix+i*4,rd(m,ACTOR+off,4,order),4,order)
    for i,(sx,sy)in enumerate(((1,1),(-1,1),(-1,-1),(1,-1))):
        wr(m,corners+i*8,rd(m,ACTOR+0x2C,4,order)^(0x80000000 if sx<0 else 0),4,order);wr(m,corners+i*8+4,rd(m,ACTOR+0x30,4,order)^(0x80000000 if sy<0 else 0),4,order)
    for i in range(4):
        point=points+i*12;x,y=(rd(m,corners+i*8+j*4,4,order)for j in range(2));calls.append((MATRIX,(matrix,x,y,0,point,point+4,point+8)))
        values=[floating(rd(m,matrix+j*4,4,order))for j in range(16)];coords=base.transformed(values,floating(x),floating(y))
        for j,v in enumerate(coords):wr(m,point+j*4,v,4,order)
        effect(m,case,MATRIX,i,home,order)
    for i in range(4):
        for j in range(3):wr(m,rd(m,cur,4,order)+j*2,trunc(floating(rd(m,points+i*12+j*4,4,order))),2,order)
        wr(m,rd(m,cur,4,order)+6,0,2,order)
        if i<3:wr(m,cur,rd(m,cur,4,order)+16,4,order)
    return dict(memory=m,observed=public(m,case),calls=calls,value=rd(m,first,4,order))

class Oracle(base.Oracle):
    def __init__(self,words,memory,case=Case(),entry=ENTRY,connected=None,arguments=None,reference_leaf=False):
        self.home=STACK+case.phase;self.copies=self.transforms=0;self.reference_oriented=reference_leaf;self.reference_leaf=False
        code=base.helpers(case);code.update(connected or{})
        FactoryOracle.__init__(self,words,memory,case,entry=entry,s=symbols(),connected=code,arguments=arguments or(ACTOR,u32(case.view)))
    def record_call(self,t):
        if t==ENTRY:
            args=tuple(map(u32,self.arguments(2)));self.calls.append((t,args));self.events.append(('CALL',t,args));self.home=self.r[29]
        else:super().record_call(t)
    def hook(self,t):
        case=self.case;a=self.calls[-1][1];value=0
        if t==ENTRY:
            assert self.reference_oriented;e=reference(self.memory,replace(case,view=a[1]),home=self.home);self.memory=e['memory'];self.calls.extend(e['calls']);value=e['value']
        elif t==BACKEND:self.put(a[3],output(case,self.home)if case.success else 0,4);self.put(a[4],case.fresh,1);effect(self.memory,case,t,0,self.home)
        elif t==COPY:base.copy_bytes(self.memory,*a);self.copies+=1;effect(self.memory,case,t,self.copies,self.home);value=a[0]
        elif t==ORIENT:
            for i,v in enumerate(matrix_values(case.pattern)):self.put(a[0]+i*4,bits(v),4)
            effect(self.memory,case,t,0,self.home)
        elif t==MATRIX:
            values=[floating(self.get(a[0]+i*4,4))for i in range(16)];coords=base.transformed(values,*map(floating,a[1:4]))
            for p,v in zip(a[4:],coords):self.put(p,v,4)
            effect(self.memory,case,t,self.transforms,self.home);self.transforms+=1
        elif t==ALLOC:value=BUFFER if case.success else 0
        else:return super().hook(t)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def caller_fixture(case,flags=0,enabled=1,visible=255,attached=0,animation=255):
    m=base.caller_fixture(case,flags,enabled,visible,attached,animation);m[ACTOR+0x73]=23;return m
def cases():
    for view,fresh,success,pattern,mutation,redirect in itertools.product((0,1,3,0x12340002),(0,1,255),(0,1),range(3),(0,1),(0,1)):
        yield Case(view=view,fresh=fresh,success=success,pattern=pattern,mutation=mutation,redirect=redirect,width=(bits(1.25),bits(-0.0),bits(-32768.5))[pattern])
    for private,alias in itertools.product((0,1,2,3,4),(0,1,2,3)):yield Case(private=private,alias=alias,mutation=1,redirect=1,phase=8)
    for connected,fresh,success,page in itertools.product((1,2,3,4,7),(0,1),(0,1),(0,1)):yield Case(connected=connected,fresh=fresh,success=success,page=page)
    for view in(0xFFFF,0x8000,0x7FFF):yield Case(view=view)
    for width in(0x7FC12345,0x7F800000,0x7F7FFFFF):yield Case(width=width)
def native_cases():
    result=[]
    for case in cases():
        if case.private or case.alias or case.connected or case.phase or case.view not in(0,1,3):continue
        e=reference(fixture(case),case);frame=STACK-216
        values=[floating(rd(e['memory'],frame+0x40+i*12+j*4))for i in range(4)for j in range(3)]if case.success else[]
        if all(math.isfinite(v)and-2147483648<=v<2147483648 for v in values):result.append(case)
    return tuple(result)
