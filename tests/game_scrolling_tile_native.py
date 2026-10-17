"""Full SDK body and separately compiled typed native32 caller."""
HEADER = '''#include <ultra64.h>
extern s32 D_80088890, D_80088894, D_80088898, D_8008889C;
'''
CALLER = '''#include <ultra64.h>
Gfx *func_150CF5E8(Gfx *);
Gfx *invoke(Gfx *commands) { return func_150CF5E8(commands); }
'''
DRIVER = '''#include <ultra64.h>
s32 D_80088890, D_80088894, D_80088898, D_8008889C;
Gfx *invoke(Gfx *);
static Gfx buffer[8];
static int check(void) {
    u32 sample,phase,i,j,at,raw[4],expected[4],w0,w1,total=0;
    if(sizeof(void*)!=4||sizeof(Gfx)!=8||sizeof(s32)!=4||(-128>>7)!=-1) return 29;
    for(sample=0;sample<192;sample++) for(phase=0;phase<2;phase++) {
        for(j=0;j<4;j++) raw[j]=(sample+1)*(j+3)*1664525u+1013904223u*(j+1);
        if(sample<13) {
            static const s32 edges[]={0,1,127,128,129,-1,-127,-128,-129,2147483647,(-2147483647-1),8388480,-8388480};
            for(j=0;j<4;j++) raw[j]=(u32)edges[(sample+j*3)%13];
        }
        D_80088890=(s32)raw[0]; D_80088894=(s32)raw[1];
        D_80088898=(s32)raw[2]; D_8008889C=(s32)raw[3];
        for(i=0;i<8;i++) { buffer[i].words.w0=0xA5000000u+i; buffer[i].words.w1=0x5A000000u+i; }
        at=2+phase;
        if(invoke(&buffer[at])!=&buffer[at+2]) return 22;
        for(j=0;j<2;j++) {
            expected[j*2]=0xF2000000u|(((raw[j*2]>>7)&4095)<<12)|((raw[j*2+1]>>7)&4095);
            expected[j*2+1]=(j<<24)|0x47E47Eu;
        }
        for(i=0;i<8;i++) {
            w0=0xA5000000u+i; w1=0x5A000000u+i;
            if(i>=at&&i<at+2) { w0=expected[(i-at)*2]; w1=expected[(i-at)*2+1]; }
            if(buffer[i].words.w0!=w0||buffer[i].words.w1!=w1) return 22;
        }
        if((u32)D_80088890!=raw[0]||(u32)D_80088894!=raw[1]||
           (u32)D_80088898!=raw[2]||(u32)D_8008889C!=raw[3]) return 22;
        total++;
    }
    return total==384?0:29;
}
void _start(void) {
    u32 code=check(); __asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory"); __builtin_unreachable();
}
'''


def controls(body):
    return dict(shift=body.replace('D_80088890 >> 7','D_80088890 >> 6'),
        wrong_first_s=body.replace('D_80088890 >> 7','D_80088894 >> 7'),
        wrong_second_s=body.replace('D_80088898 >> 7','D_80088890 >> 7'),
        wrong_second_t=body.replace('D_8008889C >> 7','D_80088894 >> 7'),
        tile=body.replace('commands++, 1,','commands++, 2,'),
        limit=body.replace('0x47E','0x47F',1),
        cursor=body.replace('return commands;','return commands - 1;'),
        first_tile=body.replace('commands++, 0,','commands++, 1,'))
