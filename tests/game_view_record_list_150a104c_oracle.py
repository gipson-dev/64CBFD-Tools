"""Ordered view/list effects and the seven-field temporary collision actor."""
import itertools
from dataclasses import dataclass
from tools.experiments import game_view_record_list_150a104c_match as source
from tools.tests.game_resource_texture_callback_1513bbfc_oracle import Oracle as FloatOracle,rd,wr,state,u32,STACK
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating

VIEW,LIST,RECORDS,ALT,ACTOR,MARK=0x120000,0x130000,0x100000,0x110000,0x140000,0x150000
DEFAULT,COLLISION,COUNT_PTR,LIST_PTR=0x8009F5AC,0x150A1DA0,0x800D3274,0x800D3270
FIELDS=(0x14,0x18,0x1C,0x180,0x2C,0x30,0x34)
SOURCE_FIELDS=(0x2F8,0x2FC,0x300,0x2FC,0x304,0x308,0x30C)
HALVES=((-32768,-32768),(32767,32767),(-32768,32767),(-123,456),(0,-1),(12,34))
half=lambda v:((v&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
    count:int=6
    kind:int=0
    flags:int=4
    rejected:int=0
    nulls:int=0
    pattern:int=1
    mutation:int=0
    alias:int=0
    phase:int=0
    special:int=0
    initial_flags:int=0xABCFFFFF
    default:int=0xC61C4000

def query(c,home=None):return u32((STACK+c.phase if home is None else home)-812)
def view(c):return VIEW if c.alias!=3 else query(c)-0x2F8+0x14
def listing(c):return query(c)+0x240 if c.alias==1 else view(c)+0x2F8 if c.alias==4 else LIST
def records(c):return query(c)+0x40 if c.alias==2 else view(c)+0x70 if c.alias==5 else RECORDS
def coordinates(c):
    return (0x80000000,0x7F800000,0xFF800000,0x7FC12345,1,0xBF800000)if c.special==1 else (0xC7000000,0x47000000,0,0x3F000000,0x3F800000,0xBF000000)if c.special==2 else tuple(bits(v)for v in(1.25,-2.5,3.75,10.0,20.0,30.0))

def fixture(c=Case()):
    home=STACK+c.phase;m={u32(home+i):(i*17+165)&255 for i in range(-2048,2048)}
    for p,n in((VIEW,2464),(LIST,64),(RECORDS,312),(ALT,312),(ACTOR,812),(MARK,16),(DEFAULT-16,64),(COUNT_PTR-8,32),(0,64)):
        for i in range(n):m[u32(p+i)]=(i*29+90)&255
    v=view(c)
    for i,value in enumerate(coordinates(c)):wr(m,v+0x2F8+4*i,value)
    wr(m,v+0x84,c.initial_flags);wr(m,v+0x364,bits(123.5));wr(m,DEFAULT,c.default)
    for base in(records(c),ALT):
        for i in range(6):
            p=base+52*i;a,b=HALVES[i]if base==records(c)else(i*100-250,-100+i*5)
            wr(m,p+2,a,2);wr(m,p+8,b,2);wr(m,p+0x15,c.flags if base==records(c)else 4+(i&3),1)
            wr(m,p+0x17,((0,2,6,9,2,0)[i]if c.pattern else c.kind)if base==records(c)else(6 if i%2==0 else 2),1)
    for i in range(16):wr(m,listing(c)+4*i,records(c)+52*i if i<6 and not(c.nulls>>i&1)else 0)
    wr(m,0x15,4,1);wr(m,0x17,2,1);wr(m,2,123,2);wr(m,8,-23,2)
    wr(m,COUNT_PTR,c.count);wr(m,LIST_PTR,listing(c));return m

def initialize(m,c,home):
    q=query(c,home);v=view(c)
    for off,src in zip(FIELDS,SOURCE_FIELDS):
        wr(m,q+off,rd(m,q+0x18)if off==0x180 else rd(m,v+src))
    constant=rd(m,DEFAULT);flags=rd(m,v+0x84)
    wr(m,v+0x364,constant);wr(m,v+0x84,flags&~0x40000)

def public(m,c):
    home=STACK+c.phase;return {p:v for p,v in m.items()if not home-2048<=p<home+2048}
def observable(m,c):return public(m,c),rd(m,view(c)+0x84),rd(m,view(c)+0x364)

def effect(m,c,args,index,ordinal,home):
    for i,value in enumerate((*args,index)):wr(m,MARK+4*i,value)
    if ordinal!=1:return
    mask=c.mutation;v=view(c)
    if mask&1:wr(m,listing(c)+4*index,ALT+52*index)
    if mask&2 and index+1<6:wr(m,listing(c)+4*(index+1),ALT+52*(index+1))
    if mask&4:wr(m,args[0]+0x14,bits(10.0))
    if mask&8:
        for i in range(6):wr(m,v+0x2F8+4*i,bits(float(90+i)))
    if mask&16:wr(m,v+0x84,0xA5A4000F)
    if mask&32:wr(m,DEFAULT,bits(222.0))
    if mask&64:
        p=rd(m,listing(c)+4*index);wr(m,p+0x15,7,1);wr(m,p+0x17,2,1);wr(m,p+2,-111,2);wr(m,p+8,23,2)
    if mask&128:
        for i in range(3):wr(m,home+4*i,0xBEEF0000+i)
    if mask&256:wr(m,v+0x364,bits(-77.5))
    if mask&512:wr(m,args[0]+0x180,bits(44.0))
    if mask&1024:wr(m,listing(c)+4*index,0)

def reference(initial,c=Case(),home=None):
    m=dict(initial);home=STACK+c.phase if home is None else home;initialize(m,c,home);calls=[];observations=[]
    assert 0<=c.count<=6
    for i in range(c.count):
        p=rd(m,listing(c)+4*i)
        if not p:continue
        args=(query(c,home),p,0);calls.append((COLLISION,args));observations.append(bytes(m[u32(args[0]+j)]for j in range(812)))
        result=int(bool(c.rejected>>i&1));effect(m,c,args,i,len(calls),home)
        if result:continue
        p=rd(m,listing(c)+4*i)
        if rd(m,p+0x15,1)>>2!=1:continue
        kind=rd(m,p+0x17,1);v=view(c)
        if kind==2:wr(m,v+0x364,bits(float(half(rd(m,p+8,2))+half(rd(m,p+2,2)))))
        elif kind==0:wr(m,v+0x84,rd(m,v+0x84)|0x40000)
        elif kind==6:wr(m,v+0x84,rd(m,v+0x84)&~0x40000)
    return observable(m,c),calls,observations,m

class Oracle(FloatOracle):
    def __init__(self,words,memory,c=Case(),entry=None,connected=None,arguments=None):
        self.target_home=STACK+c.phase;self.query_observations=[]
        FactoryOracle.__init__(self,words,memory,c,entry=source.ENTRY if entry is None else entry,connected=connected,
            arguments=(view(c),listing(c),u32(c.count))if arguments is None else arguments)
    def record_call(self,target):
        assert target in(source.ENTRY,COLLISION),hex(target)
        args=tuple(map(u32,self.arguments(3)));self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==source.ENTRY:self.target_home=self.r[29]
    def hook(self,target):
        assert target==COLLISION;args=self.calls[-1][1];c=self.case
        bases=(records(c),ALT);matches=[(args[1]-b)//52 for b in bases if 0<=u32(args[1]-b)<312 and (args[1]-b)%52==0]
        assert len(matches)==1,(args,c);index=matches[0]
        assert args==(query(c,self.target_home),args[1],0)
        self.query_observations.append(bytes(self.memory[u32(args[0]+i)]for i in range(812)))
        effect(self.memory,c,args,index,len(self.query_observations),self.target_home)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xFFFFFFFF if c.rejected>>index&1 else 0

def cases():
    for count,flags,kind,rejected,nulls,phase in itertools.product((0,1,6),(0,4,7,8,255),(0,2,6,9),(0,63),(0,21),(0,8)):
        yield Case(count=count,flags=flags,kind=kind,rejected=rejected,nulls=nulls,phase=phase,pattern=0)
    for mutation,rejected,phase in itertools.product(range(128),(0,21),(0,8)):
        yield Case(mutation=mutation,rejected=rejected,phase=phase)
    for mutation in(128,132,256,272,512,516,1024,1280):yield Case(mutation=mutation)
    # Later records can hide a stale first-slot decision; isolate that decision.
    for mutation in(1,16,32,64,65,256):yield Case(count=1,mutation=mutation)
    for alias,phase in itertools.product(range(1,6),(0,8)):yield Case(alias=alias,phase=phase)
    for special,kind in itertools.product((1,2),(0,2,6,9)):yield Case(special=special,pattern=0,kind=kind)
    for flags in(0,0x40000,0xFFFFFFFF):yield Case(initial_flags=flags)

def native_cases():return[c for c in cases()if not c.phase and not c.alias and not c.mutation&(128|1024)]

def native_harness(body=None):
    body=source.SELECTED if body is None else body
    prefix=source.source_states((source.ROOT/source.SOURCE).read_text())[1].split('s32 func_150A09D0()',1)[0];rows=[]
    for c in native_cases():
        expected,calls,obs,_=reference(fixture(c),c)
        rows.append('{%d,%d,%d,%d,%d,%d,%d,0x%XU,0x%XU,{%s},%d,0x%XU,0x%XU}'%(c.count,c.kind,c.flags,c.rejected,c.nulls,c.pattern,c.mutation,c.initial_flags,c.default,','.join('0x%XU'%v for v in coordinates(c)),len(calls),expected[1],expected[2]))
    return prefix+'''
_Static_assert(sizeof(void*)==4&&sizeof(struct127)==812&&sizeof(struct108)==2464&&sizeof(GeneratedCDE80Record)==52,"SDK O32 layout");
_Static_assert(__builtin_offsetof(GeneratedCDE80Record,heightOffset)==8&&__builtin_offsetof(GeneratedCDE80Record,flags)==21,"Record fields");
static GeneratedCDE80Record records[6],alternate[6],*list[6];static struct108 viewer;
f32 D_8009F5AC;static u32 mutation,rejected,calls,failed,expectedQuery[7];
static u32 asWord(f32 value){union{f32 f;u32 u;}v;v.f=value;return v.u;}
static f32 asFloat(u32 value){union{f32 f;u32 u;}v;v.u=value;return v.f;}
s32 func_150A1DA0(struct127*q,s32 descriptor,s32 mode){
 GeneratedCDE80Record*p=(GeneratedCDE80Record*)(u32)descriptor;u32 index=(u32)p>=(u32)alternate&&(u32)p<(u32)(alternate+6)?((u32)p-(u32)alternate)/52:((u32)p-(u32)records)/52;
 u32 seen[7]={asWord(q->x_position),asWord(q->y_position),asWord(q->z_position),asWord(q->unk180),asWord(q->old_x_position),asWord(q->old_y_position),asWord(q->old_z_position)};unsigned i;int result;
 if(index>=6||mode||calls>=6){failed=1;return 1;}for(i=0;i<7;i++)if(seen[i]!=expectedQuery[i])failed=1;
 result=(rejected>>index&1)?-1:0;calls++;
 if(calls==1){
  if(mutation&1)list[index]=&alternate[index];
  if((mutation&2)&&index+1<6)list[index+1]=&alternate[index+1];
  if(mutation&4){q->x_position=10.f;expectedQuery[0]=asWord(10.f);}
  if(mutation&8){viewer.unk2F8=90.f;viewer.unk2FC=91.f;viewer.unk300=92.f;viewer.unk304=93.f;viewer.unk308=94.f;viewer.unk30C=95.f;}
  if(mutation&16)viewer.unk84=(s32)0xA5A4000FU;
  if(mutation&32)D_8009F5AC=222.f;
  if(mutation&64){p=list[index];p->flags=7;p->field17=2;p->origin1=-111;p->heightOffset=23;}
  if(mutation&256)viewer.unk364=-77.5f;
  if(mutation&512){q->unk180=44.f;expectedQuery[3]=asWord(44.f);}
 }
 return result;
}
'''+body+'''
typedef void(*Updater)(struct108*,GeneratedCDE80Record**,s32);static Updater update=func_150A104C;
struct Row{u32 count,kind,flags,rejected,nulls,pattern,mutation,initialFlags,defaultBits,coords[6],expectedCalls,expectedFlags,expectedHeight;};
static const struct Row rows[]={'''+','.join(rows)+'''};
static const s16 halves[6][2]={{-32768,-32768},{32767,32767},{-32768,32767},{-123,456},{0,-1},{12,34}};
static int check(void){unsigned i,j;for(i=0;i<sizeof rows/sizeof rows[0];i++){
 const struct Row*r=&rows[i];static const u8 kinds[6]={0,2,6,9,2,0};mutation=r->mutation;rejected=r->rejected;calls=failed=0;
 viewer.unk84=(s32)r->initialFlags;viewer.unk364=123.5f;D_8009F5AC=asFloat(r->defaultBits);
 viewer.unk2F8=asFloat(r->coords[0]);viewer.unk2FC=asFloat(r->coords[1]);viewer.unk300=asFloat(r->coords[2]);viewer.unk304=asFloat(r->coords[3]);viewer.unk308=asFloat(r->coords[4]);viewer.unk30C=asFloat(r->coords[5]);
 expectedQuery[0]=r->coords[0];expectedQuery[1]=r->coords[1];expectedQuery[2]=r->coords[2];expectedQuery[3]=r->coords[1];expectedQuery[4]=r->coords[3];expectedQuery[5]=r->coords[4];expectedQuery[6]=r->coords[5];
 for(j=0;j<6;j++){records[j].origin1=halves[j][0];records[j].heightOffset=halves[j][1];records[j].flags=(u8)r->flags;records[j].field17=(u8)(r->pattern?kinds[j]:r->kind);alternate[j].origin1=(s16)((int)j*100-250);alternate[j].heightOffset=(s16)(-100+(int)j*5);alternate[j].flags=(u8)(4+(j&3));alternate[j].field17=(u8)(j%2?2:6);list[j]=(r->nulls>>j&1)?0:&records[j];}
 update(&viewer,list,(s32)r->count);
 if(failed||calls!=r->expectedCalls||(u32)viewer.unk84!=r->expectedFlags||asWord(viewer.unk364)!=r->expectedHeight)return 1;
 if(asWord(D_8009F5AC)!=(calls&&(mutation&32)?asWord(222.f):r->defaultBits))return 2;
}return 0;}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
