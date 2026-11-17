#include <ultra64.h>
typedef struct HeightResult71820 {f32 height;s16 vertices[9];s16 pad16;u32 metadata;u8 flags,state;u16 pad1E;s32 value;} HeightResult71820;
typedef struct HeightActor71820 HeightActor71820;
@DECLARATIONS@
f32 func_150ADA68(void);s32 func_150ADA20(void);
void func_1504715C(HeightResult71820 *,HeightActor71820 *);
struct Event {u32 target,count,args[16];u8 observed[60];};
struct Memory {u8 record[512],actor[512],other[512];u32 coefficients[3],marker;};
struct Row {u32 seed,route,mutation,phase,time;struct Memory initial,final;u32 count;struct Event calls[50];};
extern const struct Row fixture_rows[];
typedef struct {u8 prefix[14];s16 life;u8 middle[24];ActorAccumulator151AB9C8 state;u8 tail[444];} NativeRecord;
typedef struct {u32 active;u8 beforeXYZ[16];f32 xyz[3];u8 beforeID[27];u8 identity;u8 beforeValue[72];u16 value;u8 tail[378];} NativeActor;
typedef char CheckSizes[sizeof(NativeRecord)==512&&sizeof(NativeActor)==512&&sizeof(ActorAccumulator151AB9C8)==28&&sizeof(HeightResult71820)==36?1:-1];
static NativeRecord record;static NativeActor actors[2];static const struct Row *row;
f32 D_800BE9A4,D_800A9018,D_800A901C;
static u32 marker,callno,randomno,realno,emissions;static s32 bad;static HeightResult71820 *surface;static f32 *position,*velocity;
static void cp(void *d,const void *s,u32 n){u8 *a=d;const u8 *b=s;for(u32 i=0;i<n;i++)a[i]=b[i];}
static u32 word(f32 f){u32 w;cp(&w,&f,4);return w;}static f32 real(u32 w){f32 f;cp(&f,&w,4);return f;}
static u32 be(const u8 *p){return((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
static void setBE(u8 *p,u32 w){for(u32 i=0;i<4;i++)p[i]=(u8)(w>>(24-8*i));}
static void reverse(u8 *d,const u8 *s,u32 at,u32 size){for(u32 i=0;i<size;i++)d[at+i]=s[at+size-1-i];}
static void surfaceCodec(u8 *d,const u8 *s){
 cp(d,s,36);reverse(d,s,0,4);for(u32 i=4;i<=22;i+=2)reverse(d,s,i,2);reverse(d,s,24,4);reverse(d,s,30,2);reverse(d,s,32,4);
}
static void fillSurface(u32 n,s32 initial){
 u8 b[36];for(u32 i=0;i<36;i++)b[i]=(u8)(row->seed+(initial?i*7:n*11+i*3));surfaceCodec((u8*)surface,b);
}
static void effect(u32 t,u32 n){
 if((row->mutation&1)&&(t==0x150ada68||t==0x150ada20||t==0x151423d8)){
  NativeActor *a=&actors[n&1];record.state.actor=(u8*)a;
  for(u32 i=0;i<3;i++)a->xyz[i]=((s32)row->seed-100)*(s32)(i+1)*.125f+n*.5f;
  record.state.selector=(u8)(row->seed+n*13);record.prefix[12]=(u8)(row->seed+n*7);record.prefix[1]=(u8)(row->seed+n*5);
 }
 if((row->mutation&2)&&t==0x150ada68){D_800A9018=30.25f+n;D_800A901C=.125f;D_800BE9A4=.25f;if(n==0){record.state.rateBase=.5f;record.state.rateRange=.25f;record.state.time=2.25f;}}
 if((row->mutation&4)&&surface)fillSurface(n,0);
 if((row->mutation&8)&&position)for(u32 i=0;i<3;i++){position[i]=row->seed*.125f+n+i;velocity[i]=row->seed*.125f+n+i;}
 if((row->mutation&16)&&t==0x151d9014)record.state.time=emissions>=2?.25f:2.25f;
 marker=0x13579bdfu+n*0x10203u+t;
}
static void check(u32 t,const u32 *a,u32 count,const u8 *observed,u32 bytes){
 if(callno>=50){bad=1;return;}const struct Event *e=&row->calls[callno];if(e->target!=t||e->count!=count)bad=1;
 for(u32 i=0;i<count;i++)if(e->args[i]!=a[i])bad=1;for(u32 i=0;i<bytes;i++)if(e->observed[i]!=observed[i])bad=1;effect(t,callno++);
}
f32 func_150ADA68(void){check(0x150ada68,0,0,0,0);return((row->seed+realno++*37)%257)/256.f;}
s32 func_150ADA20(void){static const u32 values[]={0,0xffffffffu,0x80000000u,0x7fffffffu,25,26,100,101};u32 value=values[(row->seed+randomno)%8]+randomno*0x1020304u;randomno++;check(0x150ada20,0,0,0,0);return(s32)value;}
f32 func_151423D8(u8 angle){u32 a[]={angle};check(0x151423d8,a,1,0,0);return((s32)((angle*13+row->seed)%257)-128)/128.f;}
void func_1504715C(HeightResult71820 *out,HeightActor71820 *actor){
 surface=out;fillSurface(0,1);u32 at=actor==(HeightActor71820*)&actors[0]?0x60000:actor==(HeightActor71820*)&actors[1]?0x80000:0;
 u32 a[]={0xffffffe0,at};check(0x1504715c,a,2,0,0);
}
void *func_151D9014(void *p,f32 *v,u8 selector,f32 bias,s16 lifetime,u8 opacity,f32 size,u8 a7,f32 a8,f32 a9,u8 a10,s32 s,u8 a12,u8 a13,u8 slot,s32 context){
 if((void*)(u32)s!=surface)bad=1;position=p;velocity=v;u8 observed[60];
 for(u32 i=0;i<3;i++){setBE(observed+4*i,word(position[i]));setBE(observed+12+4*i,word(velocity[i]));}surfaceCodec(observed+24,(const u8*)surface);emissions++;
 u32 a[]={0xffffffe1,0xffffffe2,selector,word(bias),(u32)(s32)lifetime,opacity,word(size),a7,word(a8),word(a9),a10,0xffffffe0,a12,a13,slot,(u32)context};check(0x151d9014,a,16,observed,60);return 0;
}
static void setup(void){
 cp(&record,row->initial.record,512);record.life=(s16)((row->initial.record[14]<<8)|row->initial.record[15]);record.state.actor=(u8*)&actors[0];record.state.value=be(row->initial.record+48);record.state.time=real(be(row->initial.record+52));record.state.rateBase=real(be(row->initial.record+56));record.state.rateRange=real(be(row->initial.record+60));
 const u8 *b[2]={row->initial.actor,row->initial.other};for(u32 j=0;j<2;j++){cp(&actors[j],b[j],512);actors[j].active=be(b[j]);for(u32 i=0;i<3;i++)actors[j].xyz[i]=real(be(b[j]+20+4*i));actors[j].value=(u16)((b[j][132]<<8)|b[j][133]);}
 D_800BE9A4=real(row->initial.coefficients[0]);D_800A9018=real(row->initial.coefficients[1]);D_800A901C=real(row->initial.coefficients[2]);marker=row->initial.marker;
 callno=randomno=realno=emissions=bad=0;surface=0;position=velocity=0;
}
static int failure(u32 stage,u32 index){u32 v[]={(u32)(row-fixture_rows),stage,index,callno};__asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(v),"d"(16):"memory");return 3;}
@BODY@
static int run(void){
 for(u32 k=0;k<@COUNT@;k++){
  row=&fixture_rows[k];setup();invoke((u8*)&record);if(bad||callno!=row->count||marker!=row->final.marker)return failure(1,bad);
  u8 b[512];cp(b,&record,512);reverse(b,(const u8*)&record,14,2);setBE(b+40,record.state.actor==(u8*)&actors[0]?0x60000:record.state.actor==(u8*)&actors[1]?0x80000:0);setBE(b+48,record.state.value);setBE(b+52,word(record.state.time));setBE(b+56,word(record.state.rateBase));setBE(b+60,word(record.state.rateRange));
  for(u32 i=0;i<512;i++)if(b[i]!=row->final.record[i])return failure(2,i);
  const u8 *end[2]={row->final.actor,row->final.other};for(u32 j=0;j<2;j++){cp(b,&actors[j],512);setBE(b,actors[j].active);for(u32 i=0;i<3;i++)setBE(b+20+4*i,word(actors[j].xyz[i]));reverse(b,(const u8*)&actors[j],132,2);for(u32 i=0;i<512;i++)if(b[i]!=end[j][i])return failure(3+j,i);}
  if(word(D_800BE9A4)!=row->final.coefficients[0]||word(D_800A9018)!=row->final.coefficients[1]||word(D_800A901C)!=row->final.coefficients[2])return failure(5,0);
 }return 0;
}
