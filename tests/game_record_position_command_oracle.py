"""Record positioning with original helper code and two indirect dispatch windows."""
from dataclasses import dataclass
import struct
from tools.experiments import game_record_position_command_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode
COMMAND,TABLE,HEAD,NODES,INNER,LOOKUP=0x800D2F60,0x800884D4,0x800DCF38,0x50000,0x1505EEF4,0x15178B98
u32=lambda n:n&0xFFFFFFFF
s16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
    ident:int=0x123400A5
    mode:int=0
    index:int=3
    first:int=0x8765A001
    middle:int=0x12348000
    third:int=0xFEDCBA98
    last:int=0x7654FFFF
    mutation:int=0
    nodes:int=2
    phase:int=0

def symbols():return dict(func_15084000=source.RESOLVE,func_15178BE4=source.ATTACH,func_15178C34=source.POSITION,D_800CC2D0=0x800CC2D0)
def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+2048}
def fixture(c=Case()):
    m={STACK+i:(i*17+165)&255 for i in range(-2048,2048)}
    for a,n in((COMMAND,32),(NODES,256),(HEAD,4),(TABLE,60),(0x800D3840,4)):
        for i in range(n):m[a+i]=165
    for off,v in((0,c.ident),(4,c.mode),(8,c.first),(12,c.middle),(16,c.third),(20,c.last)):put(m,COMMAND+off,u32(v))
    put(m,TABLE+28,source.ENTRY);put(m,HEAD,0 if c.nodes==0 else NODES)
    for i in range(3):
        node=NODES+64*i;put(m,node+8,node+64 if i<2 else 0);m[node+0x34]=((c.ident&255)+(0 if c.nodes==i+1 else i+1))&255
    return m

def resolver_effect(m,c,home,command):
    if c.mutation&1:put(m,command+12,0xFFFF7FFF);put(m,command+8,0x10203040)
    if c.mutation&2:put(m,home,0xFFFFFFFF)

def find_node(m,ident):
    n=read(m,HEAD)
    while n:
        if m[n+0x34]==ident&255:return n
        n=read(m,n+8)
    return 0

def set_position(m,target,args,s):
    n=find_node(m,args[0])
    if not n:return
    if target==s['func_15178BE4']:put(m,n+16,args[1]);put(m,n+20,0x80000000);put(m,n+48,args[2]&65535,2)
    else:put(m,n+16,u32(args[1]<<16)|(args[2]&65535));put(m,n+20,u32(args[3]<<16));put(m,n+48,args[4]&65535,2)

def reference(initial,c=Case(),s=None,connected=False,args=None,home=None):
    s=symbols()if s is None else s;ident,mode,command=(u32(c.ident),u32(c.mode),COMMAND)if args is None else args;m=dict(initial);home=STACK+c.phase if home is None else home;put(m,home,ident);calls=[]
    if mode not in(0,1):return m,calls,0
    if mode==0:
        token=read(m,command+8)&0xFFFFDFFF;calls.append((s['func_15084000'],(token,)))
        if connected:calls.append((INNER,(token,)))
        resolver_effect(m,c,home,command);a=(read(m,home)&255,u32(s['D_800CC2D0']+c.index*0x32C+20),u32(s16(read(m,command+14,2))));target=s['func_15178BE4']
    else:a=(ident&255,*[read(m,command+i)for i in(8,12,16,20)]);target=s['func_15178C34']
    calls.append((target,a))
    if connected:calls.append((LOOKUP,(a[0],)))
    set_position(m,target,a,s);return m,calls,1

class PositionOracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None,args=None):
        self.case=c;self.syms=symbols()if s is None else s;self.home=STACK+c.phase;self.command=COMMAND
        super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=(u32(c.ident),u32(c.mode),COMMAND)if args is None else args,connected=connected)
        self.trace=[];self.all_accesses=0;self.cut=None
    def access(self):
        if self.own_instruction:
            if self.all_accesses==self.cut:raise faults.AccessBoundary
            self.all_accesses+=1
    def get(self,a,n):
        v=super().get(a,n)
        if self.own_instruction:self.trace.append(('R',a,n,v))
        return v
    def put(self,a,v,n):
        super().put(a,v,n)
        if self.recording and self.own_instruction:self.trace.append(('W',a,n,v&((1<<(8*n))-1)))
    def record_call(self,t):
        s=self.syms;counts={source.ENTRY:3,s['func_15084000']:1,s['func_15178BE4']:3,s['func_15178C34']:5,INNER:1,LOOKUP:1}
        assert t in counts,('Unbounded position provider',hex(t));a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==source.ENTRY:self.home=self.r[29];self.command=a[2]
    def hook(self,t):
        s=self.syms;c=self.case;a=self.calls[-1][1];value=0xDEADBEEF
        if t in(s['func_15084000'],INNER):
            resolver_effect(self.memory,c,self.home,self.command);value=u32(c.index)if t==s['func_15084000']else(0 if c.index<0 else u32(s['D_800CC2D0']+c.index*0x32C))
        elif t in(s['func_15178BE4'],s['func_15178C34']):set_position(self.memory,t,a,s)
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

HELPERS=((source.RESOLVE,0xB14B0,17),(source.ATTACH,0x1A6094,20),(source.POSITION,0x1A60E4,26),(LOOKUP,0x1A6048,19))
def helper_code(rom):
    result={}
    for entry,offset,n in HELPERS:result.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return result
WINDOWS=((0x150AE12C,23,(0x150AE158,0x150AE188)),(0x1509C0D8,12,(0x1509C108,)))
def caller_machine(rom,words,c=Case(),window=0,opcode=8):
    entry,n,ends=WINDOWS[window];initial=fixture(c);home=STACK+c.phase;command_word=(c.ident&0xFFFF0FFF)|(opcode<<12);put(initial,COMMAND,command_word)
    connected=helper_code(rom);connected.update(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words));connected.update({pc:0 for pc in ends})
    if window==1:put(initial,home+0x38,u32(c.mode))
    body=struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2D4B0);m=PositionOracle(body,initial,c,entry=entry,connected=connected,args=(COMMAND,0,0));m.r[10]=7;m.r[14]=3;m.r[11]=0x800D3840;m.r[7]=c.ident&0xFFF;m.r[9]=0x12345678;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=ends
    expected=dict(initial);calls=[];value=0
    if window==1:put(expected,0x800D3840,5);put(expected,home+0x1C,0x12345678)
    if window==1 or opcode:
        args=(u32(c.ident& (0xFFF if window==1 else 0xFFFF0FFF)),u32(c.mode),COMMAND);expected,calls,value=reference(expected,c,connected=True,args=args,home=home if window==1 else home-16);calls=[(source.ENTRY,args)]+calls
    return m,(expected,calls,value)
