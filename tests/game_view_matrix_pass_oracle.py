"""Ordered fixed decode/product/frustum contracts and actual helper connections."""
import itertools

from tools.experiments import game_view_matrix_pass as source
from tools.tests import game_view_projection_family_oracle as family
from tools.tests import test_game_view_frustum_planes as planes
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating,signed

CONVERT,MULTIPLY,FRUSTUM=0x151EFEB8,source.MULTIPLY_ENTRY,0x1501B22C
BASE,PAGE,COUNT,TABLE=0x800BE628,0x800BE9C0,0x80082FA0,0x800DC2A0
CONVERTED,PRODUCTS=0x800D9C10,0x800D9D10
VIEWS,ALTERNATE,FIXED,OTHER=0x24000,0x34000,0x44000,0x45000
PAGES=(0,1,128,255)
BANKS=((VIEWS,0x900),(ALTERNATE,0x900),(FIXED,0x100),(OTHER,0x100),
    (CONVERTED-32,0x240),(planes.SCALE_H-16,0x30))
TEMP_TOKEN=0xF0000000


def packed(pattern):
    if pattern%4==0:
        values=[0x10000 if i in (0,5,10,15) else 0 for i in range(16)]
    elif pattern%4==1:
        values=[((i*3+pattern)%17-8)*0x4000&0xFFFFFFFF for i in range(16)]
    elif pattern%4==2:
        values=[((i*7+pattern)%23-11)*0x8000&0xFFFFFFFF for i in range(16)]
    else:
        values=[(0x80000000,0x7FFF0000,0xFFFF8000,0x18000,0,0xFFFF0000,0x8001,0x12345678)[i%8] for i in range(16)]
    return [values[i*2]&0xFFFF0000|values[i*2+1]>>16 for i in range(8)]+[
        (values[i*2]<<16&0xFFFF0000)|(values[i*2+1]&65535) for i in range(8)]


def fixture(count=3,page=0,pattern=0,alias=0):
    memory={machine.STACK+i:(i*17+0xA5)&255 for i in range(-0x800,0x180)}
    for base,size in (*BANKS,(BASE,4),(PAGE-8,24),(COUNT-8,24),(TABLE-16,0x420)):
        memory.update({base+i:(i*13+0xA5)&255 for i in range(size)})
    for bank in (VIEWS,ALTERNATE):
        for index in range(4):
            put(memory,bank+index*0x180+0x74,bits(60+index*3))
            put(memory,bank+index*0x180+0x78,bits(45+index*5))
            for p in PAGES:
                at=bank+index*0x180+p*64+0x100
                for i,word in enumerate(packed(pattern+index+p+(4 if bank==ALTERNATE else 0))):
                    put(memory,at+i*4,word)
    for bank in (FIXED,OTHER):
        for index in range(4):
            for i,word in enumerate(packed(pattern+index+(1 if bank==FIXED else 3))):
                put(memory,bank+index*64+i*4,word)
    for p in range(256):
        put(memory,TABLE+p*4,0)
    for p in PAGES:
        put(memory,TABLE+p*4,(FIXED if p in (0,128) else OTHER) if not alias else CONVERTED if alias==1 else PRODUCTS)
    put(memory,BASE,VIEWS)
    put(memory,COUNT,count&0xFFFFFFFF)
    memory[PAGE]=page
    put(memory,planes.SCALE_H,0x3C8EFA35)
    put(memory,planes.SCALE_V,0x3C8EFA35)
    return memory


def decode(memory,destination,pointer):
    for pair in range(8):
        integer,fraction=read(memory,pointer+pair*4),read(memory,pointer+32+pair*4)
        first=integer&0xFFFF0000|fraction>>16
        second=integer<<16&0xFFFF0000|fraction&65535
        for i,value in enumerate((first,second)):
            put(memory,destination+pair*8+i*4,bits(floating(bits(float(signed(value))))/65536.0))


def multiply(memory,left,right,destination):
    cached=[read(memory,right+i*4) for i in range(16)]
    fp=family.parent.fp
    for row in range(4):
        values=[read(memory,left+row*16+i*4) for i in range(4)]
        for column in range(4):
            value=fp(values[0],cached[column],'mul')
            for k in range(1,4):
                value=fp(value,fp(values[k],cached[k*4+column],'mul'),'add')
            put(memory,destination+row*16+column*4,value)


def effects(memory,target,index,ordinal,mode,projection):
    if mode==1 and target==CONVERT and ordinal%2==1:
        memory[PAGE]=1 if memory[PAGE]==0 else 0
        put(memory,BASE,ALTERNATE)
        put(memory,TABLE+memory[PAGE]*4,OTHER)
    elif mode==2 and target==CONVERT and ordinal%2==0:
        put(memory,projection,bits(7))
        put(memory,CONVERTED+index*64+4,bits(9))
        put(memory,COUNT,0xFFFFFFFF)
    elif mode==3 and target==MULTIPLY:
        put(memory,BASE,ALTERNATE)
        put(memory,COUNT,3)
        put(memory,TABLE+memory[PAGE]*4,FIXED)
    elif mode==4 and target==FRUSTUM:
        put(memory,COUNT,0xFFFFFFFF)
        memory[PAGE]=255


def reference(memory,mode=0,phase=0,seed=0,connected=False):
    memory,calls=dict(memory),[]
    projection=machine.STACK+phase-0x44
    index,ordinal=0,0
    while index<=signed(read(memory,COUNT)):
        assert index<4,'Outside bounded matrix-pass domain'
        first=(projection,read(memory,BASE)+index*0x180+memory[PAGE]*64+0x100)
        calls.append((CONVERT,first))
        decode(memory,*first)
        ordinal+=1
        effects(memory,CONVERT,index,ordinal,mode,projection)
        second=(CONVERTED+index*64,read(memory,TABLE+memory[PAGE]*4)+index*64)
        calls.append((CONVERT,second))
        decode(memory,*second)
        ordinal+=1
        effects(memory,CONVERT,index,ordinal,mode,projection)
        product=(CONVERTED+index*64,projection,PRODUCTS+index*64)
        calls.append((MULTIPLY,product))
        multiply(memory,*product)
        effects(memory,MULTIPLY,index,ordinal,mode,projection)
        calls.append((FRUSTUM,(index,)))
        view=read(memory,BASE)+index*0x180
        memory,trig=planes.reference(memory,view,seed+index,0)
        if connected:
            calls.extend((target,(word,)) for target,word in trig)
        effects(memory,FRUSTUM,index,ordinal,mode,projection)
        index+=1
    return memory,calls


def cases():
    for count,page,pattern,mode in itertools.product((-0x80000000,-1,0,1,3),PAGES,range(4),range(5)):
        yield dict(memory=fixture(count,page,pattern),mode=mode,seed=pattern)
    for alias,page,mode in itertools.product((1,2),(0,1),(0,1,2,3,4)):
        yield dict(memory=fixture(3,page,2,alias),mode=mode,seed=2)


def canonical_calls(calls):
    projection=next((args[0] for target,args in calls if target==CONVERT),None)
    private=projection is not None and machine.STACK-0x700<=projection<machine.STACK+0x180
    return [(target,tuple(TEMP_TOKEN if private and value==projection else value for value in args)) for target,args in calls]


class ProtocolMismatch(Exception):
    pass


class MatrixPassOracle(family.FamilyOracle):
    def __init__(self,words,memory,mode=0,phase=0,seed=0,fault=None,connected=None,entry=source.ENTRY,arguments=None,expected_calls=None):
        super().__init__(words,memory,arguments or (0,),root=entry,phase=phase,connected=connected)
        self.matrix_mode,self.seed,self.phase=mode,seed,phase
        self.current_pc,self.delay_of=entry,None
        self.code=faults.TrackedCode(self.code,self)
        self.root_fault,self.root_accesses=fault,0
        self.execution_entry,self.root_size=entry,len(words)*4
        self.conversions,self.iteration,self.trig_ordinal,self.projection=0,0,0,machine.STACK+phase-0x44
        self.expected_calls=expected_calls
        self.connected_helpers=set(connected or {})&{CONVERT,MULTIPLY,FRUSTUM}
        self.return_mutations=[]

    def execute(self,word):
        super().execute(word)
        for target,last in ((CONVERT,44),(MULTIPLY,75),(FRUSTUM,58)):
            if target in self.connected_helpers and self.current_pc==target+last*4:
                self.return_mutations.append((target,self.current_pc,self.iteration))
                effects(self.memory,target,self.iteration,self.conversions,self.matrix_mode,self.projection)

    def access(self):
        if self.own_instruction and self.execution_entry<=self.current_pc<self.execution_entry+self.root_size:
            if self.root_accesses==self.root_fault:
                raise faults.AccessBoundary
            self.root_accesses+=1

    def record_call(self,target):
        if target in (planes.COS,planes.SIN):
            args=(self.f[12],)
        else:
            assert target in (CONVERT,MULTIPLY,FRUSTUM),hex(target)
            args=self.arguments(2 if target==CONVERT else 3 if target==MULTIPLY else 1)
        self.calls.append((target,args))
        self.events.append(('CALL',target,args))
        if self.expected_calls is not None:
            actual=canonical_calls(self.calls)
            if actual!=self.expected_calls[:len(actual)] or len(actual)>len(self.expected_calls):
                raise ProtocolMismatch((target,args))
        if target==CONVERT:
            self.conversions+=1
            self.iteration=(self.conversions-1)//2
            if self.conversions%2:
                self.projection=args[0]
        elif target==FRUSTUM:
            self.iteration=args[0]
            self.trig_ordinal=0

    def hook(self,target):
        args=self.calls[-1][1]
        if target==CONVERT:
            decode(self.memory,*args)
        elif target==MULTIPLY:
            multiply(self.memory,*args)
        elif target==FRUSTUM:
            view=read(self.memory,BASE)+self.iteration*0x180
            updated,_=planes.reference(self.memory,view,self.seed+self.iteration,0)
            self.memory.clear()
            self.memory.update(updated)
        else:
            assert target in (planes.COS,planes.SIN)
            self.trig_ordinal+=1
        if target in (CONVERT,MULTIPLY,FRUSTUM):
            effects(self.memory,target,self.iteration,self.conversions,self.matrix_mode,self.projection)
        for i in range(4):
            self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=0xAABB1234
        if target in (planes.COS,planes.SIN):
            self.f[0]=planes.returned(self.seed+self.iteration,self.trig_ordinal)
