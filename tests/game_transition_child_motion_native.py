"""Typed native32 child motion, including real linker aliases of the live clock."""
from tools.experiments import game_transition_child_motion as source
HEADER='#include <ultra64.h>\n'+source.DECLARATIONS
CALLER='''#include <ultra64.h>
s32 func_150CFC60(u8 *);
s32 invoke(u8 *record) { return func_150CFC60(record); }
'''
DRIVER=HEADER+'''
typedef struct { u8 pad0[16]; f32 x,y; u8 pad18[88]; f32 vx,vy,acceleration,floor; } Record;
typedef struct { u32 before[4]; Record record; u32 after[4]; } Root;
Root actual;
static Root wanted;
#ifndef CLOCK_ALIAS
#define CLOCK_ALIAS 0
#endif
#if CLOCK_ALIAS == 1
__asm__(".globl D_800BE9A4\\n.set D_800BE9A4, actual + 32");
#elif CLOCK_ALIAS == 2
__asm__(".globl D_800BE9A4\\n.set D_800BE9A4, actual + 36");
#else
f32 D_800BE9A4;
#endif
f32 D_800A0878,D_800A087C;
s32 invoke(u8 *);
static u32 word(f32 value) { union { f32 f; u32 w; } u; u.f=value; return u.w; }
f32 fabsf(f32 value) { union { f32 f; u32 w; } u; u.f=value; u.w&=0x7FFFFFFFu; return u.f; }
static f32 clock_for(Root *r) {
    return CLOCK_ALIAS==1?r->record.x:CLOCK_ALIAS==2?r->record.y:D_800BE9A4;
}
static void reference(void) {
    Record *r=&wanted.record;
    f32 vy=r->vy,acc=r->acceleration,dt,step;
    dt=clock_for(&wanted); r->x=r->x+r->vx*dt;
    dt=clock_for(&wanted); step=vy*dt+((0.5f*acc)*dt)*dt; r->y=r->y+step;
    r->vy=vy+acc*clock_for(&wanted);
    if(r->floor<r->y) {
        r->y=r->floor; vy=fabsf(r->vy);
        r->vx=r->vx*D_800A0878; r->vy=vy*D_800A087C;
    }
}
static int run(void) {
    static const f32 clocks[]={0.0f,0.5f,1.0f,2.0f,-1.0f};
    static const f32 dampX[]={0.3f,0.0f,-0.5f},dampY[]={-0.15f,0.5f,-1.0f};
    u32 t,p,f,d,i,total=0; u8 *a=(u8 *)&actual,*w=(u8 *)&wanted;
    f32 dt,newY,vy,acc;
    if(sizeof(void*)!=4||sizeof(Record)!=128||sizeof(Root)!=160||
       __builtin_offsetof(Record,vx)!=112||__builtin_offsetof(Root,record)!=16) return 29;
    for(t=0;t<5;t++) for(p=0;p<8;p++) for(f=0;f<3;f++) for(d=0;d<3;d++) {
        for(i=0;i<sizeof(actual);i++) a[i]=(u8)(i*13+0xA5);
        actual.record.x=(f32)((s32)p-4); actual.record.y=(f32)((s32)p-3);
        actual.record.vx=(p&1)?-2.25f:1.5f;
        actual.record.vy=(p&2)?-3.0f:2.5f;
        actual.record.acceleration=(p&4)?-0.25f:0.4040000141f;
        D_800BE9A4=clocks[t]; D_800A0878=dampX[d]; D_800A087C=dampY[d];
        /* The assembler alias is opaque to C: refresh fixture bytes after its write. */
        __asm__ volatile("":::"memory");
        for(i=0;i<sizeof(actual);i++) w[i]=a[i];
        vy=wanted.record.vy; acc=wanted.record.acceleration;
        dt=clock_for(&wanted); wanted.record.x+=wanted.record.vx*dt;
        dt=clock_for(&wanted); newY=wanted.record.y+(vy*dt+((0.5f*acc)*dt)*dt);
        actual.record.floor=newY+(f==0?-1.0f:f==1?0.0f:1.0f);
        for(i=0;i<sizeof(actual);i++) w[i]=a[i];
        reference();
        if(invoke((u8 *)&actual.record)!=1) return 22;
        for(i=0;i<sizeof(actual);i++) if(a[i]!=w[i]) return 22;
        if(CLOCK_ALIAS&&word(D_800BE9A4)!=word(clock_for(&wanted))) return 22;
        total++;
    }
    return total==360?0:29;
}
void _start(void) {
    u32 code=run(); __asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory"); __builtin_unreachable();
}
'''


def controls(body):
    cached=body.replace('    f32 *motion;','    f32 *motion;\n    f32 clock = D_800BE9A4;').replace(' * D_800BE9A4',' * clock')
    return dict(inclusive_floor=body.replace('0x7C) <','0x7C) <='),
        no_absolute=body.replace('fabsf(motion[1])','motion[1]'),
        missing_half=body.replace('0.5f * acceleration','1.0f * acceleration'),cached_clock=cached)
