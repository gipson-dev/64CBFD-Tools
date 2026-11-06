"""Eight argument table constructor; original record allocator and byte copy."""
from dataclasses import dataclass, replace
import itertools,struct
from tools.experiments import game_selector_table_payload_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
OWNER,RESULT,MARK=0x30000,0x60000,0x90000
CREATE,COPY,ALLOCATE=0x1516037C,0x10022EC0,0x15167A68
RAW=(0,0x80000000,1,0x007FFFFF,0x00800000,0x3F800000,0xBF800000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7F812345)
u32=lambda x:x&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    index:int=0
    selector:int=1
    owner:int=OWNER
    allocated:int=1
    mode:int=0
    phase:int=0
def symbols():return dict(D_800A670C=0x800A670C,D_800A6730=0x800A6730,D_800A6754=0x800A6754,func_1516037C=CREATE,memcpy=COPY)
def args(c):
    i=c.index
    return(c.owner,0xABCD0000|c.selector,0xFEED0000|((i*37+255)&255),0xCAFE0000|((i*73)&255),
           0x12340000|((i*109+128)&255),(0x76548000,0x76547FFF,0x7FFFFFFF,0x80000000)[i%4],
           0xBEEF0000|((i*53+255)&255),u32(i*1664525+1013904223))
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;home=STACK+c.phase
    m={home+i:(i*17+c.index*13+165)&255 for i in range(-512,1024)}
    for p,n in((OWNER-16,192),(RESULT-16,128),(MARK,4)):
        m.update({p+i:(i*29+c.index*11+89)&255 for i in range(n)})
    for k,name in enumerate(('D_800A670C','D_800A6730','D_800A6754')):
        for i in range(9 if k<2 else 3):put(m,s[name]+4*i,RAW[(c.index+i*5+k*7)%len(RAW)])
    put(m,MARK,0);return m
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-512<=a<STACK+c.phase+1024}
def effect(m,c,s,home):
    put(m,MARK,0xC001D00D)
    if c.mode&1:
        for name,n in(('D_800A670C',9),('D_800A6730',9),('D_800A6754',3)):
            for i in range(n):put(m,s[name]+4*i,read(m,s[name]+4*i)^0xA5A5A5A5)
    if c.mode&2:
        for i in range(8):put(m,home+4*i,0xABCDEF00+i)
        m[RESULT+8]^=0x55
def reference(initial,c=Case(),arguments=None,s=None,home=None,connected=False):
    a=args(c)if arguments is None else arguments;s=symbols()if s is None else s
    home=STACK+c.phase if home is None else home;m=dict(initial);calls=[];copies=[];snapshots=[]
    selector=a[1]&255
    if selector>=3:return m,calls,0,copies,snapshots
    payload,header=home-32,home-40
    for j,name in enumerate(('D_800A670C','D_800A6730')):
        blob=data(m,s[name]+12*selector,12)
        for i,v in enumerate(blob):m[payload+12*j+i]=v
    put(m,payload+24,0);put(m,payload+28,read(m,s['D_800A6754']+4*selector))
    m[header]=a[3]&255;m[header+1]=a[4]&255;put(m,header+2,a[5]&65535,2);m[header+4]=a[2]&255
    factory=(header,a[0],32,a[6]&255,u32(a[7]));calls.append((s['func_1516037C'],factory))
    snapshots.append((data(m,header,6),data(m,payload,32)));effect(m,c,s,home)
    result=RESULT if c.allocated else 0
    def copy(dst,src,n):
        calls.append((s['memcpy'],(dst,src,n)));blob=data(m,src,n);copies.append((dst,blob,n))
        for i,v in enumerate(blob):m[dst+i]=v
    if connected:calls.append((ALLOCATE,(53,u32(a[7]),56,1,a[6]&255,1)))
    if result:
        if connected:copy(RESULT+14,header,6)
        else:
            for i,v in enumerate(data(m,header,6)):m[RESULT+14+i]=v
        put(m,RESULT+20,a[0]);copy(RESULT+24,payload,32)
    return m,calls,result,copies,snapshots
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),arguments=None,s=None,entry=source.ENTRY,connected=None):
        self.c=c;self.a=args(c)if arguments is None else tuple(arguments);self.s=symbols()if s is None else s
        self.snapshots=[];self.effect_fired=False
        super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=self.a)
        self.before_f=self.f[:]
    def record_call(self,t):
        counts={source.ENTRY:8,self.s['func_1516037C']:5,self.s['memcpy']:3,ALLOCATE:6}
        assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==source.ENTRY:
            self.a=a;self.target_home=self.r[29]
            self.entry_contract=reference(self.memory,self.c,self.a,self.s,self.target_home)
        if t==self.s['func_1516037C']:
            self.snapshots.append((data(self.memory,a[0],6),data(self.memory,self.target_home-32,32)))
        if t==self.s['memcpy']:self.copy_observations.append((a[0],data(self.memory,a[1],a[2]),a[2]))
    def hook(self,t):
        a=self.calls[-1][1];result=0xDEADBEEF
        if t in(self.s['func_1516037C'],ALLOCATE):
            assert not self.effect_fired;effect(self.memory,self.c,self.s,self.target_home);self.effect_fired=True
            result=RESULT if self.c.allocated else 0
            if result and t==self.s['func_1516037C']:
                for i,v in enumerate(data(self.memory,a[0],6)):self.memory[RESULT+14+i]=v
                put(self.memory,RESULT+20,a[1])
        else:
            assert t==self.s['memcpy']and a[2]in(6,32)
            blob=data(self.memory,a[1],a[2])
            for i,v in enumerate(blob):self.memory[a[0]+i]=v
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(result)
def payload(obj):
    t,fs,rs=parse_object(obj);f=fs[source.FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:v for p,v in rs.items()if a<=p<a+n}
def bound(obj,s=None):return bound_blob(*payload(obj),symbols()if s is None else s)
def cases():
    for i,selector,allocated,mode,phase in itertools.product(range(256),(0,1,2,3,127,128,255),(0,1),(0,3),(0,8)):
        yield Case(i,selector=selector,allocated=allocated,mode=mode,phase=phase)
    for selector in range(256):yield Case(255,selector=selector,owner=0)
def controls():
    b=source.SELECTED
    return dict(reject_last=b.replace('selector >= 3','selector >= 2'),
        wrong_base=b.replace('D_800A670C[selector]','D_800A670C[0]'),
        wrong_amplitude=b.replace('D_800A6730[selector]','D_800A6730[0]'),
        wrong_phase=b.replace('payload.phase = 0.0f','payload.phase = 1.0f'),
        wrong_rate=b.replace('D_800A6754[selector]','D_800A6754[0]'),
        wrong_kind=b.replace('header.unk1 = kind','header.unk1 = flags'),
        wrong_lifetime=b.replace('header.unk2 = lifetime','header.unk2 = 0'),
        wrong_size=b.replace('sizeof(payload), priority','sizeof(payload)-4, priority'),
        short_copy=b.replace('&payload, sizeof(payload)','&payload, sizeof(payload)-4'),
        false_return=b.replace('return result;','return 0;'))
