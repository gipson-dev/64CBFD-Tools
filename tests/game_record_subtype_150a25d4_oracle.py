"""Independent subtype dispatch model and emitted-word oracle."""
import itertools,struct
from dataclasses import dataclass
from tools.experiments import game_record_subtype_150a25d4_match as source
from tools.tests.game_resource_texture_callback_1513bbfc_oracle import Oracle as FloatOracle,rd,wr,state,u32,STACK
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import signed
RECORD,ACTOR,TABLE,COUNTER,DELTA,MARK=0x30000,0x50000,0x800D9EB8,0x800D3090,0x800BE9E4,0x70000
JTBL,RAW_TABLE=0x8009F648,0x810000
RANDOM,FORWARD,AUDIO,OWNER,ACTION,HEIGHT=0x150E7290,0x150E68B0,0x10010344,0x151C8674,0x1515F270,0x151CE51C
RAW_OFFSETS=(412,64,100,160,412,412,200,412,360,380,400)
OFFSETS=(420,64,100,160,420,420,200,420,368,388,408)
SIZES={RANDOM:3,FORWARD:4,AUDIO:5,OWNER:2,ACTION:2,HEIGHT:2}

@dataclass(frozen=True)
class Case:
    kind:int=6
    selector:int=1
    high:int=0
    low:int=0
    padding:int=0xFEE1DEAD
    counter:int=0
    delta:int=1
    value:int=1441
    mutation:int=0
    new_value:int=241
    phase:int=0
    alias:int=0
    null_actor:int=0

def record(c):return TABLE+3*c.selector-(31 if c.alias==1 else 35)if c.alias in(1,2)else STACK+c.phase-16 if c.alias==4 else RECORD
def actor(c):return 0 if c.null_actor else COUNTER-0xB2 if c.alias==3 else ACTOR

def fixture(c=Case()):
    home=STACK+c.phase;m={u32(home+i):(i*17+165)&255 for i in range(-1024,512)}
    for base,n in((RECORD-64,192),(ACTOR,812),(TABLE-64,128),(COUNTER-4,12),(DELTA-4,12),(MARK,32),(JTBL,44),(RAW_TABLE,48)):
        m.update({u32(base+i):(i*29+90)&255 for i in range(n)})
    r=record(c)
    for i in range(52):m.setdefault(u32(r+i),(i*29+90)&255)
    wr(m,r+0x17,c.kind,1);wr(m,r+0x18,0x123456AB);wr(m,r+0x1C,0xABCDEF57);wr(m,r+0x20,0xFEDC8123)
    wr(m,COUNTER,c.counter,1);wr(m,DELTA,c.delta)
    wr(m,ACTOR+0xB2,c.value,2)
    if actor(c) and actor(c)!=ACTOR:wr(m,actor(c)+0xB2,c.value,2)
    wr(m,home+16,c.high);wr(m,home+20,c.low)
    for base,offsets in((JTBL,OFFSETS),(RAW_TABLE,RAW_OFFSETS)):
        for i,off in enumerate(offsets):wr(m,base+i*4,source.ENTRY+off)
    return m

def public(m,c):
    home=STACK+c.phase;return{p:v for p,v in m.items()if not home-1024<=p<home+512}

def observable(m,c):
    return public(m,c),tuple(rd(m,record(c)+off)for off in(0x18,0x1C,0x20))

def effect(m,c,target,home):
    wr(m,MARK,target)
    if c.mutation&1:wr(m,COUNTER,255,1)
    if c.mutation&2:wr(m,DELTA,2)
    if c.mutation&4 and actor(c):wr(m,actor(c)+0xB2,c.new_value,2)
    if c.mutation&8:
        wr(m,record(c)+0x17,0xE5,1);wr(m,record(c)+0x18,0x13579BDF);wr(m,record(c)+0x1C,0x2468ACED);wr(m,record(c)+0x20,0x87654321)
    if c.mutation&16:
        wr(m,home+8,0xABCDFFFF);wr(m,home+16,0xFEEDFACE);wr(m,home+20,0xDEADBEEF)

def logical(target,args):
    a=list(map(u32,args))
    if target==RANDOM:a[0]&=255;a[1]&=255
    if target==FORWARD:a[3]&=255
    return tuple(a)

def reference(initial,c=Case(),home=None):
    m=dict(initial);home=STACK+c.phase if home is None else home;calls=[];r,a=record(c),actor(c)
    wr(m,home+8,c.selector)
    def call(target,args):
        args=tuple(map(u32,args));calls.append((target,logical(target,args)))
        if target==AUDIO:wr(m,home-40+16,500)
        effect(m,c,target,home)
    kind=rd(m,r+0x17,1)
    if kind==1:
        if signed(u32(c.selector))!=255:call(RANDOM,(c.selector,255,0))
    elif kind==2:
        if signed(u32(c.selector))!=255:
            p=u32(TABLE+signed(u32(c.selector))*3)
            for i,off in enumerate((0x18,0x1C,0x20)):wr(m,p+i,rd(m,r+off),1)
    elif kind==3:
        if signed(u32(c.selector))!=255:call(FORWARD,(a,c.selector,r,rd(m,r+0x1B,1)))
    elif kind==6:
        if not c.low&1:
            wr(m,COUNTER,30,1);call(AUDIO,(0x66F,a,24000,400,500))
        tick=(rd(m,COUNTER,1)+rd(m,DELTA))&255;wr(m,COUNTER,tick,1)
        if tick>=31:
            value=rd(m,a+0xB2,2);value=1200 if value>=1441 else 90 if value<=240 else value-240
            wr(m,a+0xB2,value,2);wr(m,COUNTER,0,1)
    elif kind in(8,9,10):call({8:OWNER,9:ACTION,10:HEIGHT}[kind],(a,r))
    return observable(m,c),calls,m

class Oracle(FloatOracle):
    def __init__(self,words,memory,c=Case(),entry=None,connected=None):
        self.physical_calls=[]
        FactoryOracle.__init__(self,words,memory,c,entry=source.ENTRY if entry is None else entry,connected=connected,arguments=(record(c),actor(c),u32(c.selector),c.padding))
    def record_call(self,target):
        size=6 if target==source.ENTRY else SIZES[target]
        args=tuple(map(u32,self.arguments(size)));self.physical_calls.append((target,args))
        a=logical(target,args)if target!=source.ENTRY else args
        self.calls.append((target,a));self.events.append(('CALL',target,a))
        if target==source.ENTRY:self.target_home=self.r[29]
    def hook(self,target):
        assert target in SIZES,hex(target)
        effect(self.memory,self.case,target,self.target_home)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF

def cases():
    for kind,selector,phase in itertools.product((*range(13),63,255),(0,1,3,255,-1,511),(0,8)):
        if kind==2 and selector not in(0,1,3,255):continue
        yield Case(kind=kind,selector=selector,phase=phase)
    for counter,delta,value,low in itertools.product((0,29,30,31,255),(-256,-31,-1,0,1,255,0x80000000,0x7FFFFFFF),(0,240,241,1440,1441,65535),(0,1)):
        yield Case(counter=counter,delta=delta,value=value,low=low)
    for kind,mutation in itertools.product((1,3,6,8,9,10),(1,2,3,4,7,8,16,31)):yield Case(kind=kind,mutation=mutation)
    for high,low,padding in itertools.product((0,1,0xFFFFFFFF),(0,1,0x80000000),(0,0xFFFFFFFF)):yield Case(high=high,low=low,padding=padding)
    for alias in(1,2,4):yield Case(kind=2,selector=1,alias=alias)
    yield Case(alias=3,low=1,delta=31)
    yield Case(kind=8,null_actor=1)

def native_cases():return[c for c in cases()if not c.phase and not c.alias]

def fold(values):
    h=2166136261
    for v in values:h=u32((h^u32(v))*16777619)
    return h

def memory_hash(m,c):
    values=[rd(m,COUNTER,1),rd(m,DELTA),rd(m,ACTOR+0xB2,2)]
    values.extend(rd(m,RECORD+off,n)for off,n in((0x17,1),(0x18,4),(0x1C,4),(0x20,4)))
    values.extend(rd(m,TABLE+i,1)for i in range(12));values.append(rd(m,MARK));return fold(values)

def call_hash(calls):
    values=[]
    for target,args in calls:
        a=list(args)
        if target in(OWNER,ACTION,HEIGHT):a=[2 if a[0]else 0,1]
        elif target==AUDIO:a[1]=2 if a[1]else 0
        elif target==FORWARD:a[0]=2 if a[0]else 0;a[2]=1
        values.extend((target,*a))
    return fold(values)

def native_harness(body=None):
    rows=[]
    for c in native_cases():
        _,calls,m=reference(fixture(c),c)
        values=[c.kind,c.selector,c.high,c.low,c.counter,c.delta,c.value,c.mutation,c.new_value,c.null_actor,memory_hash(m,c),call_hash(calls)]
        rows.append('{'+','.join('0x%08XU'%u32(v)for v in values)+'}')
    live=(source.ROOT/source.SOURCE).read_text();record_type=live[live.index('typedef struct {'):live.index('} GeneratedCDE80Record;')+len('} GeneratedCDE80Record;')]
    return '#include <ultra64.h>\n#include "structs.h"\n'+record_type+'\n'+source.DECLARATIONS+r'''
typedef char check_record[(sizeof(GeneratedCDE80Record)==52)?1:-1];
typedef char check_actor[(sizeof(struct127)==812)?1:-1];
typedef char check_pointer[(sizeof(void*)==4)?1:-1];
typedef char check_mask[(sizeof(u64)==8)?1:-1];
typedef struct {u32 kind,selector,high,low,counter,delta,value,mutation,newValue,nullActor,memory,calls;} Input;
static const Input inputs[]={'''+',\n'.join(rows)+r'''};
static GeneratedCDE80Record record;
static struct127 actor;
static const Input *current;
static u32 callDigest,marker;
u8 D_800D3090,D_800D9EB8[4][3];
s32 D_800BE9E4;
static u32 mix(u32 h,u32 v){return(h^v)*16777619U;}
static u32 pointerId(u32 p){return p==(u32)&actor?2:p==(u32)&record?1:p?3:0;}
static u32 service(u32 target,u32 a,u32 b,u32 c,u32 d,u32 e){
 callDigest=mix(callDigest,target);
 if(target==0x150E7290){callDigest=mix(callDigest,a&255);callDigest=mix(callDigest,b&255);callDigest=mix(callDigest,c);}
 else if(target==0x150E68B0){callDigest=mix(callDigest,pointerId(a));callDigest=mix(callDigest,b);callDigest=mix(callDigest,pointerId(c));callDigest=mix(callDigest,d&255);}
 else if(target==0x10010344){callDigest=mix(callDigest,a);callDigest=mix(callDigest,pointerId(b));callDigest=mix(callDigest,c);callDigest=mix(callDigest,d);callDigest=mix(callDigest,e);}
 else {callDigest=mix(callDigest,pointerId(a));callDigest=mix(callDigest,pointerId(b));}
 marker=target;
 if(current->mutation&1)D_800D3090=255;
 if(current->mutation&2)D_800BE9E4=2;
 if((current->mutation&4)&&!current->nullActor)actor.unkB2=current->newValue;
 if(current->mutation&8){record.field17=0xE5;record.field18=0x13579BDF;record.field1C=0x2468ACED;record.field20=0x87654321U;}
 return 0xDEADBEEF;
}
void func_150E7290(u8 a,u8 b,s32 c){(void)service(0x150E7290,a,b,c,0,0);}
s32 func_150E68B0(struct127*a,s32 b,GeneratedCDE80Record*c,u8 d){return service(0x150E68B0,(u32)a,b,(u32)c,d,0);}
s32 func_10010344(u16 a,void*b,s32 c,s16 d,u16 e){return service(0x10010344,a,(u32)b,c,d,e);}
void func_151C8674(s32 a,s32 b){(void)service(0x151C8674,a,b,0,0,0);}
void func_1515F270(u8*a,u8*b){(void)service(0x1515F270,(u32)a,(u32)b,0,0,0);}
void func_151CE51C(struct127*a,u8*b){(void)service(0x151CE51C,(u32)a,(u32)b,0,0,0);}
'''+(source.SELECTED if body is None else body)+r'''
static void reset(const Input*c){u32 i;u8*p;
 current=c;callDigest=2166136261U;marker=0x5A7794B1;
 p=(u8*)&record;for(i=0;i<52;i++)p[i]=((i+64)*29+90)&255;
 p=(u8*)&actor;for(i=0;i<812;i++)p[i]=(i*29+90)&255;
 p=(u8*)D_800D9EB8;for(i=0;i<12;i++)p[i]=((i+64)*29+90)&255;
 record.field17=c->kind;record.field18=0x123456AB;record.field1C=0xABCDEF57;record.field20=0xFEDC8123U;
 D_800D3090=c->counter;D_800BE9E4=c->delta;actor.unkB2=c->value;
}
static u32 memoryDigest(void){u32 h=2166136261U,i;
 h=mix(h,D_800D3090);h=mix(h,D_800BE9E4);h=mix(h,actor.unkB2);
 h=mix(h,record.field17);h=mix(h,record.field18);h=mix(h,record.field1C);h=mix(h,record.field20);
 for(i=0;i<12;i++)h=mix(h,((u8*)D_800D9EB8)[i]);h=mix(h,marker);return h;
}
void _start(void){u32 i,code=0;u64 mask;void(*typed)(GeneratedCDE80Record*,struct127*,s32,u64)=func_150A25D4;
 for(i=0;i<sizeof(inputs)/sizeof(inputs[0]);i++){
  reset(inputs+i);mask=((u64)inputs[i].high<<32)|inputs[i].low;
  typed(&record,inputs[i].nullActor?0:&actor,inputs[i].selector,mask);
  if(memoryDigest()!=inputs[i].memory||callDigest!=inputs[i].calls){code=i%200+1;break;}
 }
 __asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();
}
'''


def semantic_controls(body):
    b=body
    return dict(stub=b[:b.index('{')+1]+'\nreturn;\n}',wrong_kind=b.replace('case 6:', 'case 7:'),wrong_sentinel=b.replace('selector != 255','selector != 254'),
        high_mask=b.replace('(flags & 1)', '((flags >> 32) & 1)'),early_tick=b.replace('tick >= 31','tick >= 30'),big_boundary=b.replace('value >= 1441','value >= 1442'),
        small_boundary=b.replace('value <= 240','value < 240'),wrong_subtract=b.replace('value - 240','value - 239'),wrong_reset=b.replace('D_800D3090 = 0;','D_800D3090 = 1;'),
        cached_delta=b.replace('    s32 tick;', '    s32 tick;\n    s32 savedDelta = D_800BE9E4;').replace('(u32)D_800BE9E4','(u32)savedDelta'),
        cached_counter=b.replace('    s32 tick;', '    s32 tick;\n    u8 savedCounter = D_800D3090;').replace('D_800D3090 + (u32)D_800BE9E4','savedCounter + (u32)D_800BE9E4'),
        wrong_byte=b.replace('(u8)record->field18','(u8)((u32)record->field18 >> 8)'),
        swapped_pointers=b.replace('func_151C8674((s32)actor, (s32)record)', 'func_151C8674((s32)record, (s32)actor)'),
        wrong_delta_bits=b.replace('(u32)D_800BE9E4','((u32)D_800BE9E4 & 0x7F)'))
