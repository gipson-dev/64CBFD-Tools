"""SDK native32 callback, all selector bytes, mutable tables, checked controls."""
from tools.experiments import game_selector_table_payload_candidates as source
from tools.tests import game_selector_table_payload_oracle as g
def program():
    controls=g.controls();assert len(controls)==10 and len(set(controls.values()))==10
    text='#include <ultra64.h>\n#include <string.h>\n#include "structs.h"\n'+source.TYPES
    text+='s32 D_800A670C[3][3],D_800A6730[3][3];f32 D_800A6754[3];\n'
    text+='struct225 *func_1516037C(Header *,struct226 *,s32,u8,s32);\n'+source.SELECTED+'\n'
    for name,body in controls.items():text+=body.replace(source.FUNCTION,'negative_'+name)+'\n'
    text+=r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(Header)==6&&sizeof(SelectorPayload151623F4)==32&&__builtin_offsetof(SelectorPayload151623F4,phase)==24&&__builtin_offsetof(SelectorPayload151623F4,rate)==28)?1:-1];
static const u32 raw[]={0,0x80000000u,1,0x007FFFFFu,0x00800000u,0x3F800000u,0xBF800000u,0x7F7FFFFFu,0x7F800000u,0xFF800000u,0x7FC12345u,0x7F812345u};
static union{struct225 record;u32 align[32];u8 b[128];}output;
static u32 seed,selector,allocated,mode,calls,copies,error,expected[8];static struct226*actor;
static void bytes(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static u32 word(const void*p){u32 x;bytes(&x,p,4);return x;}
static void set(void*p,u32 x){bytes(p,&x,4);}
static u32 value(u32 table,u32 i){return raw[(seed+i*5+table*7)%12];}
static void fill(u32 changed){u32 i;for(i=0;i<9;i++){set((u8*)D_800A670C+4*i,value(0,i)^changed);set((u8*)D_800A6730+4*i,value(1,i)^changed);}for(i=0;i<3;i++)set(&D_800A6754[i],value(2,i)^changed);}
__attribute__((noinline,noclone)) struct225*func_1516037C(Header*h,struct226*a,s32 size,u8 priority,s32 user){
    if(calls++||copies||selector>=3||a!=actor||size!=32||h->unk0!=(s8)(seed*73)||h->unk1!=(s8)(seed*109+128)||
       h->unk2!=(s16)((seed&1)?0x7FFF:0x8000)||h->unk4!=(s8)(seed*37+255)||priority!=(u8)(seed*53+255)||(u32)user!=seed*1664525u+1013904223u)error=1;
    if(mode)fill(0xA5A5A5A5u);
    if(!allocated)return 0;
    bytes(output.b+14,h,6);set(output.b+20,(u32)a);return &output.record;
}
__attribute__((noinline,noclone)) void*memcpy(void*d,const void*s,size_t n){
    u32 i;if(copies++||calls!=1||!allocated||d!=output.b+24||n!=32){error=1;return d;}
    for(i=0;i<8;i++)if(word((const u8*)s+4*i)!=expected[i])error=1;
    bytes(d,s,(u32)n);return d;
}
typedef struct225*(*Callback)(struct226*,u8,u8,u8,s8,s16,u8,s32);
static Callback functions[]={'''+','.join([source.FUNCTION,*['negative_'+n for n in controls]])+r'''};
static int run(void){
    u32 n,k,j,o,m,i,same,killed=0,valid;struct225*r;
    for(n=0;n<256;n++)for(k=0;k<256;k++)for(o=0;o<2;o++)for(m=0;m<2;m++)for(j=0;j<11;j++){
        seed=n;selector=k;allocated=o;mode=m;actor=(n&1)?(struct226*)&output:0;valid=k<3;calls=copies=error=0;fill(0);
        for(i=0;i<128;i++)output.b[i]=(u8)(i*17+seed);
        if(valid){for(i=0;i<3;i++){expected[i]=value(0,3*k+i);expected[3+i]=value(1,3*k+i);}expected[6]=0;expected[7]=value(2,k);}
        r=functions[j](actor,(u8)k,(u8)(n*37+255),(u8)(n*73),(s8)(n*109+128),(s16)((n&1)?0x7FFF:0x8000),(u8)(n*53+255),(s32)(n*1664525u+1013904223u));
        same=!error&&r==(valid&&o?&output.record:0)&&calls==valid&&copies==(valid&&o);
        for(i=0;i<128;i++){
            if(valid&&o&&i>=14&&i<56)continue;
            if(output.b[i]!=(u8)(i*17+n))same=0;
        }
        if(valid&&o){
            if(output.b[14]!=(u8)(n*73)||output.b[15]!=(u8)(n*109+128)||output.b[18]!=(u8)(n*37+255)||word(output.b+20)!=(u32)actor)same=0;
            {s16 life;bytes(&life,output.b+16,2);if(life!=(s16)((n&1)?0x7FFF:0x8000))same=0;}
            for(i=0;i<8;i++)if(word(output.b+24+4*i)!=expected[i])same=0;
        }
        for(i=0;i<9;i++)if(word((u8*)D_800A670C+4*i)!=(value(0,i)^((valid&&m)?0xA5A5A5A5u:0))||word((u8*)D_800A6730+4*i)!=(value(1,i)^((valid&&m)?0xA5A5A5A5u:0)))same=0;
        for(i=0;i<3;i++)if(word(&D_800A6754[i])!=(value(2,i)^((valid&&m)?0xA5A5A5A5u:0)))same=0;
        if(!same){if(!j)return 42;killed|=1u<<(j-1);}
    }return killed==1023?0:43;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''
    return text,list(controls),256*256*2*2
