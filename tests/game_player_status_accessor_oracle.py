"""Read-only status contract, raw argument homes and explicit native domains."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_player_status_accessor_candidates as candidate
from tools.experiments import game_player_status_accessor_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
u32=lambda n:n&0xFFFFFFFF
short=lambda n:((n&65535)^32768)-32768
byte=lambda n:((n&255)^128)-128
FIELDS=('D_800D213C','D_800D2140','D_800D2144','D_800D2145','D_800D2146','D_800D2148')
PATTERNS=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x7F80FE01)
@dataclass(frozen=True)
class Case:
    slot:int=0
    field:int=0
    mask:int=0xA581
    pattern:int=0
    incoming:int=0x81234560
    phase:int=0

def symbols():
    return {name:int(name[2:],16)for name in(*FIELDS,'D_800D2340')}|{'.rodata':source.TABLE,'jtbl_8009D9A0':source.TABLE}

def record_address(s,name,slot):return u32(s[name]+short(slot)*28)

def fixture(c=Case(),s=None,entry=source.ENTRY,offsets=source.CASE_OFFSETS):
    s=symbols()if s is None else s;m={STACK+i:(i*17+165)&255 for i in range(-64,128)}
    for j,name in enumerate(FIELDS):
        p=record_address(s,name,c.slot);put(m,p,PATTERNS[(c.pattern+j)%len(PATTERNS)])
    put(m,s['D_800D2340'],c.mask,2)
    for i,offset in enumerate(offsets):put(m,s['jtbl_8009D9A0']+i*4,entry+offset)
    put(m,s['jtbl_8009D9A0']+28,0)
    return m

def reference(initial,c=Case(),s=None,home=None):
    s=symbols()if s is None else s;m=dict(initial);home=STACK+c.phase if home is None else home
    put(m,home,c.slot);put(m,home+4,c.field)
    slot,field=short(c.slot),short(c.field)
    if slot>=255:return m,0
    if field==0:return m,read(m,s['D_800D2340'],2)&(1<<(slot&31))
    if field not in range(1,7):return m,u32(c.incoming)
    name=FIELDS[field-1];width=1 if field in(3,4,5)else 4;value=read(m,record_address(s,name,slot),width)
    return m,u32(byte(value)if field in(3,4)else value)

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(u32(c.slot),u32(c.field))if arguments is None else arguments)
        self.r[2]=u32(c.incoming);self.before[2]=self.r[2];self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,False
    def record_call(self,t):
        if t!=source.ENTRY:raise AssertionError(('Unexpected status accessor call',hex(t)))
        args=tuple(map(u32,self.arguments(2)));self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):raise AssertionError(('Unbounded status accessor helper',hex(t)))

def bound(obj,s):
    raw,bindings=source.function_blob(obj);words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
    for offset,rows in bindings.items():
        if len(rows)!=1:raise ValueError('Status accessor binding pair changed')
        kind,name=rows[0];value=s[name]
        if kind=='R_MIPS_HI16':words[offset//4]=(words[offset//4]&0xFFFF0000)|((value+0x8000)>>16&65535)
        elif kind=='R_MIPS_LO16':words[offset//4]=(words[offset//4]&0xFFFF0000)|(value&65535)
        else:raise ValueError('Unexpected status accessor binding kind')
    return words

def cases():
    slots=(-32768,-32767,-257,-256,-1,0,1,3,7,15,16,31,32,63,127,254,255,256,32767)
    fields=(-32768,-1,0,1,2,3,4,5,6,7,255,32767)
    for slot,field,pattern,phase in itertools.product(slots,fields,range(3),(0,8)):
        yield Case(u32(slot),u32(field),0xA581,pattern,0x81234560,phase)
    for slot,field,upper,phase in itertools.product((0,1,254,255,65535),(0,3,6,65535),(0x7FFF0000,0x80000000,0xFFFF0000),(0,8)):
        yield Case(upper|slot,upper|field,0x8001,5,0xFFFFFFFF,phase)

def controls():
    b=candidate.SELECTED
    return dict(clipped=b.replace('slot >= 255','slot >= 254'),
        signed_mask=b.replace('(u16)D_800D2340','D_800D2340'),
        bit=b.replace('(1u << slot)','(1u << (slot ^ 1))'),
        first=b.replace('return D_800D213C[slot].value','return D_800D2140[slot].value'),
        second=b.replace('return D_800D2140[slot].value','return D_800D213C[slot].value'),
        signed_first=b.replace('return D_800D2144[slot].value','return (u8)D_800D2144[slot].value'),
        signed_second=b.replace('return D_800D2145[slot].value','return (u8)D_800D2145[slot].value'),
        unsigned=b.replace('return D_800D2146[slot].value','return (s8)D_800D2146[slot].value'),
        final=b.replace('return D_800D2148[slot].value','return D_800D2140[slot].value'))

def native_source(body):
    return '''typedef unsigned int u32;typedef int s32;typedef short s16;typedef unsigned short u16;typedef signed char s8;typedef unsigned char u8;
'''+candidate.DECLARATIONS+'''
StatusWordB21B0 D_800D213C[255],D_800D2140[255],D_800D2148[255];
StatusSignedByteB21B0 D_800D2144[255],D_800D2145[255];StatusUnsignedByteB21B0 D_800D2146[255];s16 D_800D2340;
s32 func_150859AC(s16,s16) __attribute__((noinline));
'''+body+'''
static const u32 patterns[]={0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x7F80FE01};
static void quit(u32 status){__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
void _start(void){u32 typed,mask,slot,field,p,byteValue;static const s16 fields[]={-32768,-1,0,1,2,3,4,5,6,7,255,32767};
s32(*volatile call)(s16,s16)=func_150859AC;
if(sizeof(void*)!=4||sizeof(StatusWordB21B0)!=28||sizeof(StatusSignedByteB21B0)!=28||sizeof(StatusUnsignedByteB21B0)!=28)quit(9);
for(typed=0;typed<2;typed++){
for(mask=0;mask<65536;mask++){D_800D2340=(s16)mask;for(slot=0;slot<32;slot++){
u32 wanted=mask&(1u<<slot),got=(u32)(typed?call((s16)slot,0):func_150859AC((s16)slot,0));if(got!=wanted)quit(1);
}}
for(p=0;p<6;p++){
for(slot=0;slot<255;slot++){
D_800D213C[slot].value=(s32)(patterns[p]^(slot*0x10203u));D_800D2140[slot].value=(s32)(patterns[p]^(slot*0x20304u)^0xA5A50000u);D_800D2148[slot].value=(s32)(patterns[p]^(slot*0x30405u)^0x5A5A0000u);
D_800D2144[slot].value=(s8)(slot+p);D_800D2145[slot].value=(s8)(slot*3-p);D_800D2146[slot].value=(u8)(slot*5+p);
}
for(slot=0;slot<255;slot++){
u32 expected[6]={patterns[p]^(slot*0x10203u),patterns[p]^(slot*0x20304u)^0xA5A50000u,(u32)(s8)(slot+p),(u32)(s8)(slot*3-p),(u8)(slot*5+p),patterns[p]^(slot*0x30405u)^0x5A5A0000u};
for(field=1;field<7;field++){u32 got=(u32)(typed?call((s16)slot,(s16)field):func_150859AC((s16)slot,(s16)field));if(got!=expected[field-1])quit(1);}
}}
for(byteValue=0;byteValue<256;byteValue++)for(slot=0;slot<255;slot++){
D_800D2144[slot].value=(s8)byteValue;D_800D2145[slot].value=(s8)(byteValue^0x80u);D_800D2146[slot].value=(u8)byteValue;
for(field=3;field<=5;field++){u32 expected=field==3?(u32)(s8)byteValue:field==4?(u32)(s8)(byteValue^0x80u):byteValue;
u32 got=(u32)(typed?call((s16)slot,(s16)field):func_150859AC((s16)slot,(s16)field));if(got!=expected)quit(1);}}
for(slot=255;slot<32768;slot++)for(field=0;field<12;field++)if((typed?call((s16)slot,fields[field]):func_150859AC((s16)slot,fields[field]))!=0)quit(1);
}quit(0);}
'''

NATIVE_EXECUTIONS=(65536*32+6*255*6+256*255*3+(32768-255)*12)*2*3
