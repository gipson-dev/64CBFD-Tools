"""Native32 SDK layout and defined-field observer; private padding stays unspecified."""
from tools.experiments import game_oriented_effect_parameters_candidates as c

def source(body):
    return '#include <ultra64.h>\n#include "structs.h"\n'+c.HEADERS+body+r'''
f32 D_800A0C24,D_800A0C28,D_800A0C2C,D_800A0C30;
static u32 expected[4],calls,failed;static u8 mode,owner[128];
static void (*callback)(struct260 *)=func_150DBC60;
typedef char input_size[sizeof(OrientedEffectInput)==88?1:-1];
typedef char position_size[sizeof(OrientedEffectPosition)==12?1:-1];
typedef char count_offset[__builtin_offsetof(OrientedEffectInput,countBase)==0x24?1:-1];
typedef char arguments_offset[__builtin_offsetof(OrientedEffectInput,argument3C)==0x3C?1:-1];
typedef char tail_offset[__builtin_offsetof(OrientedEffectInput,fixed55)==0x55?1:-1];
static u32 bits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
void func_15152F70(OrientedEffectInput*p,u8 m){
    calls++;
    if(m!=mode||bits(p->position.x)!=expected[0]||bits(p->position.y)!=expected[1]||bits(p->position.z)!=expected[2]||bits(p->field14Base)!=expected[3])failed=1;
    if(p->fieldCBase!=2.0f||p->field10Range!=2.0f||bits(p->field18Range)!=0||p->speedBase!=7.0f||p->speedRange!=5.0f)failed=2;
    if(p->countBase!=1||p->countRange!=2||p->firstAngleBase!=-75||p->firstAngleRange!=22||p->secondAngleBase!=-38||p->secondAngleRange!=35)failed=3;
    if(p->byteBase!=3||p->byteRange!=2||p->shortBase!=41||p->shortRange!=0||p->fixed38!=10||p->fixed39!=40||p->fixed54!=255||p->fixed55!=255)failed=4;
    if(p->argument3C!=1||p->argument40||p->argument44||p->argument48||p->argument4C||p->argument50)failed=5;
    /* Only defined fields are inspected; helper mutations exercise return ABI. */
    p->position.x=17.0f;p->fixed55=19;owner[12]^=255;D_800A0C24=19.0f;
}
static int run(void){
    const u32 v[]={0,0x80000000u,0x3f800000u,0xbf800000u,1,0x7f7fffffu,0x7f800000u,0xff800000u,0x7fc12345u,0xffc54321u};
    u32 a,b,k,j;
    for(a=0;a<256;a++)for(b=0;b<100;b++){
        mode=(u8)a;owner[12]=mode;owner[13]=mode^255;
        for(j=0;j<4;j++){k=(b+j*3)%10;expected[j]=v[k];}
        D_800A0C24=real(expected[0]);D_800A0C28=real(expected[1]);D_800A0C2C=real(expected[2]);D_800A0C30=real(expected[3]);
        callback((struct260 *)owner);if(failed)return (int)failed;
    }
    return calls==25600?0:6;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
