"""SDK native32 coverage with a byte-wise, little-endian reference model."""
from tools.experiments.game_reference_command_candidates import SELECTED
def harness(body=SELECTED):
    return r'''#include <ultra64.h>
#include "functions.h"
static u32 backing[256],expected[256];
static u32 calls,expect_calls;
void func_1516972C(struct102 *p) { calls++; ((u8 *)p)[0x18]^=0x5A; *(u32 *)((u8 *)p+0x1C)=0x87654321; }
'''+body+r'''
static u32 load(u8 *p) {return (u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
static void store(u8 *p,u32 n) {u32 i;for(i=0;i<4;i++)p[i]=(u8)(n>>(8*i));}
static void reference(u8 *r,u8 *q,u32 identity,u8 cmd) {
    u32 first,second,current,fire=0;int selected=-1;
    if(cmd==0||cmd==3||cmd==17) {
        if(cmd!=17||r[0x3D]==5)fire=load(r+0x1C)==load(q)||r[0x18]==q[4];
    } else if(cmd==22)fire=identity==load(r+0x1C);
    else if(cmd==45) {
        first=load(q);second=load(q+4);current=load(r+0x1C);
        if(first==current)selected=0;else if(second==current)selected=1;
        if(selected>=0){store(r+0x1C,selected?first:second);r[0x18]=q[9-selected];}
    }
    if(fire){expect_calls++;r[0x18]^=0x5A;store(r+0x1C,0x87654321);}
}
static int run(void) {
    u32 cmd,alias,scenario,state,high,i,current,first,second;u8 *r,*q,*er,*eq;
    static const s32 offsets[8]={512,56,64,80,84,88,92,96};
    static const u8 states[3]={0,5,255};
    for(cmd=0;cmd<256;cmd++)for(alias=0;alias<8;alias++)for(scenario=0;scenario<8;scenario++)for(state=0;state<3;state++)for(high=0;high<2;high++) {
        r=(u8 *)backing+64;q=(u8 *)backing+offsets[alias];er=(u8 *)expected+64;eq=(u8 *)expected+offsets[alias];
        for(i=0;i<sizeof(backing);i++)((u8 *)backing)[i]=(u8)(i*29+90);
        first=scenario==4?0:scenario==5?0xFFFFFFFF:scenario==6?(u32)r:0x11112222;
        second=scenario==4?0:scenario==5?0x80000000:0x33334444;
        current=scenario%3==0?first:scenario%3==1?second:0x55556666;
        if(scenario==3)current=(u32)q;
        store(q,first);store(q+4,second);q[8]=0x51;q[9]=0xA2;
        store(r+0x1C,current);r[0x18]=scenario%2?0x33:q[4];r[0x3D]=states[state];
        for(i=0;i<256;i++)expected[i]=backing[i];calls=expect_calls=0;
        reference(er,eq,(u32)q,(u8)cmd);
        func_151347CC((struct102 *)r,(s32 *)q,(u8)(cmd|(high?0xABCD0000:0)));
        if(calls!=expect_calls)return 10;
        for(i=0;i<256;i++)if(backing[i]!=expected[i])return 11;
    }
    /* No ignored command may inspect either incoming pointer. */
    func_151347CC((struct102 *)0,(s32 *)0,254);
    return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
