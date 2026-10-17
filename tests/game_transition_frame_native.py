"""Typed native32 full-body checks; little-endian word reads are not N64 proof."""
from tools.experiments import game_transition_frame_lifetimes as source

HEADER = '#include <ultra64.h>\n'+source.previous.previous.DECLARATIONS+source.previous.DECLARATIONS+'''
void *memcpy(void *,const void *,size_t);
'''
CALLER = '''#include <ultra64.h>
s32 func_150CF800(u8 *);
s32 invoke(u8 *record) { return func_150CF800(record); }
'''
DRIVER = HEADER+'''
typedef struct {
    u8 field00,context,pad02[10],slot,pad0D[3];
    BurstPositionFC5F0 position;
    u8 pad18[88];
    TransitionPayloadFC5F0 transition;
} Record;
typedef struct { u32 before[4]; Record record; u32 after[4]; } Root;
static Root actual,wanted;
static BurstDescriptorFC5F0 descriptors[5];
static BurstPayloadFC5F0 payloads[5];
static u8 buffers[5][160];
static s16 angles[5];
static f32 speeds[5];
static u32 seed,pattern,effect,rng,floats,vectors,factories,copies,failed;
static u32 count,expectedRng,expectedFloats;
s32 D_80082FA0;
f32 D_800BE9A4;
static u8 tag29(void) { return 29; }
static u8 tag117(void) { return 117; }
u8 (*D_8008FCD0[])(void)={tag117,tag117,tag29};
s32 invoke(u8 *);

static void bytes(void *dest,const void *src,u32 size) {
    u32 i; u8 *d=dest; const u8 *s=src;
    for(i=0;i<size;i++) d[i]=s[i];
}
static u32 word(f32 value) { union { f32 f; u32 w; } u; u.f=value; return u.w; }
static u32 integer(u32 index) { return seed+index*1664525u+1013904223u; }
static f32 real(u32 index) {
    static const f32 values[]={0.0f,0.25f,0.5f,0.75f,1.0f};
    return values[(seed%5u+index%5u)%5u];
}
static u32 succeeds(u32 index) { return pattern==1||(pattern==2&&index%2==0); }
static int padding(u32 i) { return i==17||i==66||i==67||(i>=69&&i<=71); }
static void mutate(Record *record,u32 index) {
    if(index==0&&effect==1) {
        record->position.x=123.0f; record->position.y=-67.0f;
        record->transition.field04=0.625f; record->transition.field08=7.0f;
        record->transition.field0C=-3.0f; record->context=201; record->slot=253;
    }
}
s32 func_150ADA20(void) { return (s32)integer(rng++); }
f32 func_150ADA68(void) { return real(floats++); }
void func_15143874(s16 angle,f32 speed,f32 *x,f32 *y) {
    if(vectors>=count||angle!=angles[vectors]||word(speed)!=word(speeds[vectors])||y!=x+1) failed=1;
    *x=speed*-0.25f; *y=speed*0.5f;
    mutate(&actual.record,vectors);
    if(vectors==0&&effect==2) {
        D_80082FA0=(s32)0xABCDEF80u; D_800BE9A4=-8.0f; D_8008FCD0[2]=tag117;
    }
    vectors++;
}
f32 sinf(f32 value) { return value*0.125f; }
void *memcpy(void *dest,const void *src,size_t size) {
    if(size!=16||factories==0||dest!=buffers[factories-1]+128) failed=1;
    copies++; bytes(dest,src,size); return dest;
}
void *func_1515548C(void *descriptor,s32 kind,s32 *pair,s32 mode,s32 size,u8 slot,s32 context) {
    u32 i,n=factories++; const u8 *got=descriptor,*expected;
    if(n>=count) { failed=1; return 0; }
    expected=(const u8 *)&descriptors[n];
    if(kind!=13||pair||mode||size!=16||slot!=actual.record.slot||context!=actual.record.context) failed=1;
    for(i=0;i<88;i++) if(!padding(i)&&got[i]!=expected[i]) failed=1;
    if(!succeeds(n)) return 0;
    bytes(buffers[n]+32,descriptor,88); buffers[n][120]=13;
    return buffers[n]+16;
}

static void reference(f32 timestep) {
    u32 i,j=0,k=0; Record *r=&wanted.record;
    f32 fraction,oldX,oldY,floor,speed,scale;
    count=0;
    if(r->transition.state&1) {
        fraction=r->transition.field04+0.1900000125f*timestep;
        r->transition.field04=fraction;
        if(fraction>=1.0f) {
            r->transition.field04=1.0f; r->transition.state&=254;
            count=(integer(j++)&3)+2;
            oldX=r->position.x; oldY=r->position.y; floor=oldY+15.0f;
            for(i=0;i<count;i++) {
                BurstDescriptorFC5F0 *d=&descriptors[i];
                BurstPayloadFC5F0 *p=&payloads[i];
                u32 b; u8 *raw=(u8 *)d;
                for(b=0;b<88;b++) raw[b]=0;
                d->position.x=oldX; d->position.y=oldY;
                d->duration=integer(j++)%101u+155;
                d->tag=(effect==2&&i!=0)?117:29;
                angles[i]=(s16)(integer(j++)%65u-160);
                speed=real(k++)*2.0f+2.5f; speeds[i]=speed;
                p->velocityX=speed*-0.25f; p->velocityY=speed*0.5f;
                mutate(r,i);
                p->acceleration=real(k++)*0.3330000043f+0.4040000141f;
                scale=real(k++)*1.789999962f+1.699999928f;
                d->scale[0]=d->scale[1]=scale;
                d->id=integer(j++)%26u+30;
                d->flags=(integer(j++)&1)?2:0;
                d->flags|=((integer(j++)&1)?4:0)|0x39;
                d->size0=12; d->size1=21; d->kind=0;
                d->field1B=d->field1C=d->field1D=d->field1F=255;
                d->field20=d->field21=d->field22=d->opacity=255;
                d->field24=0; d->field28=0x200004; d->field2C=0x9F0601;
                d->field30=23; d->field34=68; d->field38=128; d->field3C=32;
                d->field40=0; d->field41=10; d->view.byte=0x23;
                d->field48=d->field4C=1.0f; d->field50=d->field54=0.0f;
                p->floor=floor;
            }
            fraction=r->transition.field04;
        }
        r->position.x=r->transition.field08+fraction*r->transition.field0C;
        r->position.y=(r->transition.field04*3.141592741f*0.125f)*-17.5f+72.0f;
    }
    expectedRng=j; expectedFloats=k;
}

static int run(void) {
    static const u8 states[]={0,1,128,255};
    static const f32 progress[]={-0.5f,0.9f,1.0f},ticks[]={-1.0f,1.0f};
    static const u32 seeds[]={0,1,2,3,0x80000000u,0xFFFFFFFFu};
    u32 a,b,t,s,p,m,i,n,at,total=0,expectedCopies,little=1;
    u8 wantedByte,*raw;
    if(sizeof(void*)!=4||sizeof(Record)!=128||sizeof(Root)!=160||sizeof(BurstDescriptorFC5F0)!=88||
        sizeof(BurstPayloadFC5F0)!=16||__builtin_offsetof(Record,transition)!=112||*(u8 *)&little!=1) return 29;
    for(a=0;a<4;a++) for(b=0;b<3;b++) for(t=0;t<2;t++) for(s=0;s<6;s++) for(p=0;p<3;p++) for(m=0;m<4;m++) {
        seed=seeds[s]; pattern=p; effect=m; raw=(u8 *)&actual;
        for(i=0;i<sizeof(actual);i++) raw[i]=(u8)(i*13+0xA5);
        actual.record.context=129; actual.record.slot=255;
        actual.record.position.x=-12.25f; actual.record.position.y=44.5f;
        actual.record.transition.state=states[a]; actual.record.transition.field04=progress[b];
        actual.record.transition.field08=-300.0f; actual.record.transition.field0C=450.0f;
        bytes(&wanted,&actual,sizeof(actual));
        D_80082FA0=(s32)0xABCD0123u; D_800BE9A4=ticks[t]; D_8008FCD0[2]=tag29;
        rng=floats=vectors=factories=copies=failed=0;
        for(n=0;n<5;n++) for(i=0;i<160;i++) buffers[n][i]=(u8)(i*7+n*11+0xA5);
        reference(ticks[t]);
        if(invoke((u8 *)&actual.record)!=1||failed||rng!=expectedRng||floats!=expectedFloats||
            vectors!=count||factories!=count) return 22;
        expectedCopies=0;
        for(n=0;n<5;n++) {
            if(n<count&&succeeds(n)) expectedCopies++;
            for(i=0;i<160;i++) {
                wantedByte=(u8)(i*7+n*11+0xA5);
                if(n<count&&succeeds(n)) {
                    if(i>=32&&i<120) {
                        at=i-32; if(padding(at)) continue;
                        wantedByte=((u8 *)&descriptors[n])[at];
                    } else if(i==120) wantedByte=13;
                    else if(i>=128&&i<144) wantedByte=((u8 *)&payloads[n])[i-128];
                }
                if(buffers[n][i]!=wantedByte) return 22;
            }
        }
        if(copies!=expectedCopies) return 22;
        for(i=0;i<sizeof(actual);i++) if(((u8 *)&actual)[i]!=((u8 *)&wanted)[i]) return 22;
        if(D_80082FA0!=(effect==2&&count?(s32)0xABCDEF80u:(s32)0xABCD0123u)||
            word(D_800BE9A4)!=word(effect==2&&count?-8.0f:ticks[t])) return 22;
        total++;
    }
    return total==1728?0:29;
}
void _start(void) {
    u32 code=run(); __asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory"); __builtin_unreachable();
}
'''


def controls(body):
    return dict(
        word_gate=(body.replace('record[0x70] & 1','*(u32 *)(record + 0x70) & 1'),0),
        word_slot=(body.replace('16, record[0xC], record[1]','16, *(u32 *)(record + 0xC), record[1]'),0),
        child_count=(body.replace('(func_150ADA20() & 3) + 2','(func_150ADA20() & 3) + 1'),22),
        short_copy=(body.replace('child + 0x70, &payload, 16','child + 0x70, &payload, 15'),22),
        speed=(body.replace('* progress + 2.5f','* progress + 2.25f'),22),
        stale_progress=(body.replace('            progress = transition->field04;\n',''),22))
