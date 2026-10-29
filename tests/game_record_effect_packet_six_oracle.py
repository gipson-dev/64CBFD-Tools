"""Record effect packet: captured bytes, expiration dispatcher, aliases, real helpers and image."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_effect_packet_six_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];RECORD,EFFECT,UPDATE,FREE=0x20000,0x50000,0x151B8000,0x1516972C
FLOATS=(0,0x80000000,0x3F800000,0xC0200000,1,0x80000001,0x7F7FFFFF,0x7FC12345)
VALUES=(0,1,127,128,255,256,32767,32768,65535,0x7FFFFFFF,0x80000000,0xFFFFFFFF)
@dataclass(frozen=True)
class Case:
    pattern:int=0
    byte:int=37
    word:int=0x8000
    allocated:bool=True
    mutation:int=0
    destination:int=0
    input_layout:int=0
    phase:int=0
    flags:int=1
    age:int=-1
    update:int=-1
    death:int=4
    ticks:int=1
    update_mode:int=0

def source_pointer(c,entered=None):
    sp=STACK+c.phase if entered is None else entered
    return(RECORD,sp-80,sp-76,sp)[c.input_layout]
def pointer(c,entered=None,record=None):
    sp=STACK+c.phase if entered is None else entered;record=source_pointer(c,sp)if record is None else record
    return(EFFECT,sp-80,sp-76,record)[c.destination]if c.allocated else 0

def fixture(c):
    sp=STACK+c.phase;m={sp+i:(i*17+0xA5)&255 for i in range(-1024,512)}
    for base,length in((RECORD-16,112),(EFFECT-16,192)):m.update({base+i:(i*13+0x59)&255 for i in range(length)})
    record=source_pointer(c)
    for i in range(80):m[record+i]=(i*13+0x59)&255
    m[record+1]=255-c.byte;m[record+12]=c.byte;m[record+13]=c.flags;put(m,record+14,c.age&65535,2);m[record+16]=c.death&255;m[record+17]=c.update&255
    for i in range(3):put(m,record+40+4*i,FLOATS[(c.pattern+i)%8])
    put(m,record+52,FLOATS[(c.pattern+3)%8]);put(m,record+56,FLOATS[(c.pattern+4)%8]);put(m,record+60,c.word&65535,2)
    for i in range(6):put(m,record+62+i*2,(c.word*(2*i+1)^(i*0x5555))&65535,2)
    for i in range(10):put(m,source.TABLE+4*i,source.ENTRY if i==4 else 0)
    for i in range(10):put(m,source.UPDATE_TABLE+4*i,UPDATE if i==2 else 0)
    put(m,source.TICKS,c.ticks&0xFFFFFFFF);return m

def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}
def half(v):return(((v&65535)^32768)-32768)&0xFFFFFFFF
def signed_half(m,address):return((read(m,address,2)^32768)-32768)
def mutate_source(m,record):
    for off,v in((40,0x42040000),(44,0xC2300000),(48,0x425C0000),(52,0x3F000000),(56,0xBF000000)):put(m,record+off,v)
    put(m,record+60,0x1234,2)
    for i,v in enumerate((9,-10,11,-12,13,-14)):put(m,record+62+2*i,v&65535,2)
    m[record+1]=0x6B;m[record+12]=0xA7

def change(m,c,entered,record):
    if c.mutation&1:mutate_source(m,record)
    if c.mutation&2:
        for i in(0,7,16,35):m[entered-40+i]=(i*3+0x19)&255
    if c.mutation&4:put(m,record+14,2,2)
def clobber(m,sp):
    for i in range(4):put(m,sp+4*i,0xB5000000+i)
def update_effect(m,c,record):
    if c.update_mode:
        put(m,record+14,1 if c.update_mode==1 else 0xFFFF,2)
        if c.update_mode==2:mutate_source(m,record)

def capture_and_spawn(initial,c,entered=None,record=None):
    sp=STACK+c.phase if entered is None else entered;record=source_pointer(c,sp)if record is None else record;m=dict(initial);packet=sp-40;frame=sp-96
    for i in range(3):put(m,packet+4*i,read(m,record+40+4*i))
    first=read(m,record+52);put(m,packet+16,0);put(m,packet+12,first);put(m,packet+20,read(m,record+56))
    for i in range(6):put(m,packet+24+2*i,read(m,record+62+2*i,2),2)
    life=half(read(m,record+60,2));put(m,frame+20,36);put(m,frame+16,0);slot=m[record+12];put(m,frame+24,slot);context=m[record+1];put(m,frame+28,context)
    calls=[(source.FACTORY,(life,0xFFFFFFFF,4,1,0,36,slot,context))];snapshot=bytes(m[packet+i]for i in range(36));change(m,c,sp,record);clobber(m,frame);copied=None
    if c.allocated:
        dst=pointer(c,sp,record)+40;calls.append((source.COPY,(dst,packet,36)));copied=bytes(m[packet+i]for i in range(36))
        for i in range(36):m[dst+i]=m[packet+i]
    return m,calls,snapshot,copied

def parent_reference(initial,c):
    m=dict(initial);calls=[];record=RECORD
    if m[record+13]&1:put(m,record+14,(signed_half(m,record+14)-read(m,source.TICKS))&65535,2)
    if m[record+17]!=255:calls.append((UPDATE,(record,)));update_effect(m,c,record)
    if signed_half(m,record+14)<0 and m[record+16]!=255:
        calls.append((source.ENTRY,(record,)));m,more,_,_=capture_and_spawn(m,c,STACK+c.phase-24,record);calls+=more
    if signed_half(m,record+14)<0:calls.append((FREE,(record,)));put(m,record+4,0xDEAD0001)
    return public(m),calls

class PacketOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,factory=source.FACTORY,copy=source.COPY,connected=None):
        self.entered=STACK+c.phase;self.record=source_pointer(c,self.entered)
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(self.record,),connected=connected)
        self.case,self.factory,self.copy,self.trace=c,factory,copy,[];self.snapshot,self.copied,self.factory_packet=None,None,None
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        sizes={source.ENTRY:1,self.factory:8,self.copy:3,source.CONSTRUCTOR:9,source.ALLOC:6,source.ZERO:2,source.HEAP:5,source.REGISTER:2,UPDATE:1,FREE:1};assert target in sizes,hex(target);args=self.arguments(sizes[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==source.ENTRY:self.entered=self.r[29];self.record=args[0]
        if target==self.factory:self.factory_packet=args;self.snapshot=bytes(self.memory[self.entered-40+i]for i in range(36))
        if target==self.copy:self.copied=bytes(self.memory[args[1]+i]for i in range(args[2]))
    def hook(self,target):
        c=self.case;a=self.calls[-1][1]
        if target in(self.factory,source.HEAP,source.ALLOC):change(self.memory,c,self.entered,self.record);result=pointer(c,self.entered,self.record)
        elif target==self.copy:
            for i in range(a[2]):self.put(a[0]+i,self.get(a[1]+i,1),1)
            result=a[0]
        elif target==source.ZERO:
            for i in range(a[1]):self.put(a[0]+i,0,1)
            result=0
        elif target==UPDATE:update_effect(self.memory,c,a[0]);result=0xDEAD0002
        elif target==FREE:put(self.memory,a[0]+4,0xDEAD0001);result=0xDEAD0001
        else:assert target==source.REGISTER;result=0xB5000001
        clobber(self.memory,self.r[29])
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result;self.hi,self.lo=0xA5000010,0xA5000011

def controls():
    b=source.SELECTED;begin=b.index('    packet.position =');end=b.index('    effect =');capture=b[begin:end];late=b[:begin]+b[end:];late=late.replace('    if (effect != NULL) {','    if (effect != NULL) {'+chr(10)+capture)
    result = dict(wrong_lifetime=b.replace('*(s16 *)(bytes + 0x3C)','(u8)*(s16 *)(bytes + 0x3C)'),wrong_kind=b.replace(' -1, 4, 1, 0,',' -1, 2, 1, 0,'),wrong_size=b.replace('sizeof(packet)','sizeof(packet) - 1'),wrong_slot=b.replace('bytes[0xC]','bytes[0xC] ^ 1U'),wrong_context=b.replace('bytes[1]','bytes[1] ^ 1U'),nonzero_phase=b.replace('packet.phase = 0.0f','packet.phase = 1.0f'),wrong_value=b.replace('packet.sourceValueB = *(f32 *)(bytes + 0x38)','packet.sourceValueB = *(f32 *)(bytes + 0x34)'),wrong_parameter=b.replace('packet.parameters[5] = *(s16 *)(bytes + 0x48)','packet.parameters[5] = 0'),wrong_destination=b.replace('(u8 *)effect + 0x28','(u8 *)effect + 0x24'),late_capture=late)
    assert all(v != b for v in result.values())
    return result

def native_harness():
    t=source.HEADERS+source.DECLARATIONS+r'''
typedef struct{EffectPacketPosition1CC440 position;f32 sourceValueA,sourceValueB;s16 lifetime;s16 parameters[6];}SourceState;
typedef struct{struct260 header;u8 gap24[4];SourceState state;}SourceRecord;
typedef char ABI[(sizeof(void*)==4&&sizeof(RecordEffectPacketSix1CC440)==36&&__builtin_offsetof(RecordEffectPacketSix1CC440,parameters)==24&&sizeof(struct260)==36&&__builtin_offsetof(SourceRecord,state)==40&&__builtin_offsetof(SourceState,parameters)==22)?1:-1];
static struct{u32 pre[4];SourceRecord record;u32 post[4];}actualInput,expectedInput;
static union{u64 align;u8 data[160];}actualOutput,expectedOutput;
static RecordEffectPacketSix1CC440 expectedPacket,captured;static u32 allocated,mutation,layout,calls,bad,wantedSlot,wantedContext;static s16 wantedLife;
static f32 real(u32 v){union{f32 f;u32 u;}x;x.u=v;return x.f;}
static void bytes(void*d,const void*s,u32 n){volatile u8*a=d;const u8*b=s;u32 i;for(i=0;i<n;i++)a[i]=b[i];}
struct260*func_151491F4(s16 life,s8 death,s8 update,u8 flags,u8 selector,s32 size,u8 slot,s32 context){
 if(calls++||life!=wantedLife||death!=-1||update!=4||flags!=1||selector||size!=36||slot!=wantedSlot||(u32)context!=wantedContext)bad=1;
 if(mutation){actualInput.record.state.position.x=33.0f;actualInput.record.state.position.y=-44.0f;actualInput.record.state.position.z=55.0f;actualInput.record.state.sourceValueA=0.5f;actualInput.record.state.sourceValueB=-0.5f;actualInput.record.state.lifetime=0x1234;for(u32 i=0;i<6;i++)actualInput.record.state.parameters[i]=(s16)(i%2?-10-(s32)i+1:9+(s32)i);((u8*)&actualInput.record)[1]=0x6B;((u8*)&actualInput.record)[12]=0xA7;}
 return allocated?(struct260*)(actualOutput.data+layout*4):0;
}
void*memcpy(void*d,const void*s,u32 n){if(calls++!=1||!allocated||d!=actualOutput.data+layout*4+40||n!=36){bad=1;return d;}bytes(&captured,s,n);bytes(d,s,n);return d;}
'''
    for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('void '+source.FUNCTION,'static void '+name)+chr(10)
    t+=r'''
typedef void(*Spawn)(struct260*);
static int check(Spawn fn){const u32 fp[]={0,0x80000000,0x3F800000,0xC0200000,1,0x80000001,0x7F7FFFFF,0x7FC12345};u32 value,a,change,offset,i,p;u8 *ai=(u8*)&actualInput,*ei=(u8*)&expectedInput;
 for(value=0;value<65536;value++)for(a=0;a<2;a++)for(change=0;change<2;change++)for(offset=0;offset<2;offset++){
  for(i=0;i<sizeof(actualInput);i++)ai[i]=ei[i]=(u8)(i*13+value);for(i=0;i<160;i++)actualOutput.data[i]=expectedOutput.data[i]=(u8)(i*17+value);
  p=value&7;actualInput.record.state.position.x=real(fp[p]);actualInput.record.state.position.y=real(fp[(p+1)&7]);actualInput.record.state.position.z=real(fp[(p+2)&7]);actualInput.record.state.sourceValueA=real(fp[(p+3)&7]);actualInput.record.state.sourceValueB=real(fp[(p+4)&7]);actualInput.record.state.lifetime=(s16)value;
  for(i=0;i<6;i++)actualInput.record.state.parameters[i]=(s16)((value*(2*i+1))^(i*0x5555));wantedLife=(s16)value;wantedSlot=value&255;wantedContext=value>>8;((u8*)&actualInput.record)[12]=(u8)wantedSlot;((u8*)&actualInput.record)[1]=(u8)wantedContext;
  bytes(&expectedInput,&actualInput,sizeof(actualInput));expectedPacket.position=actualInput.record.state.position;expectedPacket.sourceValueA=actualInput.record.state.sourceValueA;expectedPacket.phase=0.0f;expectedPacket.sourceValueB=actualInput.record.state.sourceValueB;for(i=0;i<6;i++)expectedPacket.parameters[i]=actualInput.record.state.parameters[i];
  if(change){expectedInput.record.state.position.x=33.0f;expectedInput.record.state.position.y=-44.0f;expectedInput.record.state.position.z=55.0f;expectedInput.record.state.sourceValueA=0.5f;expectedInput.record.state.sourceValueB=-0.5f;expectedInput.record.state.lifetime=0x1234;expectedInput.record.state.parameters[0]=9;expectedInput.record.state.parameters[1]=-10;expectedInput.record.state.parameters[2]=11;expectedInput.record.state.parameters[3]=-12;expectedInput.record.state.parameters[4]=13;expectedInput.record.state.parameters[5]=-14;((u8*)&expectedInput.record)[1]=0x6B;((u8*)&expectedInput.record)[12]=0xA7;}
  if(a)bytes(expectedOutput.data+offset*4+40,&expectedPacket,36);allocated=a;mutation=change;layout=offset;calls=bad=0;fn(&actualInput.record.header);
  if(bad||calls!=(a?2:1))return 1;for(i=0;i<sizeof(actualInput);i++)if(ai[i]!=ei[i])return 1;for(i=0;i<160;i++)if(actualOutput.data[i]!=expectedOutput.data[i])return 1;if(a)for(i=0;i<36;i++)if(((u8*)&captured)[i]!=((u8*)&expectedPacket)[i])return 1;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
    for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';'+chr(10)
    return t+'return 0;}'+chr(10)+START
