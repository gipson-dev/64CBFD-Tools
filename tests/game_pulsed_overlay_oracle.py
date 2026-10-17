"""Inherited blend witnesses with actual retail pulse/wave/draw code."""
import math
from collections import Counter

from tools.experiments import game_pulsed_overlay_audit as source
from tools.tests import game_color_overlay_draw_oracle as draw
from tools.tests import game_shared_overlay_oracle as caller
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_viewport_initialize_oracle import ConversionBoundary
from tools.tests.test_game_record_constructor_match import elf_slot_offset

put,read,STACK=draw.put,draw.read,draw.STACK
TIMER,ANGLE,PALETTE,ALPHA,PULSE,TABLE=0x800DDE08,0x800DDD89,0x800DDD8A,0x800DDD8B,0x800DDD8C,0x8008D010
SHIFT,WAVE,DRAW=0x15048A40,0x150489B0,0x1517F08C
MASK=0xFFFFFFFF
SEEDS=(0,0x80000000,bits(0.25),bits(1.0),bits(-1.0),bits(2.0))


def fp(value):return floating(bits(value))


def sample(memory,angle):
    phase=(angle-64)&255
    index=64-(phase&63) if phase&64 else phase&63
    word=read(memory,0x8009A220+index*4)
    return floating(word^(0x80000000 if 64<phase<=192 else 0))


def fixture(elf,timer=1,alpha=127,pulse=0,angle=0,palette=0,seed=0,phase=0,caller_frame=False):
    memory,args=draw.fixture()
    for i in range(0xC0):memory.setdefault(0x800DDD80+i,0xA5)
    for i in range(256):
        values=((10,40,80,210,140,160),(255,0,127,1,255,128),(0,255,128,255,1,0))[i%3]
        for j,value in enumerate(values):put(memory,TABLE+i*6+j,value,1)
    at=elf_slot_offset(elf,0x8009A220,260)
    memory.update({0x8009A220+i:b for i,b in enumerate(elf[at:at+260])})
    for a,v,n in ((TIMER,timer,2),(ANGLE,angle,1),(PALETTE,palette,1),(ALPHA,alpha,1),(PULSE,pulse,1)):
        put(memory,a,v,n)
    put(memory,STACK+phase-0x10-(0x28 if caller_frame else 0),seed)
    return memory,(draw.OUTPUT,)


def reference(initial,cursor,phase=0,caller_frame=False,zero=False):
    memory=dict(initial);calls=[]
    if not read(memory,TIMER,2) or not read(memory,ALPHA,1):return memory,cursor,calls,None
    alpha=read(memory,ALPHA,1);blend=floating(read(memory,STACK+phase-0x10-(0x28 if caller_frame else 0)))
    if read(memory,PULSE,1):
        angle=read(memory,ANGLE,1);calls.extend(((SHIFT,(angle,)),(WAVE,((angle-64)&255,))))
        alpha=math.trunc(fp(float(read(memory,ALPHA,1))*fp(fp(sample(memory,angle)+1.0)*0.5)))
        blend=0.0
    if zero:blend=0.0
    colors=TABLE+read(memory,PALETTE,1)*6;rgb=[]
    for i in range(3):
        a,b=read(memory,colors+i,1),read(memory,colors+i+3,1)
        value=fp(fp(float(b-a)*blend)+float(a))
        if not math.isfinite(value) or not -0x80000000<=value<0x80000000:raise ConversionBoundary
        rgb.append(math.trunc(value)&MASK)
    packet=(cursor,alpha&MASK,*rgb,0);calls.append((DRAW,packet))
    # The leaf is frame-free, called with the wrapper's outgoing home area.
    memory,result,_,_=draw.reference(memory,packet,phase-0x30-(0x28 if caller_frame else 0))
    return memory,result,calls,packet


def helpers(images):
    result={}
    for key in ('pulse','shift','wave','draw'):
        entry=source.SPANS[key][0];result.update(zip(range(entry,entry+len(images[key])*4,4),images[key]))
    return result


class PulseOracle(draw.OverlayOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,connected=None):
        self.reads=[];self.written=set();self.read_provenance=[];self.draw_packets=[]
        super().__init__(words,memory,args,phase,3,entry,connected)

    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==7:
            return draw.AreaOracle.execute(self,word)
        return super().execute(word)

    def get(self,address,size):
        value=super().get(address,size)
        if getattr(self,'own_instruction',False):
            row=(self.current_pc,self.delay_of,address,size,value)
            self.reads.append(row)
            if self.current_pc==source.ENTRY+0x50:
                self.read_provenance.append((row,any(address+i in self.written for i in range(size))))
        return value

    def put(self,address,value,size):
        if getattr(self,'own_instruction',False) and getattr(self,'recording',False):
            self.written.update(range(address,address+size))
        return super().put(address,value,size)

    def record_call(self,target):
        counts={source.ENTRY:1,SHIFT:1,WAVE:1,DRAW:6}
        if target not in counts:raise ValueError('Unexpected pulse provider: '+hex(target))
        args=self.arguments(counts[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==DRAW:self.draw_packets.append(args)

    def hook(self,target):raise ValueError('Pulse/wave/draw bodies must execute')


class CallerOracle(PulseOracle):
    def __init__(self,words,memory,args,connected,phase=0,pattern=0):
        super().__init__(words,memory,args,phase,source.SPANS['caller'][0],connected)
        self.pattern,self.overlay_mode=pattern,0
        self.counts=Counter()

    def record_call(self,target):
        if target in (source.ENTRY,SHIFT,WAVE,DRAW):return super().record_call(target)
        return caller.OverlayOracle.record_call(self,target)

    def hook(self,target):
        if target in (source.ENTRY,SHIFT,WAVE,DRAW):return super().hook(target)
        return caller.OverlayOracle.hook(self,target)
