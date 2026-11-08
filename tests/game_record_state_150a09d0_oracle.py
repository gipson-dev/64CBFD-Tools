"""Independent ordered record-state model and bounded MIPS service hooks."""
import itertools,struct
from dataclasses import dataclass
from tools.experiments import game_record_state_150a09d0_match as source
from tools.tests.game_resource_texture_callback_1513bbfc_oracle import Oracle as FloatOracle,rd,wr,state,u32,STACK
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,signed

LIMIT,POINTER,VIEWER,BOUND,GATE,MAP,ACTOR=0x800D3094,0x800D3098,0x800DBFF0,0x80082FA0,0x800C35EA,0x800DDF5C,0x800CC2D0
RECORDS,ALT,VIEWS,ALT_VIEWS,MARK=0x100000,0x110000,0x120000,0x130000,0x150000
STOP,COMMAND,COLLISION,START=0x1000FC18,0x1000E46C,0x150A1DA0,0x150A23E4
half=lambda v:((v&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
    count:int=2
    kind:int=2
    lowflags:int=0
    subtype:int=12
    status:int=2
    disabled:int=0
    timer:int=0xCAFE4201
    parameter:int=0xFEDC8123
    gate:int=1
    bound:int=1
    collision:int=0
    first:int=1
    second:int=1
    mutation:int=0
    service:int=STOP
    new_count:int=0
    phase:int=0
    alias:int=0
    coord:int=0
    incoming:int=0xD00DFEED

def table(c):
    return STACK+c.phase-64+16-0x18 if c.alias==1 else LIMIT-0x20 if c.alias==2 else RECORDS

def fixture(c=Case()):
    home=STACK+c.phase;m={u32(home+i):(i*17+165)&255 for i in range(-1024,512)}
    for base,n in((RECORDS,208),(ALT,208),(VIEWS,0x9A0*4),(ALT_VIEWS,0x9A0*4),(MARK,32),(MAP,256),(ACTOR,812),(LIMIT-64,256),(VIEWER-16,32),(BOUND-16,32),(GATE-8,24)):
        m.update({u32(base+i):(i*29+90)&255 for i in range(n)})
    for base in(table(c),ALT):
        for i in range(4):
            p=base+i*52
            for off,v in((0,-32768 if c.coord else -10-i),(2,32767 if c.coord else 20+i),(4,-1-i),(6,32767 if c.coord else -30-i)):
                wr(m,p+off,v,2)
            wr(m,p+0x14,c.disabled if base==table(c)else 0,1)
            wr(m,p+0x15,(c.kind<<2)|c.lowflags,1);wr(m,p+0x17,c.subtype if base==table(c)else 7,1)
            wr(m,p+0x18,c.parameter if base==table(c)else 0x12345678);wr(m,p+0x1C,c.timer if base==table(c)else 0xABCD5501);wr(m,p+0x20,c.status)
    wr(m,LIMIT,c.count);wr(m,POINTER,table(c));wr(m,VIEWER,VIEWS);wr(m,BOUND,c.bound);wr(m,GATE,c.gate,1)
    if c.alias==3:wr(m,VIEWER,RECORDS+0x1B-0x948)
    if c.alias==4:wr(m,VIEWER,POINTER-0x93C)
    if c.alias==5:wr(m,VIEWER,BOUND-0x93C)
    if c.alias==6:
        # Clearing map[0x42] changes the retained record word before its reread.
        wr(m,POINTER,MAP+0x42-0x1D);p=rd(m,POINTER)
        for at,n in((0,52),):m.update({p+j:0 for j in range(n)})
        wr(m,p+0x15,16,1);wr(m,p+0x17,9 if c.subtype==9 else 0,1);wr(m,p+0x1C,0xCAFE4201)
    return m

def public(m,c):
    home=STACK+c.phase;return{p:v for p,v in m.items()if not home-1024<=p<home+512}

def observable(m,c):
    return public(m,c),rd(m,STACK+c.phase),tuple(rd(m,table(c)+i*52+0x20)for i in range(1 if c.alias==1 else 4))

def effect(m,c,target,ordinal):
    wr(m,MARK,target);wr(m,MARK+4,ordinal)
    if target!=c.service or ordinal!=1:return
    mask=c.mutation
    if mask&1:wr(m,LIMIT,c.new_count)
    if mask&2:wr(m,POINTER,ALT)
    if mask&4:wr(m,VIEWER,ALT_VIEWS)
    if mask&8:wr(m,BOUND,0xFFFFFFFF)
    p=rd(m,POINTER)
    if mask&16:
        wr(m,p+0x17,0xE5,1);wr(m,p+0x18,0x13579BDF);wr(m,p+0x1C,0x2468ACED);wr(m,p+0x20,0x87654321)
    if mask&32:wr(m,GATE,0,1)

def reference(initial,c=Case(),home=None):
    m=dict(initial);home=STACK+c.phase if home is None else home;calls=[];counts={STOP:0,COMMAND:0,COLLISION:0,START:0}
    wr(m,home,c.incoming)
    def call(target,args):
        a=tuple(map(u32,args));calls.append((target,a));counts[target]+=1
        if target==STOP:wr(m,home-64+16,a[4])
        effect(m,c,target,counts[target])
        return c.collision if target==COLLISION else c.first if counts[target]==1 else c.second
    index=0;limit=rd(m,LIMIT)
    while index<limit:
        assert index<8,'Unbounded record fixture'
        off=index*52;p=u32(rd(m,POINTER)+off);flags=rd(m,p+0x15,1);kind=flags>>2
        if kind==2:
            status=rd(m,p+0x20)
            if status==1:wr(m,p+0x20,status^3)
            elif status==2:
                a=(rd(m,p+0x1C)>>16,half(rd(m,p,2)),half(rd(m,p+2,2)),half(rd(m,p+4,2)),rd(m,p+0x18))
                call(STOP,a);wr(m,u32(rd(m,POINTER)+off+0x20),0)
            if rd(m,GATE,1)==1 and call(COLLISION,(ACTOR,u32(rd(m,POINTER)+off),0))==0:
                call(START,(u32(rd(m,POINTER)+off),))
            limit=rd(m,LIMIT)
        elif kind==7:
            if flags&3==3:wr(m,p+0x20,0)
            else:
                status=rd(m,p+0x20)
                if status==1:wr(m,p+0x20,2)
                elif status==2 and call(COMMAND,(rd(m,p+0x17,1),0,rd(m,p+0x18),0)):
                    p=u32(rd(m,POINTER)+off)
                    if call(COMMAND,(rd(m,p+0x17,1),100,rd(m,p+0x1C),0)):wr(m,u32(rd(m,POINTER)+off+0x20),0)
            limit=rd(m,LIMIT)
        elif kind in(0,4):
            if kind==4:
                if rd(m,p+0x17,1)!=9:
                    old=rd(m,p+0x1C);low=old&255
                    if low:
                        low=0 if rd(m,p+0x14,1)else low-1;wr(m,p+0x1C,(old&0xFFFFFF00)|low)
                        if low==0:
                            p=u32(rd(m,POINTER)+off);m[MAP+((rd(m,p+0x1C)>>8)&255)]=0;wr(m,p+0x1C,rd(m,p+0x1C)&0xFFFF0000)
                p=u32(rd(m,POINTER)+off)
            if rd(m,p+0x17,1)==12 and rd(m,p+0x14,1)==0:
                viewer=0
                while viewer<=signed(rd(m,BOUND)):
                    assert viewer<8,'Unbounded viewer fixture'
                    v=u32(rd(m,VIEWER)+viewer*0x9A0)
                    for dst,src in((0x93C,0),(0x940,2),(0x944,4),(0x938,6)):
                        p=u32(rd(m,POINTER)+off);wr(m,v+dst,bits(float(half(rd(m,p+src,2)))))
                    p=u32(rd(m,POINTER)+off);parameter=rd(m,p+0x18);wr(m,v+0x948,1,1);wr(m,v+0x949,parameter,1)
                    viewer+=1
            limit=rd(m,LIMIT)
        index+=1
    return observable(m,c),calls,m

class Oracle(FloatOracle):
    def __init__(self,words,memory,c=Case(),entry=None,connected=None):
        self.service_counts={STOP:0,COMMAND:0,COLLISION:0,START:0}
        FactoryOracle.__init__(self,words,memory,c,entry=source.ENTRY if entry is None else entry,connected=connected,arguments=(c.incoming,))
    def record_call(self,target):
        sizes={source.ENTRY:1,STOP:5,COMMAND:4,COLLISION:3,START:1}
        assert target in sizes,hex(target)
        a=tuple(map(u32,self.arguments(sizes[target])));self.calls.append((target,a));self.events.append(('CALL',target,a))
        if target==source.ENTRY:self.target_home=self.r[29]
        else:self.service_counts[target]+=1
    def hook(self,target):
        assert target in self.service_counts,hex(target)
        c=self.case;number=self.service_counts[target]
        value=c.collision if target==COLLISION else c.first if number==1 else c.second
        effect(self.memory,c,target,number)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def cases():
    for kind,status,lowflags,gate,phase in itertools.product((0,1,2,3,4,7,8,63),(0,1,2,0xFFFFFFFF),(0,3),(0,1,2),(0,8)):
        yield Case(kind=kind,status=status,lowflags=lowflags,gate=gate,phase=phase)
    for subtype,disabled,timer,bound in itertools.product((0,9,12,0xFF),(0,1),(0xCAFE4200,0xCAFE4201,0xCAFE42FF),(-1,0,2)):
        yield Case(kind=4,subtype=subtype,disabled=disabled,timer=timer,bound=bound)
    for first,second,collision in itertools.product((0,1,0xFFFFFFFF),(0,1,0x80000000),(0,1)):
        yield Case(kind=7,first=first,second=second,collision=collision)
        yield Case(kind=2,first=first,second=second,collision=collision)
    for service,mask,new_count in itertools.product((STOP,COMMAND,COLLISION,START),(1,2,3,4,8,16,32,63),(0,3)):
        yield Case(kind=7 if service==COMMAND else 2,service=service,mutation=mask,new_count=new_count)
    yield Case(count=0)
    for status in(0,1,2):yield Case(kind=2,status=status,coord=1)
    for incoming in(0,1,0xFFFFFFFF,0x80000000):yield Case(incoming=incoming,count=0)
    for alias in(1,2,3,5,6):yield Case(alias=alias,count=1,kind=0 if alias in(3,5)else 4,bound=0)
    for count in(0xFFFFFFFF,0x80000000):yield Case(count=count,mutation=1)

def native_cases():return[c for c in cases()if not c.phase and not c.alias and c.count<=3]

def fold(values):
    h=2166136261
    for v in values:h=u32((h^u32(v))*16777619)
    return h

def memory_hash(m):
    values=[rd(m,LIMIT),int(rd(m,POINTER)==ALT),int(rd(m,VIEWER)==ALT_VIEWS),rd(m,BOUND),rd(m,GATE,1)]
    for base in(RECORDS,ALT):
        for i in range(4):
            for off,n in((0,2),(2,2),(4,2),(6,2),(0x14,1),(0x15,1),(0x17,1),(0x18,4),(0x1C,4),(0x20,4)):values.append(rd(m,base+i*52+off,n))
    for base in(VIEWS,ALT_VIEWS):
        for i in range(4):
            for off,n in((0x938,4),(0x93C,4),(0x940,4),(0x944,4),(0x948,1),(0x949,1)):values.append(rd(m,base+i*0x9A0+off,n))
    values.extend(m[MAP+i]for i in range(256));return fold(values)

def call_hash(calls):
    values=[]
    for target,args in calls:
        a=list(args)
        if target==STOP:a[4]&=65535
        if target in(COLLISION,START):
            j=1 if target==COLLISION else 0;p=a[j];bank=int(ALT<=p<ALT+208);a[j]=(0x100 if bank else 0)+(p-(ALT if bank else RECORDS))//52
        values.extend((target,*a))
    return fold(values)

def native_harness(body=None):
    """Use SDK types, the selected C, and independently generated expected results."""
    rows=[]
    for c in native_cases():
        initial=fixture(c);_,calls,m=reference(initial,c)
        values=[c.count,c.kind,c.lowflags,c.subtype,c.status,c.disabled,c.timer,c.parameter,c.gate,c.bound,c.collision,c.first,c.second,c.mutation,c.service,c.new_count,c.coord,c.incoming,memory_hash(m),call_hash(calls)]
        rows.append('{'+','.join('0x%08XU'%u32(v)for v in values)+'}')
    prefix=(source.ROOT/source.SOURCE).read_text();record=prefix[prefix.index('typedef struct {'):prefix.index('} GeneratedCDE80Record;')+len('} GeneratedCDE80Record;')].replace('s32 field20;', 'u32 field20;')
    return r'''#include <ultra64.h>
#include "structs.h"
'''+record+'\n'+source.DECLARATIONS+r'''
typedef char check_record[(sizeof(GeneratedCDE80Record)==52)?1:-1];
typedef char check_view[(sizeof(GeneratedCDE80ViewUpdate)==0x9A0)?1:-1];
typedef char check_ptr[(sizeof(void*)==4)?1:-1];
typedef char check_sdk_view[(sizeof(struct108)==0x9A0)?1:-1];
typedef struct {u32 count,kind,flags,subtype,status,disabled,timer,parameter,gate,bound,collision,first,second,mutation,service,newCount,coord,incoming,memory,calls;} Input;
static const Input inputs[]={'''+',\n'.join(rows)+r'''};
static GeneratedCDE80Record records[4],alternate[4];
static GeneratedCDE80ViewUpdate views[4],alternateViews[4];
GeneratedCDE80Record *D_800D3098;
s32 D_800D3094,D_80082FA0;
struct108 *D_800DBFF0;
struct127 D_800CC2D0[26];
u8 D_800C35EA,D_800DDF5C[256];
static const Input *current;
static u32 callDigest,serviceCount[4];
static u32 mix(u32 h,u32 v){return(h^v)*16777619U;}
static u32 ptrIndex(u32 p){u32 a=(u32)alternate;return p>=a&&p<a+sizeof(alternate)?0x100+(p-a)/52:(p-(u32)records)/52;}
static u32 service(u32 target,u32 a,u32 b,u32 c,u32 d,u32 e){
 u32 index=target==0x1000FC18?0:target==0x1000E46C?1:target==0x150A1DA0?2:3;
 callDigest=mix(callDigest,target);
 if(index==2){callDigest=mix(callDigest,0x800CC2D0);callDigest=mix(callDigest,ptrIndex(b));callDigest=mix(callDigest,c);}
 else if(index==3)callDigest=mix(callDigest,ptrIndex(a));
 else {callDigest=mix(callDigest,a);callDigest=mix(callDigest,b);callDigest=mix(callDigest,c);callDigest=mix(callDigest,d);if(index==0)callDigest=mix(callDigest,e&65535);}
 serviceCount[index]++;
 if(target==current->service&&serviceCount[index]==1){u32 mask=current->mutation;
  if(mask&1)D_800D3094=current->newCount;
  if(mask&2)D_800D3098=alternate;
  if(mask&4)D_800DBFF0=(struct108*)alternateViews;
  if(mask&8)D_80082FA0=-1;
  if(mask&16){D_800D3098->field17=0xE5;D_800D3098->field18=0x13579BDF;D_800D3098->field1C=0x2468ACED;D_800D3098->field20=0x87654321U;}
  if(mask&32)D_800C35EA=0;
 }
 return index==2?current->collision:serviceCount[index]==1?current->first:current->second;
}
void func_1000FC18(u16 a,s16 b,s16 c,s16 d,u16 e){(void)service(0x1000FC18,a,b,c,d,e);}
s32 func_1000E46C(s32 a,s32 b,s32 c,s32 d){return service(0x1000E46C,a,b,c,d,0);}
s32 func_150A1DA0(struct127*a,s32 b,s32 c){return service(0x150A1DA0,(u32)a,b,c,0,0);}
void func_150A23E4(GeneratedCDE80Record*a){(void)service(0x150A23E4,(u32)a,0,0,0,0);}
'''+(source.SELECTED if body is None else body)+r'''
static u32 pattern(u32 at,u32 n){u32 v=0,j;for(j=0;j<n;j++)v=(v<<8)|(((at+j)*29+90)&255);return v;}
static f32 fromBits(u32 n){union{u32 u;f32 f;}v;v.u=n;return v.f;}
static u32 toBits(f32 n){union{u32 u;f32 f;}v;v.f=n;return v.u;}
static void fill(void*p,u32 n){u8*b=p;u32 j;for(j=0;j<n;j++)b[j]=(j*29+90)&255;}
static void reset(const Input*c){u32 bank,i;GeneratedCDE80Record*r;GeneratedCDE80ViewUpdate*v;
 current=c;callDigest=2166136261U;for(i=0;i<4;i++)serviceCount[i]=0;
 for(bank=0;bank<2;bank++)for(i=0;i<4;i++){
  r=(bank?alternate:records)+i;fill(r,52);
  r->origin0=c->coord?-32768:-10-(s32)i;r->origin1=c->coord?32767:20+(s32)i;r->origin2=-1-(s32)i;r->radius=c->coord?32767:-30-(s32)i;
  r->disabled=bank?0:c->disabled;r->flags=(c->kind<<2)|c->flags;r->field17=bank?7:c->subtype;
  r->field18=bank?0x12345678:c->parameter;r->field1C=bank?0xABCD5501:c->timer;r->field20=c->status;
  v=(bank?alternateViews:views)+i;fill(v,0x9A0);
  v->radius=fromBits(pattern(i*0x9A0+0x938,4));v->x=fromBits(pattern(i*0x9A0+0x93C,4));v->y=fromBits(pattern(i*0x9A0+0x940,4));v->z=fromBits(pattern(i*0x9A0+0x944,4));
  v->enabled=pattern(i*0x9A0+0x948,1);v->parameter18=pattern(i*0x9A0+0x949,1);
 }
 for(i=0;i<256;i++)D_800DDF5C[i]=(i*29+90)&255;
 D_800D3094=c->count;D_800D3098=records;D_800DBFF0=(struct108*)views;D_80082FA0=c->bound;D_800C35EA=c->gate;
}
static u32 memoryDigest(void){u32 h=2166136261U,bank,i;GeneratedCDE80Record*r;GeneratedCDE80ViewUpdate*v;
 h=mix(h,D_800D3094);h=mix(h,D_800D3098==alternate);h=mix(h,D_800DBFF0==(struct108*)alternateViews);h=mix(h,D_80082FA0);h=mix(h,D_800C35EA);
 for(bank=0;bank<2;bank++)for(i=0;i<4;i++){r=(bank?alternate:records)+i;
  h=mix(h,(u16)r->origin0);h=mix(h,(u16)r->origin1);h=mix(h,(u16)r->origin2);h=mix(h,(u16)r->radius);
  h=mix(h,r->disabled);h=mix(h,r->flags);h=mix(h,r->field17);h=mix(h,r->field18);h=mix(h,r->field1C);h=mix(h,r->field20);
 }
 for(bank=0;bank<2;bank++)for(i=0;i<4;i++){v=(bank?alternateViews:views)+i;
  h=mix(h,toBits(v->radius));h=mix(h,toBits(v->x));h=mix(h,toBits(v->y));h=mix(h,toBits(v->z));h=mix(h,v->enabled);h=mix(h,v->parameter18);
 }
 for(i=0;i<256;i++)h=mix(h,D_800DDF5C[i]);return h;
}
void _start(void){u32 i,code=0;void(*typed)(s32)=func_150A09D0;
 for(i=0;i<sizeof(inputs)/sizeof(inputs[0]);i++){reset(inputs+i);typed(inputs[i].incoming);
  if(memoryDigest()!=inputs[i].memory||callDigest!=inputs[i].calls){code=i%200+1;break;}
 }
 __asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();
}
'''
