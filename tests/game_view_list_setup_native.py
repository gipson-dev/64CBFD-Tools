"""Actual SDK C in native32 arenas, including live table/buffer overlaps."""
from tools.experiments import game_view_list_setup as source
from tools.tests import game_view_list_setup_oracle as model

HEADER = '''#include <ultra64.h>
typedef union {u32 words[256];s32 signed_words[256];Gfx commands[128];} ListGlobals;
typedef union {u32 words[2048];Gfx commands[1024];} ListBuffers;
extern ListGlobals globals;extern ListBuffers buffers;extern Gfx D_8002C930[8];
#define D_800BE9C8 (globals.signed_words+242)
#define D_800BE9D8 (globals.signed_words+246)
#define D_800BE9E0 globals.signed_words[248]
#define D_800BE9C4 globals.signed_words[241]
#define D_800BE628 globals.signed_words[10]
void func_1501A39C(void);
'''


def indexed(memory):
    return [model.read(memory,base+i) for base,size in model.REGIONS for i in range(0,size,4)]


def program():
    cases = []
    for memory,args in model.corpus():
        for value in args[2:]:
            assert not any(base<=value<=base+size for base,size in model.REGIONS)
            assert value not in (model.DISPLAY+64,model.DISPLAY+80)
        before,after = indexed(memory),indexed(model.reference(memory))
        changes = [(i,b) for i,(a,b) in enumerate(zip(before,after)) if a!=b]
        assert len(changes)<=24
        cases.append('{{%s},%d,{%s}}'%(','.join('0x%Xu'%a for a in args),len(changes),
            ','.join('{%d,0x%Xu}'%item for item in changes)))
    return HEADER+'''
struct Change {u32 index,value;};
struct Case {u32 args[4],changes;struct Change patch[24];};
static const struct Case cases[]={'''+',\n'.join(cases)+'''};
ListGlobals globals;ListBuffers buffers;Gfx D_8002C930[8];
static u32 before[2320];
static void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void mismatch(u32 n,u32 index,u32 wanted,u32 actual){
 const char digits[]="0123456789ABCDEF";u32 values[4]={n,index,wanted,actual},i,j,result=4;char line[36];
 for(i=0;i<4;i++){for(j=0;j<8;j++)line[i*9+j]=digits[(values[i]>>(28-j*4))&15];line[i*9+8]=' ';}
 line[35]=10;__asm__ volatile("int $0x80":"+a"(result):"b"(2),"c"(line),"d"(36):"memory","cc");die(21);}
static u32 translate(u32 value){
 if(value>=0x800BE600u&&value<=0x800BEA00u)return (u32)&globals+value-0x800BE600u;
 if(value>=0x20000u&&value<=0x22000u)return (u32)&buffers+value-0x20000u;
 /* A live view-base alias can hold the SDK list symbol before adding 64/80. */
 if((value>=0x8002C930u&&value<=0x8002C970u)||value==0x8002C980u)
  return (u32)D_8002C930+value-0x8002C930u;
 return value;}
static u32 word(u32 index){if(index<256)return globals.words[index];
 if(index<2304)return buffers.words[index-256];return ((u32*)D_8002C930)[index-2304];}
static void run(void){u32 n,i,j,wanted;const struct Case*c;
 if(sizeof(void*)!=4||sizeof(Gfx)!=8||sizeof(globals)!=1024||sizeof(buffers)!=8192)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];
  for(i=0;i<256;i++)globals.words[i]=0xA5A5A5A5u;
  for(i=0;i<2048;i++)buffers.words[i]=0xA5A5A5A5u;
  for(i=0;i<16;i++)((u32*)D_8002C930)[i]=0xA5A5A5A5u;
  D_800BE9C8[0]=(s32)translate(c->args[0]);D_800BE9C8[1]=(s32)translate(c->args[1]);
  D_800BE9C4=(s32)c->args[2];D_800BE628=(s32)c->args[3];
  for(i=0;i<2320;i++)before[i]=word(i);
  func_1501A39C();
  for(i=0;i<2320;i++){wanted=before[i];for(j=0;j<c->changes;j++)
   if(c->patch[j].index==i)wanted=translate(c->patch[j].value);
   if(word(i)!=wanted)mismatch(n,i,wanted,word(i));}
 }}
void _start(void){run();die(0);}
'''


def controls():
    body = source.SELECTED
    return dict(one_row=body.replace('output != &D_800BE9E0','output != D_800BE9D8+1'),
        wrong_view_stride=body.replace('viewportOffset += 0x10','viewportOffset += 0x180'),
        wrong_segment=body.replace('gSPSegment(commands++, 0, 0);','gSPSegment(commands++, 1, 0);',1),
        wrong_display=body.replace('D_8002C930);','D_8002C930+1);'),
        wrong_publication=body.replace('*output++ = (s32)commands;','*output++ = (s32)(commands-1);'),
        cached_depth=body.replace('    s32 *input;', '    s32 cachedDepth = D_800BE9C4;\n    s32 *input;').replace(
            'gDPSetDepthImage(commands++, D_800BE9C4);','gDPSetDepthImage(commands++, cachedDepth);'),
        cached_views=body.replace('    s32 *input;', '    u32 cachedViews = (u32)D_800BE628;\n    s32 *input;').replace(
            '(u32)D_800BE628 + viewportOffset','cachedViews + viewportOffset'))
