"""Bounded clip commands, live tables, callbacks and actual matrix child."""
import itertools

from tools.experiments import game_view_clipping_commands as source
from tools.tests import game_view_projection_family_oracle as family
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_animation_timeline_oracle import bits,signed
from tools.tests.test_game_point_transform_match import put,read

COMMAND,QUEUE = source.TARGETS[0][1],source.TARGETS[1][1]
CHILD,BASE = family.CHILD,family.BASE
VIEWS,ALTERNATE = family.VIEWS,family.ALTERNATE
COUNT,ROWS,DIRTY = 0x80082FA0,0x800D9AF8,0x800D9B18
NEAR,FAR = 0x800D9B20,0x800D9B1C
BANKS = ((VIEWS,0x900),(ALTERNATE,0x900),(0x800D9A40,0x200),(COUNT-8,0x20))
FLOATS = (0,0x80000000,bits(2),bits(-1),0x7F800000,0xFF800000,0x7FC12345,0x7F810000,1,0x80000001)
COUNTS = (-0x80000000,-1,0,1,3,5)


def fixture(count=3,pattern=0,skip=0,alias=False):
    memory={machine.STACK+i:(i*17+0xA5)&255 for i in range(-0x600,0x180)}
    for base,size in (*BANKS,(BASE,4)):
        memory.update({base+i:(i*13+0xA5)&255 for i in range(size)})
    for bank in (VIEWS,ALTERNATE):
        for index in range(6):
            for offset,word in ((0x74,FLOATS[(pattern+index)%10]),(0x78,FLOATS[(pattern+index+3)%10]),(0x84,FLOATS[(pattern+index+6)%10])):
                put(memory,bank+index*0x180+offset,word)
    for index in range(6):
        put(memory,ROWS+index*8,bits(-1) if skip>>index&1 else FLOATS[(pattern+index)%10])
        put(memory,ROWS+index*8+4,FLOATS[(pattern+index+4)%10])
    put(memory,NEAR,FLOATS[(pattern+2)%10])
    put(memory,FAR,FLOATS[(pattern+5)%10])
    put(memory,COUNT,count&0xFFFFFFFF)
    put(memory,BASE,ROWS-0x74 if alias else VIEWS)
    memory[family.PAGE]=0
    memory[DIRTY]=0xA5
    return memory


def packet(memory,index,near,far):
    row=(read(memory,BASE)+index*0x180)&0xFFFFFFFF
    return (index,(row+0xB8)&0xFFFFFFFF,read(memory,row+0x78),read(memory,row+0x74),
        near,far,read(memory,row+0x84))


def effects(memory,args,mode,ordinal,root,phase=0):
    index=args[0]
    if mode==1:
        put(memory,COUNT,0xFFFFFFFF)
        put(memory,BASE,ALTERNATE)
        put(memory,NEAR,bits(7))
        put(memory,FAR,bits(11))
    elif mode==2:
        put(memory,BASE,ALTERNATE)
        if index<5:
            put(memory,ROWS+(index+1)*8,bits(0.5))
            put(memory,ROWS+(index+1)*8+4,0x7FCAB123)
    elif mode==3:
        put(memory,ROWS+index*8,bits(9))
        put(memory,ROWS+index*8+4,bits(-11))
        memory[DIRTY]=0xFE
    elif mode==4:
        if root==COMMAND:
            for i,value in enumerate((3,bits(7),bits(11))):
                put(memory,machine.STACK+phase+i*4,value)
        elif ordinal==1:
            put(memory,COUNT,5)
            put(memory,BASE,ALTERNATE)


def reference(memory,args=(),root=COMMAND,mode=0,phase=0,connected=False):
    memory,calls=dict(memory),[]
    def call(parameters):
        calls.append((CHILD,parameters))
        if connected:
            updated,child=family.child_reference(memory,parameters)
            memory.clear()
            memory.update(updated)
            calls.extend(child)
        ordinal=sum(target==CHILD for target,_ in calls)
        effects(memory,parameters,mode,ordinal,root,phase)
    if root==COMMAND:
        index,near,far=args
        near=read(memory,NEAR) if near&0x7FFFFFFF==0 else near
        far=read(memory,FAR) if far&0x7FFFFFFF==0 else far
        for i,value in enumerate((index,near,far)):
            put(memory,machine.STACK+phase+i*4,value)
        call(packet(memory,index,near,far))
        index,near,far=(read(memory,machine.STACK+phase+i*4) for i in range(3))
        put(memory,ROWS+index*8,near)
        put(memory,ROWS+index*8+4,far)
        memory[DIRTY]=1
    else:
        index,count=0,signed(read(memory,COUNT))
        while index<=count:
            assert index<6,'Outside bounded clip-row domain'
            row=ROWS+index*8
            near=read(memory,row)
            if near!=bits(-1):
                far=read(memory,row+4)
                call(packet(memory,index,near,far))
                put(memory,row,bits(-1))
                count=signed(read(memory,COUNT))
            index+=1
        memory[DIRTY]=0
    return memory,calls


def command_cases():
    for index,near,far,mode in itertools.product((0,1,3),FLOATS,FLOATS,range(5)):
        yield dict(memory=fixture(pattern=(index+mode)%10),args=(index,near,far),root=COMMAND,mode=mode)
    for pattern,near,far in itertools.product(range(10),(0,bits(2)),(0,0x80000000)):
        yield dict(memory=fixture(pattern=pattern,alias=True),args=(0,near,far),root=COMMAND,mode=0)


def queue_cases():
    for count,pattern,skip,mode in itertools.product(COUNTS,range(10),(0,0x15,0x3F),range(5)):
        yield dict(memory=fixture(count,pattern,skip),args=(),root=QUEUE,mode=mode)


class ClippingOracle(family.FamilyOracle):
    def __init__(self,words,memory,args=(),root=COMMAND,mode=0,phase=0,fault=None,connected=None,entry=None):
        super().__init__(words,memory,args or (0,),root=entry or root,phase=phase,connected=connected)
        self.root,self.clip_mode,self.phase=root,mode,phase
        self.execution_entry,self.root_size=entry or root,len(words)*4
        self.root_fault,self.root_accesses=fault,0
        self.code=faults.TrackedCode(self.code,self)
        self.current_pc,self.delay_of=self.execution_entry,None

    def access(self):
        if self.own_instruction and self.execution_entry<=self.current_pc<self.execution_entry+self.root_size:
            if self.root_accesses==self.root_fault:
                raise faults.AccessBoundary
            self.root_accesses+=1

    def record_call(self,target):
        assert target in (CHILD,family.PERSPECTIVE,family.FIXED),hex(target)
        parameters=self.arguments(2 if target==family.FIXED else 7)
        self.calls.append((target,parameters))
        self.events.append(('CALL',target,parameters))

    def hook(self,target):
        if target!=CHILD:
            super().hook(target)
        if target in (CHILD,family.FIXED):
            arguments=[args for entry,args in self.calls if entry==CHILD]
            effects(self.memory,arguments[-1],self.clip_mode,len(arguments),self.root,self.phase)
        if target==CHILD:
            for i in range(4):
                self.put(self.r[29]+i*4,0xB5000000+i,4)
            for register in (1,2,3,*range(4,16),24,25):
                self.r[register]=0xA5000000+register
            self.f[:20]=[0xA5000000+i for i in range(20)]
            self.r[2]=0xAABB1234
