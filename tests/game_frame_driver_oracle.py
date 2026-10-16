"""Ordered scheduler/display-list contract with bounded shutdown, not hardware emulation."""
from collections import Counter
import re

from tools.experiments import game_frame_driver as source
from tools.tests import game_frame_sequence_oracle as frame

put,read,signed=frame.put,frame.read,frame.signed
STACK=frame.matrix.machine.STACK
QUEUE,MESSAGE,CURSOR,BASES,MAP,INDEX,COUNT=(0x800BEA10,0x20000,0x800BE9D0,0x800BE9C8,
    0x800BE630,0x80082FA4,frame.COUNT)
STOP,RESET,PENDING,LIMIT,UCODE,PAGE,OLD,NEXT,HOLD=(0x800BE615,0x800BE614,0x800DC9F0,
    0x800BEBA4,0x800BEBA0,frame.PAGE,frame.DISABLED,0x800BEAC1,0x800BEAC2)
BUFFERS=(0x50000,0x58000)
SIZE=0x2000
RECV=0x10023440
POINTER_OUT=0xF0000001
PROTOTYPES=source.DECLARATIONS+'''
s32 func_1501A680(s32);
s32 func_15019130(void);
s32 func_1515D6D0(s32, s32);
s32 func_150195A0(s32, s32);
s32 func_150198FC(s32);
s32 func_15019CC8(s32, s32);
s32 func_151DCFD8(s32);
void func_10004074(s32);
void func_10004674(void);
void func_1000E2F4(s32);
void func_10011E94(s32);
void func_10001444(void);
void func_151E6BFC(void);
s32 func_1501BBB8(void);
'''
SIGNATURES=dict(frame.SIGNATURES)
for result,name,args in re.findall(r'(void|s32|Gfx \*)\s*(func_[0-9A-F]+)\(([^;{}]*)\);',PROTOTYPES):
    SIGNATURES[int(name[5:],16)]=(name,result,0 if args=='void' else len(args.split(',')))
SIGNATURES[RECV]=('osRecvMesg','s32',3)
CURSOR_CALLS={0x1501A680,0x15019464,0x1515D6D0,0x150195A0,0x150198FC,
    0x15019CC8,0x15019BB8,0x15019E60,0x151E84B0,0x15043384}
FIELDS=((COUNT,4),(CURSOR,4),(INDEX,4),(PAGE,1),(OLD,1),(NEXT,1),(HOLD,1),
    (STOP,1),(RESET,1),(0x800BE9B4,1),(0x800BEAA8,2),(PENDING,4),
    (BASES,4),(BASES+4,4),(UCODE,1),(0x800D9AF0,1),(0x800D9B18,1),
    (0x8002AC60,1),(0x8002AC64,2),(0x800BEB9C,4),(LIMIT,4))


def snapshot(memory):
    return tuple(read(memory,address) if size==4 else int.from_bytes(bytes(memory[address+i] for i in range(size)),'big')
        for address,size in FIELDS)


def fixture(message=1,count=1,pattern=0,disabled=0,stop=0):
    memory=frame.fixture(count,pattern,disabled)
    for address,size in ((QUEUE,32),(0x800BE600,0x630),(MAP-0x8000,4),(MESSAGE,4),
            (0x8002AC5C,12),(0x800BE728,4),(0x8002AC50,4),(0x800D18A0,6),(0x800BE5E0,1)):
        memory.update({address+i:(i*13+0xA5)&255 for i in range(size)})
    for base in BUFFERS:
        memory.update({base+i:0xA5 for i in range(-16,SIZE+16)})
    for i in range(256):memory[MAP+i]=(i+(0,1,128,255)[pattern%4])&255
    for page in (0,1,128,255):put(memory,BASES+page*4,BUFFERS[page&1])
    put(memory,CURSOR,BUFFERS[0]+32)
    put(memory,COUNT,count&0xFFFFFFFF)
    put(memory,INDEX,0x12345678)
    put(memory,LIMIT,(0,1,127,0xFFFFFFFF)[pattern%4])
    put(memory,PENDING,pattern&1)
    put(memory,0x800BEB9C,0x80401000)
    put(memory,0x800BE728,0x8002AC50)
    put(memory,frame.matrix.BASE,frame.matrix.VIEWS)
    put(memory,MESSAGE,message&65535,2)
    put(memory,0x800BEAA8,(0,1,0x8000,0xFFFF)[pattern%4],2)
    put(memory,0x8002AC64,0xA55A,2)
    for address,value in ((STOP,stop),(RESET,(0,1,128,255)[pattern%4]),(OLD,disabled),
        (NEXT,(0,1,128,255)[pattern%4]),(HOLD,(0,1,128,255)[pattern%4]),
        (PAGE,(0,1,128,255)[pattern%4]),(UCODE,pattern&1),(0x800D9AF0,pattern&1),
        (0x800D9B18,pattern>>1&1),(0x800BE9B4,0xA5),(0x8002AC60,0xA5)):
        memory[address]=value
    return memory


def returned(target,args,ordinal,pattern,mode):
    if target in CURSOR_CALLS:return (args[0]+8*(1+(target//4+pattern)%3))&0xFFFFFFFF
    if target==0x15019130:return int(mode!=3)
    if target==0x151F2CDC:return (0,1,0x80000000,0xFFFFFFFF)[pattern%4]
    if target==0x151DCFD8:return 0xFFFFFFFF if ordinal<=pattern%4 else 0
    return 0xAABB1234


def effects(memory,target,args,ordinal,mode):
    if mode==1 and target==0x151E51EC:memory[STOP]=1
    elif mode==2 and target==0x1501A39C:memory[RESET]=7
    elif mode==2 and target==0x1510B3B0:memory[0x800D9B18]=1
    elif mode==4 and target==0x15018F80 and ordinal==1:put(memory,INDEX,0x12348001)
    elif mode==4 and target==0x15019464 and ordinal==1:put(memory,COUNT,0xFFFFFFFF)
    elif mode==4 and target==0x15019414:put(memory,COUNT,1)
    elif mode==5 and target==0x1515D69C:put(memory,CURSOR,BUFFERS[1]+32)
    elif mode==5 and target==0x1515D6D0:put(memory,INDEX,0x12348001)
    elif mode==5 and target==0x150195A0 and ordinal==1:
        memory[PAGE]=1
        put(memory,LIMIT,0)
    elif mode==6 and target==0x15019CC8:
        memory[OLD]=0
        put(memory,COUNT,0)
    elif mode==6 and target==0x15019E60:
        memory[OLD]=0
        put(memory,COUNT,0)
    elif mode==6 and target==0x15019BB8:
        put(memory,COUNT,2 if ordinal==1 else 0xFFFFFFFF)
    elif mode==7 and target==0x1000E2F4:
        memory[OLD]=128
        memory[NEXT]=255
    elif mode==8 and target==0x1517E1AC:put(memory,PENDING,1)
    elif mode==8 and target==0x151412BC:
        put(memory,0x800BEAA8,1,2)
        memory[STOP]=1
    elif mode==9 and target==0x10004074 and ordinal==1:
        put(memory,BASES+4,BUFFERS[1]+144)
        put(memory,BASES,BUFFERS[0]+160)
    else:return False
    return True


def half(word):
    word&=65535
    return (word if word<32768 else word-65536)&0xFFFFFFFF


class HaltBoundary(Exception):pass
class CallBoundary(Exception):pass


def reference(memory,pattern=0,mode=0,phase=0,connected=False):
    memory,calls,observations,returns,actions=dict(memory),[],[],[],[]
    counts=Counter()
    def call(target,*args):
        nonlocal memory
        args=tuple(a&0xFFFFFFFF for a in args)
        calls.append((target,args))
        observations.append((target,snapshot(memory)))
        counts[target]+=1
        value=returned(target,args,counts[target],pattern,mode)
        returns.append(value)
        if target==RECV:put(memory,args[1],MESSAGE)
        if connected and target==0x15019130:
            memory,more,_=frame.reference(memory,phase=phase-104,connected=True)
            calls.extend(more)
        if effects(memory,target,args,counts[target],mode):actions.append((target,counts[target],mode))
        return value
    def emit(w0,w1,reverse=False):
        at=read(memory,CURSOR)
        put(memory,CURSOR,(at+8)&0xFFFFFFFF)
        pairs=((4,w1),(0,w0)) if reverse else ((0,w0),(4,w1))
        for offset,value in pairs:put(memory,at+offset,value)
    def view_loop(body):
        view=0
        while signed(view)<=signed(read(memory,COUNT)):
            body(signed(view))
            view=half(view+1)
            assert len(calls)<4096,'Require a bounded view-loop cut'
    call(RECV,QUEUE,STACK+phase-4,1)
    memory[0x8002AC60]=0
    put(memory,0x8002AC64,800,2)
    code=int.from_bytes(bytes(memory[MESSAGE+i] for i in range(2)),'big')
    if code==2:
        call(0x1517E1AC)
        if read(memory,PENDING):call(0x151412BC)
        counter=(int.from_bytes(bytes(memory[0x800BEAA8+i] for i in range(2)),'big')-1)&65535
        put(memory,0x800BEAA8,counter,2)
        if memory[STOP] and not counter:
            call(0x10004074,read(memory,BASES))
            call(0x10004074,read(memory,BASES+4))
            put(memory,BASES,0)
            return memory,calls,observations,returns,actions,0,False
    elif code==4:
        while call(0x151DCFD8,1):pass
        return memory,calls,observations,returns,actions,None,True
    elif code==1:
        if memory[STOP]:return memory,calls,observations,returns,actions,1,False
        call(0x151E51EC)
        if memory[STOP]:return memory,calls,observations,returns,actions,1,False
        if memory[RESET]:
            call(0x1501A39C)
            memory[RESET]=0
        if memory[0x800D9AF0]:call(0x1510B3B0)
        if memory[0x800D9B18]:call(0x1510B51C)
        call(0x1501905C)
        if not memory[OLD] and not call(0x15019130):return memory,calls,observations,returns,actions,1,False
        put(memory,CURSOR,call(0x1501A680,read(memory,CURSOR)))
        call(0x1515D69C)
        call(0x15167310)
        def first(view):
            put(memory,INDEX,memory[MAP+view])
            call(0x15018F80,half(read(memory,INDEX)))
            put(memory,CURSOR,call(0x15019464,read(memory,CURSOR),half(read(memory,INDEX))))
        view_loop(first)
        if not memory[UCODE]:
            emit(0xE1000000,read(memory,0x800BEB9C))
            emit(0xDD0007FF,0x800C1060,True)
            emit(0xD9C2F9FA,0,True)
            emit(0xD9FFFFFF,0x220005)
            emit(0xDA380003,0x80089470)
            emit(0xDC08000A,0x800D9B90+memory[PAGE]*32)
            emit(0xDC08060A,0x800D9B90+memory[PAGE]*32+16)
        def second(view):
            saved=read(memory,CURSOR)
            put(memory,INDEX,memory[MAP+view])
            put(memory,CURSOR,call(0x1515D6D0,read(memory,CURSOR),read(memory,INDEX)))
            put(memory,CURSOR,call(0x150195A0,read(memory,CURSOR),half(read(memory,INDEX))))
            used=signed((read(memory,CURSOR)-read(memory,BASES+memory[PAGE]*4))&0xFFFFFFFF)>>3
            if used>signed(read(memory,LIMIT)):put(memory,CURSOR,saved)
        view_loop(second)
        put(memory,INDEX,0)
        call(0x15019414)
        put(memory,CURSOR,call(0x150198FC,read(memory,CURSOR)))
        def third(view):
            put(memory,INDEX,memory[MAP+view])
            put(memory,CURSOR,call(0x1515D6D0,read(memory,CURSOR),read(memory,INDEX)))
            put(memory,CURSOR,call(0x15019CC8,read(memory,CURSOR),read(memory,INDEX)))
            if not memory[OLD] and signed(read(memory,COUNT))>0:
                put(memory,CURSOR,call(0x15019BB8,read(memory,CURSOR),read(memory,INDEX)))
        view_loop(third)
        put(memory,CURSOR,call(0x15019E60,read(memory,CURSOR)))
        if not memory[OLD] and not read(memory,COUNT):
            def single(view):
                put(memory,INDEX,memory[MAP+view])
                put(memory,CURSOR,call(0x15019BB8,read(memory,CURSOR),read(memory,INDEX)))
            view_loop(single)
        for target in (0x151E84B0,0x15043384):put(memory,CURSOR,call(target,read(memory,CURSOR)))
        for target,args in ((0x150347E8,()),(0x1502E474,()),(0x15189118,(0,)),(0x15084A18,()),(0x15125628,())):call(target,*args)
        emit(0xE9000000,0,True)
        emit(0xDF000000,0,True)
        for target in (0x10004674,0x1510D404,0x15114A1C,0x1517CFC4):call(target)
        call(0x1501C880,0,1)
        memory[0x800BE9B4]=0
        if memory[OLD]:memory[HOLD]=2
        elif memory[HOLD]:memory[HOLD]-=1
        if memory[NEXT]!=memory[OLD]:
            memory[OLD]=memory[NEXT]
            if memory[OLD]:
                call(0x1000E2F4,1);call(0x10011E94,1)
                if call(0x151F2CDC):call(0x151F2BE8)
            else:
                call(0x1000E2F4,0);call(0x10011E94,0)
                if call(0x151F2CDC):call(0x151F2C4C)
    return memory,calls,observations,returns,actions,1,False


class DriverCode(frame.prepare.faults.TrackedCode):
    def __getitem__(self,pc):
        word=super().__getitem__(pc)
        if pc==self.owner.halt and word==0x1000FFFF:raise HaltBoundary
        return word


class DriverOracle(frame.FrameOracle):
    def __init__(self,words,memory,pattern=0,mode=0,phase=0,fault=None,connected=None,
            entry=source.ENTRY,target_limit=None):
        super().__init__(words,memory,phase=phase,fault=fault,connected=connected,entry=entry)
        self.pattern,self.driver_mode=pattern,mode
        self.driver_counts,self.observations,self.driver_actions=Counter(),[],[]
        self.target_boundary=target_limit
        self.halt=source.ENTRY+(0x640 if len(words)==411 else 0x644)
        self.code=DriverCode(self.code,self)

    def record_call(self,target):
        if target in (frame.matrix.CONVERT,frame.matrix.MULTIPLY):return super().record_call(target)
        args=self.arguments(SIGNATURES[target][2])
        self.calls.append((target,args));self.events.append(('CALL',target,args))
        self.observations.append((target,snapshot(self.memory)))
        self.driver_counts[target]+=1
        if self.target_boundary==(target,self.driver_counts[target]):raise CallBoundary
        if target==0x15094EA0:self.outer_index,self.index,self.conversions=args[0],args[0],0

    def hook(self,target):
        args=self.calls[-1][1]
        if target==RECV:
            assert args==(QUEUE,STACK+self.phase-4,1)
            assert self.get(args[1],4)==0
            self.put(args[1],MESSAGE,4)
        value=returned(target,args,self.driver_counts[target],self.pattern,self.driver_mode)
        if effects(self.memory,target,args,self.driver_counts[target],self.driver_mode):
            self.driver_actions.append((target,self.driver_counts[target],self.driver_mode))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=value


def state(m):
    return frame.state(m),m.observations,m.driver_counts,m.driver_actions


public=frame.public
