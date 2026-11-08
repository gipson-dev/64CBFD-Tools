"""Ordered record-parameter model and bounded O32 guest fixtures."""
from dataclasses import dataclass, replace
import itertools
from tools.experiments import game_record_parameter_150a2940_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_resource_texture_callback_1513bbfc_oracle import rd, wr, state, u32, STACK

COUNT, POINTER, TABLE, ALT, PACKET = 0x800D3094, 0x800D3098, 0x30000, 0x40000, 0x50000

@dataclass(frozen=True)
class Case:
    identity: int = 0
    count: int = 4
    value: int = 0x12345678
    kind: int = 0xABCD80FF
    alias: int = 0
    phase: int = 0
    seed: int = 0


def fixture(c=Case()):
    m = {}
    for base, size in ((STACK+c.phase-1024,1536),(COUNT-64,256),(TABLE,1024),(ALT,1024),(PACKET,32)):
        m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(size)})
    base = TABLE if not c.alias else POINTER-(0x18 if c.alias == 1 else 0x14)
    at = u32(base+(c.identity&0xFFF)*52)
    for i in range(52):m.setdefault(u32(at+i),(i*29+c.seed*11+90)&255)
    wr(m,COUNT,c.count);wr(m,POINTER,base)
    # Byte alias turns the pointer's low byte into 0xA0, an aligned second record.
    wr(m,PACKET+8,c.value);wr(m,PACKET+12,c.kind)
    return m


def reference(initial,c=Case(),order='big'):
    m = dict(initial);identity = c.identity&0xFFF
    if identity < rd(m,COUNT,4,order):
        if u32(c.value) != 0xFFFFFFFF:
            wr(m,u32(rd(m,POINTER,4,order)+identity*52+0x18),c.value,4,order)
        if u32(c.kind) != 0xFFFFFFFF:
            wr(m,u32(rd(m,POINTER,4,order)+identity*52+0x17),c.kind,1,order)
        wr(m,u32(rd(m,POINTER,4,order)+identity*52+0x1C),0,4,order)
    return m


class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=None,connected=None,arguments=None):
        super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,connected=connected,
                         arguments=tuple(map(u32,(c.identity,c.value,c.kind))) if arguments is None else arguments)
    def record_call(self,target):
        assert target == source.ENTRY,hex(target)
        args=tuple(map(u32,self.arguments(3)));self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):raise AssertionError('No opaque services in record updater')


def cases():
    for identity,count,value,kind in itertools.product((0,3,4,0xFFFFF003,0xFFFFFFFF),
            (0,4,0x80000000,0xFFFFFFFF),(0,0xFFFFFFFF,0x80000000),(0,0xFFFFFFFF,0x123400FF,0xFFFF00FF)):
        yield Case(identity,count,value,kind,seed=(identity^count^value^kind)&7)
    for phase in (0,8):
        yield Case(value=ALT,alias=1,phase=phase)
        yield Case(value=0xFFFFFFFF,kind=0xA0,alias=2,phase=phase)


def native_cases():
    return [Case(identity,count,value,kind) for identity,count,value,kind in itertools.product(
        (0,3,4,0xFFFFF003,0xFFFFF00F),(0,4,16),(0,0xFFFFFFFF,0x80000000),
        (0,0xFFFFFFFF,0xFF,0xABCD00FF,0x80000000))]


def native_harness(body=None):
    body=source.SELECTED if body is None else body
    prefix=(source.ROOT/source.SOURCE).read_text().split('extern GeneratedCDE80Record *D_800D3098;')[0]
    rows=[]
    for c in native_cases():
        rows.append('{0x%XU,%d,0x%XU,0x%XU}'%(u32(c.identity),c.count,u32(c.value),u32(c.kind)))
    return prefix+'''
GeneratedCDE80Record *D_800D3098;
s32 D_800D3094;
typedef char check_record_size[sizeof(GeneratedCDE80Record)==52?1:-1];
typedef char check_pointer_size[sizeof(void*)==4?1:-1];
static GeneratedCDE80Record records[16];
'''+body+'''
struct Input {u32 id; s32 count; u32 value,kind;};
static const struct Input inputs[]={'''+','.join(rows)+'''};
static int check(void) {
    unsigned i,j,k; u8 expected[sizeof records],*bytes=(u8*)records;
    for(i=0;i<sizeof inputs/sizeof inputs[0];i++) {
        const struct Input *p=&inputs[i];u32 id=p->id&0xFFF;
        for(j=0;j<sizeof records;j++)expected[j]=bytes[j]=(u8)(j*29+i*11+90);
        D_800D3094=p->count;D_800D3098=records;
        if(id<(u32)p->count){
            if(p->value!=0xFFFFFFFFU)for(k=0;k<4;k++)expected[id*52+0x18+k]=(u8)(p->value>>(k*8));
            if(p->kind!=0xFFFFFFFFU)expected[id*52+0x17]=(u8)p->kind;
            for(k=0;k<4;k++)expected[id*52+0x1C+k]=0;
        }
        func_150A2940(p->id,(s32)p->value,(s32)p->kind);
        for(j=0;j<sizeof records;j++)if(bytes[j]!=expected[j])return 1;
        if(D_800D3094!=p->count||D_800D3098!=records)return 2;
    }return 0;
}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
