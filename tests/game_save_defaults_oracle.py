"""Ordered byte clear/default stores, live pointer aliases and original callers."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_save_defaults_candidates as candidate
from tools.experiments import game_save_defaults_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode as BaseWindowCode,WindowBoundary
PAYLOAD=0x60000
READ=0x151DD3A0
def symbols():return dict(D_800BE2F0=0x800BE2F0,D_800BE358=0x800BE358,D_80082BBC=0x80082BBC,jtbl_80095A00_game=source.TABLE,**{'.rodata':source.TABLE})
@dataclass(frozen=True)
class Case:
    pattern:int=0
    placement:int=0
    phase:int=0
    pointer_alias:int=-1
    packet:int=0
    checksum_match:bool=False
def fixture(c=Case(),s=None,entry=source.ENTRY):
    s=symbols()if s is None else s;start=s['D_800BE2F0'];end=s['D_800BE358'];variable=s['D_80082BBC']
    m={STACK+i:(i*17+165)&255 for i in range(-0x500,0x400)}
    def mapped(p,n):
        for i in range(n):m[(p+i)&0xFFFFFFFF]=(i*29+c.pattern*71+123)&255
    mapped((start-16)&0xFFFFFFFF,400);mapped(PAYLOAD-16,400);mapped(variable-8,144)
    pointer=(start+2,start,start+4,PAYLOAD,PAYLOAD+1,PAYLOAD+10)[c.placement]
    if c.pointer_alias>=0:
        pointer=(variable+c.pointer_alias-1)&0xFFFFFFFF
        shifted=(pointer&~(255<<(24-8*c.pointer_alias)))|(3<<(24-8*c.pointer_alias))
        mapped((pointer-16)&0xFFFFFFFF,160);mapped((shifted-16)&0xFFFFFFFF,160)
    put(m,variable,pointer)
    for i,offset in enumerate(source.TARGET_OFFSETS):put(m,s['jtbl_80095A00_game']+4*i,entry+offset)
    return m
def reference(initial,s=None):
    s=symbols()if s is None else s;m=dict(initial);trace=[];p=s['D_800BE2F0'];end=s['D_800BE358'];steps=0
    def wr(at,v,n=1):
        at&=0xFFFFFFFF;assert all((at+i)&0xFFFFFFFF in m for i in range(n));put(m,at,v,n);trace.append(('W',at,n,v&((1<<(8*n))-1)))
    while True:
        wr(p,0);p=(p+1)&0xFFFFFFFF;steps+=1;assert steps<=1024
        if not p<end:break
    for index in range(10):
        stores=[(1,3),(3,2),(4,1),(2,10)]
        if index==0:stores.append((5,3))
        elif index in(1,2):stores.append((5,5))
        elif index==7:stores.append((5,20))
        elif index==5:stores.extend(((5,20),(2,0)))
        elif index in(8,9):stores.append((5,3))
        stores.append((9,0))
        for offset,value in stores:
            pointer=read(m,s['D_80082BBC']);trace.append(('R',s['D_80082BBC'],4,pointer));wr(pointer+index*10+offset,value)
    return m,trace,steps
class WindowCode(BaseWindowCode):
    def __getitem__(self,pc):
        if pc in self.ends:self.owner.current_pc=pc;self.owner.delay_of=None;raise WindowBoundary
        return super().__getitem__(pc)
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None):
        self.s=symbols()if s is None else s;self.read_packets=[]
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=())
    def record_call(self,t):
        assert t in(source.ENTRY,READ),hex(t)
        a=tuple(self.arguments(4))if t==READ else();self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        assert t==READ;a=self.calls[-1][1];assert a[1:]==(0x44,self.s['D_800BE2F0'],112)
        packet=packet_bytes(self.case);self.read_packets.append(packet)
        for i,v in enumerate(packet):self.memory[a[2]+i]=v
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0x87654321
def packet_bytes(c):
    b=bytearray((i*31+c.packet*71+17)&255 for i in range(112));value=(0xCC+(b[2]<<2)+(b[3]<<3)+sum(b[i]<<(i&3)for i in range(4,104)))&65535
    struct.pack_into('>H',b,0,value if c.checksum_match else value^1);return bytes(b)
def public(m):return {p:v for p,v in m.items()if not STACK-0x500<=p<STACK+0x400}
def bound(obj,s,fitted=False):
    raw,bindings=source.function_blob(obj)
    if fitted:
        raw=source.normalized(raw,bindings,(candidate.ROOT/source.ROM_IMAGE).read_bytes()[source.ROM:source.ROM+276]);bindings={at:rows[:]for at,rows in bindings.items()}
        for at,a,b,old,new in source.PATCHES:bindings[at]=[('R_MIPS_HI16',new)]
    words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
    for at,rows in bindings.items():
        if words[at//4]&65535:raise ValueError('Use the GNU linker for nonzero relocation addends')
        kind,name=rows[0];value=s[name]
        words[at//4]=(words[at//4]&0xFFFF0000)|((((value+0x8000)>>16)if kind=='R_MIPS_HI16'else value)&65535)
    return words
def cases():
    for pattern,placement,phase in itertools.product(range(16),range(6),(0,8)):yield Case(pattern=pattern,placement=placement,phase=phase)
    for alias,pattern,phase in itertools.product(range(4),(0,1),(0,8)):yield Case(pointer_alias=alias,pattern=pattern,phase=phase)
def controls():
    b=candidate.SELECTED
    cached=b.replace('    u32 index;','    u32 index;\n    SaveDefaultRecord33990 *records;').replace('    for (index = 0;','    records = (SaveDefaultRecord33990 *)D_80082BBC;\n    for (index = 0;').replace('((SaveDefaultRecord33990 *)D_80082BBC)[index]','records[index]')
    return dict(short_clear=b.replace('u8 *end = D_800BE358;','u8 *end = D_800BE358 - 1;'),
      long_clear=b.replace('u8 *end = D_800BE358;','u8 *end = D_800BE358 + 8;'),
      first=b.replace('.value1 = 3','.value1 = 4'),second=b.replace('.value3 = 2','.value3 = 1'),third=b.replace('.value4 = 1','.value4 = 2'),fourth=b.replace('.value2 = 10','.value2 = 9'),
      case_one=b.replace('.value5 = 5','.value5 = 4'),case_seven=b.replace('.value5 = 20','.value5 = 19',1),
      missing_special_zero=b.replace('            ((SaveDefaultRecord33990 *)D_80082BBC)[index].value2 = 0;\n',''),
      case_eight=b.replace('        case 9:\n            ((SaveDefaultRecord33990 *)D_80082BBC)[index].value5 = 3;','        case 9:\n            ((SaveDefaultRecord33990 *)D_80082BBC)[index].value5 = 4;'),
      tail=b.replace('.value9 = 0','.value9 = 1'),retained=b.replace('        switch (index) {','        ((SaveDefaultRecord33990 *)D_80082BBC)[index].retained0 = 0;\n        switch (index) {'),
      next_record=b.replace(')[index]',')[index + 1]'),cached_pointer=cached)
