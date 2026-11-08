"""Ordered position query, short-coordinate ABI and opaque collision effects."""
import itertools,struct
from dataclasses import dataclass,replace
from tools.experiments import game_position_subtype_150a3058_match as source
from tools.tests.game_resource_texture_callback_1513bbfc_oracle import Oracle as FloatOracle,rd,wr,state,u32,STACK,trunc
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating

LIMIT,POINTER,COLLISION=0x800D3094,0x800D3098,0x150A1DA0
RECORDS,ALT,MARK,ACTOR=0x40000,0x50000,0x60000,0x70000
FIELDS=(0x14,0x18,0x1C,0x2C,0x180,0x30,0x34)
half=lambda v:((v&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
    subtype:int=3
    coords:tuple=(0xABCD8000,0x12347FFF,0xFEDCFFFF)
    count:int=5
    pattern:int=0
    hit:int=3
    rejection:int=1
    mutation:int=0
    new_count:int=2
    alias:int=0
    phase:int=0


def query_address(c,home=None):return u32((STACK+c.phase if home is None else home)-816)
def record_base(c):
    return RECORDS if not c.alias else query_address(c)+0x40 if c.alias==1 else query_address(c)+0x16C if c.alias==2 else STACK+c.phase-16 if c.alias==3 else LIMIT-0x14

def fixture(c=Case()):
    home=STACK+c.phase;m={home+i:(i*17+165)&255 for i in range(-2048,1024)}
    for p,n in ((RECORDS,312),(ALT,312),(MARK,16),(LIMIT-64,512),(ACTOR,64)):
        for i in range(n):m[u32(p+i)]=(i*29+90)&255
    for base in (record_base(c),ALT):
        for i in range(6):
            at=u32(base+i*52);wr(m,at+0x14,int(c.pattern==0 and i==0),1)
            wr(m,at+0x15,8 if c.pattern==0 and i==1 else 12+(i&3),1)
            wr(m,at+0x17,c.subtype+(1 if c.pattern==0 and i==2 else 0),1)
    wr(m,LIMIT,c.count);wr(m,POINTER,record_base(c));return m


def payload(c):
    x,y,z=(bits(float(half(v)))for v in c.coords)
    return x,y,z,x,y,y,z


def initialize(m,c,home):
    for i,value in enumerate(c.coords,1):wr(m,home+i*4,value)
    for offset,value in zip(FIELDS,payload(c)):wr(m,query_address(c,home)+offset,value)


def public(m,c):
    home=STACK+c.phase;return {p:v for p,v in m.items() if not home-2048<=p<home+1024}


def effect(m,c,args,index,ordinal,home):
    for i,value in enumerate((*args,index)):wr(m,MARK+i*4,value)
    if ordinal!=1:return
    if c.mutation&1:wr(m,LIMIT,c.new_count)
    if c.mutation&2:wr(m,POINTER,ALT)
    if c.mutation&4:
        at=u32(rd(m,POINTER)+(index+1)*52+0x17);wr(m,at,(rd(m,at,1)^0x55),1)
    if c.mutation&8:
        for i in range(1,4):wr(m,home+i*4,0xBEEF0000+i)
    if c.mutation&16:wr(m,args[0]+0x14,bits(10.0))


def reference(initial,c=Case(),home=None):
    m=dict(initial);home=STACK+c.phase if home is None else home;initialize(m,c,home);calls=[];observations=[]
    if not rd(m,LIMIT):return public(m,c),calls,0,observations,m
    index=0
    while True:
        base=rd(m,POINTER);at=u32(base+index*52)
        if rd(m,at+0x14,1)==0 and rd(m,at+0x15,1)>>2==3 and rd(m,at+0x17,1)==u32(c.subtype):
            args=(query_address(c,home),at,0);calls.append((COLLISION,args));observations.append(bytes(m[u32(args[0]+i)]for i in range(812)))
            result=0 if index==c.hit else u32(c.rejection);effect(m,c,args,index,len(calls),home)
            if result==0:return public(m,c),calls,1,observations,m
        index+=1
        if not index<rd(m,LIMIT):break
        assert index<6,'Fixture exhausted before scan exit'
    return public(m,c),calls,0,observations,m


class Oracle(FloatOracle):
    def __init__(self,words,memory,c=Case(),entry=None,connected=None,arguments=None):
        self.target_home=STACK+c.phase;self.query_observations=[]
        FactoryOracle.__init__(self,words,memory,c,entry=source.ENTRY if entry is None else entry,connected=connected,
            arguments=tuple(map(u32,(c.subtype,*c.coords))) if arguments is None else arguments)
    def record_call(self,target):
        assert target in (source.ENTRY,COLLISION),hex(target)
        args=tuple(map(u32,self.arguments(4 if target==source.ENTRY else 3)));self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==source.ENTRY:self.target_home=self.r[29]
    def hook(self,target):
        assert target==COLLISION;args=self.calls[-1][1];c=self.case
        index=u32(args[1]-rd(self.memory,POINTER))//52
        assert args==(query_address(c,self.target_home),u32(rd(self.memory,POINTER)+index*52),0)
        self.query_observations.append(bytes(self.memory[u32(args[0]+i)]for i in range(812)))
        result=0 if index==c.hit else u32(c.rejection)
        effect(self.memory,c,args,index,len(self.query_observations),self.target_home)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=result


def cases():
    for subtype,count,pattern,hit,coords,phase in itertools.product((0,3,255,0x10003,-1),(0,1,4,5),(0,1),(-1,0,3,4),
        ((0,0,0),(0xABCD8000,0x12347FFF,0xFEDCFFFF)),(0,8)):
        yield Case(subtype=subtype,count=count,pattern=pattern,hit=hit,coords=coords,phase=phase)
    for mutation,hit,rejection,phase in itertools.product(range(32),(-1,4),(1,0xFFFFFFFF),(0,8)):
        yield Case(pattern=1,mutation=mutation,hit=hit,rejection=rejection,phase=phase)
    for alias,phase in itertools.product((1,2,3),(0,8)):
        yield Case(pattern=1,alias=alias,phase=phase)
    yield Case(count=1,pattern=1,hit=4,mutation=1,new_count=5)
    yield Case(count=0xFFFFFFFF,pattern=1,hit=0)
    yield Case(count=0x000C0001,pattern=1,subtype=1,hit=0,alias=4)


def native_cases():return [c for c in cases() if not c.alias and not c.phase and not c.mutation&8]


def native_harness(body=None):
    body=source.SELECTED if body is None else body;prefix=(source.ROOT/source.SOURCE).read_text().split('s32 func_150A09D0()',1)[0];rows=[]
    for c in native_cases():
        expected,calls,value,obs,_=reference(fixture(c),c);rows.append('{0x%XU,{%s},0x%XU,%d,%d,0x%XU,%d,%d,%d,%d}'%(u32(c.subtype),','.join('0x%XU'%u32(v)for v in c.coords),u32(c.count),c.pattern,c.hit,u32(c.rejection),c.mutation,c.new_count,len(calls),value))
    return prefix+'''
_Static_assert(sizeof(void*)==4&&sizeof(struct127)==812&&sizeof(GeneratedCDE80Record)==52,"SDK O32 layout");
static GeneratedCDE80Record records[6],alternate[6];GeneratedCDE80Record *D_800D3098;s32 D_800D3094;
static u32 subtype,hit,rejection,mutation,newCount,calls,failed;static s32 xyz[3];
static u32 seen[6][7],mark[4];
s32 func_150A1DA0(struct127*q,s32 descriptor,s32 mode){
 GeneratedCDE80Record *p=(GeneratedCDE80Record*)(u32)descriptor;u32 index=(u32)(p-D_800D3098);u32 *words=seen[calls];int result;
 if(index>=6||mode!=0||calls>=6){failed=1;return 1;}
 if(q->x_position!=(calls&&(mutation&16)?10.f:(f32)xyz[0])||q->y_position!=(f32)xyz[1]||q->z_position!=(f32)xyz[2]||q->old_x_position!=(f32)xyz[0]||q->unk180!=(f32)xyz[1]||q->old_y_position!=(f32)xyz[1]||q->old_z_position!=(f32)xyz[2])failed=1;
 words[0]=index;words[1]=(u32)q;mark[0]=(u32)q;mark[1]=(u32)p;mark[2]=(u32)mode;mark[3]=index;calls++;
 result=index==hit?0:(s32)rejection;
 if(calls==1){if(mutation&1)D_800D3094=(s32)newCount;if(mutation&2)D_800D3098=alternate;if(mutation&4)D_800D3098[index+1].field17^=0x55;if(mutation&16)q->x_position=10.f;}
 return result;
}
'''+body+'''
typedef s32(*Query)(s32,s16,s16,s16);static Query query=func_150A3058;
struct Row{u32 subtype,coords[3],count,pattern,hit,rejection,mutation,newCount,expectedCalls,expected;};
static const struct Row rows[]={'''+','.join(rows)+'''};
static int check(void){unsigned i,j,k;for(i=0;i<sizeof rows/sizeof rows[0];i++){
 const struct Row*r=&rows[i];u32 answer;subtype=r->subtype;hit=r->hit;rejection=r->rejection;mutation=r->mutation;newCount=r->newCount;calls=failed=0;
 for(j=0;j<3;j++)xyz[j]=(s16)r->coords[j];
 for(j=0;j<6;j++)for(k=0;k<2;k++){GeneratedCDE80Record *p=k?&alternate[j]:&records[j];((u8*)p)[0x14]=(u8)(r->pattern==0&&j==0);p->flags=(u8)(r->pattern==0&&j==1?8:12+(j&3));p->field17=(u8)(subtype+(r->pattern==0&&j==2));}
 D_800D3098=records;D_800D3094=(s32)r->count;
 answer=(u32)query((s32)r->subtype,(s16)r->coords[0],(s16)r->coords[1],(s16)r->coords[2]);
 if(failed||answer!=r->expected||calls!=r->expectedCalls)return 1;
 if((u32)D_800D3094!=(calls&&(mutation&1)?newCount:r->count))return 2;
 if(D_800D3098!=(calls&&(mutation&2)?alternate:records))return 3;
}return 0;}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
