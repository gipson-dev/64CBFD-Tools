"""Independent ordered scanner semantics and bounded resource-provider machine."""
from tools.experiments import game_texture_vertex_span as source
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import game_view_projection_family_oracle as family
from tools.tests.test_game_point_transform_match import put,read,external_memory
from tools.tests.game_animation_timeline_oracle import signed

COMMANDS,OUTPUT,CACHE,PROVIDER=0x22000,0x24000,0x800B0E58,0x1510D0EC
TEXTURE,OTHER,VERTICES=0x80040000,0x80050000,0x80060000


def opcode(memory,cursor):
    byte=read(memory,cursor,1)
    return byte if byte<128 else byte-256


def decode(first,second):
    kind=(first>>24)&255
    if kind in (5,6):
        values=[first>>16&255,first>>8&255,first&255]
        if kind==6:
            values += [second>>16&255,second>>8&255,second&255]
        return [v>>1 for v in values]
    return [(second>>shift)&31 for shift in (25,20,15,10,5,0)]+[
        (first>>shift)&31 for shift in (10,5,0,23,18)]+[(second>>30&3)+(first>>15&7)*4]


def triangle(kind,values):
    if kind in (5,6):
        values=list(values)*(6 if kind==6 else 3)
        a,b,c=values[:3]
        first=kind<<24|((a*2)&255)<<16|((b*2)&255)<<8|((c*2)&255)
        second=0
        if kind==6:
            a,b,c=values[3:6]
            second=((a*2)&255)<<16|((b*2)&255)<<8|((c*2)&255)
        return first,second
    values=(list(values)*12)[:12]
    first=0x10000000
    for i,shift in zip((6,7,8,9,10),(10,5,0,23,18)):
        first|=(values[i]&31)<<shift
    first|=((values[11]>>2)&7)<<15
    second=sum((values[i]&31)<<shift for i,shift in enumerate((25,20,15,10,5,0)))
    second|=(values[11]&3)<<30
    return first,second


def fixture(commands,resource=3,occurrence=0,start=0,output=OUTPUT,mode=0):
    memory={machine.STACK+i:(i*17+0xA5)&255 for i in range(-0x800,0x180)}
    for base,size in ((COMMANDS-32,0x200),(OUTPUT-16,48),(CACHE,32)):
        memory.update({base+i:(i*13+0xA5)&255 for i in range(size)})
    for i,(first,second) in enumerate(commands):
        put(memory,COMMANDS+i*8,first)
        put(memory,COMMANDS+i*8+4,second)
    for i in range(8):
        put(memory,CACHE+i*4,TEXTURE)
    return dict(memory=memory,args=(COMMANDS+start*8,resource,output,occurrence&0xFFFFFFFF),mode=mode)


def provider_effects(memory,args,mode):
    if mode==1:
        put(memory,CACHE+args[1]*4,OTHER)
    elif mode==2:
        put(memory,args[0]+4,OTHER)
    elif mode==3:
        put(memory,args[2],0xDEADBEEF)


def reference(memory,args,mode=0,limit=512):
    memory=dict(memory)
    cursor,resource,output,occurrence=args
    occurrence=signed(occurrence)
    provider_effects(memory,args,mode)
    put(memory,output,0)
    stage,maximum,nested,trim=0,0,0,False
    base=None
    visits=[]
    for _ in range(limit):
        visits.append(cursor)
        kind=opcode(memory,cursor)
        if stage==0:
            if kind==-33:
                return memory,0,visits
            if kind==-3 and read(memory,cursor+4)==read(memory,CACHE+resource*4):
                old=occurrence
                occurrence=signed((occurrence-1)&0xFFFFFFFF)
                if old<1:
                    stage=1
        elif stage==1:
            while kind not in (1,5,6) and kind>>4!=1:
                cursor+=8
                kind=opcode(memory,cursor)
            stage=2
            if kind!=1:
                trim=True
                while kind!=1:
                    if kind==-3:
                        nested-=1
                    cursor-=8
                    kind=opcode(memory,cursor)
            cursor-=8
            continue
        else:
            if kind==-33:
                break
            if kind==-3:
                nested+=1
                if nested>0:
                    break
            elif kind==1:
                base=read(memory,cursor+4)
                maximum=0
                first=read(memory,output)
                if first==0 or base<first:
                    put(memory,output,base)
            elif kind in (5,6) or kind>>4==1:
                indices=decode(read(memory,cursor),read(memory,cursor+4))
                maximum=max(maximum,*indices)
                if nested==0 and trim:
                    trim=False
                    put(memory,output,(read(memory,output)+(min(indices)&255)*16)&0xFFFFFFFF)
        cursor+=8
    else:
        raise ValueError('Outside bounded scanner domain')
    if base is None:
        raise ValueError('No defined vertex base at span return')
    result=signed((base+(maximum+1)*16-read(memory,output))&0xFFFFFFFF)>>4
    return memory,result&0xFFFFFFFF,visits


def cases():
    end=(0xDF000000,0)
    vertex=(0x01000000,VERTICES)
    texture=(0xFD000000,TEXTURE)
    noop=(0,0)
    yield fixture([end])
    yield fixture([vertex,triangle(5,[1,3,2]),end])
    for delta in (-64,64):
        yield fixture([noop,vertex,(0x01000000,VERTICES+delta),texture,triangle(5,[1,5,3]),end])
    for kind in (5,6,16):
        for values in ([0,0,0],[1,5,3],[31,0,17],[127,126,125],list(range(12)),list(range(31,19,-1))):
            tri=triangle(kind,values)
            for occurrence in (-1,0,1,2,0x7FFFFFFF):
                for layout in range(5):
                    if layout==0:
                        commands=[texture,noop,vertex,tri,end]
                    elif layout==1:
                        commands=[noop,vertex,texture,tri,end]
                    elif layout==2:
                        commands=[noop,vertex,texture,tri,texture,tri,end]
                    elif layout==3:
                        commands=[noop,vertex,texture,(0xFD000000,OTHER),tri,texture,tri,end]
                    else:
                        commands=[texture,noop,vertex,tri,(0x01000000,VERTICES-64),tri,end]
                    for mode in (0,1,2,3):
                        yield fixture(commands,occurrence=occurrence,mode=mode)
    for kind in (5,6,16):
        for first in (0,0x7FFFFFF0,0x80000000,0xFFFFFFF0):
            for second in (0,0x7FFFFFF0,0x80000000,0xFFFFFFF0):
                yield fixture([texture,noop,(0x01000000,first),triangle(kind,[1,5,3]),
                    (0x01000000,second),triangle(kind,[1,2,0]),end])
    for kind,count,limit in ((5,3,128),(6,6,128),(16,12,32)):
        for field in range(count):
            for value in (0,1,limit//2,limit-1):
                values=[3]*count
                values[field]=value
                yield fixture([noop,vertex,texture,triangle(kind,values),end])


class SpanOracle(family.FamilyOracle):
    def __init__(self,words,memory,args,mode=0,phase=0,entry=source.ENTRY,fault=None):
        super().__init__(words,memory,args,root=entry,phase=phase)
        self.input_args,self.mode=args,mode
        self.current_pc,self.delay_of=entry,None
        self.code=faults.TrackedCode(self.code,self)
        self.root_fault,self.root_accesses=fault,0
        self.span_entry,self.span_size=entry,len(words)*4

    def access(self):
        if self.own_instruction and self.span_entry<=self.current_pc<self.span_entry+self.span_size:
            if self.root_accesses==self.root_fault:
                raise faults.AccessBoundary
            self.root_accesses+=1

    def record_call(self,target):
        assert target==PROVIDER
        args=self.arguments(4)
        self.calls.append((target,args))
        self.events.append(('CALL',target,args))
        assert args[0]==self.input_args[1] and args[2:]==(3,0)
        assert machine.STACK-0x300<=args[1]<machine.STACK+0x180

    def hook(self,target):
        assert target==PROVIDER
        provider_effects(self.memory,self.input_args,self.mode)
        self.put(self.calls[-1][1][1],0x12345678,4)
        for i in range(4):
            self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=0xBAD01234
