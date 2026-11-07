"""Independent little-endian coherent byte fixtures for the recovered SDK view."""
from functools import lru_cache
from tools.experiments import game_record_state_dispatch_150a24c0_candidates as c
from tools.tests import game_record_state_dispatch_150a24c0_oracle as g
def digest(values):
    h=2166136261
    for v in values:h=((h^v)*16777619)&0xFFFFFFFF
    return h
def trace(calls):
    return digest(b for t,args in calls for v in(t,len(args),*args)for b in g.u32(v).to_bytes(4,'little'))
def cases():
    for case in g.cases():
        if case.alias==0:yield case
@lru_cache(None)
def rows():
    values=[]
    for case in cases():
        initial=g.fixture(case,'little');e=g.reference(initial,case,'little',guest=False)
        values.append('{%s}'%','.join('0x%Xu'%g.u32(v)for v in(case.selector,case.phase_byte,case.mode,case.pattern,case.result,case.mutation,digest(g.data(e['memory'],g.RECORD,52)),trace(e['calls']))))
    return ',\n'.join(values)
def harness(body=None):
    return '#include <ultra64.h>\n'+c.RECORD_VIEW+'\n'+c.SUPPORT+(c.SELECTED if body is None else body)+r'''
typedef char RecordSize[sizeof(GeneratedCDE80Record)==52?1:-1];
typedef char ModeOffset[__builtin_offsetof(GeneratedCDE80Record,field17)==23?1:-1];
typedef char Word18Offset[__builtin_offsetof(GeneratedCDE80Record,field18)==24?1:-1];
typedef char StateOffset[__builtin_offsetof(GeneratedCDE80Record,field1C)==28?1:-1];
typedef char ExtraOffset[__builtin_offsetof(GeneratedCDE80Record,field20)==32?1:-1];
typedef struct {u32 selector,low,mode,pattern,result,mutation,hash,trace;} Case;
static const Case cases[]={
'''+rows()+r'''};
static u32 arena[13];static u8 *p=(u8 *)arena;static const Case *current;static u32 traceHash;
static void wr(u32 offset,u32 v,u32 n){u32 i;for(i=0;i<n;i++){p[offset+i]=(u8)v;v>>=8;}}
static void mix(u32 v){u32 i;for(i=0;i<4;i++){traceHash=(traceHash^(u8)v)*16777619u;v>>=8;}}
s32 func_15183290(s32 a,s32 b,s32 d,u8 e,s32 f,s32 h,s32 j,s32 k,s32 l,s32 n,s32 o){
    u32 args[11]={(u32)a,(u32)b,(u32)d,e,(u32)f,(u32)h,(u32)j,(u32)k,(u32)l,(u32)n,(u32)o},i;
    mix(0x15183290);mix(11);for(i=0;i<11;i++)mix(args[i]);
    if(current->mutation&1)p[23]=9;if(current->mutation&2)p[23]=2;
    if(current->mutation&4)wr(28,0x76543210,4);
    if(current->mutation&8){wr(0,0x13572468,4);wr(24,0x2468ACE0,4);wr(32,0xDEADBEEF,4);}
    return(s32)current->result;
}
static const u32 coords[3][4]={{0x8000,0x7FFF,0xFFFF,0x8001},{0x7FFF,0x8000,0,0x7FFF},{0,0x1234,0x8001,0}};
static const u32 properties[3]={0xFEDCBA98,0x800100FF,0x7FFF00A5},states[3]={0xABCD0100,0x0011FF00,0xFFEEDD00},extras[3]={0x80000001,0xFFFFFFFF,0x12345678};
int main(void){u32 i,j,h;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
    current=&cases[i];for(j=0;j<52;j++)p[j]=(u8)(j*29+90);for(j=0;j<4;j++)wr(j*2,coords[current->pattern][j],2);
    p[23]=(u8)current->mode;wr(24,properties[current->pattern],4);wr(28,states[current->pattern]|current->low,4);wr(32,extras[current->pattern],4);
    traceHash=2166136261u;func_150A24C0((GeneratedCDE80Record *)p,(s32)current->selector);
    h=2166136261u;for(j=0;j<52;j++)h=(h^p[j])*16777619u;if(h!=current->hash||traceHash!=current->trace)return 1;
}return 0;}
void _start(void){int answer=main();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''
