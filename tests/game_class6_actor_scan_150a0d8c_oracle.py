"""Ordered class-6 scan, single-precision effects and bounded service hooks."""
import itertools,struct
from dataclasses import dataclass
from tools.experiments import game_class6_actor_scan_150a0d8c_match as source
from tools.tests.game_resource_texture_callback_1513bbfc_oracle import Oracle as FloatOracle,rd,wr,state,u32,STACK,trunc,sub,mul
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating,signed

ACTORS,LIMIT,POINTER,SCALE,GATE,FX_GATE=0x800CC2D0,0x800D3094,0x800D3098,0x8009F5A8,0x800BE616,0x800C3F00
RECORDS,ALT,MARK=0x100000,0x110000,0x150000
COLLISION,DISTANCE,EFFECT=0x150A1DA0,0x150AD9A0,0x15035808
half=lambda v:((v&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
    count:int=2
    kind:int=0
    flags:int=24
    disabled:int=0
    radius:int=100
    distance:int=-1
    reject:int=0
    actors:int=0
    scale:int=0x3E800000
    coords:int=0
    collision_mut:int=0
    distance_mut:int=0
    effect_mut:int=0
    new_count:int=0
    new_radius:int=-1
    connected:int=0
    alias:int=0
    phase:int=0

def table(c):return STACK+c.phase-128+16 if c.alias==1 else ACTORS+0x14 if c.alias==2 else LIMIT-0x14 if c.alias==3 else RECORDS
def fixture(c=Case()):
    home=STACK+c.phase;m={u32(home+i):(i*17+165)&255 for i in range(-2048,512)}
    for base,n in((ACTORS,26*812),(RECORDS,156),(ALT,156),(MARK,20),(LIMIT-64,256),(SCALE-16,64),(GATE-8,24),(FX_GATE-8,24)):
        for i in range(n):m[u32(base+i)]=(i*29+90)&255
    for i in range(26):
        p=ACTORS+812*i;active=(i in(0,1,2,24,25))if c.actors==0 else c.actors==1
        wr(m,p,int(active));wr(m,p+5,2 if i==2 and c.actors==0 else i&1,1)
        values=(30.75+i,-2.5+i,-7.75-i,50.25+i)if not c.coords else(65536.25+i,-65537.75+i,32768.5-i,-0.0)if c.coords==1 else(float('inf'),float('nan'),-float('inf'),0.0)
        for at,v in zip((0x14,0x18,0x1C,0x180),values):wr(m,p+at,bits(v))
    for base in(table(c),ALT):
        for i in range(3):
            p=base+i*52
            for at,v in((0,10+i*3),(2,-20+i),(4,5-i),(6,c.radius if base==table(c)else 300),(8,123)):
                wr(m,p+at,v,2)
            wr(m,p+0x10,bits(1.25+i if base==table(c)else -3.5-i))
            wr(m,p+0x14,c.disabled if base==table(c)else 0,1);wr(m,p+0x15,c.flags if base==table(c)else 24,1);wr(m,p+0x17,c.kind,1)
    wr(m,LIMIT,c.count);wr(m,POINTER,table(c));wr(m,SCALE,c.scale);wr(m,GATE,0,1);wr(m,FX_GATE,15,1)
    return m

def approximate(args):
    a,b,c=sorted((abs(signed(v))for v in args),reverse=True)
    return u32(a+((11*b)>>5)+(c>>2))
def public(m,c):
    home=STACK+c.phase;return{p:v for p,v in m.items()if not home-2048<=p<home+512}
def observable(m,c):
    fields=((0,2),(2,2),(4,2),(6,2),(8,2),(0x10,4),(0x14,1),(0x15,1),(0x17,1))
    return public(m,c),tuple(rd(m,table(c)+at,n)for at,n in fields)

def effect(m,c,target,record,actor,ordinal,home):
    wr(m,MARK,target);wr(m,MARK+4,record);wr(m,MARK+8,actor);wr(m,MARK+12,ordinal)
    if ordinal!=1:return
    mask=c.collision_mut if target==COLLISION else c.distance_mut if target==DISTANCE else c.effect_mut
    if mask&1:wr(m,LIMIT,c.new_count)
    if mask&2:wr(m,POINTER,ALT)
    a=ACTORS+actor*812;p=u32(rd(m,POINTER)+record*52)
    if mask&4:
        for off,v in((0x14,11.5),(0x18,12.5),(0x1C,13.5),(0x180,14.5)):wr(m,a+off,bits(v))
    if mask&8:wr(m,p+0x15,0,1)
    if mask&16:wr(m,SCALE,bits(2.0))
    if mask&32:wr(m,p+6,c.new_radius,2)
    if mask&64:wr(m,p+0x17,rd(m,p+0x17,1)^1,1)

def reference(initial,c=Case(),home=None):
    m=dict(initial);home=STACK+c.phase if home is None else home;calls=[];counts={COLLISION:0,DISTANCE:0,EFFECT:0};limit=rd(m,LIMIT)
    if not limit:return observable(m,c),calls,m
    scale=floating(rd(m,SCALE));index=0
    def call(target,args,actor):
        args=tuple(map(u32,args));calls.append((target,args));counts[target]+=1
        if target==EFFECT:
            for j,value in enumerate(args[4:],4):wr(m,home-128+4*j,value)
        if not(target==DISTANCE and c.connected&1)and not(target==EFFECT and c.connected&2):effect(m,c,target,index,actor,counts[target],home)
        if target==COLLISION:return 0xFFFFFFFF if c.reject>>actor&1 else 0
        if target==DISTANCE:return approximate(args)if c.connected&1 else u32(c.distance)
        return 0xA5000002
    while True:
        p=u32(rd(m,POINTER)+index*52)
        if rd(m,p+0x14,1)==0 and rd(m,p+0x15,1)>>2==6:
            for actor in range(25):
                a=ACTORS+actor*812
                if not rd(m,a)or rd(m,a+5,1)not in(0,1):continue
                if call(COLLISION,(a,u32(rd(m,POINTER)+index*52),1),actor):continue
                p=u32(rd(m,POINTER)+index*52);dy=half(trunc(sub(floating(rd(m,a+0x18)),float(half(rd(m,p+2,2))))))
                if rd(m,p+0x17,1)==0:
                    dx=half(trunc(sub(floating(rd(m,a+0x14)),float(half(rd(m,p,2))))));dz=half(trunc(sub(floating(rd(m,a+0x1C)),float(half(rd(m,p+4,2))))))
                    distance=call(DISTANCE,(dx,dy,dz),actor);p=u32(rd(m,POINTER)+index*52);radius=half(rd(m,p+6,2))
                    if signed(distance)>=radius:continue
                    inner=mul(float(radius),scale)
                    if 100.0<inner:inner=100.0
                    args=(2,actor,bits(float(half(rd(m,p,2)))),bits(float(half(rd(m,p+2,2)))),bits(float(half(rd(m,p+4,2)))),0,rd(m,p+0x10),bits(sub(float(radius),inner)),bits(float(radius)),bits(255.0))
                else:args=(1,actor,rd(m,a+0x14),rd(m,a+0x180),rd(m,a+0x1C),0,0,bits(100.0),bits(150.0),bits(255.0))
                call(EFFECT,args,actor)
            limit=rd(m,LIMIT)
        index+=1
        if index>=limit:break
        assert index<3,'Fixture table exhausted before exit'
    return observable(m,c),calls,m

class Oracle(FloatOracle):
    def __init__(self,words,memory,c=Case(),entry=None,connected=None):
        self.target_home=STACK+c.phase;self.service_counts={COLLISION:0,DISTANCE:0,EFFECT:0};self.current_actor=0;self.current_record=0
        FactoryOracle.__init__(self,words,memory,c,entry=source.ENTRY if entry is None else entry,connected=connected,arguments=())
    def execute(self,w):
        op,fn,rs,rt,rd_=w>>26,w&63,w>>21&31,w>>16&31,w>>11&31
        if op==17 and rs==16 and fn==60:self.condition=floating(self.f[rd_])<floating(self.f[rt]);return
        if op==0 and fn in(32,34,38,24):
            x,y=signed(self.r[rs]),signed(self.r[rt])
            if fn==24:v=x*y;self.hi=u32(v>>32);self.lo=u32(v)
            else:
                v=x+y if fn==32 else x-y if fn==34 else self.r[rs]^self.r[rt]
                if fn!=38:assert -2147483648<=v<=2147483647,'Bounded handwritten helper overflow'
                self.r[rd_]=u32(v)
            self.r[0]=0;return
        return super().execute(w)
    def record_call(self,target):
        assert target in(source.ENTRY,COLLISION,DISTANCE,EFFECT),hex(target)
        args=tuple(map(u32,self.arguments(0 if target==source.ENTRY else 10 if target==EFFECT else 3)));self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==source.ENTRY:self.target_home=self.r[29]
        elif target==COLLISION:
            self.current_actor=(args[0]-ACTORS)//812;matches=[(args[1]-base)//52 for base in(table(self.case),ALT)if 0<=u32(args[1]-base)<156 and(args[1]-base)%52==0]
            assert len(matches)==1 and 0<=self.current_actor<25 and args[2]==1,(args,self.case);self.current_record=matches[0]
        if target in self.service_counts:self.service_counts[target]+=1
    def hook(self,target):
        assert target in self.service_counts;args=self.calls[-1][1];c=self.case
        value=(0xFFFFFFFF if c.reject>>self.current_actor&1 else 0)if target==COLLISION else u32(c.distance)if target==DISTANCE else 0xA5000002
        effect(self.memory,c,target,self.current_record,self.current_actor,self.service_counts[target],self.target_home)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

def connected_code(rom,c):
    code={}
    if c.connected&1:code.update(zip(range(DISTANCE,DISTANCE+128,4),struct.unpack_from('>32I',rom,0xDAE50)))
    if c.connected&2:code.update(zip(range(EFFECT,0x15035D6C,4),struct.unpack_from('>345I',rom,0x62CB8)))
    return code
def cases():
    for count,kind,radius,distance,flags,disabled,phase in itertools.product((0,1,2),(0,1),(0,1000),(-1,1000),(24,28),(0,1),(0,8)):
        yield Case(count=count,kind=kind,radius=radius,distance=distance,flags=flags,disabled=disabled,phase=phase)
    masks=(0,1,2,3,4,8,16,32,64,5,10,18,36,68,127)
    for stage,mask,new_count in itertools.product(('collision_mut','distance_mut','effect_mut'),masks,(0,3)):
        yield Case(**{stage:mask},new_count=new_count,new_radius=-1 if new_count==0 else 32767)
    for radius,distance in itertools.product((-32768,32767),(-2147483648,-1,0,32767)):
        yield Case(radius=radius,distance=distance)
    for scale in(0,0x80000000,0xBE800000,0x3F800000,0x7FC12345,0x7F800000,0xFF800000):yield Case(scale=scale)
    for coords,kind in itertools.product((1,2),(0,1)):yield Case(coords=coords,kind=kind)
    for reject in(1,3,0xFFFFFFFF):yield Case(reject=reject)
    for actors in(1,2):yield Case(actors=actors)
    yield Case(alias=1,count=1);yield Case(alias=2,count=1);yield Case(alias=3,count=0x00180001,collision_mut=1)
    for count in(0xFFFFFFFF,0x80000000):yield Case(count=count,collision_mut=1)
def native_cases():return[c for c in cases()if c.count<=3 and not c.phase and not c.alias and not c.coords and c.scale not in(0x7FC12345,0x7F800000,0xFF800000)]

def fold(values):
    h=2166136261
    for v in values:h=u32((h^u32(v))*16777619)
    return h
def call_hash(calls,c):
    values=[]
    for target,args in calls:
        if target==COLLISION:
            bank=int(ALT<=args[1]<ALT+156);base=ALT if bank else table(c)
            values.extend((1,(args[0]-ACTORS)//812,bank,(args[1]-base)//52,args[2]))
        else:values.extend((2 if target==DISTANCE else 3,*args))
    return fold(values)
def memory_hash(m,c):
    values=[rd(m,LIMIT),int(rd(m,POINTER)==ALT),rd(m,SCALE)]
    for base in(table(c),ALT):
        for i in range(3):
            for off,n in((0,2),(2,2),(4,2),(6,2),(8,2),(0x10,4),(0x14,1),(0x15,1),(0x17,1)):values.append(rd(m,base+52*i+off,n))
    for i in range(26):
        for off,n in((0,4),(5,1),(0x14,4),(0x18,4),(0x1C,4),(0x180,4)):values.append(rd(m,ACTORS+812*i+off,n))
    return fold(values)

def native_harness(body=None):
    body=source.SELECTED if body is None else body;prefix=source.source_states((source.ROOT/source.SOURCE).read_text())[1].split('s32 func_150A09D0()',1)[0];rows=[]
    for c in native_cases():
        _,calls,m=reference(fixture(c),c)
        values=(c.count,c.kind,c.flags,c.disabled,u32(c.radius),u32(c.distance),c.reject,c.actors,c.scale,c.collision_mut,c.distance_mut,c.effect_mut,c.new_count,u32(c.new_radius),call_hash(calls,c),memory_hash(m,c))
        rows.append('{'+','.join('0x%XU'%v for v in values)+'}')
    return prefix+'''
_Static_assert(sizeof(void*)==4&&sizeof(struct127)==812&&sizeof(GeneratedCDE80Record)==52,"SDK O32 layout");
_Static_assert(__builtin_offsetof(GeneratedCDE80Record,radius)==6&&__builtin_offsetof(GeneratedCDE80Record,parameter10)==16&&__builtin_offsetof(GeneratedCDE80Record,disabled)==20,"Recovered fields");
struct127 D_800CC2D0[26];static GeneratedCDE80Record records[3],alternate[3];GeneratedCDE80Record *D_800D3098;s32 D_800D3094;f32 D_8009F5A8;
struct Row{u32 count,kind,flags,disabled,radius,distance,reject,actors,scale,collisionMut,distanceMut,effectMut,newCount,newRadius,callHash,memoryHash;};
static const struct Row rows[]={'''+','.join(rows)+'''};
static const struct Row*row;static u32 hash,counts[3],actorIndex,recordIndex,failed;
static u32 asWord(f32 value){union{f32 f;u32 u;}v;v.f=value;return v.u;}
static f32 asFloat(u32 value){union{f32 f;u32 u;}v;v.u=value;return v.f;}
static void push(u32 value){hash=(hash^value)*16777619U;}
static void mutate(unsigned stage){
 u32 mask=stage==0?row->collisionMut:stage==1?row->distanceMut:row->effectMut;GeneratedCDE80Record*p;struct127*a;
 if(counts[stage]!=1)return;if(mask&1)D_800D3094=(s32)row->newCount;if(mask&2)D_800D3098=alternate;
 p=&D_800D3098[recordIndex];a=&D_800CC2D0[actorIndex];
 if(mask&4){a->x_position=11.5f;a->y_position=12.5f;a->z_position=13.5f;a->unk180=14.5f;}
 if(mask&8)p->flags=0;if(mask&16)D_8009F5A8=2.f;if(mask&32)p->radius=(s16)row->newRadius;if(mask&64)p->field17^=1;
}
s32 func_150A1DA0(struct127*a,s32 descriptor,s32 mode){
 u32 p=(u32)descriptor,bank=p>=(u32)alternate&&p<(u32)(alternate+3);actorIndex=(u32)(a-D_800CC2D0);recordIndex=(p-(u32)(bank?alternate:records))/52;
 if(actorIndex>=25||recordIndex>=3||mode!=1){failed=1;return 1;}
 push(1);push(actorIndex);push(bank);push(recordIndex);push((u32)mode);counts[0]++;mutate(0);return(row->reject>>actorIndex&1)?-1:0;
}
s32 func_150AD9A0(s32 x,s32 y,s32 z){push(2);push((u32)x);push((u32)y);push((u32)z);counts[1]++;mutate(1);return(s32)row->distance;}
s32 func_15035808(s32 type,s32 index,f32 x,f32 y,f32 z,f32 p5,f32 p6,f32 p7,f32 p8,f32 p9){
 push(3);push((u32)type);push((u32)index);push(asWord(x));push(asWord(y));push(asWord(z));push(asWord(p5));push(asWord(p6));push(asWord(p7));push(asWord(p8));push(asWord(p9));
 if((u32)index!=actorIndex)failed=1;counts[2]++;mutate(2);return 0x12345678;
}
'''+body+'''
typedef void(*Scan)(void);static Scan scan=func_150A0D8C;
static u32 memoryHash(void){unsigned i,j;hash=2166136261U;push((u32)D_800D3094);push(D_800D3098==alternate);push(asWord(D_8009F5A8));
 for(j=0;j<2;j++)for(i=0;i<3;i++){GeneratedCDE80Record*p=j?&alternate[i]:&records[i];push((u16)p->origin0);push((u16)p->origin1);push((u16)p->origin2);push((u16)p->radius);push((u16)p->heightOffset);push(asWord(p->parameter10));push(p->disabled);push(p->flags);push(p->field17);}
 for(i=0;i<26;i++){struct127*a=&D_800CC2D0[i];push((u32)a->interaction_state);push(a->unk5);push(asWord(a->x_position));push(asWord(a->y_position));push(asWord(a->z_position));push(asWord(a->unk180));}return hash;
}
static int check(void){unsigned n,i,j;for(n=0;n<sizeof rows/sizeof rows[0];n++){
 row=&rows[n];D_800D3094=(s32)row->count;D_800D3098=records;D_8009F5A8=asFloat(row->scale);hash=2166136261U;counts[0]=counts[1]=counts[2]=actorIndex=recordIndex=failed=0;
 for(i=0;i<26;i++){struct127*a=&D_800CC2D0[i];a->interaction_state=(s32)(row->actors==0?(i==0||i==1||i==2||i==24||i==25):row->actors==1);a->unk5=(u8)(i==2&&row->actors==0?2:i&1);a->x_position=30.75f+(f32)i;a->y_position=-2.5f+(f32)i;a->z_position=-7.75f-(f32)i;a->unk180=50.25f+(f32)i;}
 for(j=0;j<2;j++)for(i=0;i<3;i++){GeneratedCDE80Record*p=j?&alternate[i]:&records[i];p->origin0=(s16)(10+(int)i*3);p->origin1=(s16)(-20+(int)i);p->origin2=(s16)(5-(int)i);p->radius=(s16)(j?300:(s32)row->radius);p->heightOffset=123;p->parameter10=j?-3.5f-(f32)i:1.25f+(f32)i;p->disabled=(u8)(j?0:row->disabled);p->flags=(u8)(j?24:row->flags);p->field17=(u8)row->kind;}
 scan();if(failed||hash!=row->callHash)return 1;if(memoryHash()!=row->memoryHash)return 2;
}return 0;}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
