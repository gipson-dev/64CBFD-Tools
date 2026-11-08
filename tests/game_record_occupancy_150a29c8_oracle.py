"""Ordered mask/collision model and original SDK shift execution for the query."""
import itertools,struct
from dataclasses import dataclass
from functools import lru_cache
from tools.experiments import game_record_occupancy_150a29c8_match as source
from tools.tests.game_actor_record_list_150a2aec_oracle import Oracle as ShiftOracle
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_resource_texture_callback_1513bbfc_oracle import rd,wr,state,u32,STACK

SHIFT,COLLISION=0x10026800,0x150A1DA0
ENABLED,LIMIT,POINTER,MASKS,ACTORS=0x800D2340,0x800D3094,0x800D3098,0x800D30F0,0x800CC2D0
RECORDS,ALT,MARK=0x50000,0x70000,0x90000

@lru_cache(maxsize=2)
def shift_words(root):return struct.unpack_from('>11I',(root/'conker/conker.us.bin').read_bytes(),0x26800)

@dataclass(frozen=True)
class Case:
    index:int=3
    identity:int=0x4041
    limit:int=192
    enabled:int=8
    bits:int=1
    result:int=0
    mutation:int=0
    phase:int=0


def actor(c):return u32(ACTORS+u32(c.index)*812)
def masked(c):return u32(c.index)<16 and bool(c.enabled&(1<<c.index))
def accepted(c):return (c.identity&4095)<=u32(c.limit)
def mask(c):return (1<<(c.identity&63)) if c.bits==1 else 0 if c.bits==0 else (1<<64)-1 if c.bits==2 else 1<<((c.identity+1)&63)


def fixture(c=Case()):
    home=STACK+c.phase;m={home+i:(i*17+165)&255 for i in range(-1024,512)}
    for p,n in ((ENABLED,2),(LIMIT,4),(POINTER,4),(MARK,16)):
        for i in range(n):m[p+i]=(i*29+90)&255
    wr(m,ENABLED,c.enabled,2);wr(m,LIMIT,c.limit);wr(m,POINTER,RECORDS)
    if masked(c):
        p=u32(MASKS+c.index*24+((c.identity&4095)>>6)*8);bits=mask(c)
        wr(m,p,bits>>32);wr(m,p+4,bits)
    return m


def public(m,c):
    home=STACK+c.phase
    return {p:v for p,v in m.items() if not home-1024<=p<home+512}


def effect(m,c,args,home,order='big'):
    for i,value in enumerate((*args,c.identity&4095)):wr(m,MARK+i*4,value,4,order)
    if c.mutation&1:wr(m,LIMIT,0,4,order)
    if c.mutation&2:wr(m,POINTER,ALT,4,order)
    if c.mutation&4:wr(m,ENABLED,0xFFFF,2,order)
    if c.mutation&8:wr(m,home,0x89ABCDEF,4,order)
    if c.mutation&16:wr(m,home+4,0xFEDCBA98,4,order)


def reference(initial,c=Case(),home=None):
    m=dict(initial);home=STACK+c.phase if home is None else home;calls=[]
    if not accepted(c):return public(m,c),calls,1
    identity=c.identity&4095
    if masked(c):
        p=u32(MASKS+c.index*24+(identity>>6)*8);hi,lo=rd(m,p),rd(m,p+4)
        calls.append((SHIFT,(hi,lo,0,identity&63)))
        return public(m,c),calls,0 if (((hi<<32)|lo)>>(identity&63))&1 else 1
    args=(actor(c),u32(rd(m,POINTER)+identity*52),1);calls.append((COLLISION,args));effect(m,c,args,home)
    return public(m,c),calls,u32(c.result)


class Oracle(ShiftOracle):
    def __init__(self,words,memory,c=Case(),entry=None,connected=None,arguments=None):
        code={} if entry==SHIFT else dict(zip(range(SHIFT,SHIFT+44,4),shift_words(source.ROOT)))
        code.update(connected or {});self.target_home=STACK+c.phase
        FactoryOracle.__init__(self,words,memory,c,entry=source.ENTRY if entry is None else entry,connected=code,
            arguments=tuple(map(u32,(c.index,c.identity))) if arguments is None else arguments)
    def record_call(self,target):
        assert target in (source.ENTRY,SHIFT,COLLISION),hex(target)
        args=tuple(map(u32,self.arguments(4 if target==SHIFT else 3 if target==COLLISION else 2)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==source.ENTRY:self.target_home=self.r[29]
    def hook(self,target):
        assert target==COLLISION;args=self.calls[-1][1]
        assert args==(actor(self.case),u32(rd(self.memory,POINTER)+(self.case.identity&4095)*52),1)
        effect(self.memory,self.case,args,self.target_home)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(self.case.result)


def cases():
    for index,enabled,identity,limit,result,phase in itertools.product((0,3,15,16,25,0x100,0xFFFFFFFF),
        (0,0xFFFF),(0,0x4040,0x40BF,0xFFFFF000,0xFFFFFFFF),(0,192,0xFFFFFFFF),(0,0x80000001),(0,8)):
        yield Case(index,identity,limit,enabled,(identity^limit)&3,result,phase=phase)
    for identity,bits in itertools.product(range(64),(0,1,2,3)):yield Case(identity=identity,bits=bits)
    for identity,limit in ((0,0),(1,1),(63,63),(64,64),(127,127),(128,128),(191,191),(192,192),(4095,4095),(0x80000FFF,0x80000000)):
        yield Case(identity=identity,limit=limit)
    for mutation,result,phase in itertools.product(range(32),(0,1,0xFFFFFFFF),(0,8)):
        yield Case(enabled=0,mutation=mutation,result=result,phase=phase)


def native_cases():
    return [c for c in cases() if 0<=c.index<26 and (c.identity&4095)<=192 and c.limit<=192 and
        (not masked(c) or(c.identity&4095)<192) and not c.mutation&24 and not c.phase]


def native_harness(body=None):
    body=source.SELECTED if body is None else body
    prefix=(source.ROOT/source.SOURCE).read_text().split('s32 func_150A09D0()',1)[0]
    rows=[]
    for c in native_cases():
        result=reference(fixture(c),c)[2];calls=int(accepted(c) and not masked(c))
        rows.append('{%dU,0x%XU,0x%XU,%d,%d,0x%XU,%d,%d,0x%XU}'%(c.index,u32(c.identity),u32(c.limit),c.enabled,c.bits,u32(c.result),c.mutation,calls,result))
    return prefix+'''
_Static_assert(sizeof(void*)==4&&sizeof(struct127)==812&&sizeof(GeneratedCDE80Record)==52,"O32 layout");
struct127 D_800CC2D0[26];static GeneratedCDE80Record records[193],alternate[193];
GeneratedCDE80Record *D_800D3098;s32 D_800D3094;u16 D_800D2340;u64 D_800D30F0[48];
static u32 identity,actorIndex,answer,mutation,calls,mark[4];
s32 func_150A1DA0(struct127 *actor,s32 descriptor,s32 mode){
 if(actor!=&D_800CC2D0[actorIndex]||(u32)descriptor!=(u32)&records[identity]||mode!=1)return 12345;
 calls++;mark[0]=(u32)actor;mark[1]=(u32)descriptor;mark[2]=mode;mark[3]=identity;
 if(mutation&1)D_800D3094=0;if(mutation&2)D_800D3098=alternate;if(mutation&4)D_800D2340=0xFFFF;
 return(s32)answer;
}
'''+body+'''
typedef s32(*Query)(u32,u32);static Query query=func_150A29C8;
struct Row{u32 index,id,limit;u32 enabled,bits,result,mutation,expectedCalls,expected;};
static const struct Row rows[]={'''+','.join(rows)+'''};
static int check(void){unsigned i,j;for(i=0;i<sizeof rows/sizeof rows[0];i++){
 const struct Row*r=&rows[i];u32 value;actorIndex=r->index;identity=r->id&4095;answer=r->result;mutation=r->mutation;calls=0;
 D_800D3094=(s32)r->limit;D_800D3098=records;D_800D2340=(u16)r->enabled;
 for(j=0;j<48;j++)D_800D30F0[j]=0;for(j=0;j<4;j++)mark[j]=0;
 if(actorIndex<16&&identity<192)D_800D30F0[actorIndex*3+(identity>>6)]=r->bits==1?1ULL<<(identity&63):r->bits==0?0:r->bits==2?~0ULL:1ULL<<((identity+1)&63);
 value=(u32)query(r->index,r->id);if(value!=r->expected||calls!=r->expectedCalls)return 1;
 if((u32)D_800D3094!=(calls&&(mutation&1)?0:r->limit))return 2;
 if(D_800D3098!=(calls&&(mutation&2)?alternate:records))return 3;
 if(D_800D2340!=(calls&&(mutation&4)?0xFFFF:r->enabled))return 4;
 if(calls&&(mark[0]!=(u32)&D_800CC2D0[actorIndex]||mark[1]!=(u32)&records[identity]||mark[2]!=1||mark[3]!=identity))return 5;
}return 0;}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
