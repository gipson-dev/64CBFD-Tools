"""Bounded overlay/capture contracts over the existing guest instruction engine."""
from collections import Counter

from tools.experiments import game_shared_overlay_pass as source
from tools.tests import game_view_render_pass_oracle as previous
from tools.tests import game_view_projection_family_oracle as signed_byte
from tools.tests.game_animation_timeline_oracle import bits,floating,signed

put,read,STACK,CURSOR=previous.put,previous.read,previous.STACK,previous.CURSOR
MODE,COUNT,INDEX,BASE,DISABLED,NEXT,PHASE,WIDTH,HEIGHT,BUFFER,PAGE,WORLD,TABLE=(
    0x800BE575,0x80082FA0,0x80082FA4,0x800BE628,0x800BEAC0,0x800BEAC1,
    0x80082F90,0x800BE620,0x800BE624,0x800BE9C4,0x800BE9C0,0x800BE9F0,0x8002AAEC)
FIELDS=((MODE,1),(COUNT,4),(INDEX,4),(BASE,4),(DISABLED,1),(NEXT,1),(PHASE,1),
    (WIDTH,4),(HEIGHT,4),(BUFFER,4),(PAGE,1),(WORLD,4))
SIGNATURES={0x151D6778:1,0x1501A490:6,0x151D5E90:4,0x1501A680:1,0x151D61B0:1,
    0x1517EFAC:1,0x1517E28C:2,0x15172F70:1,0x15181EE0:1,0x1517F564:1,
    0x1508FD38:1,0x151674F8:4,0x15096934:1}


def fixture(count=0,phase=0,pattern=0,disabled=0,next_=0,dimensions=(320,240)):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
    for base,length in ((TABLE-1024,1040),(CURSOR-32,0x1000)):
        memory.update({base+i:0xA5 for i in range(length)})
    for address,size in FIELDS:
        for i in range(-4,size+4):memory[address+i]=0xA5
    values=(pattern%4,count&0xFFFFFFFF,0x12348001,0x80401234,disabled,next_,phase,
        dimensions[0]&0xFFFFFFFF,dimensions[1]&0xFFFFFFFF,0x81607FFC,(0,1,128,255)[pattern%4],0x12348001)
    for (address,size),value in zip(FIELDS,values):put(memory,address,value,size)
    for page in range(256):put(memory,TABLE-page*4,0x81200000+page*0x1000)
    return memory


def buffer_hash(memory):
    result=2166136261
    for address in range(CURSOR-32,CURSOR-32+512,4):result=((result^read(memory,address))*16777619)&0xFFFFFFFF
    return result


def snapshot(memory):
    return tuple(int.from_bytes(bytes(memory[a+i] for i in range(n)),'big') for a,n in FIELDS)+(buffer_hash(memory),)


def returned(target,args,ordinal,pattern):
    if target==0x1517EFAC:return 0x80000000 if pattern&2 else 0
    if target==0x151D61B0:return 0xDEADBEEF
    return (args[0]+8*(1+(target//4+ordinal+pattern)%3))&0xFFFFFFFF


def effects(memory,target,args,ordinal,mode):
    if mode==1 and target==0x151D6778:put(memory,COUNT,0xFFFFFFFF)
    elif mode==2 and target==0x1501A490:memory[DISABLED]=1;memory[PHASE]=0
    elif mode==3 and target==0x151D5E90 and ordinal==1:
        memory[PHASE]=7;memory[PAGE]=255;put(memory,BUFFER,0x81718004)
    elif mode==3 and target==0x1501A680:memory[PHASE]=128
    elif mode==4 and target==0x151D61B0:memory[PHASE]=128;put(memory,BUFFER,0x81718004)
    elif mode==5 and target==0x1517EFAC:put(memory,WORLD,0x87654321)
    elif mode==6 and target==0x1517F564:memory[DISABLED]=0;memory[NEXT]=1
    elif mode==7 and target==0x1517F564:memory[DISABLED]=1;memory[NEXT]=0
    elif mode==8 and target==0x1501A490:memory[DISABLED]=0;memory[PHASE]=255
    elif mode==9 and target==0x151D5E90 and ordinal==1:
        put(memory,WIDTH,4096);put(memory,HEIGHT,1);put(memory,BUFFER,0x81718004)
    else:return False
    return True


def reference(memory,pattern=0,mode=0,cursor=CURSOR):
    memory,calls,observations,returns,fired=dict(memory),[],[],[],[]
    counts=Counter()
    def call(target,*args):
        args=tuple(a&0xFFFFFFFF for a in args)
        calls.append((target,args));observations.append((target,snapshot(memory)))
        counts[target]+=1
        value=returned(target,args,counts[target],pattern);returns.append(value)
        if effects(memory,target,args,counts[target],mode):fired.append((target,counts[target],mode))
        return value
    def emit(w0,w1):
        nonlocal cursor
        assert CURSOR-32<=cursor< CURSOR-32+512-7,'Outside observed callback buffer prefix'
        put(memory,cursor,w0);put(memory,cursor+4,w1);cursor+=8
    if memory[MODE]==1:cursor=call(0x151D6778,cursor)
    count=read(memory,COUNT)
    if count:
        index=(count+1)&0xFFFFFFFF;put(memory,INDEX,index)
        address=(index*0x180+read(memory,BASE)+64)&0xFFFFFFFF
    else:address=(read(memory,BASE)+64)&0xFFFFFFFF
    emit(0xDC080008,address)
    cursor=call(0x1501A490,cursor,255,0,0,0,0)
    if memory[DISABLED]:
        phase=(memory[PHASE]^128)-128
        if phase==0:
            emit(0xFF100000|((read(memory,WIDTH)-1)&4095),read(memory,BUFFER))
            component=lambda a:int(floating(bits(floating(bits(float(signed(read(memory,a)))))*4.0)))&4095
            emit(0xED000000,(component(WIDTH)<<12)|component(HEIGHT))
            cursor=call(0x151D5E90,cursor,read(memory,TABLE-memory[PAGE]*4),0,1)
            cursor=call(0x1501A680,cursor)
            memory[PHASE]=1
        elif phase<5:
            memory[PHASE]=(phase+1)&255
            call(0x151D61B0,read(memory,BUFFER))
        cursor=call(0x151D5E90,cursor,read(memory,BUFFER),0,1)
    else:memory[PHASE]=0
    if call(0x1517EFAC,0)==0:
        cursor=call(0x1517E28C,cursor,read(memory,WORLD))
        cursor=call(0x15172F70,cursor)
        cursor=call(0x15181EE0,cursor)
    cursor=call(0x1517F564,cursor)
    if not memory[DISABLED] and not memory[NEXT]:cursor=call(0x1508FD38,cursor)
    cursor=call(0x151674F8,cursor,3,0,0)
    cursor=call(0x151674F8,cursor,3,0,1)
    cursor=call(0x15096934,cursor)
    return memory,calls,observations,returns,fired,cursor


class OverlayOracle(previous.RenderOracle):
    def __init__(self,words,memory,pattern=0,mode=0,phase=0,fault=None,entry=source.ENTRY,arguments=None,connected=None):
        super().__init__(words,memory,pattern=pattern,phase=phase,fault=fault,entry=entry,
            arguments=arguments or (CURSOR,),connected=connected)
        self.overlay_mode=mode

    def execute(self,word):
        if word>>26==32:
            self.dispatched_word=word
            return signed_byte.FamilyOracle.execute(self,word)
        return super().execute(word)

    def record_call(self,target):
        args=self.arguments(SIGNATURES[target])
        self.calls.append((target,args));self.events.append(('CALL',target,args))
        self.observations.append((target,snapshot(self.memory)))
        self.counts[target]+=1

    def hook(self,target):
        args=self.calls[-1][1]
        value=returned(target,args,self.counts[target],self.pattern)
        if effects(self.memory,target,args,self.counts[target],self.overlay_mode):
            self.fired.append((target,self.counts[target],self.overlay_mode))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=value


public,state=previous.public,previous.state
