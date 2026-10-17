"""Full native32 body, independent ordered reference and effective controls."""
from tools.tests import game_overlay_defaults_oracle as model

HEADER = '''#include <ultra64.h>
extern union ResetArena { u32 words[256]; float values[256]; unsigned char bytes[1024]; } arena;
extern unsigned locations[11];
'''
for i, name in enumerate(model.NAMES):
    kind = 'f32' if name in (model.SCALE,model.PROJECTED,model.CONSTANT,model.SPEED) else 's32' if name in (model.DURATION,model.COUNTER) else 'u8'
    cast = 'f32 (*)[2]' if name == model.PROJECTED else kind+' *'
    HEADER += '#define %s ((%s)(arena.bytes + locations[%d]))%s\n' % (name,cast,i,'[0]' if name in (model.MODE,model.CONSTANT) else '')

CALLER = '''#include <ultra64.h>
void func_15181E18(s32 channel);
void reset_caller(s32 channel) { func_15181E18(channel); }
'''

DRIVER = '''#include <ultra64.h>
union ResetArena { u32 words[256]; float values[256]; unsigned char bytes[1024]; } arena;
unsigned locations[11];
void reset_caller(s32 channel);
static void store(unsigned char *p, unsigned at, u32 word) {
    unsigned i; for(i=0;i<4;i++) p[at+i]=(unsigned char)(word>>(i*8));
}
static u32 load(const unsigned char *p, unsigned at) {
    return p[at]|(u32)p[at+1]<<8|(u32)p[at+2]<<16|(u32)p[at+3]<<24;
}
static void reference(unsigned char *p, int channel) {
    if (p[locations[0]]) {
        p[locations[1]+channel*3]=0; p[locations[1]+channel*3+1]=0; p[locations[1]+channel*3+2]=0;
        store(p,locations[2]+channel*4,25); store(p,locations[3]+channel*4,0);
        p[locations[4]+channel]=0; p[locations[5]+channel]=0;
    } else {
        p[locations[6]+channel]=1; store(p,locations[7]+channel*4,0x3F800000);
        store(p,locations[8]+channel*8,0); store(p,locations[8]+channel*8+4,0);
        store(p,locations[10]+channel*4,load(p,locations[9]));
    }
}
static int check(void) {
    static const u32 constants[]={0xBB83126F,0x80000000,0x7FC12345,0x7F800000,0x3F800000};
    static const unsigned flags[]={0,1,2,255};
    unsigned char expected[1024]; unsigned c,f,k,a,s,i;
    if(sizeof(void*)!=4||sizeof(u32)!=4) return 29;
    arena.words[0]=0x01020304; if(arena.bytes[0]!=4) return 29;
    for(c=0;c<4;c++) for(f=0;f<4;f++) for(k=0;k<5;k++) for(a=0;a<4;a++) for(s=0;s<2;s++) {
        for(i=0;i<11;i++) locations[i]=32+i*64;
        if(a==1) locations[9]=locations[8]+c*8;
        if(a==2) locations[9]=locations[7]+c*4;
        if(a==3) for(i=1;i<11;i++) locations[i]=128;
        for(i=0;i<sizeof(arena.bytes);i++) arena.bytes[i]=(unsigned char)(i*13+s*37+0xA5);
        store(arena.bytes,locations[9],constants[k]); arena.bytes[locations[0]]=(unsigned char)flags[f];
        for(i=0;i<sizeof(expected);i++) expected[i]=arena.bytes[i];
        reference(expected,c); reset_caller(c);
        for(i=0;i<sizeof(expected);i++) if(expected[i]!=arena.bytes[i]) return 22;
    }
    return 0;
}
void _start(void) {
    u32 code=check(); __asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory"); __builtin_unreachable();
}
'''


def controls(body):
    return dict(mode=body.replace('D_800BE616 != 0','D_800BE616 == 1'),
        wide_clear=body.replace('color[2] = 0;','color[2] = 0;\n        color[3] = 0;'),
        duration=body.replace('= 25;','= 24;'), enabled=body.replace('D_800DDE3C[channel] = 1','D_800DDE3C[channel] = 0'),
        scale=body.replace('= 1.0f;','= 0.0f;'), omitted_second=body.replace('projected[1] = 0.0f;',''),
        constant=body.replace('= D_800A72B4;','= 0.0f;'),
        early_constant=body.replace('    u8 *color;','    f32 captured = D_800A72B4;\n    u8 *color;').replace(
            'D_800DDDD8[channel] = D_800A72B4','D_800DDDD8[channel] = captured'))
