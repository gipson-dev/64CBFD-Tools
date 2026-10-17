"""Native semantic fields exclude padding; this is not byte-match acceptance."""
from tools.experiments import game_overlay_fade_packet as source

HEADER = '#include <ultra64.h>\n'+source.DECLARATIONS
CALLER = '''#include <ultra64.h>
void func_15182670(u8,u8,u8,u8,s16,u8,u8,s32);
void invoke(u8 r,u8 g,u8 b,u8 alpha,s16 duration,u8 channel,u8 owner,s32 context) {
    func_15182670(r,g,b,alpha,duration,channel,owner,context);
}
'''
DRIVER = HEADER+'''
static u8 output[128];
static u32 observed[9],count,copies,outcome,misaligned;
void invoke(u8,u8,u8,u8,s16,u8,u8,s32);
void *func_15149130(s16 duration,s8 a,s8 b,s8 c,u8 d,u8 e,s32 size,u8 owner,s32 context) {
    observed[0]=(u32)(s32)duration; observed[1]=(u32)(s32)a; observed[2]=(u32)(s32)b;
    observed[3]=(u32)(s32)c; observed[4]=d; observed[5]=e; observed[6]=(u32)size;
    observed[7]=owner; observed[8]=(u32)context; count++;
    return outcome ? output+misaligned : 0;
}
void *memcpy(void *destination,const void *source,size_t size) {
    size_t i; u8 *d=destination; const u8 *s=source;
    copies++; for(i=0;i<size;i++) d[i]=s[i]; return destination;
}
static int check(void) {
    static const s16 durations[]={-32768,-1,0,1,2,15,255,32767};
    static const u8 alphas[]={0,1,200,255};
    static const s32 contexts[]={0,(s32)0x8765ABCDu,-1};
    u32 d,a,c,o,k,i,rate,active,expected[9],at,total=0; u8 red,green,blue,channel,owner,value;
    if(sizeof(void*)!=4||sizeof(OverlayFadePacket1AC2F0)!=8||
       __builtin_offsetof(OverlayFadePacket1AC2F0,channel)!=4||
       __builtin_offsetof(OverlayFadePacket1AC2F0,fade)!=6) return 29;
    for(d=0;d<8;d++) for(a=0;a<4;a++) for(c=0;c<3;c++) for(o=0;o<2;o++) for(k=0;k<2;k++) {
        red=(u8)(0xCC+d*13); green=(u8)(0x45+a*17); blue=(u8)(0xFF-c*31);
        channel=c?255:0; owner=(u8)(0x81+c); outcome=o; misaligned=k;
        for(i=0;i<128;i++) output[i]=(u8)(i*13+0xA5);
        count=copies=0; for(i=0;i<9;i++) observed[i]=0xA5A5A5A5u;
        invoke(red,green,blue,alphas[a],durations[d],channel,owner,contexts[c]);
        active=durations[d]>0;
        if(count!=active||copies!=(active&&outcome)) return 22;
        if(active) {
            expected[0]=(u32)(s32)durations[d]; expected[1]=0xFFFFFFFFu; expected[2]=0x39;
            expected[3]=3; expected[4]=1; expected[5]=0; expected[6]=8; expected[7]=owner; expected[8]=(u32)contexts[c];
            for(i=0;i<9;i++) if(observed[i]!=expected[i]) return 22;
            rate=alphas[a]/durations[d];
        } else rate=0;
        at=40+misaligned;
        for(i=0;i<128;i++) {
            value=(u8)(i*13+0xA5);
            if(active&&outcome&&i>=at&&i<at+8) {
                switch(i-at) {
                    case 0:value=red;break; case 1:value=green;break; case 2:value=blue;break;
                    case 3:value=alphas[a];break; case 4:value=channel;break;
                    case 5:continue;
                    case 6:value=(u8)rate;break; case 7:value=(u8)(rate>>8);break;
                }
            }
            if(output[i]!=value) return 22;
        }
        total++;
    }
    return total==384?0:29;
}
void _start(void) {
    u32 code=check(); __asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory"); __builtin_unreachable();
}
'''


def controls(body):
    return dict(duration_gate=body.replace('duration > 0','duration > 1'),
        wrong_blue=body.replace('packet.blue = blue','packet.blue = 0'),
        wrong_channel=body.replace('packet.channel = channel','packet.channel = 0'),
        quotient=body.replace('alpha / duration','alpha / (duration + 1)'),
        factory_kind=body.replace('duration, -1, 0x39','duration, -1, 0x38'),
        factory_duration=body.replace('func_15149130(duration,','func_15149130(1,'),
        owner=body.replace('0, 8, arg6, context','0, 8, 0, context'),
        short_copy=body.replace('&packet, 8','&packet, 7'))


ZERO_PADDING = source.SELECTED.replace('        packet.channel = channel;',
    '        packet.channel = channel;\n        ((u8 *)&packet)[5] = 0;')
