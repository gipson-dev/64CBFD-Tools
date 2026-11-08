"""Independent ordered public-RAM model; canonical floats, no FCSR claim."""
from dataclasses import dataclass,replace
import itertools,math,struct,sys
from pathlib import Path
from tools.experiments import game_oriented_strip_1513fab4_candidates as c
ROOT=c.ROOT
from tools.tests import game_record_vertex_callback_1513e83c_oracle as base
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
ENTRY,GETTER,CROSS=0x1513FAB4,0x15144B34,0x150AD8B0
ACTOR,BUFFER,ALT,STACK,PAGE,BACKEND,COPY,ALLOC=base.ACTOR,base.BUFFER,base.ALT,base.STACK,base.PAGE,base.BACKEND,base.COPY,base.ALLOC
SCALE,CAMERA,STATE=0xB0000,0xC0000,0x800DBFF0
u32,half,rd,wr,state=base.u32,base.half,base.rd,base.wr,base.state
floating,trunc=base.floating,base.trunc
def bits(v):return 0x7FC00000 if math.isnan(v)else base.bits(v)
def add(a,b):return floating(bits(a+b))
def sub(a,b):return floating(bits(a-b))
def mul(a,b):return floating(bits(a*b))
def sqrt(a):return floating(bits(math.sqrt(a)if a>=0 else math.nan))
def div(a,b):return floating(bits(a/b if b else math.nan if not a else math.copysign(math.inf,a*math.copysign(1.,b))))
CENTERS=(10.5,-12.25,3.75)
TARGETS=((11.5,-11.25,4.75),CENTERS,(10.5,-8.25,3.75),(6.5,-12.25,3.75),(10.5,-12.25,-3.75))
@dataclass(frozen=True)
class Case(base.Case):
    vertexOrder:int=1
    widthFactor:int=0x3F800000
    heightFactor:int=0x3F800000
    geometry:int=0
    viewerMode:int=0
def viewer(view):return u32(CAMERA+half(view)*0x9A0+0x2F8)
def slot(view):return u32(ACTOR+0x100+half(view)*4)
def output(c):return ACTOR+0x30 if c.alias==2 else BUFFER+(0 if c.page else 64)
def fixture(c=Case(),order='big'):
    m=base.fixture(c,order)
    for i,v in enumerate(TARGETS[c.geometry]):wr(m,ACTOR+0x40+i*4,bits(v),4,order)
    for p,v in((SCALE,c.widthFactor),(SCALE+4,c.heightFactor),(STATE,CAMERA)):
        for i in range(4):m.setdefault(p+i,0)
        wr(m,p,v,4,order)
    if c.private==1:wr(m,slot(1),ALT,4,order)
    for v in{0,1,2,3,half(c.view)}:
        point=(1.25*v,-.5*v,20.+2.*v)if c.viewerMode==0 else(11.+v,-10.-2.*v,-5.+.25*v)if c.viewerMode==1 else tuple(add(a,mul(mul(sub(t,a),mul(floating(c.height),floating(c.heightFactor))),.5))for a,t in zip(CENTERS,TARGETS[c.geometry]))
        for i,x in enumerate(point):
            for j in range(4):m.setdefault(viewer(v)+4*i+j,0)
            wr(m,viewer(v)+4*i,bits(x),4,order)
    return m
def public(m,c):return base.public(m,c)
def symbols():return dict(func_151D5D60=BACKEND,memcpy=COPY,func_15144B34=GETTER,func_150AD8B0=CROSS)
def cross_values(h,e):return(sub(mul(h[1],e[2]),mul(h[2],e[1])),sub(mul(h[2],e[0]),mul(h[0],e[2])),sub(mul(h[0],e[1]),mul(h[1],e[0])))
def effect(m,c,stage,home,cur,index=0,order='big'):
    frame=home-152
    if stage==BACKEND and c.private==1:wr(m,home+12,0x12340001,4,order)
    if stage==COPY and index==1 and c.mutation&1:
        wr(m,slot(half(rd(m,home+12,4,order))),ALT,4,order);wr(m,ACTOR+0x2C,bits(-4.75),4,order)
    if stage==GETTER and c.mutation&2:
        for off,v in((0x2C,19.),(0x30,6.5),(0x40,-2.),(0x44,3.25),(0x48,8.5)):wr(m,ACTOR+off,bits(v),4,order)
        wr(m,SCALE,bits(-.5),4,order);wr(m,SCALE+4,bits(2.),4,order)
    if stage==CROSS:
        if c.mutation&4:
            for off,v in((0x34,-7.5),(0x38,2.25),(0x3C,-9.5),(0x2C,0.)):wr(m,ACTOR+off,bits(v),4,order)
            wr(m,SCALE,bits(8.),4,order)
        if c.redirect:wr(m,cur,ALT+64,4,order)
        if c.private==2:wr(m,frame+0x90,ALT+128,4,order)
        if c.private==3:wr(m,frame+0x44,bits(-3.),4,order)
        if c.private==4:
            for i,x in enumerate((5.,-2.,8.)):wr(m,frame+0x74+i*4,bits(x),4,order)
        if c.private==5:wr(m,home+4,0x12340000,4,order)
def reference(initial,c=Case(),order='big',home=None):
    m=dict(initial);home=STACK+c.phase if home is None else home;frame=home-152;cur,first,fresh=(frame+x for x in(0x94,0x90,0x43));calls=[];semantic=[];casts=[]
    for p,v in((home+4,c.vertexOrder),(home+8,SCALE),(home+12,c.view)):wr(m,p,v,4,order)
    calls.append((BACKEND,(ACTOR+0x100,u32(half(c.view)),64,cur,fresh)));semantic.append((BACKEND,(ACTOR+0x100,u32(half(c.view)),64,0x200,0x201)))
    if c.connected&4:
        p=rd(m,slot(c.view),4,order);m[fresh]=0
        if not p:
            calls.append((ALLOC,(128,1,2,1)));semantic.append(calls[-1]);p=BUFFER if c.success else 0;wr(m,slot(c.view),p,4,order)
            if p:m[fresh]=1
        answer=u32(p+(0 if c.page else 64))if p else 0
    else:m[fresh]=c.fresh;answer=output(c)if c.success else 0
    wr(m,cur,answer,4,order);effect(m,c,BACKEND,home,cur,order=order);wr(m,first,answer,4,order)
    def finish():return dict(memory=m,observed=public(m,c),calls=calls,semantic_calls=semantic,value=rd(m,first,4,order),casts=casts)
    if not answer:return finish()
    if m[fresh]:
        address=slot(rd(m,home+12,4,order));wr(m,frame+0x34,ACTOR+0xC0,4,order);wr(m,frame+0x38,address-0x100,4,order)
        for i in range(2):
            a=(u32(rd(m,address,4,order)+i*64),ACTOR+0xC0,64);calls.append((COPY,a));semantic.append(calls[-1]);base.copy_bytes(m,*a,order);effect(m,c,COPY,home,cur,i+1,order)
    view=half(rd(m,home+12,4,order));point=viewer(view);calls.append((GETTER,(u32(view),)));semantic.append(calls[-1])
    if not c.connected&16:effect(m,c,GETTER,home,cur,order=order)
    load=lambda p:floating(rd(m,u32(p),4,order))
    store=lambda p,v:wr(m,p,bits(v),4,order)
    width=mul(load(ACTOR+0x2C),load(SCALE));factor=mul(load(ACTOR+0x30),load(SCALE+4));store(frame+0x44,width)
    h=[sub(load(ACTOR+0x40+i*4),load(ACTOR+0x34+i*4))for i in range(3)]
    for i,v in enumerate(h):store(frame+0x80+i*4,v)
    h=[mul(v,factor)for v in h]
    for i,v in enumerate(h):store(frame+0x80+i*4,v)
    end=[add(load(ACTOR+0x34+i*4),h[i])for i in range(3)]
    for i,v in enumerate(end):store(frame+0x74+i*4,v)
    eye=[sub(add(load(ACTOR+0x34+i*4),mul(h[i],.5)),load(point+i*4))for i in range(3)]
    for i,v in enumerate(eye):store(frame+0x5C+i*4,v)
    calls.append((CROSS,(frame+0x80,frame+0x5C,frame+0x50)));semantic.append((CROSS,tuple(bits(v)for v in h+eye)+(0x202,)))
    v=cross_values(h,eye)
    for i in(2,0,1):store(frame+0x50+i*4,v[i])
    if not c.connected&8:effect(m,c,CROSS,home,cur,order=order)
    side=[load(frame+0x50+i*4)for i in range(3)];endZ=load(frame+0x7C);length=add(add(mul(side[0],side[0]),mul(side[1],side[1])),mul(side[2],side[2]))
    if length==0.:side=[0.]*3
    else:
        factor=div(load(frame+0x44),sqrt(length));side=[mul(x,factor)for x in side]
    for i in(2,0,1):store(frame+0x50+i*4,side[i])
    alternate=rd(m,home+4,4,order)&255
    def flag():wr(m,rd(m,cur,4,order)+6,0,2,order)
    for i in range(4):
        end_point=(i>=2)if alternate else i in(1,2);plus=(i in(0,3))if alternate else i in(2,3)
        early=bool(alternate and i>=2)
        if early:flag()
        for j in range(3):
            center=(endZ if j==2 else load(frame+0x74+j*4))if end_point else load(ACTOR+0x34+j*4)
            v=add(center,side[j])if plus else sub(center,side[j]);casts.append(bits(v));wr(m,rd(m,cur,4,order)+j*2,trunc(v),2,order)
            if not alternate and i==1 and j==1:flag()
        if not early and not(not alternate and i==1):flag()
        if i<3:wr(m,cur,rd(m,cur,4,order)+16,4,order)
    return finish()
class Oracle(base.Oracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,arguments=None,connected=None):
        self.home=STACK+c.phase;self.copies=0;self.semantic_calls=[];code={}
        for bit,address,off,n in((1,COPY,0x22EC0,11),(4,BACKEND,0x203210,52),(8,CROSS,0xDAD60,19),(16,GETTER,0x171FE4,13)):
            if c.connected&bit:code.update(zip(range(address,address+n*4,4),struct.unpack_from('>%dI'%n,base.rom(),off)))
        code.update(connected or{});FactoryOracle.__init__(self,words,memory,c,entry=entry,s=symbols(),connected=code,arguments=arguments or(ACTOR,c.vertexOrder,SCALE,u32(c.view)))
    def execute(self,w):
        op,rs,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        if op==17 and rs==16:
            a,b=floating(self.f[fs]),floating(self.f[ft])
            if fn==0:self.f[fd]=bits(add(a,b))
            elif fn==1:self.f[fd]=bits(sub(a,b))
            elif fn==2:self.f[fd]=bits(mul(a,b))
            elif fn==3:self.f[fd]=bits(div(a,b))
            elif fn==4:self.f[fd]=bits(sqrt(a))
            elif fn==6:self.f[fd]=self.f[fs]
            elif fn==7:self.f[fd]=self.f[fs]^0x80000000
            elif fn==13:self.f[fd]=trunc(a)
            elif fn==50:self.condition=a==b
            else:raise AssertionError(('foreign strip FP',hex(w)))
            self.r[0]=0;return
        return super().execute(w)
    def record_call(self,t):
        counts={BACKEND:5,COPY:3,GETTER:1,CROSS:3,ALLOC:4,ENTRY:4};assert t in counts,hex(t)
        a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.home=self.r[29]
        if t==BACKEND:self.cursor_slot,self.fresh_slot=a[3:];s=(a[0],a[1],a[2],0x200,0x201)
        elif t==CROSS:s=tuple(rd(self.memory,p+i*4,4)for p in a[:2]for i in range(3))+(0x202,)
        else:s=a
        self.semantic_calls.append((t,s))
    def hook(self,t):
        c=self.case;a=self.calls[-1][1];value=0
        if t==BACKEND:self.put(a[3],output(c)if c.success else 0,4);self.put(a[4],c.fresh,1);effect(self.memory,c,t,self.home,self.cursor_slot)
        elif t==COPY:base.copy_bytes(self.memory,*a);self.copies+=1;effect(self.memory,c,t,self.home,self.cursor_slot,self.copies);value=a[0]
        elif t==GETTER:value=viewer(a[0]);effect(self.memory,c,t,self.home,self.cursor_slot)
        elif t==CROSS:
            h,e=([floating(rd(self.memory,p+i*4,4))for i in range(3)]for p in a[:2]);v=cross_values(h,e)
            for i in(2,0,1):self.put(a[2]+i*4,bits(v[i]),4)
            effect(self.memory,c,t,self.home,self.cursor_slot)
        elif t==ALLOC:value=BUFFER if c.success else 0
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def cases():
    for mode,view,geometry,viewerMode,fresh,success in itertools.product((0,1,255,0x12340002),(0,1,0x12340003),range(5),(0,2),(0,1),(0,1)):
        yield Case(vertexOrder=mode,view=view,geometry=geometry,viewerMode=viewerMode,fresh=fresh,success=success)
    for mutation,redirect,alias in itertools.product(range(8),(0,1),range(3)):yield Case(mutation=mutation,redirect=redirect,alias=alias)
    for private in range(1,6):yield Case(private=private,mutation=7,redirect=1)
    for connected,fresh,success,page in itertools.product((1,4,8,16,29),(0,1),(0,1),(0,1)):yield Case(connected=connected,fresh=fresh,success=success,page=page,view=3)
    for view in(0xFFFF,0x8000,0x7FFF):yield Case(view=view)
    for value in(0,0x80000000,bits(-2.75),bits(32767.75),0x7F800000,0x7FC12345):yield Case(width=value)
    for width,height in((0,0),(0x80000000,bits(-1.)),(bits(-2.),bits(3.)),(0x7F800000,bits(1.)),(bits(1.),0x7FC12345)):
        yield Case(widthFactor=width,heightFactor=height)
