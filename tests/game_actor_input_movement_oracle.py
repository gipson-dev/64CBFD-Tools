"""Independent ordered float32 movement model and bounded opaque-provider contracts."""
from collections import Counter
import math
import struct

from tools.experiments import game_actor_input_movement_recovery as source
from tools.tests import game_view_point_projection_oracle as point
from tools.tests.test_game_point_transform_match import put, read

STACK,ACTOR,INPUT,OTHER_INPUT,SLOT=point.STACK,0x20000,0x60000,0x60010,0x62000
TABLE=0x800CC2D0
FIELDS=((0x18,4),(0x20,4),(0x24,4),(0x28,4),(0x3C,4),(0x40,4),(0x44,4),
    (0x76,2),(0x78,2),(0x7A,2),(0x7E,1),(0x80,1),(0x83,1),(0x86,1),(0xAB,1),
    (0xAD,1),(0xB8,4),(0xC0,4),(0xC4,4),(0xF8,4),(0x102,1),(0x103,1),
    (0x104,1),(0x118,4),(0x13C,1),(0x13D,1),(0x1CC,4),(0x218,4),(0x222,1),
    (0x232,1),(0x25C,4))
SIZES={0x800BE710:2,0x800BE728:4,0x800CC284:4,0x800CC288:4,0x80082FA0:4,
    0x800C3E78:1,0x800E0B94:1,0x800CC26D:1,0x800CBDD3:1,0x800CC280:4,
    0x800BE9F0:4,0x800D1550:4,0x800D1580:4,0x800D154C:4}
NORMAL={0x150585F0:2,0x15059140:1,0x1505A5CC:1,0x15052590:1,0x1506E8D8:0,
    0x1506E5FC:0,0x1505959C:2,0x1505A6F8:2,0x150599C8:3,0x15073FA0:0,
    0x150F34A0:2,0x1505E650:7}
bits,floating=point.bits,point.floating


def rounded(v):return floating(bits(v))
def signed(v,n=32):return ((v&((1<<n)-1))^(1<<(n-1)))-(1<<(n-1))
def trunc(v):return math.trunc(v)&0xFFFFFFFF if math.isfinite(v) and -(2**31)<=v<2**31 else 0x80000000
def public(memory):return {a:v for a,v in memory.items() if not STACK-0x600<=a<STACK+0x140}


def fixture(rom,**spec):
    case=dict(mode=1,disabled=0,buttons=0,pressed=0,x=17,y=-23,held=0,cooldown=0,
        position=100.,threshold=-100.,depth=75.,speed=30.,velocity=-4.,below=0,
        nearby=0,control=0,gate=0,count=0,category=0x3C,magnitude=32.5,angle=0xE123,
        yaw=-32768,pattern=0,mutation=0,phase=0,actor=ACTOR,eligible=(),distances=())
    case.update(spec);actor=case['actor']
    memory={STACK+i:(i*17+case['pattern']*31+0xA5)&255 for i in range(-0x600,0x140)}
    for base,length in ((TABLE,25*0x32C),(actor,0x32C),(INPUT,32),(SLOT,4)):
        memory.update({base+i:0xA5 for i in range(length)})
    for address,size in SIZES.items():memory.update({address+i:0xA5 for i in range(-4,size+4)})
    for i in range(25):
        row=TABLE+i*0x32C
        for off,value,size in ((0,1 if 1<=i<=case['count'] else 0,4),(4,0x25,1),(0x1CA,0,1),
                (0x28,bits(0.),4),(0x232,0,1),(0x18,bits(12.5+i),4),
                (0x13D,0xA7,1),(0x104,1,1),(0x218,0xA5A5A5A5,4),(0xF8,0xA5A5A5A5,4)):
            put(memory,row+off,value,size)
    for index,active,eligible,depth,animation,kind in case['eligible']:
        row=TABLE+index*0x32C
        for off,value,size in ((0,active,4),(0x1CA,eligible,1),(0x28,bits(depth),4),
                              (0x232,animation,1),(4,kind,1)):put(memory,row+off,value,size)
    for off,value,size in ((0,1,4),(4,0x9B,1),(0x18,bits(case['position']),4),
            (0x20,bits(case['velocity']),4),(0x24,bits(-3.),4),(0x28,bits(case['depth']),4),
            (0x3C,bits(case['speed']),4),(0x76,0xFEDC,2),(0x7A,case['yaw'],2),
            (0x86,case['below'],1),(0xB8,bits(11.5),4),(0xC0,bits(-7.),4),
            (0xC4,bits(2.5),4),(0x102,case['mode'],1),(0x103,case['cooldown'],1),
            (0x104,case['disabled'],1),(0x118,bits(case['threshold']),4),
            (0x13C,case['held'],1),(0x25C,case['control'],4)):put(memory,actor+off,value,size)
    values={0x800BE710:case['pressed'],0x800BE728:SLOT,0x800CC284:OTHER_INPUT,
        0x800CC288:0xA5A5A5A5,0x80082FA0:0,0x800C3E78:0,0x800E0B94:0,
        0x800CC26D:case['nearby'],0x800CBDD3:0,0x800CC280:0xFEDC1234,
        0x800BE9F0:case['category'],0x800D1550:bits(1.),0x800D1580:0xA5A5A5A5,
        0x800D154C:actor}
    if case['gate']==2:values[0x80082FA0]=0xFFFFFFFF
    if case['gate']==4:values[0x800E0B94]=2
    for address,value in values.items():put(memory,address,value,SIZES[address])
    put(memory,SLOT,INPUT)
    put(memory,INPUT,case['buttons'],2);put(memory,INPUT+2,case['x'],1);put(memory,INPUT+3,case['y'],1)
    put(memory,OTHER_INPUT,0x4000,2);put(memory,OTHER_INPUT+2,-111,1);put(memory,OTHER_INPUT+3,91,1)
    put(memory,0x800DDE3C,1 if case['gate'] else 0,1)
    put(memory,0x800DDDC8,bits(.75 if case['gate']==3 else 1.))
    for address in range(0x800A1980,0x800A19D8,4):
        put(memory,address,struct.unpack_from('>I',rom,0x246440+address-0x800A1980)[0])
    return memory,case


def snapshot(memory,actor):
    return tuple(read(memory,actor+off,size) for off,size in FIELDS)+(
        read(memory,0x800CC284),read(memory,0x800CC288),read(memory,0x800CC26D,1),
        read(memory,0x800CBDD3,1),read(memory,0x800D1580))


def provider(memory,case,target,args,ordinal):
    actor=case['actor'];mode=case['mutation']
    if target==0x1505A630:value=case['angle']
    elif target==0x1505A5CC:value=bits(case['magnitude'])
    elif target==0x1505A6F8:
        index=(args[1]-TABLE)//0x32C;choices=dict(case['distances'])
        value=bits(choices.get(index,1000.-index*11.))
    elif target==0x150F34A0:
        v=floating(args[1])
        value=point.add(point.mul(args[1],read(memory,0x800A1980)),read(memory,0x800A1984)) if v < -5. else bits(.75)
    else:value=0xA5000002
    actions=[]
    if mode==1 and target==0x1505A630:actions=[(0x800CC284,OTHER_INPUT,4)]
    elif mode==2 and target==0x15059140:
        actions=[(actor+0x13C,101,1),(actor+0x28,bits(25.),4),(actor+0x3C,bits(-2.),4)]
    elif mode==3 and target==0x1505A6F8:
        actions=[(0x800D154C,TABLE+2*0x32C,4),(0x800CC26D,101,1)]
    elif mode==4 and target==0x1505A3A8:
        actions=[(actor+0x20,bits(-100.),4),(actor+0x3C,bits(205.),4),
                 (actor+0x7A,0x7FFF,2),(actor+0x86,1,1)]
    elif mode==5 and target==0x150599C8:actions=[(0x800CC284,OTHER_INPUT,4)]
    elif mode==6 and target==0x1506E8D8:actions=[(0x800CC26D,102,1),(0x800C3E78,2,1)]
    elif mode==7 and target==0x1505959C:actions=[(0x800CC26D,102,1)]
    elif mode==8 and target==0x15059140:
        actions=[(actor+0x25C,2,4),(actor+0x13C,101,1),(INPUT,0,2)]
    elif mode==9 and target==0x15052590:actions=[(0x800CC26D,101,1)]
    for at,v,size in actions:put(memory,at,v,size)
    return value,actions


def reference(initial,case):
    m=dict(initial);actor=case['actor'];calls=[];observations=[];counts=Counter();fired=[]
    def r(at,size=4):return read(m,at,size)
    def w(at,v,size=4):put(m,at,v&((1<<(8*size))-1),size)
    def f(at):return floating(r(at))
    def wf(at,v):w(at,bits(v))
    def af(off):return f(actor+off)
    def sf(off,v):wf(actor+off,v)
    def ar(off,size=1):return r(actor+off,size)
    def aw(off,v,size=1):w(actor+off,v,size)
    def flag(mask):return r(r(0x800CC284),2)&mask
    def stick(off):return float(signed(r(r(0x800CC284)+off,1),8))
    def k(at):return f(at)
    def mul(a,b):return rounded(a*b)
    def add(a,b):return rounded(a+b)
    def sub(a,b):return rounded(a-b)
    def call(target,*args):
        args=tuple(v&0xFFFFFFFF for v in args);calls.append((target,args))
        observations.append(snapshot(m,actor));counts[target]+=1
        value,actions=provider(m,case,target,args,counts[target])
        if actions:fired.append((target,counts[target]))
        return value
    def release():
        record=(TABLE+(ar(0x13C)-100)*0x32C)&0xFFFFFFFF
        w(record+0x13D,0,1);w(record+0x232,0x21,1);w(record+0x218,0)
        w(record+0x104,0,1);w(record+0xF8,r(record+0xF8)&~0x400)
        w(record+0x3C,r(actor+0x3C));aw(0x13C,0)
    contact=0.
    aw(0xAB,1);aw(0x80,1);aw(0x222,0)
    w(0x800CC288,r(0x800BE710,2));controller=r(r(0x800BE728));w(0x800CC284,controller)
    index=r(0x800C3E78,1)
    if signed(r(0x80082FA0))>=index and r(0x800DDE3C+index,1) and k(0x800DDDC8+index*4)>.75 and r(0x800E0B94,1)!=2:
        w(controller+2,0,1);w(r(0x800CC284)+3,0,1);w(r(0x800CC284),0,2);w(0x800CC288,0)
    w(actor+0xF8,r(actor+0xF8)|0x40);w(actor+0x1CC,r(actor+0x18))
    if ar(0x103):aw(0x103,ar(0x103)-1)
    if ar(0x104):
        call(0x150585F0,actor,bits(.25));call(0x15059140,actor)
        sf(0x40,mul(float(signed(ar(0x7A,2),16)+0x4000),floating(0x3BB40000)))
        if ar(0x13C):release()
        return m,calls,observations,fired
    if not ar(0x102):
        aw(0xAD,0)
        angle=call(0x1505A630,bits(stick(2)),bits(stick(3)),0)&65535
        value=floating(call(0x1505A5CC,r(0x800CC284)))
        if flag(0x10):value=0.
        aw(0x78,ar(0x7A,2),2)
        if value>1.:aw(0x78,angle+r(0x800CC280),2)
        aw(0x232,7);aw(0x218,0,4);sf(0x44,mul(value,k(0x800A1988)))
        if r(0x800CC288)&0xC000 or af(0x28)>100.:aw(0x232,8);aw(0x102,1)
        call(0x15052590,actor)
        if r(0x800CC26D,1):
            if af(0x28)>30.:
                w(0x800D1580,0xFF010074);call(0x1506E8D8)
                call(0x1505959C,(TABLE+r(0x800CC26D,1)*0x32C-100*0x32C)&0xFFFFFFFF,r(0x800C3E78,1))
                aw(0x102,1);aw(0x13C,r(0x800CC26D,1))
            sf(0x20,23.)
        if af(0x18)<af(0x118):aw(0x102,1);aw(0x86,1);sf(0x20,-6.)
        return m,calls,observations,fired
    speed=af(0x3C)
    if speed>60.:speed=60.
    inp=mul(stick(3),1.25)
    masked=flag(0x10)
    if masked:inp=0.
    if ar(0x13C):
        if not masked:sf(0x18,sub(af(0x18),mul(16.,k(0x800D1550))))
    else:
        distance=1000.
        for index in range(25):
            record=TABLE+index*0x32C
            if r(record) and r(record+0x1CA,1) and f(record+0x28)==0. and r(record+0x232,1)!=0x21 and r(record+4,1) in (0x9C,0x9D):
                value=floating(call(0x1505A6F8,r(0x800D154C),record))
                if value<distance:aw(0x222,index);distance=value
    if inp < -90.:inp=-90.
    if inp > 90.:inp=90.
    if k(0x800A198C)<af(0x18):
        if af(0x20)>-30.:sf(0x20,sub(af(0x20),1.5))
        inp=40.
    value=af(0xC4)
    sf(0xC4,add(value,mul(sub(stick(2),value),mul(k(0x800A1990),k(0x800D1550)))))
    aw(0x7E,25)
    value=mul(mul(mul(mul(af(0xC4),k(0x800D1550)),k(0x800A1994)),
              mul(sub(100.,speed),k(0x800A1998))),220.)
    angle=(ar(0x76,2)-trunc(value))&65535;aw(0x76,angle,2);call(0x150599C8,actor,8,angle)
    sf(0xC0,0.);speed=0.;rate=k(0x800A199C)
    if af(0x18)<af(0x118):
        if not ar(0x86):aw(0x86,1);sf(0x3C,0.);sf(0x20,-6.)
    elif ar(0x86):aw(0x86,0);sf(0x20,9.)
    buttons=r(r(0x800CC284),2)
    if not buttons&0x10:
        if buttons&0x8000:
            sf(0xC0,-22.);speed=1.;rate=k(0x800A19A0);buttons=r(r(0x800CC284),2)
        if buttons&0x4000:
            value=af(0x20);sf(0xC0,30.)
            if value<0.:sf(0xC0,sub(af(0xC0),mul(value,k(0x800A19A4))))
            speed=1.5;rate=k(0x800A19A8)
    call(0x1505A3A8,r(actor+0xC0),actor,bits(speed),bits(rate),1)
    sf(0x40,mul(float(signed(ar(0x7A,2),16)+0x4000),floating(0x3BB40000)))
    sf(0x24,mul(mul(inp,k(0x800A19AC)),sub(200.,af(0x3C))))
    if not ar(0x13C):
        if af(0x20)>26.:sf(0x20,26.)
        if af(0x20)<-34.:sf(0x20,-34.)
    magnitude=abs(mul(inp,.5))
    if ar(0x86):magnitude=mul(magnitude,k(0x800A19B0));sf(0x24,mul(af(0x24),k(0x800A19B4)))
    acceleration,velocity=af(0x24),af(0x20)
    if acceleration==0.:
        if abs(velocity)<1.5:sf(0x20,0.)
        elif velocity>0.:sf(0x24,k(0x800A19B8))
        else:sf(0x24,k(0x800A19BC))
    elif mul(magnitude,k(0x800A19C0))<velocity and acceleration<0. or velocity<mul(-magnitude,1.5) and acceleration>0.:
        sf(0x24,0.)
    aw(0xAD,10)
    if flag(0x10):
        value=af(0xB8);sf(0x20,0.);sf(0x24,0.)
        sf(0xB8,add(value,mul(sub(stick(3),value),k(0x800A19C4))))
    else:
        value=mul(sub(af(0x20),0.),-2.);sf(0xB8,value)
        if value>40.:sf(0xB8,40.)
        elif af(0xB8)<-55.:sf(0xB8,-55.)
    speed=af(0x20);w(0x800CBDD3,1,1);call(0x15059140,actor);w(0x800CBDD3,0,1)
    if ar(0x13C) and af(0x28)<50.:contact=50.
    if not flag(0x10):
        if r(0x800CC26D,1) and not ar(0x13C):
            record=(TABLE+r(0x800CC26D,1)*0x32C-100*0x32C)&0xFFFFFFFF
            if f(record+0x28)==0.:
                sf(0x20,20.);sf(0x18,add(f(record+0x18),70.))
                call(0x1505959C,(TABLE+r(0x800CC26D,1)*0x32C-100*0x32C)&0xFFFFFFFF,r(0x800C3E78,1))
                aw(0x13C,r(0x800CC26D,1));w(0x800D1580,0xFF010074);call(0x1506E8D8)
        if ar(0x13C):
            if ar(0x25C,4)&2:
                aw(0x25C,ar(0x25C,4)&~2,4);release();sf(0x20,0.)
                w(0x800D1580,0x76);call(0x1506E8D8)
        elif r(0x800CC288)&0x2000 and not ar(0x103) and r(0x800BE9F0)==0x3C:
            count=sum(bool(r(TABLE+i*0x32C)) and r(TABLE+i*0x32C+4,1)==0x25 for i in range(1,25))
            if count<5:w(0x800D1580,6);aw(0x103,4);call(0x15073FA0)
    if af(0x28)<=contact:
        sf(0x3C,mul(af(0x3C),k(0x800A19C8)))
        if flag(0x4000) or ar(0x86) or ar(0x13C):
            if ar(0x13C):
                if af(0x20)<-10.:
                    w(0x800D1580,0xFF0100A7);call(0x1506E5FC);w(0x800D1580,0xFF060372);call(0x1506E8D8)
            elif af(0x18)<0.:w(0x800D1580,0xFF010072);call(0x1506E8D8)
            if not ar(0x13C):sf(0x20,20.)
            elif not ar(0x86):sf(0x20,38.)
            inp=-80.
        else:aw(0x102,0);sf(0x20,mul(speed,-1.));sf(0xB8,0.);sf(0x28,k(0x800A19CC))
    if not flag(0x10):sf(0xB8,add(af(0xB8),20.))
    else:sf(0x20,mul(af(0xB8),k(0x800A19D0)))
    if ar(0x86):
        aw(0x83,0);amount=1. if abs(inp)>8. or af(0xC0)>7. else .5
    else:amount=floating(call(0x150F34A0,actor,bits(inp)))
    animation=0xF
    if af(0xB8)>40. and inp>20.:animation=0x11
    if af(0x3C)<20. and af(0xC0)<=0. and inp==0.:animation=0x18
    if af(0x3C)<0.:animation=0x1F
    if ar(0x13C):animation=0x17;amount=add(amount,k(0x800A19D4))
    call(0x1505E650,actor,animation,bits(amount),bits(9.),0,0,0)
    return m,calls,observations,fired


class Oracle(point.PointProjectionOracle):
    def __init__(self,words,memory,case,connected=None,entry=source.ENTRY):
        super().__init__(words,memory,(case['actor'],),[],case['phase'],entry,connected)
        self.case=case;self.observations=[];self.fired=[];self.counts=Counter()

    def execute(self,word):
        op,rs,rt,rd,fd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
        self.dispatched_word=word
        if op==32:
            self.own_instruction=True
            try:
                address=(self.r[rs]+signed(word,16))&0xFFFFFFFF
                self.r[rt]=signed(self.get(address,1),8)&0xFFFFFFFF
            finally:self.own_instruction=False
        elif op==17 and rs==16 and fn in (5,7,13):
            self.f[fd]=(self.f[rd]&0x7FFFFFFF if fn==5 else self.f[rd]^0x80000000 if fn==7 else trunc(floating(self.f[rd])))
        else:super().execute(word)
        self.r[0]=0

    def record_call(self,target):
        if target==0x1505A630:args=(self.f[12],self.f[14],self.r[6])
        elif target==0x1505A3A8:args=(self.f[12],*self.arguments(5)[1:])
        else:args=self.arguments(NORMAL[target])
        self.calls.append((target,args));self.events.append(('CALL',target,args))
        self.observations.append(snapshot(self.memory,self.case['actor']));self.counts[target]+=1

    def hook(self,target):
        value,actions=provider(self.memory,self.case,target,self.calls[-1][1],self.counts[target])
        if actions:self.fired.append((target,self.counts[target]))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        if target in (0x1505A5CC,0x1505A6F8,0x1505A3A8):self.f[0]=value
        else:self.r[2]=value
