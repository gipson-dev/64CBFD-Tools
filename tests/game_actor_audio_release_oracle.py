"""Independent actor/audio-release effects and bounded original helper execution."""
from dataclasses import dataclass
import math,struct
from tools.experiments import game_actor_audio_release_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
ACTOR,VOICE,OTHER,MARK=0x30000,0x40000,0x41000,0x50000
STOP_TABLE,VOICE_STOP,AUDIO_BASE,UNLINK,FALLBACK,DESTRUCTOR,DESTRUCTORS=0x800425E0,0x10017594,0x10010E78,0x151696DC,0x15169804,0x15200000,0x8008B4D0
u32=lambda n:n&0xFFFFFFFF
s16=lambda n:(n&65535)-65536 if n&32768 else n&65535
bits=lambda f:struct.unpack('>I',struct.pack('>f',f))[0]
floating=lambda n:struct.unpack('>f',struct.pack('>I',n))[0]
COORDS=((0.0,-0.0,0.0),(1.75,-1.75,17.5),(32767.75,-32768.75,65535.75),(-65536.75,65536.75,123.25),(1073741824.0,-1073741824.0,2147483520.0))
@dataclass(frozen=True)
class Case:
    slot:int=3
    matching:bool=True
    handle:int=1
    position:int=1
    stop_mode:int=0
    audio_mode:int=0
    release_mode:int=0
    phase:int=0
    alias:int=0
    stop_valid:bool=True
    voice:bool=True
    kind:int=2
    post_kind:int=-1
    destructor:bool=False

def symbols():return dict(D_800D99D0=source.TABLE,func_100111C8=source.STOP,func_10010F88=source.AUDIO,func_1516972C=source.RELEASE)
def addresses(c,s=None):
    s=symbols()if s is None else s
    if c.alias==1:return s['D_800D99D0']+128*4-0x48,s['D_800D99D0']
    if c.alias==2:return s['D_800D99D0']+c.slot*4-0x28,s['D_800D99D0']
    return ACTOR,s['D_800D99D0']
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+768}
def fixture(c=Case(),s=None):
    actor,table=addresses(c,s);m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,768)}
    for base,size in((actor,0x200),(table,1024),(STOP_TABLE,192),(MARK,16),(OTHER,64)):
        for i in range(size):m[u32(base+i)]=(i*29+0xA5)&255
    for i,value in enumerate(COORDS[c.position]):put(m,actor+0x28+i*4,bits(value))
    m[actor]=c.kind;m[actor+0x48]=c.slot;put(m,actor+0x4A,c.handle,2)
    slot=128 if c.alias==1 else c.slot
    put(m,u32(table+slot*4),actor if c.matching else OTHER)
    handle=read(m,actor+0x4A,2);p=STOP_TABLE+(handle&15)*12
    put(m,p,handle if c.stop_valid else handle^1,2);put(m,p+4,0x1234,2);put(m,p+8,VOICE if c.voice else 0)
    for kind in{c.kind,c.post_kind&255}:put(m,DESTRUCTORS+kind*52,DESTRUCTOR if c.destructor else 0)
    return m
def snapshot(m,c,s):
    a,t=addresses(c,s);return(read(m,a+0x4A,2),tuple(read(m,a+0x28+4*i)for i in range(3)),m[a+0x48],read(m,u32(t+c.slot*4)),read(m,MARK))
def effect(m,c,s,which):
    a,t=addresses(c,s)
    if which=='stop':
        if c.stop_mode&1:put(m,a+0x4A,0x2468,2)
        if c.stop_mode&2:
            for i,f in enumerate((123.75,-234.5,32767.75)):put(m,a+0x28+i*4,bits(f))
        if c.stop_mode&4:m[a+0x48]=255;put(m,u32(t+c.slot*4),OTHER)
    if which=='audio':
        if c.audio_mode&1:put(m,a+0x4A,0x1357,2)
        if c.audio_mode&2:put(m,u32(t+c.slot*4),a)
        if c.audio_mode&4:put(m,a+0x28,bits(-99.5))
    if which=='release'and c.release_mode:put(m,a+0x4A,0xBEEF,2);put(m,MARK,0xABCDEF01)
    if which=='unlink'and c.post_kind>=0:m[a]=c.post_kind
def audio_arguments(m,a):return(0x2D7,0x5DC0,0,0,0,*[u32(math.trunc(floating(read(m,a+0x28+4*i))))for i in range(3)],1000,6000)
def reference(initial,c=Case(),s=None,connected=False):
    s=symbols()if s is None else s;m=dict(initial);a,t=addresses(c,s);calls=[];observations=[]
    def call(target,args):
        args=tuple(map(u32,args));calls.append((target,args));observations.append((target,snapshot(m,c,s)))
    slot=m[a+0x48];p=u32(t+slot*4)
    if read(m,p)==a:put(m,p,0)
    handle=read(m,a+0x4A,2)
    if handle:
        call(s['func_100111C8'],(handle,))
        if connected:
            p=STOP_TABLE+(handle&15)*12;voice=read(m,p+8)
            if voice and read(m,p,2)==handle:
                put(m,p,0,2);put(m,p+4,0,2);call(VOICE_STOP,(voice,));effect(m,c,s,'stop');put(m,p+8,0)
        else:effect(m,c,s,'stop')
        put(m,a+0x4A,0,2);args=audio_arguments(m,a);call(s['func_10010F88'],args)
        if connected:call(AUDIO_BASE,(0,*args[:5],*[s16(v)for v in args[5:]]))
        effect(m,c,s,'audio')
    call(s['func_1516972C'],(a,))
    if connected:
        call(UNLINK,(a,));effect(m,c,s,'unlink');kind=m[a]
        if kind>=2:call(read(m,DESTRUCTORS+kind*52)or FALLBACK,(a,));effect(m,c,s,'release')
    else:effect(m,c,s,'release')
    return m,calls,observations

class AudioReleaseOracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None):
        self.case=c;self.syms=symbols()if s is None else s
        super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=(addresses(c,self.syms)[0],),connected=connected)
        self.trace=[];self.observations=[];self.all_accesses=0;self.cut=None
    def access(self):
        if self.own_instruction:
            if self.all_accesses==self.cut:raise faults.AccessBoundary
            self.all_accesses+=1
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
    def execute(self,word):
        if word>>26==32:
            self.own_instruction=True
            try:
                value=self.get(u32(self.r[word>>21&31]+s16(word)),1)
                self.r[word>>16&31]=u32((value^128)-128);self.r[0]=0
            finally:self.own_instruction=False
        else:super().execute(word)
    def record_call(self,target):
        s=self.syms;counts={source.ENTRY:1,s['func_100111C8']:1,s['func_10010F88']:10,s['func_1516972C']:1,VOICE_STOP:1,AUDIO_BASE:11,UNLINK:1,FALLBACK:1,DESTRUCTOR:1}
        assert target in counts,('Unbounded actor audio release provider',hex(target));args=self.arguments(counts[target]);self.calls.append((target,args));self.events.append(('CALL',target,args));self.observations.append((target,snapshot(self.memory,self.case,s)))
    def hook(self,target):
        s=self.syms
        if target in(s['func_100111C8'],VOICE_STOP):effect(self.memory,self.case,s,'stop')
        elif target in(s['func_10010F88'],AUDIO_BASE):effect(self.memory,self.case,s,'audio')
        elif target in(s['func_1516972C'],FALLBACK,DESTRUCTOR):effect(self.memory,self.case,s,'release')
        else:assert target==UNLINK;effect(self.memory,self.case,s,'unlink')
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0x4321

HELPERS=((source.STOP,0x111C8,29),(source.AUDIO,0x10F88,29),(source.RELEASE,0x196BDC,28))
WINDOWS=((0x150E3648,7,(0x150E3664,0x150E367C)),(0x150E3778,14,(0x150E37B0,)),(0x150E37D8,7,(0x150E37F8,0x150E3FD4)),(0x150E392C,4,(0x150E3FD4,)),(0x150E393C,6,(0x150E3954,0x150E3FD4)))
TICKS,RECORD=0x800BE9E4,0x60000
def helper_code(rom):
    result={}
    for entry,offset,n in HELPERS:result.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return result
def caller_machine(rom,words,c=Case(),window=0,selector=-1,timer=0,ticks=1,flag=0):
    from tools.tests.test_game_character_effect_pair import WindowCode
    entry,n,ends=WINDOWS[window];initial=fixture(c);actor,_=addresses(c)
    for i in range(32):initial[RECORD+i]=0
    put(initial,RECORD,flag);put(initial,RECORD+0x14,bits(17.5));put(initial,TICKS,ticks);put(initial,actor+0x7C,timer,2)
    put(initial,STACK+c.phase+0xBC,0xDEAD0000)
    connected=helper_code(rom);connected.update(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words));connected.update({pc:0 for pc in ends})
    body=struct.unpack_from('>%dI'%n,rom,entry-source.ENTRY+source.ROM)
    m=AudioReleaseOracle(body,initial,c,entry=entry,connected=connected)
    m.r[2]=RECORD;m.r[9]=OTHER;m.r[16]=u32(selector);m.r[17]=0xFFFFFFFF if window==0 else actor;m.r[14]=u32(timer);m.r[30]=0;m.before=m.r[:]
    m.code=WindowCode(m.code,m);m.code.ends=ends
    expected=dict(initial);called=True
    if window==0:
        put(expected,RECORD,OTHER);called=selector==-1 or selector==c.slot
    elif window==1:
        t=s16(timer)
        if t!=-99:t=s16(t-ticks);put(expected,actor+0x7C,t,2);called=t<0
        else:called=False
    elif window==2:called=flag==0
    elif window==4:put(expected,actor+0x44,timer);called=timer<=0
    calls=[];observations=[]
    if called:
        prefix=(source.ENTRY,(actor,));obs=(source.ENTRY,snapshot(expected,c,symbols()))
        expected,calls,observations=reference(expected,c,connected=True);calls=[prefix]+calls;observations=[obs]+observations
    return m,(expected,calls,observations),called
