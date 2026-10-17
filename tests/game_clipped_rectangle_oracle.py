"""Independent signed clipping and ordered command/home publication reference."""
import itertools
import math

from tools.experiments import game_clipped_rectangle as source
from tools.tests import game_view_point_projection_oracle as point
from tools.tests.game_animation_timeline_oracle import bits,floating,signed

put,read,STACK=point.put,point.read,point.STACK
MASK,BASE,VIEWS,OUTPUT=0xFFFFFFFF,0x800BE628,0x30000,0x20020
BOUNDS=((2.75,100.5,-3.75,150.25),(0.,240.,0.,320.),(-1030.5,2050.75,-2048.5,3073.25),
    (40.,-40.,50.,-50.),(-0.,0.,-0.,0.),(-2147483648.,2147483520.,-2147483648.,2147483520.),
    (math.nan,math.inf,-math.inf,2147483648.),(1.,2.,-0.75,0.75))
ENDPOINTS=((10,20,30,40),(30,40,10,20),(-3,2,150,100),(-4,1,151,101),
    (-20,-30,10,20),(10,20,10,40),(10,20,30,20),(-10,2,5,100),
    (150,2,200,100),(-20,-20,-3,100),(0,100,150,101),(0,0,5,2),
    (-0x80000000,-0x80000000,0x7FFFFFFF,0x7FFFFFFF),(0x10005,-5,-5,0x10006))
SITES=(0x151808A8,0x151808FC,0x1518097C,0x151809FC,0x15180B04,0x15180B60,
    0x15180C14,0x15180C6C,0x15180CC4,0x15180D1C,0x15180D74,0x15180DCC,
    0x15180E24,0x15180E7C,0x151820A8,0x15182128)


def store(memory,address,value):put(memory,address&MASK,value&MASK)


def truncate(word):
    value=floating(word)
    return math.trunc(value) if math.isfinite(value) and -2147483648.<=value<2147483648. else -0x80000000


def reference(initial,args,phase=0):
    memory=dict(initial);cursor,left,top,right,_,_=args;sp=STACK+phase
    store(memory,sp+16,args[4]);store(memory,sp+20,args[5]);store(memory,sp,cursor)
    bottom=signed(read(memory,sp+16));view=read(memory,sp+20)
    left,top,right=map(signed,(left,top,right))
    left,right=min(left,right),max(left,right);top,bottom=min(top,bottom),max(top,bottom)
    row=(read(memory,BASE)+view*384)&MASK
    loX,loY,hiX,hiY=[truncate(read(memory,(row+at)&MASK)) for at in (44,36,48,40)]
    if not (top<hiY and loY<bottom and left<hiX and loX<right):return memory,read(memory,sp),False
    clamp=lambda value,low,high:low if value<low else high if high<value else value
    x0,y0,x1,y1=clamp(left,loX,hiX),clamp(top,loY,hiY),clamp(right,loX,hiX),clamp(bottom,loY,hiY)
    cursor=read(memory,sp);store(memory,sp,cursor+8)
    store(memory,cursor+4,((x0&1023)<<14)|((y0&1023)<<2))
    store(memory,cursor,0xF6000000|((x1&1023)<<14)|((y1&1023)<<2))
    return memory,read(memory,sp),True


def fixture(view=0,endpoints=0,bounds=0,alias=0,phase=0):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x200,0x200)}
    memory.update({BASE+i:0xA5 for i in range(-16,24)})
    memory.update({OUTPUT+i:(i*13+0xA5)&255 for i in range(-32,64)})
    row=(VIEWS+view*384)&MASK
    if alias==8:row=STACK+phase-44
    for i in range(-16,400):memory[(row+i)&MASK]=0xA5
    for at,value in zip((36,40,44,48),BOUNDS[bounds]):store(memory,row+at,bits(value))
    store(memory,BASE,row-view*384)
    cursor=(OUTPUT,BASE,row+36,STACK+phase,STACK+phase-4,STACK+phase+16,STACK+phase+20,0xFFFFFFF8,OUTPUT)[alias]&MASK
    for i in range(-16,24):memory.setdefault((cursor+i)&MASK,0xA5)
    return memory,tuple(v&MASK for v in (cursor,*ENDPOINTS[endpoints],view))


def corpus():
    for view,endpoints,bounds,phase in itertools.product((0,1,3,-1,0x10001,0x80000000),range(len(ENDPOINTS)),range(len(BOUNDS)),(0,8)):
        yield (*fixture(view,endpoints,bounds,phase=phase),phase)
    for alias,view,endpoints,phase in itertools.product(range(1,9),(0,1,3),(0,1,3,12),(0,8)):
        yield (*fixture(view,endpoints,0,alias,phase),phase)


class RectangleOracle(point.PointProjectionOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,connected=None):
        super().__init__(words,memory,args,[],phase,entry,connected)

    def execute(self,word):
        if word>>26==0 and word&63==3:
            self.r[word>>11&31]=(signed(self.r[word>>16&31])>>(word>>6&31))&MASK
        elif word>>26==17 and word>>21&31==16 and word&63==13:
            self.f[word>>6&31]=truncate(self.f[word>>11&31])&MASK
        else:super().execute(word)

    def record_call(self,target):
        if target!=source.ENTRY:raise ValueError('Unexpected rectangle call')
        args=self.arguments(6);self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):raise ValueError('Actual rectangle must execute')


def packet_reference(index,registers,fp,memory,phase):
    r=list(registers);memory=dict(memory);sp=STACK+phase
    half=lambda value:((value&65535)^32768)-32768
    if index==0:store(memory,sp+16,half(fp[10]))
    elif index==1:r[6]=half(truncate(fp[6]))&MASK
    elif index==2:store(memory,sp+16,r[15]);r[7]=half(fp[6])&MASK
    elif index==3:store(memory,sp+16,half(fp[4]))
    elif index==4:store(memory,sp+16,r[12]+r[16]);r[6]=(half(r[17])-r[16])&MASK
    elif index==5:r[7]=(half(r[20])+r[16])&MASK;r[5]=(half(r[10]>>16)-r[16])&MASK
    elif index==6:
        store(memory,sp+16,r[14]+r[16]);r[7]=(r[25]+r[16])&MASK;r[6]=(r[17]-r[16])&MASK;store(memory,sp+0xDC,r[15])
    elif 7<=index<=13:
        bottom,x1,x0,y0=((11,10,14,15),(15,11,13,12),(12,15,24,14),(14,12,25,13),
            (13,14,10,24),(24,13,11,25),(25,24,15,10))[index-7]
        store(memory,sp+16,r[bottom]);r[7]=(r[x1]+r[16])&MASK;r[5]=(r[x0]-r[16])&MASK;r[6]=(r[y0]-r[16])&MASK
        store(memory,sp+20,r[23])
    elif index==14:
        value=half(r[8]>>16);store(memory,sp+16,value);store(memory,sp+0x40,value);store(memory,sp+0xEC,r[2])
    elif index==15:
        r[6]=half(r[8])&MASK;store(memory,sp+0x3C,r[6]);store(memory,sp+0xE8,r[8])
    else:raise ValueError('Unknown original caller packet')
    return memory,tuple(r[4:8])+(read(memory,sp+16),read(memory,sp+20))
