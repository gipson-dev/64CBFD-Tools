"""Frame callback protocol, live gates and page ages; not whole-game emulation."""
from collections import Counter
import re

from tools.experiments import game_frame_sequence as source
from tools.tests import test_game_view_matrix_prepare as prepare

matrix = prepare.model
put,read,signed = matrix.put,matrix.read,matrix.signed
TABLE,COUNT,DISABLED,FLAG,EXTERNAL,CC,PAGE,CONTEXT,RESET = (
    0x80043B40,0x80082FA0,0x800BEAC0,0x800D23A9,0x800BE616,0x800CC2B0,
    0x800BE9C0,0x800BE9F0,0x800DCD27)
PROTOTYPES = source.DECLARATIONS+'''
void func_10004250(void);
void func_15018DFC(void);
void func_1501C860(void);
void func_1511FC20(s32);
void func_15122AE0(void);
'''
SIGNATURES = {int(name[5:],16):(name,result,0 if args=='void' else len(args.split(',')))
    for result,name,args in re.findall(r'(void|s32) (func_[0-9A-F]+)\((void|s32(?:, s32)*)\);',PROTOTYPES)}


def fixture(count=3,pattern=0,disabled=0):
    memory = prepare.fixture(0,pattern%2,pattern)
    memory.update({TABLE+i:(i*13+0xA5)&255 for i in range(-16,0xFF0)})
    for i in range(508):
        put(memory,TABLE+i*8,0xD15A0000+i)
        put(memory,TABLE+i*8+4,(0,1,0x7FFFFFFF,0xFFFFFFFF,0x80000000)[(i+pattern)%5])
    put(memory,COUNT,count&0xFFFFFFFF)
    put(memory,CONTEXT,0x12345678)
    for address,value in ((DISABLED,disabled),(FLAG,(0,1,128,255)[pattern%4]),
            (EXTERNAL,(0,128,1,255)[pattern%4]),(CC,(0,1,128,255)[pattern%4]),(RESET,0xA5)):
        memory[address] = value
    return memory


def effects(memory,target,args,ordinal,mode):
    if mode==1 and target==0x15113E54:
        memory[DISABLED]=1
    elif mode==1 and target==0x15018DFC:
        memory[DISABLED]=0
    elif mode==2 and target==0x15177A94:
        memory[DISABLED]=1
    elif mode==3 and target==0x1510FC34 and args==(0,):
        put(memory,COUNT,3 if read(memory,COUNT)==0 else 0xFFFFFFFF)
    elif mode==3 and target==0x1510B690 and ordinal==2:
        put(memory,COUNT,1)
    elif mode==4 and target==0x151749F8:
        put(memory,CONTEXT,0x87654321)
    elif mode==4 and target==0x1501C860:
        memory[PAGE]=255
    elif mode==5 and target==0x15034F20:
        put(memory,TABLE+507*8+4,0x7FFFFFFF)
    elif mode==5 and target==0x1515D6C8:
        put(memory,TABLE+4,0xFFFFFFFF)
        put(memory,TABLE+253*8+4,0x80000000)
    elif mode==6 and target==0x15113180:
        memory[DISABLED]=0
    elif mode==6 and target==0x1501E2F8:
        memory[FLAG]=128
    elif mode==6 and target==0x1502BEE4:
        memory[EXTERNAL]=0
    elif mode==6 and target==0x15113C88:
        memory[CC]=1
    elif mode==7 and target==0x15094EA0 and ordinal==1:
        put(memory,COUNT,3 if read(memory,COUNT)==0 else 0xFFFFFFFF)
    elif mode==8 and target==0x15094EA0 and args==(255,):
        put(memory,COUNT,0)
    elif mode==8 and target==0x15094EA0 and args==(0,) and ordinal>=257:
        put(memory,COUNT,0xFFFFFFFF)
    else:
        return False
    return True


class CallBoundary(Exception):
    pass


def reference(memory,mode=0,phase=0,connected=False,limit=None):
    memory,calls,ordinals,actions = dict(memory),[],Counter(),[]
    def call(target,*args):
        nonlocal memory
        calls.append((target,args))
        if limit is not None and len(calls)==limit:
            raise CallBoundary
        ordinals[target]+=1
        if connected and target==0x15094EA0:
            memory,more=prepare.reference(memory,args[0],phase=phase-40)
            calls.extend(more)
        if target==0x10004250:
            assert memory[RESET]==0
        if effects(memory,target,args,ordinals[target],mode):
            actions.append((target,ordinals[target],mode))
    def batch(rows):
        for row in rows:
            call(*row)
    batch(((0x1510D864,),(0x1509BA04,0),(0x1509BBA0,2)))
    memory[RESET]=0
    batch(((0x10004250,),(0x1501E400,0),(0x15034F20,),(0x1510B690,),
        (0x1510F800,0),(0x15113180,)))
    if not memory[DISABLED]:call(0x15113E54,1)
    if not memory[DISABLED]:call(0x15114188)
    batch(((0x15044A28,),(0x15018DFC,),(0x150242F8,1,0),(0x1501EC38,0),
        (0x150242F8,0,0),(0x15020EC4,0),(0x1501E2F8,0)))
    if memory[FLAG]:call(0x15087CC0)
    batch(((0x15122AE0,),(0x1504ADD0,),(0x1510F800,0)))
    for target,mask in ((0x1510FC34,0xFFFFFFFF),(0x15094EA0,255)):
        if target==0x15094EA0:call(0x1510B690)
        index=0
        while signed(index)<=signed(read(memory,COUNT)):
            call(target,index)
            index=(index+1)&mask
            assert len(calls)<2048,'Reference requires a bounded prefix for this count'
    batch(((0x15112A80,0),(0x151749F8,read(memory,CONTEXT),0),(0x1501C860,)))
    call(0x1511FC20,memory[PAGE])
    call(0x15188B74,0)
    if not memory[DISABLED]:batch(((0x1516706C,),(0x151671E8,)))
    call(0x1502BEE4)
    if not memory[EXTERNAL]:call(0x150A0D8C)
    batch(((0x15113218,),(0x15188B74,1)))
    call(0x151738C4,read(memory,CONTEXT))
    batch(((0x1502C1A4,),(0x15113C88,)))
    if memory[CC]:call(0x150636F0)
    if not memory[DISABLED]:batch(((0x15183D28,),(0x151670C0,),(0x15177A94,)))
    if not memory[DISABLED]:call(0x151814FC)
    batch(((0x1517F75C,),(0x1517F7B4,),(0x15036148,),(0x1515D6C8,)))
    for index in range(508):
        at=TABLE+index*8+4
        put(memory,at,(read(memory,at)+1)&0xFFFFFFFF)
    return memory,calls,actions


class FrameOracle(prepare.PrepareOracle):
    def __init__(self,words,memory,mode=0,phase=0,fault=None,connected=None,
            entry=source.ENTRY,limit=None,target_limit=None):
        super().__init__(words,memory,phase=phase,fault=fault,connected=connected,entry=entry)
        self.frame_mode,self.ordinals,self.frame_actions = mode,Counter(),[]
        self.limit,self.target_limit,self.outer_index = limit,target_limit,0

    def record_call(self,target):
        if target in (matrix.CONVERT,matrix.MULTIPLY):
            return super().record_call(target)
        if target==source.ENTRY:
            args=()
        else:
            args=self.arguments(SIGNATURES[target][2])
        self.calls.append((target,args))
        self.events.append(('CALL',target,args))
        self.ordinals[target]+=1
        if self.limit==len(self.calls):raise CallBoundary
        if self.target_limit==(target,self.ordinals[target]):raise CallBoundary
        if target==0x15094EA0:
            self.outer_index,self.index,self.conversions=args[0],args[0],0

    def apply_effect(self,target,args):
        if target==0x10004250:assert self.memory[RESET]==0
        if effects(self.memory,target,args,self.ordinals[target],self.frame_mode):
            self.frame_actions.append((target,self.ordinals[target],self.frame_mode))

    def execute(self,word):
        super().execute(word)
        if self.current_pc==0x15094EA0+39*4:
            self.apply_effect(0x15094EA0,(self.outer_index,))

    def hook(self,target):
        assert target in SIGNATURES or target==source.ENTRY,hex(target)
        self.apply_effect(target,self.calls[-1][1])
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=1 if target==source.ENTRY else 0xAABB1234


def state(m):
    return prepare.state(m),m.frame_actions,m.ordinals


public=prepare.public
