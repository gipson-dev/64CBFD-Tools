"""Independent four-quadrant packet reference and bounded emitted MIPS execution."""
import itertools
import math

from tools.experiments import game_mirrored_texture_rectangles as source
from tools.tests import game_clipped_rectangle_oracle as previous
from tools.tests import game_color_overlay_draw_oracle as unsigned
from tools.tests.test_game_area_sampler_recovery import AreaOracle

put,read,STACK=previous.put,previous.read,previous.STACK
bits,floating,signed=previous.bits,previous.floating,previous.signed
MASK,BASE,VIEWS,PROJECTED,OUTPUT=0xFFFFFFFF,previous.BASE,previous.VIEWS,0x800DDDE8,previous.OUTPUT
CENTERS=((141.5,103.25,3.75,-5.5),(0.,-0.,0.,0.),(-40.25,-13.5,-7.75,5.),
    (9000.5,-9000.75,0.,0.),(-9000.5,9000.75,0.,0.),(math.nan,math.inf,-math.inf,math.nan))
SIZES=(1,2,3,32,255,0,-1,0x7FFFFFFF)
TEXTURES=(0,32,64,65535,0x200000,0x3FFFFF,0x400000,-1)
OFFSETS=((0.,0.),(3.25,-4.5),(-17.75,23.125),(0.75,-0.75))


def half(value):return ((value&65535)^32768)-32768
def add(x,y):return bits(floating(x)+floating(y))
def sub(x,y):return bits(floating(x)-floating(y))
def mul(x,y):return bits(floating(x)*floating(y))


def divide(x,y):
    a,b=floating(x),floating(y)
    return bits(a/b if b else math.nan if not a else math.copysign(math.inf,a*math.copysign(1.,b)))


def trunc(value):return previous.truncate(value)
def quarter(value):return (trunc(value)*4)&MASK
def phase(value):return trunc(mul(value,bits(32.)))&31


def correction(coordinate,step,vertical=False):
    if (signed(coordinate) if vertical else half(coordinate))>=0:return 0
    scaled=(half(coordinate)*half(step))>>7
    return max(scaled,0) if half(step)<0 else min(scaled,0)


def packet(xl,yl,xh,yh,s,t,dx,dy):
    low=lambda value:max(half(value),0)&4095
    return (0xE4000000|low(xh)<<12|low(yh),low(xl)<<12|low(yl),0xE1000000,
        ((s-correction(xl,dx))&65535)<<16|((t-correction(yl,dy,True))&65535),
        0xF1000000,(dx&65535)<<16|(dy&65535))


def reference(initial,args):
    cursor,size,texture,offX,offY,view=args;memory=dict(initial);size=signed(size);texture=signed(texture)
    row=(read(memory,BASE)+view*384)&MASK;projected=(PROJECTED+view*8)&MASK
    x=add(read(memory,row+12),read(memory,projected));y=add(read(memory,row+16),read(memory,projected+4))
    sizeWord=bits(float(size));px=add(x,offX);py=add(y,offY);nx=sub(x,offX);ny=sub(y,offY)
    farX=sub(nx,sizeWord);farY=sub(ny,sizeWord)
    step=unsigned.unsigned(mul(divide(bits(float(texture)),sizeWord),bits(1024.)))&65535
    shift=(texture*32)&MASK
    rectangles=((px,py,add(px,sizeWord),add(py,sizeWord),phase(px)+shift,phase(py)+shift,-step,-step),
        (farX,farY,nx,ny,31-phase(farX),31-phase(farY),step,step),
        (px,farY,add(px,sizeWord),ny,phase(px)+shift,31-phase(farY),-step,step),
        (farX,py,nx,add(py,sizeWord),31-phase(farX),phase(py)+shift,step,-step))
    words=[]
    for xl,yl,xh,yh,s,t,dx,dy in rectangles:words.extend(packet(*(quarter(v) for v in (xl,yl,xh,yh)),s,t,dx,dy))
    for i,value in enumerate(words):put(memory,(cursor+i*4)&MASK,value)
    return memory,(cursor+96)&MASK,words,step


def fixture(view=0,size=32,texture=64,center=0,offset=0,alias=0,phase=0):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x300,0x120)}
    memory.update({BASE+i:0xA5 for i in range(-16,24)})
    row=(VIEWS+view*384)&MASK;point=(PROJECTED+view*8)&MASK
    for start,length in ((row,384),(point-16,40),(OUTPUT-32,160)):
        for i in range(length):memory[(start+i)&MASK]=0xA5
    extentX,extentY,deltaX,deltaY=CENTERS[center]
    put(memory,BASE,VIEWS);put(memory,row+12,bits(extentX));put(memory,row+16,bits(extentY))
    put(memory,point,bits(deltaX));put(memory,point+4,bits(deltaY))
    cursor=(OUTPUT,BASE-16,row,point-8)[alias]&MASK
    for i in range(-16,112):memory.setdefault((cursor+i)&MASK,0xA5)
    args=(cursor,size&MASK,texture&MASK,*(bits(v) for v in OFFSETS[offset]),view&MASK)
    return memory,args


def cases():
    for view,size,texture,center,offset in itertools.product((0,1,3,-1,0x10001),SIZES,TEXTURES,range(len(CENTERS)),range(len(OFFSETS))):
        yield fixture(view,size,texture,center,offset)
    for alias,view,size,center in itertools.product(range(1,4),(0,1,3),(1,32,255),(0,2,3,4)):
        yield fixture(view,size,64,center,1,alias)


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x300<=a<STACK+0x120}


class MirroredOracle(previous.RectangleOracle):
    def __init__(self,words,memory,args,phase=0,fcsr=0,entry=source.ENTRY,connected=None):
        super().__init__(words,memory,args,phase,entry,connected);self.fcsr=self.initial_fcsr=fcsr
        self.conversions=[];self.store_sites=[]

    def put(self,address,value,size):
        super().put(address,value,size)
        if hasattr(self,'store_sites') and self.own_instruction:self.store_sites.append((self.current_pc,address,size,value))

    def execute(self,word):
        op,rs,fn=word>>26,word>>21&31,word&63
        if op==17 and (rs in (2,6) or rs==16 and fn==36):
            AreaOracle.execute(self,word)
            if rs==16:self.conversions.append((self.current_pc,self.fcsr))
        else:super().execute(word)

    def record_call(self,target):
        if target!=source.ENTRY:raise ValueError('Unexpected mirrored texture call')
        args=self.arguments(6);self.calls.append((target,args));self.events.append(('CALL',target,args))

    def run(self):
        result=super().run()
        assert self.fcsr==self.initial_fcsr,'Mirrored rectangle leaked conversion control state'
        return result
