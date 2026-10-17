"""Independent ordered packets, bounded IDO unsigned conversion and live aliases."""
import itertools
import math

from tools.experiments import game_color_overlay_draw as source
from tools.tests import game_color_progress_oracle as progress
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_animation_timeline_oracle import bits,floating

put,read,STACK=progress.put,progress.read,progress.STACK
MASK,BASE,VIEWS,OUTPUT,PACKET=0xFFFFFFFF,0x800BE628,0x30000,0x20020,0x22000
OFFSETS=(0x24,0x28,0x2C,0x30)
COORDS=((5.5,180.25,4.25,200.75),(0.,0.,0.,0.),(-0.5,1023.75,1024.5,2048.25),
    (-1.,-2.,-0.,-2147483648.),(2147483648.,4294967040.,2147483904.,16777217.),
    (math.inf,-math.inf,math.nan,4294967296.),(1.,-0.,math.nan,-0.75),
    (2147483648.,4294967040.,2147483904.,2147484160.))
RGBA=((0,0,0,0),(255,255,128,17),(0x12345678,-1,-0x80000000,0x7FFFFFFF),(0,0x3F,0x80,0))
FCSRS=(0,3,0x800004,0xA5A50003)
CALLERS=(('func_1517F3A0',0x1517F3A0,27),('func_1517F4D8',0x1517F4D8,35),
    ('func_15182768',0x15182768,25),('func_1510448C',0x1510448C,26),('func_150D22F4',0x150D22F4,32))


def store(memory,address,value):put(memory,address&MASK,value&MASK)


def unsigned(word):
    value=floating(word)
    return math.trunc(value)&MASK if math.isfinite(value) and -1.0<value<4294967296. else MASK


def prefix(initial,args,phase):
    memory=dict(initial);cursor,alpha,red,green,blue,channel=args
    store(memory,STACK+phase+16,blue);store(memory,STACK+phase+20,channel)
    for offset,value in ((0,0xE7000000),(4,0),(8,0xFCFFFFFF),(12,0xFFFDF6FB),(16,0xFA000000)):
        store(memory,cursor+offset,value)
    blue=read(memory,STACK+phase+16)
    store(memory,cursor+20,(red&255)<<24|(green&255)<<16|(blue&255)<<8|(alpha&255))
    store(memory,cursor+24,0xEF002CFF);store(memory,cursor+28,0x00504344)
    return memory,read(memory,STACK+phase+20)


def reference(initial,args,phase=0):
    memory,channel=prefix(initial,args,phase);cursor=args[0]
    row=(read(memory,BASE)+channel*0x180)&MASK
    bottom,right=(read(memory,(row+at)&MASK) for at in (0x28,0x30))
    store(memory,cursor+32,0xF6000000|(unsigned(right)&1023)<<14|(unsigned(bottom)&1023)<<2)
    row=(read(memory,BASE)+channel*0x180)&MASK
    top,left=(read(memory,(row+at)&MASK) for at in (0x24,0x2C))
    store(memory,cursor+36,(unsigned(left)&1023)<<14|(unsigned(top)&1023)<<2)
    valid=all(math.isfinite(floating(v)) and -1.0<floating(v)<4294967296. for v in (bottom,right,top,left))
    return memory,(cursor+40)&MASK,valid,(bottom,right,top,left)


def map_row(memory,row,coords,replace=False):
    absent={at for at in OFFSETS if (row+at)&MASK not in memory}
    for i in range(-16,0x190):memory.setdefault((row+i)&MASK,(i*13+0xA5)&255)
    for at,value in zip(OFFSETS,coords):
        if replace or at in absent:store(memory,row+at,bits(value))


def fixture(channel=0,coords=0,rgba=0,alias=0,phase=0):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
    memory.update({BASE+i:0xA5 for i in range(-16,24)})
    memory.update({OUTPUT+i:(i*13+0xA5)&255 for i in range(-32,96)})
    memory.update({PACKET+i:0xA5 for i in range(128)})
    memory.update({progress.BASE+i:(i*13+0xA5)&255 for i in range(progress.LENGTH)})
    for i in range(4):map_row(memory,VIEWS+i*0x180,COORDS[0],True)
    row=(VIEWS+channel*0x180)&MASK;map_row(memory,row,COORDS[coords],True);store(memory,BASE,VIEWS)
    cursor=(OUTPUT,BASE,BASE-4,BASE-16,BASE-20,BASE-32,row+4,row+12,row+8,row-32,STACK+phase+16,0xFFFFFFE0)[alias]&MASK
    for i in range(-16,64):memory.setdefault((cursor+i)&MASK,0xA5)
    alpha,red,green,blue=RGBA[rgba];args=tuple(v&MASK for v in (cursor,alpha,red,green,blue,channel))
    work,actual_channel=prefix(memory,args,phase)
    first=(read(work,BASE)+actual_channel*0x180)&MASK
    map_row(memory,first,(91.25,207.5,17.75,253.5))
    work,actual_channel=prefix(memory,args,phase)
    bottom,right=(read(work,(first+at)&MASK) for at in (0x28,0x30))
    store(work,cursor+32,0xF6000000|(unsigned(right)&1023)<<14|(unsigned(bottom)&1023)<<2)
    second=(read(work,BASE)+actual_channel*0x180)&MASK
    map_row(memory,second,(37.25,199.5,73.75,281.5))
    return memory,args


def cases():
    for channel,coords,rgba,phase in itertools.product((0,1,3,-1,0x10001,0x80000000),range(len(COORDS)),range(len(RGBA)),(0,8)):
        yield (*fixture(channel,coords,rgba,phase=phase),phase)
    for alias,channel,coords,phase in itertools.product(range(1,12),(0,1,3),(0,2,5),(0,8)):
        yield (*fixture(channel,coords,3,alias,phase),phase)


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x400<=a<STACK+0x100}


def caller_fixture(kind=0,channel=0,variant=0,coords=0):
    memory,_=fixture(channel,coords)
    timing=((0,0,0,0),(0,0,1,0),(-1,1,1,0),(0,0,0,255))[variant%4]
    color,_,_=progress.fixture(channel,*timing)
    memory.update({a:v for a,v in color.items() if progress.BASE<=a<progress.BASE+progress.LENGTH})
    put(memory,0x800DDE10+channel*2,(0,1,65535,1,1,65535)[variant%6],2)
    put(memory,0x800DDD9C+channel,(0,1,255,255,0,1)[variant%6],1)
    for offset,value in zip(range(0x28,0x2D),(0x3F,0x80,0,variant%256,channel)):
        put(memory,PACKET+offset,value,1)
    put(memory,PACKET+0x1B,(0,1,4,5,255,255)[variant%6],1)
    put(memory,PACKET+0x28,(0,1,255)[variant%3] if kind==4 else 0x3F,1)
    put(memory,PACKET+0x3C,(0,1,255)[variant%3],1);put(memory,PACKET+0x3D,(255,0,1)[variant%3],1)
    if kind<2:args=(OUTPUT,channel)
    elif kind==2:args=(OUTPUT,PACKET,channel if variant%2 else (channel+1)&MASK)
    elif kind==3:args=(OUTPUT,PACKET,(0,0,1,0,MASK,0)[variant%6])
    else:args=(OUTPUT,PACKET,channel)
    return memory,args


def caller_reference(memory,args,kind):
    memory=dict(memory);cursor=args[0];calls=[];packet=None
    if kind==0:
        channel=args[1];calls.append((progress.source.ENTRY,(channel,)))
        alpha,trap=progress.reference(memory,channel)
        if trap:raise progress.DivisionTrap(trap)
        if alpha:packet=(cursor,alpha,*[read(memory,0x800DDDA0+channel*3+i,1) for i in range(3)],channel)
    elif kind==1:
        channel=args[1]
        if read(memory,0x800DDE10+channel*2,2) and read(memory,0x800DDD9C+channel,1):
            packet=(cursor,read(memory,0x800DDD9C+channel,1),*[read(memory,0x800DDD90+channel*3+i,1) for i in range(3)],channel)
    elif kind==2:
        data=args[1]+0x28;gate=((args[2]&65535)^0x8000)-0x8000
        if gate==read(memory,data+4,1):packet=(cursor,read(memory,data+3,1),*[read(memory,data+i,1) for i in range(3)],read(memory,data+4,1))
    elif kind==3:
        gate=((args[2]&65535)^0x8000)-0x8000;value=read(memory,args[1]+0x1B,1)
        if gate==0 and value:packet=(cursor,value*63>>8,0,0,0,args[2])
    else:
        white=read(memory,args[1]+0x28,1)==1;color=255 if white else 0
        packet=(cursor,read(memory,args[1]+(0x3C if white else 0x3D),1),color,color,color,args[2])
    if packet:
        calls.append((source.ENTRY,packet));memory,cursor,_,_=reference(memory,packet)
    return memory,cursor,calls,packet


class OverlayOracle(progress.ProgressOracle):
    def __init__(self,words,memory,args,phase=0,fcsr=0,entry=source.ENTRY,helpers=None):
        super().__init__(words,memory,args,phase,entry,helpers)
        self.fcsr=self.initial_fcsr=fcsr;self.conversions=[];self.call_controls=[]

    def execute(self,word):
        op,rs,fn=word>>26,word>>21&31,word&63
        if op==17 and (rs in (2,6) or rs==16 and fn==36):
            AreaOracle.execute(self,word)
            if rs==16:self.conversions.append((self.current_pc,self.fcsr))
        else:super().execute(word)

    def record_call(self,target):
        if target==source.ENTRY:args=self.arguments(6)
        elif target==progress.source.ENTRY:args=self.arguments(1)
        else:raise ValueError('Unknown overlay caller target')
        self.calls.append((target,args));self.events.append(('CALL',target,args));self.call_controls.append(self.fcsr)

    def hook(self,target):raise ValueError('Overlay/progress code must execute, not be hooked')

    def run(self):
        result=super().run()
        assert self.fcsr==self.initial_fcsr,'Overlay conversion control state leaked'
        return result
