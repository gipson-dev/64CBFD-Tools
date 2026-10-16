"""Native32 C over one valid memory union with big-endian byte-label views."""
from tools.experiments import game_frame_timing_update as source
from tools.tests import game_frame_timing_oracle as model

HEADER='''#include <ultra64.h>
typedef union {u32 words[276];s32 signed_words[276];f32 floats[276];u8 bytes[1104];} TimingMemory;
extern TimingMemory timing_memory;
extern const f32 D_800968D0;
void func_15019F20(void);
s32 func_150A019C(void);
'''
for address in (model.PHASE,model.INDEX,model.SAMPLES,model.HALF,model.DIVISOR):
    HEADER+='#define D_%08X timing_memory.bytes[%d]\n'%(address,(address-model.BASE)^3)
for address in (model.REMAINDER,model.TOTAL):
    HEADER+='#define D_%08X timing_memory.words[%d]\n'%(address,(address-model.BASE)//4)
for address in (model.TICKS,model.SNAPSHOT,model.MOD):
    HEADER+='#define D_%08X timing_memory.signed_words[%d]\n'%(address,(address-model.BASE)//4)
for address in (model.TIME,model.INV,model.MEAN,model.MEAN_INV):
    HEADER+='#define D_%08X timing_memory.floats[%d]\n'%(address,(address-model.BASE)//4)
HEADER+='#define D_800BE5E8 (timing_memory.floats+6)\n'


def program():
    literal=lambda values:'{'+','.join('0x%Xu'%v for v in values)+'}'
    rows=[];maximum=0
    for initial,mode,args in model.corpus():
        final,_,observations=model.reference(initial,mode)
        changes=['{%d,0x%Xu}'%(i,model.read(final,model.BASE+i*4)) for i in range(276)
            if model.read(initial,model.BASE+i*4)!=model.read(final,model.BASE+i*4)]
        maximum=max(maximum,len(changes));assert len(changes)<=16
        rows.append('{%s,%d,0x%Xu,%d,{%s}}'%(literal(args),mode,observations[0],len(changes),','.join(changes)))
    histories=','.join(literal(model.hist(i)) for i in range(6))
    return HEADER+'''
struct Change{u32 index,value;};
struct Case{u32 args[8],mode,observation,changes;struct Change patch[16];};
static const struct Case cases[]={'''+','.join(rows)+'''};
static const u32 histories[6][10]={'''+histories+'''};
TimingMemory timing_memory;const f32 D_800968D0=0.1f;
static const struct Case*c;static u32 calls,before[276];
static void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static u32 digest(void){u32 i,value=2166136261u;
 for(i=0;i<276;i++)value=(value^timing_memory.words[i])*16777619u;return value;}
s32 func_150A019C(void){calls++;if(calls!=1)die(21);
 if(digest()!=c->observation)die(22);
 if(c->mode==1){D_800BE9E4=(s32)0x87654321u;timing_memory.words[251]=0x80000000u;}
 if(c->mode==2){D_800BE619=255;D_800BE61A=0;}
 return (s32)0xDEADBEEFu;}
static void run(void){u32 n,i,j,wanted;
 if(sizeof(void*)!=4||sizeof(TimingMemory)!=1104||sizeof(f32)!=4)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];calls=0;
  for(i=0;i<276;i++)timing_memory.words[i]=0xA5A5A5A5u;
  D_800BE9E4=(s32)c->args[0];D_800BEA0C=(u8)c->args[1];D_800BE610=c->args[2];
  D_800BE5E0=(u8)c->args[3];D_800BE619=(u8)c->args[4];D_800BE61A=(u8)c->args[5];
  D_800BE9AC=c->args[7];D_800BEA08=(s32)0x87654321u;
  timing_memory.words[245]=0x80000000u;timing_memory.words[246]=0x3E800000u;
  timing_memory.words[250]=0xBF800000u;timing_memory.words[251]=0x3F800000u;
  D_800BE9B0=(s32)0xDEADBEEFu;D_800BE9A0=0xA5;
  for(i=0;i<10;i++)timing_memory.words[6+i]=histories[c->args[6]][i];
  for(i=0;i<276;i++)before[i]=timing_memory.words[i];
  func_15019F20();if(calls!=1)die(23);
  for(i=0;i<276;i++){wanted=before[i];
   for(j=0;j<c->changes;j++)if(c->patch[j].index==i)wanted=c->patch[j].value;
   if(timing_memory.words[i]!=wanted)die(24);}
 }}
void _start(void){run();die(0);}
'''


def controls():
    body=source.SELECTED
    return dict(ordinary_remainder=body.replace('((u32)D_800BE9E4 * total)','((u32)D_800BE9E4 * divisor)'),
        unmasked_phase=body.replace('    D_800BE5E0 &= 1;',''),
        wrong_history_page=body.replace('D_800BE5E8[historyIndex]','D_800BE5E8[historyIndex ^ 1]'),
        unsigned_modulo=body.replace('(s32)D_800BE9AC % 30','D_800BE9AC % 30'),
        normalize_negative_zero_mean=body.replace('            D_800BE9BC = 0.0f;','            D_800BE9B8 = 0.0f;\n            D_800BE9BC = 0.0f;'),
        cached_samples=body.replace('void func_15019F20(void) {','void func_15019F20(void) {\n    u8 initialSamples = D_800BE61A;').replace('D_800BE61A < 10','initialSamples < 10'),
        uncached_history_index=body.replace('D_800BE619 = historyIndex + 1;','D_800BE619++;'),
        dropped_callback=body.replace('    func_150A019C();',''),
        reverse_sum=body.replace('for (i = 0; i < 10; i++)','for (i = 9; i >= 0; i--)'),
        wrong_mean_factor=body.replace('sum * D_800968D0','sum * 0.2f'))
