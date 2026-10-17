"""Native32 signed/wrapped progress plus complete predicate and renderer wrappers."""
import itertools

from tools.tests import game_color_progress_oracle as model

HEADER='''#include <ultra64.h>
struct Bank{u32 pre;u8 bytes[0xB0];u32 post;};extern struct Bank bank;
extern u8 *p_busy,*p_colors;extern s8 *p_modes;extern s32 *p_ticks,*p_limits;
s32 func_1517EF00(s32);s32 func_1517EFAC(s32);s32 func_1517F3A0(s32,s32);
s32 func_1517F08C(s32,s32,s32,s32,s32,s32);
'''
MACROS='''#define D_800DDDC0 p_busy
#define D_800DDDAC p_modes
#define D_800DDDB0 p_ticks
#define D_800DDE28 p_limits
#define D_800DDDA0 p_colors
'''
PAIRS=((0,0),(0,1),(1,1),(-1,1),(-0x80000000,1),(0x7FFFFFFF,-1),
    (8421504,1),(8421505,1),(-1,-1),(-0x80000000,0),(0x7FFFFFFF,-0x80000000))


def cases():
    for channel,timing,mode,busy in itertools.product(range(4),PAIRS,model.MODES,(0,1,255)):
        yield model.fixture(channel,*timing,mode,busy)
    for channel,alias,timing,mode,busy in itertools.product(range(4),(1,2,3),((0,0),(-1,1)),(0,127),(0,255)):
        yield model.fixture(channel,*timing,mode,busy,alias)


def program():
    initial=[];rows=[]
    for memory,args,g in cases():
        wanted,trap=model.reference(memory,args[0],g)
        assert trap is None
        at=len(initial);initial.extend(memory[model.BASE+i] for i in range(model.LENGTH))
        colors=[memory[model.previous.GLOBALS['colors']+args[0]*3+i] for i in range(3)]
        rows.append('{{%s},%s,%d,0x%Xu,{%s}}'%(','.join(str(g[n]-model.BASE) for n in model.NAMES),
            str(args[0]),at,wanted,','.join(map(str,colors))))
    return HEADER+'''
struct Bank bank;static struct Bank saved;
u8*p_busy,*p_colors;s8*p_modes;s32*p_ticks,*p_limits;
static u32 calls,packet[6];
struct Case{u32 offsets[4],channel,initial,wanted,colors[3];};
'''+ 'static const u8 initial[]={'+','.join(map(str,initial))+'};\n'+ \
        'static const struct Case cases[]={'+','.join(rows)+'};\n'+HARNESS


HARNESS=r'''
static __attribute__((noreturn)) void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void fill(void*p,u32 n){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=0xA5;}
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static u32 big(const u8*p){return ((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
s32 func_1517F08C(s32 a,s32 b,s32 c,s32 d,s32 e,s32 f){
 calls++;packet[0]=a;packet[1]=b;packet[2]=c;packet[3]=d;packet[4]=e;packet[5]=f;return 0x13579BDF;
}
void _start(void){u32 n,i,k,kind,at,value,wanted;const struct Case*c;const u8*a,*b;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  c=&cases[n];fill(&bank,sizeof(bank));copy(bank.bytes,initial+c->initial,0xB0);
  for(k=1;k<=2;k++)for(i=0;i<4;i++){at=c->offsets[k]+i*4;*(u32*)(bank.bytes+at)=big(initial+c->initial+at);}
  copy(&saved,&bank,sizeof(bank));p_busy=bank.bytes+c->offsets[0];p_limits=(s32*)(bank.bytes+c->offsets[1]);
  p_ticks=(s32*)(bank.bytes+c->offsets[2]);p_modes=(s8*)(bank.bytes+c->offsets[3]);p_colors=bank.bytes+0x10;
  for(kind=0;kind<3;kind++){
   calls=0;fill(packet,sizeof(packet));
   if(kind==0){value=func_1517EF00((s32)c->channel);wanted=c->wanted;}
   else if(kind==1){value=func_1517EFAC((s32)c->channel);wanted=c->wanted==255;}
   else{value=func_1517F3A0(0x12345678,(s32)c->channel);wanted=c->wanted?0x13579BDF:0x12345678;}
   if(value!=wanted)die(22);
   if(kind==2&&c->wanted){
    if(calls!=1||packet[0]!=0x12345678||packet[1]!=c->wanted||packet[5]!=c->channel)die(22);
    for(i=0;i<3;i++)if(packet[2+i]!=c->colors[i])die(22);
   }else if(calls)die(22);
   a=(const u8*)&bank;b=(const u8*)&saved;for(i=0;i<sizeof(bank);i++)if(a[i]!=b[i])die(22);
  }
 }
 die(0);
}
'''
