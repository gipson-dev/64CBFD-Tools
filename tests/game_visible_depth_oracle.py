"""Bounded projection/provider reference; not a complete VR4300 FCSR model."""
import math

from tools.experiments import game_visible_depth_packet as source
from tools.tests import game_projected_packet_oracle as previous

STACK, put, read = previous.STACK, previous.put, previous.read
bits, floating, rounded = previous.bits, previous.floating, previous.rounded
STATUS = 0x31000


def unsigned(value):
    if not math.isfinite(value) or value >= 2**32 or value <= -1:
        return 0xFFFFFFFF
    return math.trunc(value) & 0xFFFFFFFF


def fixture(coordinates=(-32768,0,32767),transformed=(17.25,-91.5,100.,2.),visible=0x12345678,alias=0):
    memory,args,transformed=previous.fixture(coordinates,transformed,alias=alias==1)
    memory.update({STATUS+i:0xA5 for i in range(16)})
    status=args[0]+4 if alias==2 else STATUS
    put(memory,status,visible)
    put(memory,source.SCALE,bits(16352.))
    return memory,(*args,status),transformed


def effects(memory,outputs,packet,status,decision,mode):
    if decision is not None:
        put(memory,status,decision)
    if mode==1:
        put(memory,source.SCALE,bits(32704.))
    elif mode==2:
        put(memory,outputs[2],bits(4.25))
        put(memory,packet,0x12345678)


def reference(initial,args,transformed,phase=0,decision=1,mode=0):
    private=STACK+phase-0x48
    outputs=tuple(private+i for i in (0x44,0x40,0x3C,0x38))
    memory,active=previous.project_reference(initial,outputs,transformed)
    calls=[('matrix',previous.MATRIX+read(initial,previous.source.FRAME_INDEX)*64,
        *[bits(float(previous.half(read(initial,args[1]+i*2,2)))) for i in range(3)],*outputs)]
    if not active:
        put(memory,args[2],0)
        return memory,args[0],calls
    calls.append(('provider',args[1],read(memory,outputs[0]),read(memory,outputs[1]),
        read(memory,outputs[3]),1,args[2]))
    effects(memory,outputs,args[1],args[2],decision,mode)
    if not read(memory,args[2]):
        return memory,args[0],calls
    scale=floating(read(memory,source.SCALE))
    put(memory,args[0],0xE7000000)
    put(memory,args[0]+4,0)
    put(memory,args[0]+8,0xEE000000)
    value=rounded(rounded(rounded(floating(read(memory,outputs[2]))/floating(read(memory,outputs[3])))*scale)+scale)
    put(memory,args[0]+12,unsigned(value)<<16)
    return memory,args[0]+16,calls


class VisibleDepthOracle(previous.ProjectionOracle):
    def __init__(self,words,memory,args,transformed,decision=1,provider_result=0,**kwargs):
        self.decision,self.provider_result,self.outputs=decision,provider_result,None
        super().__init__(words,memory,args,transformed,entry=kwargs.pop('entry',source.ENTRY),**kwargs)

    def record_call(self,target):
        target=self.bindings.get(target,target)
        if target==source.PROVIDER:
            self.calls.append(('provider',*self.arguments(6)))
        else:
            if target==previous.MATRIX_CALL:
                self.outputs=self.arguments(8)[4:]
            super().record_call(target)

    def hook(self,target):
        target=self.bindings.get(target,target)
        if target!=source.PROVIDER:
            # The matrix provider itself is unmodified in this fixture.
            mode,self.mode=self.mode,0
            super().hook(target)
            self.mode=mode
            return
        args=self.arguments(6)
        effects(self.memory,self.outputs,args[0],args[5],self.decision,self.mode)
        for r in (*range(1,16),24,25):
            self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=self.provider_result
