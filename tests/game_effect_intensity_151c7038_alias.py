"""Check owner/effect overlap and helper mutations in guest memory."""
import itertools
from tools.tests import game_effect_intensity_151c7038_oracle as d

class Alias(d.Machine):
    def __init__(self,ws,c,mem,ep):self.ep=ep;super().__init__(ws,c,mem)
    def record_call(self,target):
        assert target==d.HELPER
        args=tuple(self.arguments(1));assert args==(self.ep,);self.calls.append((target,args))
    def hook(self,target):
        assert target==d.HELPER
        c=self.case
        if c.mutation&1:
            d.put(self.memory,self.ep+0x4c,0x40000000);d.put(self.memory,self.ep+0x84,0x1234,2)
        if c.mutation&2:
            d.put(self.memory,d.OWNER+0x60,0x80705030);d.put(self.memory,d.OWNER+0x7c,d.ALT)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=c.answer

def run(state):
    bodies=[d.words(state[x]) for x in ('after','retail','generated')];count=0
    for delta,kind,value,answer,mutation in itertools.product((0,0x30,-0x4c,0x14),(0xe9,0xe8),
            (0,0x3f800000,0xbf800000,0x7fc12345),(0,1),(0,1,2,3)):
        ep=d.OWNER+delta;c=d.Case(0,kind,value,0x12345678,answer,mutation,0)
        mem={d.STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
        mem.update({d.OWNER+i:(i*29+0x59)&255 for i in range(-256,1024)})
        mem.update({d.ALT+i:(i*7+3)&255 for i in range(256)})
        d.put(mem,ep+0x4c,value);d.put(mem,ep+0x84,kind,2)
        d.put(mem,d.OWNER+0x60,c.flag);d.put(mem,d.OWNER+0x7c,ep)
        machines=[Alias(ws,c,mem.copy(),ep).run() for ws in bodies]
        results=[(d.public(m.memory),m.calls,m.r[2],m.fcsr,d.external_trace(m)) for m in machines]
        assert results[0]==results[1]==results[2],(delta,c);count+=1
    return {'cases':count,'overlap_offsets':[0,0x30,-0x4c,0x14]}
