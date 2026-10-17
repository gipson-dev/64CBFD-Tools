"""Typed native32 body: compare all initialized bytes, not padding guesses."""
from tools.experiments import game_fixed_transition_constructor as source

HEADER = '#include <ultra64.h>\n'+source.DECLARATIONS+'void *memcpy(void *,const void *,size_t);\n'
CALLER = '''#include <ultra64.h>
void func_150CF680(s16,u8,s32);
void invoke(s16 id,u8 slot,s32 context) { func_150CF680(id,slot,context); }
'''
DRIVER = HEADER+'''
s32 D_80082FA0;
static u8 buffer[192],observed[88],expected[88],wantedPayload[16];
static u32 arguments[6],calls,copies,outcome,unaligned;
void invoke(s16,u8,s32);
static void word(u8 *where,u32 value,u32 size) {
    u32 i; const u8 *bytes=(const u8 *)&value;
    for(i=0;i<size;i++) where[i]=bytes[i];
}
static int descriptorPadding(u32 i) { return i==17||i==66||i==67||(i>=69&&i<=71); }
void *memcpy(void *destination,const void *src,size_t size) {
    u8 *d=destination; const u8 *s=src; size_t i;
    copies++; for(i=0;i<size;i++) d[i]=s[i]; return destination;
}
void *func_1515548C(void *descriptor,s32 kind,s32 *pair,s32 mode,s32 size,u8 slot,s32 context) {
    u8 *d=descriptor,*event=buffer+16+unaligned; u32 i;
    arguments[0]=(u32)kind; arguments[1]=(u32)pair; arguments[2]=(u32)mode;
    arguments[3]=(u32)size; arguments[4]=slot; arguments[5]=(u32)context;
    calls++; for(i=0;i<88;i++) observed[i]=d[i];
    if(!outcome) return 0;
    for(i=0;i<88;i++) event[16+i]=d[i];
    event[104]=(u8)kind;
    return event;
}
static int check(void) {
    static const s16 ids[]={0,1,32767,-32768,-1,-32767};
    static const u8 slots[]={0,1,255};
    static const s32 contexts[]={0,(s32)0x8765ABCDu,-1};
    static const s32 views[]={0,255,65538,(s32)0x80000003u};
    u32 a,b,c,v,o,k,i,at,total=0,little=1; u8 wanted;
    if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(TransitionDescriptorFC5F0)!=88||
       sizeof(TransitionPayloadFC5F0)!=16||sizeof(TransitionViewFC5F0)!=4||
       __builtin_offsetof(TransitionDescriptorFC5F0,id)!=18||
       __builtin_offsetof(TransitionDescriptorFC5F0,view)!=68||
       __builtin_offsetof(TransitionDescriptorFC5F0,field54)!=84||
       __builtin_offsetof(TransitionPayloadFC5F0,field04)!=4||*(u8*)&little!=1) return 29;
    for(a=0;a<6;a++) for(b=0;b<3;b++) for(c=0;c<3;c++) for(v=0;v<4;v++) for(o=0;o<2;o++) for(k=0;k<2;k++) {
        D_80082FA0=views[v]; outcome=o; unaligned=k; calls=copies=0;
        for(i=0;i<192;i++) buffer[i]=(u8)(i*13+0xA5);
        for(i=0;i<88;i++) observed[i]=expected[i]=0xA5;
        for(i=0;i<16;i++) wantedPayload[i]=0xA5;
        word(expected+0,0xC3960000u,4); word(expected+4,0x42900000u,4);
        word(expected+8,0x40F00000u,4); word(expected+12,0x40F00000u,4);
        expected[16]=193; word(expected+18,(u16)ids[a],2); word(expected+20,49,2);
        word(expected+22,1,2); word(expected+24,255,2); expected[26]=8;
        for(i=27;i<36;i++) expected[i]=255;
        word(expected+36,0,4); word(expected+40,0x200004,4); word(expected+44,0x9F0601,4);
        word(expected+48,23,4); word(expected+52,68,4); word(expected+56,128,4); word(expected+60,32,4);
        expected[64]=0; expected[65]=10; expected[68]=(u8)views[v];
        word(expected+72,0x3F800000u,4); word(expected+76,0x3F800000u,4);
        word(expected+80,0,4); word(expected+84,0,4);
        wantedPayload[0]=0; word(wantedPayload+4,0,4); word(wantedPayload+8,0xC3960000u,4); word(wantedPayload+12,0,4);
        invoke(ids[a],slots[b],contexts[c]);
        if(calls!=1||copies!=outcome||D_80082FA0!=views[v]) return 22;
        if(arguments[0]!=12||arguments[1]||arguments[2]||arguments[3]!=16||
           arguments[4]!=slots[b]||arguments[5]!=(u32)contexts[c]) return 22;
        for(i=0;i<88;i++) if(!descriptorPadding(i)&&observed[i]!=expected[i]) return 22;
        at=16+unaligned;
        for(i=0;i<192;i++) {
            wanted=(u8)(i*13+0xA5);
            if(outcome&&i>=at+16&&i<at+104) {
                if(descriptorPadding(i-at-16)) continue;
                wanted=expected[i-at-16];
            } else if(outcome&&i==at+104) wanted=12;
            else if(outcome&&i>=at+112&&i<at+128) {
                u32 offset=i-at-112;
                if(offset>=1&&offset<=3) continue;
                wanted=wantedPayload[offset];
            }
            if(buffer[i]!=wanted) return 22;
        }
        total++;
    }
    return total==864?0:29;
}
void _start(void) {
    u32 code=check(); __asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory"); __builtin_unreachable();
}
'''


def controls(body):
    return dict(tag=body.replace('descriptor.tag = 0xC1','descriptor.tag = 0xC0'),
        id=body.replace('descriptor.id = id','descriptor.id = 0'),
        position=body.replace('72.0f','73.0f'),
        size=body.replace('descriptor.size1 = 0xFF','descriptor.size1 = 0xFE'),
        view=body.replace('descriptor.view.byte = D_80082FA0','descriptor.view.byte = 0'),
        kind=body.replace('&descriptor, 12,','&descriptor, 11,'),
        payload=body.replace('payload.field08 = -300.0f','payload.field08 = -299.0f'),
        short_copy=body.replace('&payload, 16','&payload, 15'),
        slot=body.replace('16, slot, context','16, 0, context'),
        context=body.replace('16, slot, context','16, slot, 0'))


ZERO_PADDING = source.SELECTED.replace('    event = func_1515548C',
    ''.join('    ((u8 *)&descriptor)[%d] = 0;\n'%i for i in (17,66,67,69,70,71))+
    ''.join('    ((u8 *)&payload)[%d] = 0;\n'%i for i in (1,2,3))+'    event = func_1515548C')
