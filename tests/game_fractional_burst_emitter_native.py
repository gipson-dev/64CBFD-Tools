"""Typed native packets, live provider mutation and float-field global aliases."""
from tools.experiments import game_fractional_burst_emitter_candidates as c
from tools.tests import game_fractional_burst_emitter_oracle as g
from tools.tests.test_game_row_destination_fill import START
def cases():
    phases=(0,0x80000000,g.bits(-1.),0x3F7FFFFF,0x3F800000,0x3F800001,g.bits(2.),g.bits(3.25),g.bits(8.5),0x7FC12345,0xFF800000)
    for i in range(2048):yield g.Case(phase_value=phases[i%11],step=(0,g.bits(.5),g.bits(1.),g.bits(2.5))[i%4],
        tag=i&255,context=(i*37)&255,mode=(i//7)%16,random=(i//11)%7,alias=(0,1,2)[i%3],offset=(0x28,0x2C,0x30,0x38)[i//3%4])
def source(controls):
    rows=[]
    for case in cases():
        initial=g.fixture(case);wanted,calls=g.reference(initial,case);a=g.actor(case,g.syms());packets=[args for t,args in calls if t==g.EMIT]
        assert len(packets)<=9
        outs=[g.read(wanted,a+at)for at in(0x28,0x2C,0x30,0x38)]+[wanted[a+0x34],wanted[a+0xC],g.read(wanted,g.RATE),g.read(wanted,g.STEP)]
        head=(case.phase_value,case.step,case.rate,case.tag,case.context,case.mode,case.random,case.alias,case.offset)
        rows.append('{{%s},{%s},%d,{%s}}'%(','.join('0x%08Xu'%v for v in head),','.join('0x%08Xu'%v for v in outs),len(packets),','.join('{'+','.join('0x%08Xu'%v for v in p)+'}'for p in packets)or'{0}'))
    text='typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;\n#define NULL ((void*)0)\n'
    text+=c.DECLARATIONS.replace('extern f32 D_800A8D10, D_800BE9A4;','')
    text+='static f32 *rate,*step;\n#define D_800A8D10 (*rate)\n#define D_800BE9A4 (*step)\n'
    for name,body in dict(selected=c.SELECTED,**controls).items():text+=body.replace(c.FUNCTION,name)+'\n'
    text+='''
typedef char size_check[sizeof(FractionalBurstEmitter151A0AF8)==0x3C?1:-1];
typedef char payload_check[__builtin_offsetof(FractionalBurstEmitter151A0AF8,payload)==0x28?1:-1];
typedef char context_check[__builtin_offsetof(FractionalBurstEmitter151A0AF8,context)==0x0C?1:-1];
typedef char phase_check[__builtin_offsetof(FractionalBurstPayload151A0AF8,phase)==0x10?1:-1];
typedef char tag_check[__builtin_offsetof(FractionalBurstPayload151A0AF8,tag)==0x0C?1:-1];
typedef struct {u32 input[9],output[8],count,packets[9][12];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+'''};
static struct {u8 left[16];FractionalBurstEmitter151A0AF8 r;u8 right[16];} actual,expected;
static f32 externalRate,externalStep;static u32 n,event,bad,packets[20][12],mode,pattern;
typedef union {u32 u;f32 f;} Float;
static f32 real(u32 v){Float x;x.u=v;return x.f;}static u32 word(f32 v){Float x;x.f=v;return x.u;}
static int nanword(u32 x){return (x&0x7F800000u)==0x7F800000u&&(x&0x7FFFFFu)!=0;}
static int equalword(u32 a,u32 b){return a==b||(nanword(a)&&nanword(b));}
static f32 *field(FractionalBurstEmitter151A0AF8*p,u32 at){if(at==0x28)return &p->payload.x;if(at==0x2C)return &p->payload.y;if(at==0x30)return &p->payload.z;return &p->payload.phase;}
static void effect(int emit){FractionalBurstEmitter151A0AF8*p=&actual.r;if(n!=1)return;
 if(!emit){if(mode&1){p->payload.x=100.f;p->payload.y=101.f;p->payload.z=102.f;p->payload.tag=128;p->context=255;p->payload.phase=3.75f;}
 if(mode&2){*rate=4.f;*step=8.f;}}
 else{if(mode&4)p->payload.phase=.25f;if(mode&8){p->payload.x=200.f;p->payload.y=201.f;p->payload.z=202.f;p->payload.tag=255;p->context=128;}}
 }
__attribute__((noinline,noclone)) f32 func_150ADA68(void){static const u32 values[]={0,0x3E800000u,0x3F000000u,0x3F800000u,0xBF800000u,0x7FC12345u,0x7F800000u};
 if(event)bad=1;event=1;n++;if(n>16){bad=2;actual.r.payload.phase=0;return 0;}
 effect(0);return real(values[(pattern+n-1)%7]);}
__attribute__((noinline,noclone)) void func_1514C678(f32 x,f32 y,f32 z,f32 magnitude,s16 low,s16 high,s16 count,u8 kind,s32 tag,f32 zero,void*data,u8 context){
 u32 a[12]={word(x),word(y),word(z),word(magnitude),(u32)(s32)low,(u32)(s32)high,(u32)(s32)count,kind,(u32)tag,word(zero),(u32)data,context},i;
 if(event!=1||n==0||n>20){bad=3;return;}event=0;for(i=0;i<12;i++)packets[n-1][i]=a[i];effect(1);}
typedef void(*Handler)(FractionalBurstEmitter151A0AF8*);
__attribute__((noinline,noclone))static void invoke(Handler fn,FractionalBurstEmitter151A0AF8*p){fn(p);}
static int variant(Handler fn,u32 typed){u32 i,j,k,at;u8*p=(u8*)&actual,*q=(u8*)&expected;const Row*r;
 for(i=0;i<2048;i++){r=rows+i;for(j=0;j<sizeof(actual);j++)p[j]=(u8)(j*13+89);
 actual.r.payload.x=1.25f;actual.r.payload.y=-2.5f;actual.r.payload.z=real(0x80000000u);actual.r.payload.phase=real(r->input[0]);actual.r.payload.tag=(u8)r->input[3];actual.r.context=(u8)r->input[4];
 externalRate=real(r->input[2]);externalStep=real(r->input[1]);rate=&externalRate;step=&externalStep;
 if(r->input[7]==1)rate=field(&actual.r,r->input[8]);if(r->input[7]==2)step=field(&actual.r,r->input[8]);*rate=real(r->input[2]);*step=real(r->input[1]);
 for(j=0;j<sizeof(actual);j++)q[j]=p[j];
 for(j=0;j<4;j++){at=j<3?0x28+4*j:0x38;*field(&expected.r,at)=real(r->output[j]);}
 expected.r.payload.tag=(u8)r->output[4];expected.r.context=(u8)r->output[5];mode=r->input[5];pattern=r->input[6];n=event=bad=0;
 if(typed)invoke(fn,&actual.r);else if(fn==selected)selected(&actual.r);else fn(&actual.r);
 if(bad||event||n!=r->count)return 1;
 for(j=0;j<4;j++){at=j<3?0x28+4*j:0x38;if(!equalword(word(*field(&actual.r,at)),word(*field(&expected.r,at))))return 1;*field(&actual.r,at)=*field(&expected.r,at);}
 if(!equalword(word(*rate),r->output[6])||!equalword(word(*step),r->output[7]))return 1;
 for(j=0;j<sizeof(actual);j++)if(p[j]!=q[j])return 1;
 for(j=0;j<n;j++)for(k=0;k<12;k++)if(k<4||k==9){if(!equalword(packets[j][k],r->packets[j][k]))return 1;}else if(packets[j][k]!=r->packets[j][k])return 1;
 }return 0;}
static int run(void){if(sizeof(void*)!=4)return 99;if(variant(selected,0)||variant(selected,1))return 1;
'''
    for i,name in enumerate(controls):text+='if(variant(%s,0)!=1)return %d;\n'%(name,i+2)
    return text+'return 0;}\n'+START
