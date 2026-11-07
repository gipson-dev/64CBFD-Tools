"""Native32 SDK Vtx math with controlled sine services and independent hashes."""
from functools import lru_cache
import itertools,struct
from tools.experiments import game_resource_texture_callback_1513bbfc_candidates as c
from tools.tests import game_resource_texture_callback_1513bbfc_oracle as g
def cases():
    for layout,geometry,page,positions in itertools.product((0,1,2,3,4,5),(0,1),(0,1),(0,1)):
        yield g.Case(layout=layout,geometry=geometry,page=page,positions=positions)
    for value in(0.0,-0.0,1023.75,1024.0,1025.5,-1025.5,1048576.25,-1048576.25):
        yield g.Case(layout=4,scrollS=g.bits(value),scrollT=g.bits(-value))
    for mutation,view in itertools.product((1,2,3),(0,1,3)):yield g.Case(layout=4,mutation=mutation,view=view)
    for a,b in((0,0),(0x3F800000,0xBF800000),(0x80000000,0x3F000000)):
        yield g.Case(layout=4,sin0=a,sin1=b)
def digest(values):
    h=2166136261
    for v in values:h=((h^v)*16777619)&0xFFFFFFFF
    return h
@lru_cache(None)
def rows():
    rows=[]
    for case in cases():
        e=g.reference(g.fixture(case,'little'),case,'little');trace=[]
        for t,a in e['calls']:
            for v in(t,len(a),*a):trace.extend(g.u32(v).to_bytes(4,'little'))
        observed=b''.join(g.data(e['memory'],a,n)for a,n in((g.RESOURCE,16384),(g.BUFFER0,4096),(g.BUFFER1,4096),(g.CENTERS,196),(g.VIEWER,32)))+bytes([e['memory'][g.PAGE]])
        values=(case.view,case.page,case.layout,case.geometry,case.positions,case.mutation,case.seed,case.scrollS,case.scrollT,case.sin0,case.sin1,digest(observed),digest(trace),e['value'])
        rows.append('{'+','.join('0x%Xu'%g.u32(v)for v in values)+'}')
    return ',\n'.join(rows)
def harness(body=None):
    retained=','.join('0x%Xu'%w for w, in struct.iter_unpack('>I',g.retained_data()))
    return '#include <ultra64.h>\n'+c.DECLARATIONS+'\nextern u8 D_800BE9C0;\ns32 func_1513B968(s32,s16);\n'+(c.SELECTED if body is None else body)+r'''
typedef char VtxSize[sizeof(Vtx)==16?1:-1];
typedef char VtxST[__builtin_offsetof(Vtx,v.tc)==8?1:-1];
typedef char RangeSize[sizeof(TextureVertexRange168A90)==8?1:-1];
typedef char Pointer32[sizeof(void *)==4?1:-1];
typedef struct{u32 view,page,layout,geometry,positions,mutation,seed,scrollS,scrollT,sin0,sin1,hash,trace,value;}Case;
static const Case cases[]={
'''+rows()+r'''};
static const u32 retained[]={'''+retained+r'''};
static u32 resourceWords[4096] __attribute__((section(".resource"),used,aligned(8)));
static u32 bank0Words[1024] __attribute__((section(".bank0"),used,aligned(8)));
static u32 bank1Words[1024] __attribute__((section(".bank1"),used,aligned(8)));
static u32 viewerWords[8] __attribute__((section(".viewer"),used,aligned(8)));
static u32 textureWords[49] __attribute__((section(".texture_data"),used,aligned(4)));
__asm__(".globl D_800A49C0\n.set D_800A49C0,textureWords\n.globl D_800A4A2C\n.set D_800A4A2C,textureWords+108\n.globl D_800A4A74\n.set D_800A4A74,textureWords+180\n.globl D_800A4A78\n.set D_800A4A78,textureWords+184\n.globl D_800A4A7C\n.set D_800A4A7C,textureWords+188\n.globl D_800A4A80\n.set D_800A4A80,textureWords+192\n");
static u8 *resource=(u8 *)resourceWords,*bank0=(u8 *)bank0Words,*bank1=(u8 *)bank1Words,*viewData=(u8 *)viewerWords,*tableData=(u8 *)textureWords;
u8 D_800BE9C0;static const Case *current;static u32 traceHash,sineCalls;
static void mix(u32 v){u32 i;for(i=0;i<4;i++){traceHash=(traceHash^(u8)v)*16777619u;v>>=8;}}
static void begin(u32 t,u32 n){mix(t);mix(n);}
static u32 word(f32 f){union{f32 f;u32 w;}u;u.f=f;return u.w;}
static f32 value(u32 w){union{f32 f;u32 w;}u;u.w=w;return u.f;}
static void wr(u8 *p,u32 v,u32 n){u32 i;for(i=0;i<n;i++){p[i]=(u8)v;v>>=8;}}
static u32 rd(u8 *p){return(u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
static u8 *payload(void){return resource+rd(resource+0x50)+0xF8;}
static void effect(u32 t){
    if(current->mutation==1&&t==0x1513B968){wr(resource+0x50,0x400,4);wr(payload()+12,word(0.75f),4);}
    if(current->mutation==2&&t==0x15047D60&&sineCalls==1){wr(payload()+16,word(1.25f),4);wr(tableData+180,word(2.0f),4);wr(tableData+184,word(1.0f),4);wr(tableData+188,word(3.0f),4);wr(tableData+192,word(2.0f),4);}
    if(current->mutation==3&&t==0x15144B34){u8 *p=payload();wr(p,word(-2049.75f),4);wr(p+4,word(2050.25f),4);wr(resource+0x50,0x600,4);}
}
s32 func_1513B968(s32 record,s16 view){begin(0x1513B968,2);mix((u32)record);mix((u32)(s32)view);effect(0x1513B968);return 1;}
f32 sinf(f32 angle){begin(0x15047D60,1);mix(word(angle));sineCalls++;effect(0x15047D60);return value(sineCalls==1?current->sin0:current->sin1);}
f32 *func_15144B34(s32 view){begin(0x15144B34,1);mix((u32)view);effect(0x15144B34);return(f32 *)viewData;}
f32 sqrtf(f32 input){f32 output;__asm__("sqrtss %1,%0":"=x"(output):"x"(input));return output;}
static u32 hash(u32 h,u8 *p,u32 n){u32 i;for(i=0;i<n;i++)h=(h^p[i])*16777619u;return h;}
static int run(void){u32 i,j,k,h,v;u8 *p[4]={resource,bank0,bank1,viewData};u32 n[4]={16384,4096,4096,32};
    if((u32)resource!=0x50000||(u32)bank0!=0x60000||(u32)bank1!=0x70000||(u32)viewData!=0x90000||(u32)tableData!=0x800A49C0||(u32)&D_800A4A74!=(u32)(D_800A4A2C+9))return 2;
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        current=&cases[i];for(k=0;k<4;k++)for(j=0;j<n[k];j++)p[k][j]=(u8)(j*29+current->seed*11+90);
        for(j=0;j<49;j++)wr(tableData+4*j,retained[j],4);
        if(current->geometry)for(j=0;j<27;j++)wr(tableData+j*4,0,4);
        for(j=0;j<9;j++){
            u32 first=rd(tableData+108+8*j),count=rd(tableData+112+8*j);
            if(current->layout==1){first=j==0?0:j*2;count=j==0?2:0;}
            if(current->layout==2){first=j*4;count=0;}
            if(current->layout==3){first=j*4;count=0xFFFFFFFFu;}
            if(current->layout==4){first=j;count=1;}
            if(current->layout==5){first=0;count=2;}
            wr(tableData+108+j*8,first,4);wr(tableData+112+j*8,count,4);
        }
        for(k=1;k<=2;k++)for(j=0;j<160;j++){
            s32 x=(s32)(j*17%1000)-500,y=(s32)(j*7%500)-250,z=(s32)(j*31%1000)-500;
            if(current->positions){x=-32768;y=32767;z=0;}
            wr(p[k]+j*16,(u32)x,2);wr(p[k]+j*16+2,(u32)y,2);wr(p[k]+j*16+4,(u32)z,2);
        }
        wr(resource+0x50,0x200,4);D_800BE9C0=(u8)current->page;for(j=0;j<3;j++)wr(viewData+j*4,0,4);
        wr(resource+0x58+(s32)(s16)current->view*4,0x60000,4);wr(resource+0x68+(s32)(s16)current->view*4,0x70000,4);
        for(j=0;j<3;j++){u8 *a=resource+0x2F8+j*0x200;wr(a,current->scrollS,4);wr(a+4,current->scrollT,4);wr(a+8,0,4);wr(a+12,word(0.125f),4);wr(a+16,word(-0.5f),4);}
        traceHash=2166136261u;sineCalls=0;v=(u32)func_1513BBFC(resource,(s16)current->view);
        h=hash(2166136261u,resource,16384);h=hash(h,bank0,4096);h=hash(h,bank1,4096);h=hash(h,tableData,196);h=hash(h,viewData,32);h=hash(h,&D_800BE9C0,1);
        if(h!=current->hash||traceHash!=current->trace||v!=current->value)return 1;
    }return 0;
}
void _start(void){int answer=run();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}
'''
LINK_FLAGS=['-Wl,--section-start=.resource=0x50000,--section-start=.bank0=0x60000,--section-start=.bank1=0x70000,--section-start=.viewer=0x90000,--section-start=.texture_data=0x800A49C0']
