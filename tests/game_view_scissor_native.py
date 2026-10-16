"""Native32 SDK caller and the actual recovered clamp in separate C units."""
from tools.experiments import game_view_scissor_setup as source
from tools.tests import game_view_scissor_oracle as model

HEADER='''#include <ultra64.h>
typedef struct {u8 padding0[12];f32 extentX,extentY;u8 padding14[16];
 f32 top,bottom,left,right;u8 padding34[56];f32 baseFovX,baseFovY;u8 padding74[268];} ViewProjection476D0;
typedef union {u32 words[64];s32 signed_words[64];Gfx commands[32];} ScissorGlobals;
typedef union {u32 words[768];ViewProjection476D0 views[8];} ScissorViews;
typedef union {u32 words[32];Gfx commands[16];} ScissorOutput;
extern ScissorGlobals globals;extern ScissorViews records;extern ScissorOutput output;
#define D_800BE620 globals.signed_words[8]
#define D_800BE624 globals.signed_words[9]
#define D_800BE628 globals.signed_words[10]
#define VIEW_PROJECTIONS_476D0 ((ViewProjection476D0 *)D_800BE628)
void func_1501AF44(f32*,f32*,f32*,f32*);
s32 func_1501A490(Gfx*,s16,s32,s32,s32,s32);
'''


def cases():
    for memory,args,spec in model.corpus():
        final,observations,writes,complete,result=model.reference(memory,args)
        view=model.half(args[1])
        if not complete or view!=255 and not -2<=view<=3:continue
        if not any(base<=args[0] and args[0]+16<=base+size for base,size in model.REGIONS):continue
        patches=[]
        for address in sorted(set(writes)):
            index=0
            for base,size in model.REGIONS:
                if base<=address<base+size:break
                index+=size//4
            else:raise AssertionError('Unmapped native scissor output')
            patches.append((index+(address-base)//4,model.read(final,address)))
        assert len(patches)==4
        yield args,spec,patches


def program():
    rows=[]
    for args,(width,height,coords),patches in cases():
        values=(*args,width&0xFFFFFFFF,height&0xFFFFFFFF,*coords)
        rows.append('{{%s},{%s}}'%(','.join('0x%Xu'%x for x in values),','.join('{%d,0x%Xu}'%p for p in patches)))
    return HEADER+'''
struct Change{u32 index,value;};struct Case{u32 args[12];struct Change patch[4];};
static const struct Case cases[]={'''+',\n'.join(rows)+'''};
ScissorGlobals globals;ScissorViews records;ScissorOutput output;
static u32 before[864];
static void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static u32 pointer(u32 a){
 if(a>=0x800BE600u&&a<=0x800BE700u)return (u32)&globals+a-0x800BE600u;
 if(a>=0x2FD00u&&a<=0x30900u)return (u32)&records+a-0x2FD00u;
 if(a>=0x20000u&&a<=0x20080u)return (u32)&output+a-0x20000u;
 die(29);return 0;}
static u32 word(u32 i){if(i<64)return globals.words[i];if(i<832)return records.words[i-64];return output.words[i-832];}
static void run(void){u32 n,i,j,row,wanted,result;const struct Case*c;
 if(sizeof(void*)!=4||sizeof(ViewProjection476D0)!=384||sizeof(Gfx)!=8||
  __builtin_offsetof(ViewProjection476D0,top)!=0x24||__builtin_offsetof(ViewProjection476D0,bottom)!=0x28||
  __builtin_offsetof(ViewProjection476D0,left)!=0x2C||__builtin_offsetof(ViewProjection476D0,right)!=0x30)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];
  for(i=0;i<64;i++)globals.words[i]=0xA5A5A5A5u;
  for(i=0;i<768;i++)records.words[i]=0xA5A5A5A5u;
  for(i=0;i<32;i++)output.words[i]=0xA5A5A5A5u;
  D_800BE620=(s32)c->args[6];D_800BE624=(s32)c->args[7];D_800BE628=(s32)&records.views[2];
  row=(u32)(2+(s16)c->args[1]);if((s16)c->args[1]!=255){
   records.words[row*96+11]=c->args[8];records.words[row*96+9]=c->args[9];
   records.words[row*96+12]=c->args[10];records.words[row*96+10]=c->args[11];}
  for(i=0;i<864;i++)before[i]=word(i);
  result=(u32)func_1501A490((Gfx*)pointer(c->args[0]),(s16)c->args[1],(s32)c->args[2],(s32)c->args[3],(s32)c->args[4],(s32)c->args[5]);
  if(result!=pointer(c->args[0]+16))die(22);
  for(i=0;i<864;i++){wanted=before[i];for(j=0;j<4;j++)if(c->patch[j].index==i)wanted=c->patch[j].value;
   if(word(i)!=wanted)die(21);}
 }}
void _start(void){run();die(0);}
'''


def controls():
    body=source.SELECTED
    return dict(byte_view=body.replace('view == 0xFF','(u8)view == 0xFF'),
        wrong_record=body.replace('VIEW_PROJECTIONS_476D0[view]','VIEW_PROJECTIONS_476D0[view+1]'),
        wrong_limit=body.replace('(f32)bottomLimit <','(f32)bottomLimit >'),
        wrong_border=body.replace('(u32)D_800BE620 - 2','(u32)D_800BE620 - 1'),
        missing_advance=body.replace('gDPPipeSync(commands++);','gDPPipeSync(commands);'),
        wrong_quantization=body.replace('gDPSetScissor(', 'gDPSetScissorFrac('),
        swapped_clamp=body.replace('func_1501AF44(&left, &top, &right, &bottom);','func_1501AF44(&top, &left, &right, &bottom);'))
