"""Native32 complete color body/caller with typed lanes and byte-bank canaries."""
import itertools

from tools.tests import game_color_state_submit_oracle as model


def header(mode_type='s8'):
    return '''#include <ultra64.h>
#include "structs.h"
struct Bank{u32 pre;u8 bytes[0xB0];u32 post;};extern struct Bank bank;
extern u8 *p_colors,*p_busy;extern s8 *p_modes,*slots;extern s32 *p_ticks,*p_limits;
void func_1517EE40(s32,s32,s32,s32,%s,s32);
void func_15172CA8(s32);
'''%mode_type


MACROS='''#define D_800DDDA0 p_colors
#define D_800DDDAC p_modes
#define D_800DDDB0 p_ticks
#define D_800DDDC0 p_busy
#define D_800DDE28 p_limits
#define D_800DD2B0 slots
'''


def cases():
    for channel,mode,timing,busy in itertools.product(range(4),(-128,-1,0,1,127),(0,4,5),(0,255)):
        yield 0,model.fixture(channel,mode,mode,model.TIMES[timing],busy,-1,model.RGB[2])
    for alias,channel,mode in itertools.product((3,4),range(4),(-128,-1,0,1,127)):
        yield 0,model.fixture(channel,mode,mode,(0,1),255,0x7FFFFFFF,model.RGB[2],alias)
    for channel,state,mode,alias in itertools.product(range(4),(-128,-1,0,1,127),(0,1),(0,3,4)):
        yield 1,model.fixture(channel,mode,mode,(1,0),0,7,model.RGB[2],alias,state)


def program(mode_type='s8'):
    initial=[];final=[];slot_initial=[];slot_final=[];rows=[]
    for kind,(memory,args,g) in cases():
        wanted=model.reference(memory,args,g)[0] if kind==0 else model.pair_reference(memory,args[5],g)[0]
        init=len(initial);slot_init=len(slot_initial)
        initial.extend(memory[model.BASE+i] for i in range(model.LENGTH));final.extend(wanted[model.BASE+i] for i in range(model.LENGTH))
        slot_initial.extend(memory[model.SLOTS+i] for i in range(16));slot_final.extend(wanted[model.SLOTS+i] for i in range(16))
        rows.append('{%d,{%s},{%s},%d,%d}'%(kind,','.join('0x%Xu'%v for v in args),
            ','.join(str(g[name]-model.BASE) for name in model.NAMES),init,slot_init))
    text=header(mode_type)+'''
struct Bank bank;static struct Bank wanted;
u8*p_colors,*p_busy;s8*p_modes,*slots;s32*p_ticks,*p_limits;
static u8 slot_storage[24],wanted_slots[24];
struct Case{u32 kind,args[6],offsets[5],initial,slots;};
'''
    text+='static const u8 initial[]={'+','.join(str(v) for v in initial)+'};\n'
    text+='static const u8 final[]={'+','.join(str(v) for v in final)+'};\n'
    text+='static const u8 slot_initial[]={'+','.join(str(v) for v in slot_initial)+'};\n'
    text+='static const u8 slot_final[]={'+','.join(str(v) for v in slot_final)+'};\n'
    text+='static const struct Case cases[]={'+','.join(rows)+'};\n'
    return text+HARNESS.replace('MODE_TYPE',mode_type)


HARNESS=r'''
static __attribute__((noreturn)) void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void fill(void*p,u32 n){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=0xA5;}
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static u32 big(const u8*p){return ((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
static void lanes(struct Bank*b,const u8*input,const struct Case*c){u32 k,i,at;
 for(k=2;k<=4;k+=2)for(i=0;i<4;i++){at=c->offsets[k]+i*4;*(u32*)(b->bytes+at)=big(input+at);}
}
void _start(void){u32 n,i;const struct Case*c;const u8*a,*b;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  c=&cases[n];fill(&bank,sizeof(bank));fill(slot_storage,sizeof(slot_storage));
  copy(bank.bytes,initial+c->initial,0xB0);lanes(&bank,initial+c->initial,c);
  copy(&wanted,&bank,sizeof(bank));copy(wanted.bytes,final+c->initial,0xB0);lanes(&wanted,final+c->initial,c);
  copy(slot_storage+4,slot_initial+c->slots,16);copy(wanted_slots,slot_storage,sizeof(slot_storage));copy(wanted_slots+4,slot_final+c->slots,16);
  p_colors=bank.bytes+c->offsets[0];p_modes=(s8*)(bank.bytes+c->offsets[1]);p_ticks=(s32*)(bank.bytes+c->offsets[2]);
  p_busy=bank.bytes+c->offsets[3];p_limits=(s32*)(bank.bytes+c->offsets[4]);slots=(s8*)slot_storage+4;
  if(c->kind==0)func_1517EE40((s32)c->args[0],(s32)c->args[1],(s32)c->args[2],(s32)c->args[3],(MODE_TYPE)c->args[4],(s32)c->args[5]);
  else func_15172CA8((s32)c->args[5]);
  a=(const u8*)&bank;b=(const u8*)&wanted;for(i=0;i<sizeof(bank);i++)if(a[i]!=b[i])die(22);
  for(i=0;i<sizeof(slot_storage);i++)if(slot_storage[i]!=wanted_slots[i])die(22);
 }
 die(0);
}
'''
