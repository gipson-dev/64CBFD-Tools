"""Ordered quad/copy/float32 model, original helpers and original dispatch caller."""
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,math,struct
from tools.experiments import game_record_vertex_callback_1513e83c_candidates as c
from tools.tests import game_resource_texture_callback_1513bbfc_oracle as ram
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating,signed

ENTRY,CALLER,BACKEND,COPY,ORIENT,MATRIX,ALLOC=0x1513E83C,0x1513DB00,0x151D5D60,0x10022EC0,0x150A8050,0x150A7960,0x10003C40
ACTOR,BUFFER,ALT,GFX,PAGE,TABLE=0x30000,0x60000,0x70000,0x90000,0x800BE9C0,0x80089E1C
STACK,u32,rd,wr,state=ram.STACK,ram.u32,ram.rd,ram.wr,ram.state
half=lambda v:((v&65535)^32768)-32768
mul=lambda a,b:floating(bits(a*b))
add=lambda a,b:floating(bits(a+b))
trunc=ram.trunc

@dataclass(frozen=True)
class Case:
    view:int=0
    width:int=0x3FA00000
    height:int=0x40200000
    fresh:int=1
    success:int=1
    pattern:int=1
    scale:int=1
    mutation:int=0
    redirect:int=0
    private:int=0
    alias:int=0
    page:int=0
    connected:int=0
    phase:int=0
    seed:int=0

def symbols():return dict(func_151D5D60=BACKEND,memcpy=COPY,func_150A8050=ORIENT,func_150A7960=MATRIX)
def slot(case):return u32(ACTOR+0x100+half(case.view)*4)
def output(case):return ACTOR+0x40 if case.alias==2 else BUFFER+(0 if case.page else 64)
def template_buffer(case):return ACTOR+0xC0 if case.alias==1 else BUFFER

def matrix_values(pattern):
    m=[0.0]*16;m[15]=1.0
    for i,v in zip((0,1,2,4,5,6,8,9,10),((1,0,0,0,1,0,0,0,1),(-1,.5,1,2,0,-1,0,0,1),(.25,2,-.5,-3,1.5,.75,2,-1,.5))[pattern]):m[i]=float(v)
    return m

def fixture(case=Case(),order='big'):
    rr=((ACTOR,512),(BUFFER,320),(ALT,320),(STACK+case.phase-2048,2560),(PAGE,1));seen=set();m={}
    for p,n in rr:
        addresses={u32(p+i)for i in range(n)};assert not seen&addresses,'Fixture banks must be disjoint';seen|=addresses
        m.update({u32(p+i):(i*29+case.seed*11+90)&255 for i in range(n)})
    for off,v in((0x2C,case.width),(0x30,case.height),(0x34,bits(10.5)),(0x38,bits(-12.25)),(0x3C,bits(3.75)),(0x40,bits(.25)),(0x44,bits(-.5)),(0x48,bits(1.0))):wr(m,ACTOR+off,v,4,order)
    for off,v in zip((0x4C,0x50,0x54),((1,1,1),(-.5,2,1.5),(0,-1,3))[case.scale]):wr(m,ACTOR+off,bits(v),4,order)
    if slot(case)not in m:
        for i in range(4):assert slot(case)+i not in m;m[slot(case)+i]=0
    pointer=0 if case.connected&4 and(case.fresh or not case.success)else template_buffer(case)
    wr(m,slot(case),pointer,4,order);m[PAGE]=case.page
    return m

def public(m,case):return {a:v for a,v in m.items()if not STACK+case.phase-2048<=a<STACK+case.phase+512}

def copy_bytes(m,dest,source,n,order='big'):
    for i in range(n):m[u32(dest+i)]=m[u32(source+i)]

def effect(m,case,stage,index,home,order='big'):
    if stage==BACKEND and case.private:wr(m,home+4,0x7FFF,4,order)
    if stage==COPY and index==1 and case.mutation:
        wr(m,slot(case),ALT,4,order);wr(m,ACTOR+0x2C,bits(-4.75),4,order)
    if stage==ORIENT and case.mutation:
        wr(m,ACTOR+0x34,bits(-7.5),4,order);wr(m,ACTOR+0x50,bits(-2.0),4,order);wr(m,ACTOR+0x2C,bits(19.0),4,order)
    if stage==ORIENT and case.private==2:wr(m,home-216+0x8C,ALT+64,4,order)
    if stage==MATRIX and case.redirect:wr(m,home-216+0x90,ALT+index*16,4,order)

def transformed(values,x,y,z=0.0):
    return [bits(add(add(mul(values[i],x),mul(values[i+4],y)),add(mul(values[i+8],z),values[i+12])))for i in range(3)]

def reference(initial,case=Case(),order='big',home=None):
    m=dict(initial);calls=[];home=STACK+case.phase if home is None else home;frame=home-216;cur,first,fresh,points,matrix=(frame+x for x in(0x90,0x8C,0x5B,0x5C,0x98));view=u32(half(case.view));wr(m,home+4,case.view,4,order)
    calls.append((BACKEND,(ACTOR+0x100,view,64,cur,fresh)))
    if case.connected&4:
        p=rd(m,slot(case),4,order);m[fresh]=0
        if not p:
            calls.append((ALLOC,(128,1,2,1)));p=BUFFER if case.success else 0;wr(m,slot(case),p,4,order)
            if p:m[fresh]=1
        answer=u32(p+(0 if case.page else 64))if p else 0
    else:m[fresh]=case.fresh;answer=output(case)if case.success else 0
    wr(m,cur,answer,4,order);effect(m,case,BACKEND,0,home,order);wr(m,first,answer,4,order)
    if not answer:return dict(memory=m,observed=public(m,case),calls=calls,value=0)
    if m[fresh]:
        for i in range(2):
            dest=u32(rd(m,slot(case),4,order)+i*64);calls.append((COPY,(dest,ACTOR+0xC0,64)));copy_bytes(m,dest,ACTOR+0xC0,64,order);effect(m,case,COPY,i+1,home,order)
    # The eight corner components are read before orientation can mutate actor fields.
    for i,(sx,sy)in enumerate(((1,1),(-1,1),(-1,-1),(1,-1))):
        wr(m,points+i*12,rd(m,ACTOR+0x2C,4,order)^(0x80000000 if sx<0 else 0),4,order);wr(m,points+i*12+4,rd(m,ACTOR+0x30,4,order)^(0x80000000 if sy<0 else 0),4,order)
    calls.append((ORIENT,(matrix,*[rd(m,ACTOR+o,4,order)for o in(0x40,0x44,0x48)])))
    values=matrix_values(case.pattern)
    for i,v in enumerate(values):wr(m,matrix+i*4,bits(v),4,order)
    effect(m,case,ORIENT,0,home,order)
    for i,off in enumerate((0x34,0x38,0x3C),12):wr(m,matrix+i*4,rd(m,ACTOR+off,4,order),4,order)
    for row,off in enumerate((0x4C,0x50,0x54)):
        for col in range(3):
            p=matrix+(row*4+col)*4;wr(m,p,bits(mul(floating(rd(m,p,4,order)),floating(rd(m,ACTOR+off,4,order)))),4,order)
    for i in range(4):
        point=points+i*12;x,y=(rd(m,point+j*4,4,order)for j in range(2));calls.append((MATRIX,(matrix,x,y,0,point,point+4,point+8)))
        values=[floating(rd(m,matrix+j*4,4,order))for j in range(16)];coords=transformed(values,floating(x),floating(y))
        for j,v in enumerate(coords):wr(m,point+j*4,v,4,order)
        effect(m,case,MATRIX,i,home,order)
        for j,v in enumerate(coords):wr(m,rd(m,cur,4,order)+j*2,trunc(floating(v)),2,order)
        wr(m,rd(m,cur,4,order)+6,0,2,order);wr(m,cur,rd(m,cur,4,order)+16,4,order)
    return dict(memory=m,observed=public(m,case),calls=calls,value=rd(m,first,4,order))

@lru_cache(None)
def rom():return(c.ROOT/'conker/conker.us.bin').read_bytes()
def helpers(case):
    code={}
    for bit,entry,at,n in((1,COPY,0x22EC0,11),(2,MATRIX,0xD4E10,40),(4,BACKEND,0x203210,52)):
        if case.connected&bit:code.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom(),at)))
    return code

class Oracle(ram.Oracle):
    def __init__(self,words,memory,case=Case(),entry=ENTRY,connected=None,arguments=None,reference_leaf=False):
        self.home=STACK+case.phase;self.copies=0;self.transforms=0;self.reference_leaf=reference_leaf
        code=helpers(case);code.update(connected or{})
        FactoryOracle.__init__(self,words,memory,case,entry=entry,s=symbols(),connected=code,arguments=arguments or(ACTOR,u32(case.view)))
    def execute(self,w):
        if w>>26 not in(53,61):return super().execute(w)
        op,rs,rt=w>>26,w>>21&31,w>>16&31;at=u32(self.r[rs]+half(w));assert rt%2==0 and at%8==0
        old=self.own_instruction;self.own_instruction=True;self.dispatched_word=w
        try:
            if op==61:self.put(at,self.f[rt+1]<<32|self.f[rt],8)
            else:v=self.get(at,8);self.f[rt],self.f[rt+1]=v&0xFFFFFFFF,v>>32
        finally:self.own_instruction=old
    def record_call(self,t):
        counts={BACKEND:5,COPY:3,ORIENT:4,MATRIX:7,ALLOC:4,ENTRY:2,0x100043B4:2,0x151462C8:9,0x151441A4:14,0x151442FC:14,0x15142B7C:3,0x15142E24:11,0x15142C10:6,0x15142CF0:8,0x1513F4E4:3,0x15142FBC:3}
        assert t in counts,hex(t);args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args))
        if t==ENTRY:self.home=self.r[29]
        if t==BACKEND:self.cursor_slot,self.fresh_slot=args[3:]
    def hook(self,t):
        case=self.case;a=self.calls[-1][1];value=0
        if t==ENTRY:
            assert self.reference_leaf;e=reference(self.memory,replace(case,view=a[1]),home=self.home);self.memory=e['memory'];self.calls.extend(e['calls']);value=e['value']
        elif t==BACKEND:
            self.put(a[3],output(case)if case.success else 0,4);self.put(a[4],case.fresh,1);effect(self.memory,case,t,0,self.home)
        elif t==COPY:
            copy_bytes(self.memory,*a);self.copies+=1;effect(self.memory,case,t,self.copies,self.home);value=a[0]
        elif t==ALLOC:value=BUFFER if case.success else 0
        elif t==ORIENT:
            for i,v in enumerate(matrix_values(case.pattern)):self.put(a[0]+i*4,bits(v),4)
            effect(self.memory,case,t,0,self.home)
        elif t==MATRIX:
            values=[floating(self.get(a[0]+i*4,4))for i in range(16)];coords=transformed(values,*map(floating,a[1:4]))
            for p,v in zip(a[4:],coords):self.put(p,v,4)
            effect(self.memory,case,t,self.transforms,self.home);self.transforms+=1
        elif t in(0x151441A4,0x151442FC):
            for i,p in enumerate(a[:4]):self.put(p,11*(i+1),2)
        elif t==0x100043B4:value=0
        else:value=u32(a[0]+8)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def caller_fixture(case,flags=0,enabled=1,visible=255,attached=0,animation=255):
    m=fixture(case)
    for i,v in enumerate(rom()[0x22E8DC:0x22E978]):m[TABLE+i]=v
    for off,v,n in((0x10,enabled,4),(0x58,flags,4),(0x64,visible,1),(0x60,0xA0000 if attached else 0,4),(0x73,0,1),(0x18,animation,1),(0x1A,0,2)):wr(m,ACTOR+off,v,n)
    if attached:wr(m,0xA0002,attached,2)
    for p,n in((GFX,4096),(0x800D2C9C,4),(0x80090B60,512),(0x800A4AC8,2048)):
        for i in range(n):assert p+i not in m;m[p+i]=0
    return m

def cases():
    widths=(bits(0.0),bits(-0.0),bits(1.25),bits(-2.75),bits(32767.75),bits(65536.5))
    for view,fresh,success,pattern,scale,mutation,redirect in itertools.product((0,1,0xFFFF,0x12340002),(0,1,255),(0,1),range(3),range(3),(0,1),(0,1)):
        yield Case(view=view,fresh=fresh,success=success,pattern=pattern,scale=scale,mutation=mutation,redirect=redirect,width=widths[(pattern+scale)%6])
    for connected,fresh,success,page in itertools.product((1,2,3,4,7),(0,1),(0,1),(0,1)):
        yield Case(connected=connected,fresh=fresh,success=success,page=page,view=3,scale=2)
    for private,alias in itertools.product((0,1,2),(0,1,2)):
        yield Case(private=private,alias=alias,mutation=1,redirect=1,phase=8)
    for view in(0x8000,0x7FFF):yield Case(view=view,fresh=1)
    for width in(0x7FC12345,0x7F800000,0x7F7FFFFF):yield Case(width=width,fresh=0)

def native_cases():
    result=[]
    for case in cases():
        if case.private or case.alias or case.connected or case.view not in(0,1,3)or case.phase:continue
        e=reference(fixture(case),case);frame=STACK-216
        values=[floating(rd(e['memory'],frame+0x5C+i*12+j*4))for i in range(4)for j in range(3)]if case.success else[]
        if all(math.isfinite(v)and-2147483648<=v<2147483648 for v in values):result.append(case)
    return tuple(result)
