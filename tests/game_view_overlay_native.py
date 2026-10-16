"""Separate-unit native32 SDK source with a real 256-word page table."""
from tools.experiments import game_view_overlay_pass as source
from tools.tests import game_view_overlay_oracle as model

HEADER='''#include <ultra64.h>
extern s32 D_800BE628,D_800BE9F0;
extern u8 D_800BE9C0;
extern Mtx D_80089470;
extern u32 page_table[256];
#define D_800DC2A0 page_table[0]
s32 func_15019CC8(Gfx *,s32);
s32 func_1501A490(s32,s16,s32,s32,s32,s32);
Gfx *func_1502BAD0(Gfx *,s32,s16);
void *func_151674F8(void *,s32,s16,s32);
'''


def corpus():
    return (case for case in model.corpus() if case[3]!=5)


def program():
    literal=lambda values:'{'+','.join('0x%Xu'%v for v in values)+'}'
    rows=[]
    for initial,view,pattern,mode in corpus():
        final,calls,observations,_,result=model.reference(initial,view,pattern,mode)
        packets=['{0x%Xu,%s,%s,0x%Xu}'%(target,literal((*args,*([0]*(6-len(args))))),
            literal(state),model.returned(target,args,1 if target!=model.MODE_PASS else args[3]+1,pattern))
            for (target,args),(_,state) in zip(calls,observations)]
        changes=['{%d,0x%Xu}'%(i,model.read(final,0x50000+i*4)) for i in range(1024)
            if model.read(initial,0x50000+i*4)!=model.read(final,0x50000+i*4)]
        assert len(changes)==10 and len(calls)<=4
        rows.append('{0x%Xu,%d,%s,%s,0x%Xu,%d,{%s},{%s}}'%(view,mode,
            literal(model.snapshot(initial)),literal(model.snapshot(final)),result,len(calls),','.join(packets),','.join(changes)))
    return HEADER+'''
struct Packet{u32 target,args[6],state[4],result;};
struct Change{u32 index,value;};
struct Case{u32 view,mode,initial[4],final[4],result,count;struct Packet packets[4];struct Change patch[10];};
static const struct Case cases[]={'''+','.join(rows)+'''};
s32 D_800BE628,D_800BE9F0;u8 D_800BE9C0;Mtx D_80089470;u32 page_table[256];
static Gfx storage[512];static const struct Case*c;static u32 cursor,mode_ordinal;
static void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static u32 canon(u32 value){u32 base=(u32)storage;
 if(value>=base&&value<base+sizeof(storage))return 0x50000u+value-base;
 if(value==(u32)&D_80089470)return 0x80089470u;return value;}
static u32 uncanon(u32 value){if(value>=0x50000u&&value<0x51000u)return (u32)storage+value-0x50000u;return value;}
static u32 buffer_hash(void){u32 i,value=2166136261u;for(i=0;i<128;i++){
 u32 word=canon((i&1)?storage[i/2].words.w1:storage[i/2].words.w0);value=(value^word)*16777619u;}return value;}
static u32 get(u32 field){switch(field){case 0:return (u32)D_800BE628;case 1:return D_800BE9C0;
 case 2:return (u32)D_800BE9F0;case 3:return buffer_hash();}die(29);return 0;}
static void effect(u32 target,u32 ordinal){
 if(c->mode==1&&target==0x1501A490u){D_800BE628=(s32)0x80507FFCu;D_800BE9C0=255;D_800BE9F0=0x1D;}
 if(c->mode==2&&target==0x1501A490u){D_800BE9F0=0x1001D;D_800BE9C0=128;}
 if(c->mode==3&&target==0x151674F8u&&ordinal==2){D_800BE628=(s32)0xFFFFFF80u;D_800BE9C0=1;page_table[1]=0x12348004u;}
 if(c->mode==4&&target==0x151674F8u&&ordinal==1){D_800BE628=(s32)0x81718004u;D_800BE9C0=128;}}
static u32 notify(u32 target,u32 a,u32 b,u32 d,u32 e,u32 f,u32 g){u32 i,ordinal=1;const struct Packet*p;
 u32 args[6]={a,b,d,e,f,g};if(cursor>=c->count)die(21);p=&c->packets[cursor++];
 if(p->target!=target)die(21);for(i=0;i<6;i++)if(args[i]!=p->args[i])die(21);
 for(i=0;i<4;i++)if(get(i)!=p->state[i])die(22);
 if(target==0x151674F8u)ordinal=++mode_ordinal;effect(target,ordinal);return p->result;}
s32 func_1501A490(s32 a,s16 b,s32 d,s32 e,s32 f,s32 g){return (s32)uncanon(notify(0x1501A490u,canon((u32)a),(u32)b,(u32)d,(u32)e,(u32)f,(u32)g));}
Gfx *func_1502BAD0(Gfx*a,s32 b,s16 d){return (Gfx*)uncanon(notify(0x1502BAD0u,canon((u32)a),(u32)b,(u32)d,0,0,0));}
void *func_151674F8(void*a,s32 b,s16 d,s32 e){return (void*)uncanon(notify(0x151674F8u,canon((u32)a),(u32)b,(u32)d,(u32)e,0,0));}
static void run(void){u32 n,i,j,k,word,value;
 if(sizeof(void*)!=4||sizeof(Gfx)!=8||sizeof(page_table)!=1024)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];cursor=mode_ordinal=0;
  for(i=0;i<256;i++)page_table[i]=0x81200000u+i*0x1000;
  for(i=0;i<512;i++)storage[i].words.w0=storage[i].words.w1=0xA5A5A5A5u;
  D_800BE628=(s32)c->initial[0];D_800BE9C0=(u8)c->initial[1];D_800BE9F0=(s32)c->initial[2];
  if(canon((u32)func_15019CC8(storage+4,(s32)c->view))!=c->result)die(23);
  if(cursor!=c->count)die(24);for(i=0;i<4;i++)if(get(i)!=c->final[i])die(25);
  for(i=0;i<512;i++)for(j=0;j<2;j++){word=i*2+j;value=0xA5A5A5A5u;
   for(k=0;k<10;k++)if(c->patch[k].index==word)value=c->patch[k].value;
   if(canon(j?storage[i].words.w1:storage[i].words.w0)!=value)die(26);}
  for(i=0;i<256;i++)if(page_table[i]!=(c->mode==3&&i==1?0x12348004u:0x81200000u+i*0x1000))die(27);
 }}
void _start(void){run();die(0);}
'''


def controls():
    body=source.SELECTED
    return dict(narrow_address_view=body.replace('    s32 narrowedView;','    s32 narrowedView;\n    view = (s16)view;'),
        lost_helper_sign=body.replace('narrowedView = (s16)view;','narrowedView = view & 0x7FFF;'),
        low_half_category=body.replace('D_800BE9F0 == 0x1D','(u16)D_800BE9F0 == 0x1D'),
        wrong_view_argument=body.replace('commands, 5, 0,','commands, 5, narrowedView,'),
        wrong_matrix_mode=body.replace('G_MTX_PROJECTION | G_MTX_MUL','G_MTX_PROJECTION | G_MTX_LOAD'),
        wrong_table_page=body.replace('[D_800BE9C0]','[D_800BE9C0 ^ 1]'),
        cached_page=body.replace('    s32 narrowedView;','    s32 narrowedView;\n    u8 page = D_800BE9C0;').replace('D_800BE9C0 *','page *').replace('[D_800BE9C0]','[page]'),
        lost_return=body.replace('return (s32)commands;','return (s32)(commands - 1);'))
