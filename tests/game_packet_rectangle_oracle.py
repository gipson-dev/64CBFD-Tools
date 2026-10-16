"""Independent float32/word rectangle reference with bounded guest trap handling."""
from tools.tests import game_packet_visibility_oracle as visibility
from tools.tests.game_animation_timeline_oracle import signed
from tools.experiments import game_packet_rectangle as source

base=visibility.base
bits,floating,rounded,put,read=base.bits,base.floating,base.rounded,base.put,base.read
STACK,PACKET,DESCRIPTOR,OUTPUT=visibility.STACK,visibility.PACKET,visibility.DESCRIPTOR,base.OUTPUT
GLOBALS=tuple(0x800D2C70+i*4 for i in range(7))
COLORS=(0x800D2DA8,0x800D2DA9,0x800D2DAA)
TINT_LOCK,TIMESTEP=0x800D2DAB,0x800BE9A0


class ArithmeticTrap(Exception):
    def __init__(self,code):
        self.code=code


def word(value):
    return value&0xFFFFFFFF


def half(value):
    return ((value+32768)&65535)-32768


def trunc(value):
    return signed(base.edge.trunc(value))


def quotient(numerator,denominator):
    if not denominator:
        raise ArithmeticTrap(7)
    if numerator==-2**31 and denominator==-1:
        raise ArithmeticTrap(6)
    return (abs(numerator)//abs(denominator))*(-1 if (numerator<0)!=(denominator<0) else 1)


def fixture(values=(2.5,3.25,-4.75,-2.125,4096.,32.5,20.25),flip=0,tint=0,
        animation=0,frame=0,speed=1,timestep=1,offsets=(0,0,0),dimensions=(16,8),alias=0):
    memory,_=visibility.fixture(dimensions=dimensions)
    memory.update({DESCRIPTOR+i:0xA5 for i in range(64)})
    for i,value in enumerate(dimensions):
        put(memory,DESCRIPTOR+4+i*2,value,2)
    put(memory,DESCRIPTOR+10,animation,1)
    for a,v in zip(GLOBALS,values):
        put(memory,a,bits(v))
    for a,v in zip(COLORS,(17,128,254)):
        put(memory,a,v,1)
    put(memory,TINT_LOCK,tint,1)
    put(memory,TIMESTEP,timestep,1)
    for offset,value in ((10,171),(11,speed),(12,frame),(13,flip)):
        put(memory,PACKET+offset,value,1)
    out=(OUTPUT,DESCRIPTOR+4,PACKET+20)[alias]
    return memory,(out,PACKET,*[word(v) for v in offsets])


def correction(position,step,full_sign=False):
    if (signed(position) if full_sign else half(position))>=0:
        return 0
    product=(half(position)*half(step))>>7
    return max(product,0) if half(step)<0 else min(product,0)


def animation_result(old,delta,flags):
    if not flags:
        return old
    updated=(old+(-delta if flags&128 and old&128 else delta))&255
    if flags&128:
        if old&128:
            return updated if updated&128 else old&127
        return old|128 if updated>=((flags&127)*8) else updated
    limit=flags*8
    return (updated-limit)&255 if updated>=limit else updated


def reference(initial,args):
    memory=dict(initial)
    output,packet,s_offset,inset_t,width_adjust=args
    scale_x,scale_y,left,top,divisor=[floating(read(memory,a)) for a in GLOBALS[:5]]
    int_scale_x,int_scale_y=trunc(scale_x),trunc(scale_y)
    if inset_t:
        width=floating(read(memory,GLOBALS[5]))
        height=floating(read(memory,GLOBALS[6]))
        put(memory,GLOBALS[5],bits(rounded(width-base.edge.divide(rounded(scale_x+scale_x),divisor))))
        put(memory,GLOBALS[6],bits(rounded(height-base.edge.divide(rounded(scale_y+scale_y),divisor))))
        left=rounded(left+base.edge.divide(scale_x,divisor))
        top=rounded(top+base.edge.divide(scale_y,divisor))
    width,height=[floating(read(memory,a)) for a in GLOBALS[5:]]
    if width<2.:
        width=2.
    numerator=signed(word(trunc(divisor)<<10))
    try:
        step_s=quotient(numerator,int_scale_x)
        step_t=quotient(numerator,int_scale_y)
    except ArithmeticTrap as error:
        return memory,args[0],error.code
    x,y=trunc(left),trunc(top)
    if not read(memory,TINT_LOCK,1):
        put(memory,output,0xFA000100)
        color=(read(memory,COLORS[0],1)<<24)|(read(memory,COLORS[1],1)<<16)|(
            read(memory,COLORS[2],1)<<8)|read(memory,packet+10,1)
        put(memory,output+4,color)
        output+=8
    s=trunc(base.edge.divide(rounded(rounded(32.-rounded(rounded(left-rounded(float(x)))*32.))*divisor),rounded(float(int_scale_x))))
    s=word(s+s_offset+0x2000)
    flips=read(memory,packet+13,1)
    fractional_t=trunc(base.edge.divide(rounded(rounded(32.-rounded(rounded(top-rounded(float(y)))*32.))*divisor),rounded(float(int_scale_y))))
    t=word(fractional_t+inset_t+0x2000)
    if flips&1:
        step_s=(-step_s)&65535
        s=(read(memory,read(memory,packet+16)+4,2)+255)<<5
    if flips&2:
        step_t=(-step_t)&65535
        t=word(((read(memory,read(memory,packet+16)+6,2)+255)<<5)-fractional_t)
    qx,qy=word(x<<2),word(y<<2)
    adjusted_width=rounded(rounded(float(signed(width_adjust)))+width)
    right_size=trunc(rounded(adjusted_width-1.))
    bottom_size=trunc(rounded(height-1.))
    right=max(half(word((right_size+x)<<2)),0)
    bottom=max(half(word((bottom_size+y)<<2)),0)
    put(memory,output,0xE4000000|((right&4095)<<12)|(bottom&4095))
    put(memory,output+4,((max(half(qx),0)&4095)<<12)|(max(half(qy),0)&4095))
    put(memory,output+8,0xE1000000)
    put(memory,output+12,(((s-correction(qx,step_s))&65535)<<16)|((t-correction(qy,step_t,True))&65535))
    put(memory,output+16,0xF1000000)
    put(memory,output+20,((step_s&65535)<<16)|(step_t&65535))
    output+=24
    descriptor=read(memory,packet+16)
    flags=read(memory,descriptor+10,1)
    if flags:
        delta=read(memory,packet+11,1)*read(memory,TIMESTEP,1)
        old=read(memory,packet+12,1)
        if flags&128:
            if old&128:
                put(memory,packet+12,old-delta,1)
                now=read(memory,packet+12,1)
                if not now&128:
                    put(memory,packet+12,(now+delta)&127,1)
            else:
                put(memory,packet+12,old+delta,1)
                now=read(memory,packet+12,1)
                if now>=((read(memory,descriptor+10,1)&127)<<3):
                    put(memory,packet+12,(now-delta)|128,1)
        else:
            put(memory,packet+12,old+delta,1)
            now=read(memory,packet+12,1)
            limit=read(memory,descriptor+10,1)<<3
            if now>=limit:
                put(memory,packet+12,now-limit,1)
    return memory,output,None


class RectangleOracle(base.edge.EdgeOracle):
    def __init__(self,words,memory,args,**kwargs):
        super().__init__(words,memory,args,entry=kwargs.pop('entry',source.ENTRY),**kwargs)

    def execute(self,instruction):
        op,rs,rt,fn=instruction>>26,instruction>>21&31,instruction>>16&31,instruction&63
        if op==0 and fn==26 and (not self.r[rt] or self.r[rs]==0x80000000 and self.r[rt]==0xFFFFFFFF):
            # Only BREAK classification and public writes are qualified on these paths.
            self.lo=self.hi=0
        elif instruction in (0x0006000D,0x0007000D):
            raise ArithmeticTrap(6 if instruction==0x0006000D else 7)
        else:
            super().execute(instruction)
