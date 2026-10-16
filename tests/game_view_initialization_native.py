"""Actual native32 C with callback snapshots and full public-region canaries."""
from tools.experiments import game_view_initialization as source
from tools.tests import game_view_initialization_oracle as model

HEADER = '''#include <ultra64.h>
typedef union {u32 words[64];s32 signed_words[64];f32 floats[64];u8 bytes[256];} InitMemory;
typedef struct {u8 bytes[384];} ViewProjection476D0;
extern InitMemory init_memory;
extern s32 D_80082FA0,D_800BE9F0;
extern const f32 D_800968E0;
s32 allocate_memory(s32,s32,s32,s32);
void func_150006E0(s32);
s32 func_1501A8C0(s32,s32,s32,s32);
void func_1510B070(s32);
void func_1501A220(s32,s32);
'''
for name,address in (('D_800BE628',model.FIRST),('D_800BE62C',model.SECOND)):
    HEADER += '#define %s init_memory.signed_words[%d]\n'%(name,(address-model.BASE)//4)
HEADER += '#define D_800BE63C (init_memory.signed_words+15)\n#define D_800BE6B8 init_memory.floats[46]\n'
for address in model.FLAGS:
    HEADER += '#define D_%08X init_memory.bytes[%d]\n'%(address,(address-model.BASE)^3)


def words(memory):
    return [model.read(memory,model.COUNT),model.read(memory,model.CATEGORY)] + [
        model.canonical(model.read(memory,model.BASE+i)) if model.BASE+i==model.BIAS else model.read(memory,model.BASE+i)
        for i in range(0,model.LENGTH,4)]


def program():
    cases,calls = [],[]
    for initial,count,projection,mode in model.corpus():
        final,events,observations,complete = model.reference(initial,count,projection,mode)
        assert complete
        before,after = words(initial),words(final)
        changes = [(i,b) for i,(a,b) in enumerate(zip(before,after)) if a!=b]
        assert len(changes)<=12
        start = len(calls)
        for (target,args),observation in zip(events,observations):
            calls.append('{0x%Xu,%d,{%s},0x%Xu}'%(target,len(args),','.join('0x%Xu'%v for v in args),observation))
        patches = ','.join('{%d,0x%Xu}'%item for item in changes)
        cases.append('{{0x%Xu,0x%Xu,0x%Xu,%d},%d,%d,%d,{%s}}'%(
            count&0xFFFFFFFF,model.read(initial,model.HEIGHT),projection,mode,start,len(events),len(changes),patches))
    return HEADER+'''
struct Change{u32 index,value;};
struct Case{u32 args[4],start,calls,changes;struct Change patch[12];};
struct Call{u32 target,argc,args[4],digest;};
static const struct Case cases[]={'''+','.join(cases)+'''};
static const struct Call calls[]={'''+','.join(calls)+'''};
InitMemory init_memory;s32 D_80082FA0,D_800BE9F0;const f32 D_800968E0=0.8f;
static const struct Case*c;static u32 next_call,allocations,views,before[66];
static void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static u32 canonical(u32 value){return (value&0x7F800000u)==0x7F800000u&&(value&0x7FFFFFu)?0x7FC00000u:value;}
static u32 word(u32 i){if(i==0)return (u32)D_80082FA0;if(i==1)return (u32)D_800BE9F0;
 return i==48?canonical(init_memory.words[46]):init_memory.words[i-2];}
static u32 digest(void){u32 i,value=2166136261u;for(i=0;i<66;i++)value=(value^word(i))*16777619u;return value;}
static void observe(u32 target,u32 argc,u32 a,u32 b,u32 d,u32 e){
 const struct Call*x;u32 args[4]={a,b,d,e},i;
 if(next_call>=c->calls)die(21);x=&calls[c->start+next_call++];
 if(x->target!=target||x->argc!=argc)die(21);
 for(i=0;i<argc;i++)if(x->args[i]!=args[i])die(21);
 if(x->digest!=digest())die(22);}
s32 allocate_memory(s32 size,s32 tag,s32 pool,s32 flags){
 u32 mode=c->args[3];observe(0x10003C40u,4,(u32)size,(u32)tag,(u32)pool,(u32)flags);allocations++;
 if(mode==1&&allocations==1){D_80082FA0=1;D_800BE63C[0]=7;D_800BE9F0=0x13579BDF;}
 if(mode==2&&allocations==2){D_80082FA0=0;D_800BE63C[0]=(s32)0x80000000u;}
 if(mode==8)return allocations==1?0:(s32)0xFFFF1234u;
 return (s32)(0x81400000u+allocations*0x1000u);}
void func_150006E0(s32 category){observe(0x150006E0u,1,(u32)category,0,0,0);
 if(c->args[3]==3)D_80082FA0=2;if(c->args[3]==7)D_80082FA0=1;
 if(c->args[3]==9)D_800BE628=(s32)0xDEADC0DEu;}
s32 func_1501A8C0(s32 index,s32 count,s32 mask,s32 flags){
 observe(0x1501A8C0u,4,(u32)index,(u32)count,(u32)mask,(u32)flags);views++;
 if(c->args[3]==4&&views<=2)D_80082FA0=views==1?3:0;
 if(c->args[3]==5&&views==1)D_80082FA0=-1;return (s32)0xB500A8C0u;}
void func_1510B070(s32 mode){observe(0x1510B070u,1,(u32)mode,0,0,0);
 if(c->args[3]==6){D_800BE617=0xA1;D_800BE614=0xB2;D_800BE635=0xC3;
  D_80082FA0=(s32)0x87654321u;init_memory.words[46]=0x80000000u;}}
static void run(void){u32 n,i,j,wanted;
 if(sizeof(void*)!=4||sizeof(InitMemory)!=256||sizeof(ViewProjection476D0)!=384)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];next_call=allocations=views=0;
  for(i=0;i<64;i++)init_memory.words[i]=0xA5A5A5A5u;
  D_80082FA0=(s32)c->args[0];D_800BE9F0=(s32)0x87654321u;
  D_800BE63C[0]=(s32)c->args[1];init_memory.words[46]=0xBF800000u;
  for(i=0;i<66;i++)before[i]=word(i);
  func_1501A220((s32)c->args[0],(s32)c->args[2]);if(next_call!=c->calls)die(23);
  for(i=0;i<66;i++){wanted=before[i];for(j=0;j<c->changes;j++)if(c->patch[j].index==i)wanted=c->patch[j].value;
   if(word(i)!=wanted)die(24);}
 }}
void _start(void){run();die(0);}
'''


def controls():
    body = source.SELECTED
    return dict(cached_loop=body.replace('index <= (viewCount = D_80082FA0)','index <= viewCount'),
        cached_height_gate=body.replace('if (D_80082FA0 == 1)','if (viewCount == 1)'),
        unsigned_remainder=body.replace('rounded - rounded % 4','rounded - (rounded & 3)'),
        dropped_extra=body.replace('if (viewCount != 0)','if (0)'),
        wrong_size=body.replace('sizeof(ViewProjection476D0)','0x100'),
        wrong_height=body.replace('(f32)D_800BE63C[0] - 2.0f','(f32)D_800BE63C[0]'),
        late_flags=body.replace('    D_800BE617 = 1;\n    D_800BE614 = 1;\n    D_800BE635 = 0;\n    func_1510B070(projectionMode);',
            '    func_1510B070(projectionMode);\n    D_800BE617 = 1;\n    D_800BE614 = 1;\n    D_800BE635 = 0;'))
