"""Native32 finite fixtures serialized from the independent float32 model."""
from functools import lru_cache
from tools.experiments import game_resource_scroll_update_1513beb0_candidates as c
from tools.tests import game_resource_scroll_update_1513beb0_oracle as g

def cases():return tuple(case for case in g.cases()if case.alias==0)
def digest(data):
    h=2166136261
    for v in data:h=((h^v)*16777619)&0xFFFFFFFF
    return h
def bytes_at(m):return b''.join(g.fp.data(m,a,n)for a,n in g.REGIONS)
def trace(calls):return b''.join(g.u32(v).to_bytes(4,'little')for t,a in calls for v in(t,len(a),*a))
@lru_cache(None)
def rows():
    result=[]
    for case in cases():
        initial=g.fixture(case,'little');e=g.reference(initial,case,'little')
        values=[case.sine,case.mutation,digest(bytes_at(e['memory'])),digest(trace(e['calls'])),e['value']]
        result.append('{'+','.join('0x%Xu'%v for v in values)+',{'+','.join(str(v)for v in bytes_at(initial))+'}}')
    return ',\n'.join(result)

def harness(body=None):
    return '#include <ultra64.h>\n'+c.DECLARATIONS+'\nextern f32 D_800BE9A4,D_800A56A4;\nf32 func_15144B68(f32);\n'+(c.SELECTED if body is None else body)+r'''
typedef char Pointer32[sizeof(void *)==4?1:-1];
typedef char Float32[sizeof(f32)==4?1:-1];
static u8 resource[2048] __attribute__((section(".resource"),used,aligned(8)));
static u32 coeff[16] __attribute__((section(".coeff"),used,aligned(4)));
static u32 timing[16] __attribute__((section(".timing"),used,aligned(4)));
static u32 limit[4] __attribute__((section(".limit"),used,aligned(4)));
__asm__(".globl D_800A4A84\n.set D_800A4A84,coeff+16\n.globl D_800A4A88\n.set D_800A4A88,coeff+20\n.globl D_800A4A8C\n.set D_800A4A8C,coeff+24\n.globl D_800A4A90\n.set D_800A4A90,coeff+28\n.globl D_800A4A94\n.set D_800A4A94,coeff+32\n.globl D_800BE9A4\n.set D_800BE9A4,timing+16\n.globl D_800A56A4\n.set D_800A56A4,limit+4\n");
typedef struct{u32 sine,mutation,hash,trace,value;u8 bytes[2192];}Case;
static const Case cases[]={
'''+rows()+r'''};
static const Case *current;static u32 traceHash;
static u32 word(f32 f){union{f32 f;u32 w;}u;u.f=f;return u.w;}
static f32 value(u32 w){union{f32 f;u32 w;}u;u.w=w;return u.f;}
static void mix(u32 v){u32 i;for(i=0;i<4;i++){traceHash=(traceHash^(u8)v)*16777619u;v>>=8;}}
static void begin(u32 t,u32 n){mix(t);mix(n);}
static void wr(u8 *p,u32 w){u32 i;for(i=0;i<4;i++){p[i]=(u8)w;w>>=8;}}
f32 func_15144B68(f32 angle){begin(0x15144B68,1);mix(word(angle));while(D_800A56A4<angle)angle-=D_800A56A4;while(angle<0.0f)angle+=D_800A56A4;return angle;}
f32 sinf(f32 angle){
    begin(0x15047D60,1);mix(word(angle));
    if(current->mutation==1){D_800BE9A4=2.5f;D_800A4A90=0.5f;D_800A4A94=-0.25f;}
    if(current->mutation==2){wr(resource+0x304,word(-18.0f));wr(resource+0x308,word(19.0f));wr(resource+0x50,0x400);}
    if(current->mutation==3)wr(resource+0x2F8,word(-8193.5f));
    return value(current->sine);
}
static int run(void){u8 *p[4]={resource,(u8 *)coeff,(u8 *)timing,(u8 *)limit};u32 n[4]={2048,64,64,16};u32 i,j,k,at,h,v;
    if((u32)resource!=0x50000||(u32)&D_800A4A84!=0x800A4A84||(u32)&D_800BE9A4!=0x800BE9A4||(u32)&D_800A56A4!=0x800A56A4)return 2;
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        current=&cases[i];at=0;for(k=0;k<4;k++)for(j=0;j<n[k];j++)p[k][j]=current->bytes[at++];
        traceHash=2166136261u;v=(u32)func_1513BEB0(resource);h=2166136261u;
        for(k=0;k<4;k++)for(j=0;j<n[k];j++)h=(h^p[k][j])*16777619u;
        if(h!=current->hash||traceHash!=current->trace||v!=current->value)return 1;
    }return 0;
}
void _start(void){int answer=run();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''

LINK_FLAGS=['-Wl,--section-start=.resource=0x50000,--section-start=.coeff=0x800A4A74,--section-start=.timing=0x800BE994,--section-start=.limit=0x800A56A0']
